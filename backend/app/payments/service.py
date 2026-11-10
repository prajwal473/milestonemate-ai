from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from urllib.parse import urlsplit
from app.payments.errors import AmountMismatchError

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.models import Payment, PaymentEvent
from app.payments.errors import (
    InvalidPaymentStateError,
    PaymentNotFoundError,
    PaymentAuthorizationError,
    PayPalError,
)
from app.payments.state import (
    PaymentStatus,
    validate_transition,
)
from app.payments.paypal_client import PayPalClient
from app.payments.mock_client import MockPaymentClient
from app.services import audit, milestones, notifications


def _get_provider() -> str:
    """Return the configured payment provider."""

    mode = settings.payments_mode.lower()

    if mode == "mock":
        return "MOCK"

    if mode in {"paypal", "paypal_sandbox"}:
        return "PAYPAL"

    raise ValueError(f"Unsupported payment mode: {mode}")


def _get_payment_client(provider: str):
    """Create the configured payment client."""

    if provider == "MOCK":
        return MockPaymentClient()

    if provider == "PAYPAL":
        return PayPalClient()

    raise ValueError(f"Unsupported payment provider: {provider}")


def _restore_mock_order(payment: Payment) -> None:
    if payment.provider == "MOCK" and payment.paypal_order_id:
        MockPaymentClient.restore_order(payment.paypal_order_id, payment)


def _record_event(
    db: Session,
    payment: Payment,
    event_type: str,
    source: str,
    from_status: str | None = None,
    to_status: str | None = None,
    paypal_ref: str | None = None,
    details: dict | None = None,
) -> None:
    """Record a payment lifecycle event."""

    db.add(
        PaymentEvent(
            payment_id=payment.id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            source=source,
            paypal_ref=paypal_ref,
            details=details or {},
        )
    )


def _validate_provider_order(order: dict, payment: Payment) -> None:
    units = order.get("purchase_units", [])
    amount = units[0].get("amount", {}) if units else {}
    try:
        value = Decimal(str(amount.get("value")))
    except Exception as exc:
        raise AmountMismatchError("Provider order amount is invalid.") from exc
    if (
        amount.get("currency_code") != payment.currency
        or not value.is_finite()
        or value != payment.amount
    ):
        raise AmountMismatchError("Provider order amount or currency does not match payment.")


def _validate_amount_fields(amount: dict, payment: Payment) -> None:
    try:
        value = Decimal(str(amount.get("value")))
    except Exception as exc:
        raise AmountMismatchError("Provider amount is invalid.") from exc
    if (
        amount.get("currency_code") != payment.currency
        or not value.is_finite()
        or value != payment.amount
    ):
        raise AmountMismatchError("Provider amount or currency does not match payment.")


def _persist_amount_mismatch(
    db: Session, payment: Payment, actor_id: int | None, provider_ref: str | None
) -> None:
    payment.failure_code = "AMOUNT_MISMATCH"
    payment.failure_message = "Provider amount or currency did not match the local payment."
    _transition_payment(
        db, payment, PaymentStatus.FAILED, "AMOUNT_MISMATCH", "API",
        actor_id, paypal_ref=provider_ref,
    )
    notifications.notify(
        db, user_id=payment.payer_id, event_type="payment.failed",
        payload={"payment_id": payment.id, "failure_code": "AMOUNT_MISMATCH"},
    )
    db.commit()


def _transition_payment(
    db: Session,
    payment: Payment,
    target: PaymentStatus,
    event_type: str,
    source: str,
    actor_id: int | None = None,
    paypal_ref: str | None = None,
    details: dict | None = None,
) -> None:
    """Validate and record a payment status transition."""

    previous_status = payment.status

    try:
        validate_transition(previous_status, target)
    except ValueError as exc:
        raise InvalidPaymentStateError(str(exc)) from exc

    payment.status = target.value

    _record_event(
        db=db,
        payment=payment,
        event_type=event_type,
        source=source,
        from_status=previous_status,
        to_status=target.value,
        paypal_ref=paypal_ref,
        details=details,
    )

    audit.record(
        db,
        actor_id=actor_id,
        action=f"payment.{target.value.lower()}",
        entity_type="payment",
        entity_id=payment.id,
        details=details or {},
    )


def _mark_milestone_paid(db: Session, payment: Payment, actor_id: int | None) -> None:
    milestone = payment.milestone
    if milestone.id != payment.milestone_id or milestone.project_id != payment.project_id:
        raise PayPalError("Payment and milestone relationship is inconsistent.")
    milestones.mark_paid(db, milestone.id, payment.id)
    audit.record(
        db,
        actor_id=actor_id,
        action="milestone.paid",
        entity_type="milestone",
        entity_id=milestone.id,
        details={"payment_id": payment.id},
    )

def create_order_for_milestone(
    db: Session,
    *,
    milestone_id: int,
    actor_id: int,
) -> Payment:
    """Create a payment order for an approved milestone."""

    try:
        # Verify milestone exists, is approved, and belongs to this client.
        milestone = milestones.get_for_payment(
            db,
            milestone_id,
            actor_id,
        )

        project = milestone.project
        amount = Decimal(str(milestone.amount))
        try:
            rounded_amount = amount.quantize(Decimal("0.01"))
        except InvalidOperation as exc:
            raise ValueError("Milestone amount is outside the supported USD range.") from exc
        if (
            not amount.is_finite()
            or amount <= 0
            or amount != rounded_amount
        ):
            raise ValueError("Milestone amount must be a positive USD amount with at most two decimal places.")
        if (project.currency or "USD").upper() != "USD":
            raise ValueError("Only USD milestone payments are supported.")
        if project.freelancer_id is None:
            raise ValueError("Cannot create payment without an assigned freelancer.")

        # A repeated Pay click must reuse the live order.  The partial unique
        # index remains the concurrency backstop when two requests race.
        existing = (
            db.query(Payment)
            .filter(Payment.milestone_id == milestone.id)
            .filter(Payment.status.in_([
                PaymentStatus.CREATED.value,
                PaymentStatus.PENDING_APPROVAL.value,
            ]))
            .with_for_update()
            .first()
        )
        if existing is not None:
            if (
                existing.status == PaymentStatus.PENDING_APPROVAL.value
                or existing.paypal_order_id
            ):
                existing._idempotent_reuse = True
                db.commit()
                db.refresh(existing)
                return existing
            # Resume an interrupted create using the same durable idempotency
            # key. The row lock serializes concurrent recovery attempts.
            payment = existing
            provider = existing.provider
        else:
            payment = None

        active = (
            db.query(Payment)
            .filter(Payment.milestone_id == milestone.id)
            .filter(Payment.status.in_([
                PaymentStatus.APPROVED.value,
                PaymentStatus.CAPTURE_PENDING.value,
                PaymentStatus.COMPLETED.value,
            ]))
            .first()
        )
        if active is not None:
            raise InvalidPaymentStateError(
                "A payment for this milestone is already being processed."
            )

        if payment is None:
            provider = _get_provider()
            payment = Payment(
                milestone_id=milestone.id,
                project_id=project.id,
                payer_id=actor_id,
                amount=rounded_amount,
                currency="USD",
                status=PaymentStatus.CREATED.value,
                provider=provider,
                payee_mode=settings.payee_mode,
                payee_email=(
                    project.freelancer.email
                    if settings.payee_mode == "direct_payee"
                    else None
                ),
            )
            db.add(payment)
            db.flush()
            _record_event(
                db, payment, "ORDER_REQUESTED", "API",
                from_status=None, to_status=PaymentStatus.CREATED.value,
                details={"provider": provider},
            )
            audit.record(
                db, actor_id=actor_id, action="payment.created",
                entity_type="payment", entity_id=payment.id,
                details={"provider": provider},
            )
            db.commit()
            # Reacquire the row lock after making CREATED durable. If another
            # request completed the provider call first, reuse its order.
            payment = (
                db.query(Payment).filter(Payment.id == payment.id)
                .with_for_update().one()
            )
            if payment.status == PaymentStatus.PENDING_APPROVAL.value:
                payment._idempotent_reuse = True
                db.commit()
                db.refresh(payment)
                return payment

        # Create the provider order.
        client = _get_payment_client(provider)

        try:
            order = client.create_order(
                amount=payment.amount,
                currency_code=payment.currency,
                reference_id=str(milestone.id),
                custom_id=str(payment.id),
                invoice_id=f"MM-PAYMENT-{payment.id}",
                description=f"Milestone: {milestone.title}",
                return_url=(
                    f"{settings.frontend_base_url}/payments/return"
                    f"?payment_id={payment.id}"
                ),
                cancel_url=(
                    f"{settings.frontend_base_url}/payments/cancel"
                    f"?payment_id={payment.id}"
                ),
                request_id=f"mm-create-{payment.idempotency_key}",
                payee_email=payment.payee_email,
            )
        finally:
            client.close()

        order_id = order.get("id")

        if not order_id:
            raise PayPalError(
                "Payment provider did not return an order ID."
            )

        approval_link = next(
            (
                link["href"]
                for link in order.get("links", [])
                if link.get("rel") in ("approve", "payer-action")
            ),
            None,
        )

        if not approval_link:
            raise PayPalError(
                "Payment provider did not return an approval URL."
            )

        if provider == "MOCK":
            if not approval_link.startswith("/mock-paypal/checkout?"):
                raise PayPalError("Mock provider returned an unsafe checkout URL.")
        else:
            approval_url = urlsplit(approval_link)
            if (
                approval_url.scheme != "https"
                or approval_url.hostname != "www.sandbox.paypal.com"
                or approval_url.username is not None
                or approval_url.password is not None
            ):
                raise PayPalError("PayPal returned an unsafe Sandbox checkout URL.")

        provider_status = order.get("status")

        if provider_status not in ("CREATED", "PAYER_ACTION_REQUIRED"):
            raise PayPalError(
                f"Unexpected order status: {provider_status}"
            )

        payment.paypal_order_id = order_id
        payment.paypal_order_status = provider_status
        payment.approve_url = approval_link

        _transition_payment(
            db=db,
            payment=payment,
            target=PaymentStatus.PENDING_APPROVAL,
            event_type="ORDER_CREATED",
            source="API",
            actor_id=actor_id,
            paypal_ref=order_id,
            details={"provider": provider},
        )

        if project.freelancer_id is not None:
            notifications.notify(
                db,
                user_id=project.freelancer_id,
                event_type="payment.pending_approval",
                payload={"payment_id": payment.id, "milestone_id": milestone.id,
                        "project_id": project.id, "simulated": provider == "MOCK"},
            )

        db.commit()
        db.refresh(payment)

        return payment

    except PayPalError as exc:
        if "payment" in locals() and payment.status == PaymentStatus.CREATED.value:
            error_code = getattr(exc, "code", None)
            status_code = getattr(exc, "status_code", None)
            payment.failure_code = (error_code or "PAYPAL_ERROR")[:100]
            payment.failure_message = str(exc)[:1000]
            if status_code is not None and 400 <= status_code < 500:
                _transition_payment(
                    db, payment, PaymentStatus.FAILED, "ORDER_FAILED", "API",
                    actor_id, details={"provider": payment.provider},
                )
                notifications.notify(
                    db, user_id=payment.payer_id, event_type="payment.failed",
                    payload={"payment_id": payment.id, "milestone_id": payment.milestone_id},
                )
            else:
                # Network failures and server errors can happen after PayPal
                # created the order. Keep CREATED and retry the same request
                # ID so we cannot make an orphaned second order.
                _record_event(
                    db, payment, "ORDER_CREATE_RETRYABLE_FAILURE", "API",
                    from_status=PaymentStatus.CREATED.value,
                    to_status=PaymentStatus.CREATED.value,
                    details={"provider": payment.provider},
                )
                audit.record(
                    db, actor_id=actor_id, action="payment.order_retryable_failure",
                    entity_type="payment", entity_id=payment.id,
                    details={"provider": payment.provider},
                )
            db.commit()
        else:
            db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        # A concurrent create may have committed after our initial lookup.
        existing = (
            db.query(Payment)
            .filter(Payment.milestone_id == milestone_id)
            .filter(Payment.status.in_([
                PaymentStatus.CREATED.value,
                PaymentStatus.PENDING_APPROVAL.value,
            ]))
            .first()
        )
        if existing is not None:
            if (existing.status == PaymentStatus.CREATED.value
                    and not existing.paypal_order_id):
                raise InvalidPaymentStateError(
                    "Payment order creation is already being recovered; retry shortly."
                ) from exc
            existing._idempotent_reuse = True
            return existing
        raise InvalidPaymentStateError(
            "A payment for this milestone already exists."
        ) from exc

    except Exception:
        db.rollback()
        raise

def capture_payment(
    db: Session,
    *,
    payment_id: int,
    actor_id: int,
    paypal_order_id: str,
) -> Payment:
    """Capture an approved payment and mark its milestone as paid."""

    client = None

    try:
        # Lock the payment row to prevent concurrent captures.
        payment = (
            db.query(Payment)
            .filter(Payment.id == payment_id)
            .with_for_update()
            .first()
        )

        if payment is None:
            raise PaymentNotFoundError("Payment not found.")

        # Only the original payer can capture this payment.
        if payment.payer_id != actor_id:
            raise PaymentAuthorizationError(
                "Only the payment's client can capture it."
            )

        # Verify the supplied order belongs to this payment.
        if payment.paypal_order_id != paypal_order_id:
            raise PaymentAuthorizationError(
                "PayPal order does not belong to this payment."
            )

        # Repeated capture requests must be idempotent.
        if payment.status == PaymentStatus.COMPLETED.value:
            db.commit()
            db.refresh(payment)
            return payment

        if payment.status not in (
            PaymentStatus.PENDING_APPROVAL.value,
            PaymentStatus.APPROVED.value,
            PaymentStatus.CAPTURE_PENDING.value,
        ):
            raise InvalidPaymentStateError(
                f"Cannot capture payment in state {payment.status}."
            )

        client = _get_payment_client(payment.provider)
        _restore_mock_order(payment)

        # Ask the provider for the authoritative order status.
        order = client.get_order(paypal_order_id)

        if order.get("status") != "APPROVED":
            if order.get("status") == "COMPLETED":
                return sync_payment(
                    db, payment_id=payment_id, actor_id=actor_id
                )
            raise InvalidPaymentStateError(
                "PayPal order has not been approved."
            )

        # Validate the order amount before capturing.
        try:
            _validate_provider_order(order, payment)
        except AmountMismatchError:
            _persist_amount_mismatch(db, payment, actor_id, paypal_order_id)
            raise

        if payment.status == PaymentStatus.PENDING_APPROVAL.value:
            payment.approved_at = datetime.now(timezone.utc)
            payment.paypal_order_status = "APPROVED"

            _transition_payment(
                db=db,
                payment=payment,
                target=PaymentStatus.APPROVED,
                event_type="ORDER_APPROVED",
                source="API",
                actor_id=actor_id,
                paypal_ref=paypal_order_id,
            )

        # Use a stable request ID for provider-side idempotency.
        try:
            capture_result = client.capture_order(
                paypal_order_id,
                request_id=f"mm-capture-{payment.idempotency_key}",
            )
        except PayPalError as exc:
            error_code = getattr(exc, "code", None)
            status_code = getattr(exc, "status_code", None)
            if error_code == "ORDER_ALREADY_CAPTURED":
                return sync_payment(
                    db, payment_id=payment_id, actor_id=actor_id
                )
            if error_code == "ORDER_NOT_APPROVED":
                raise InvalidPaymentStateError(
                    "PayPal order has not been approved yet."
                ) from exc
            # A definitive provider 4xx is safe to record as a failure. A
            # timeout/5xx is ambiguous, so keep the state resumable and let
            # sync/webhook reconciliation determine whether capture landed.
            if status_code is not None and 400 <= status_code < 500:
                target = (
                    PaymentStatus.DENIED
                    if error_code in {"INSTRUMENT_DECLINED", "PAYER_CANNOT_PAY"}
                    else PaymentStatus.FAILED
                )
                payment.failure_code = (error_code or "PAYPAL_ERROR")[:100]
                payment.failure_message = str(exc)[:1000]
                _transition_payment(
                    db, payment, target, "CAPTURE_REJECTED", "API",
                    actor_id, paypal_ref=paypal_order_id,
                )
                notifications.notify(
                    db, user_id=payment.payer_id,
                    event_type=f"payment.{target.value.lower()}",
                    payload={"payment_id": payment.id, "failure_code": payment.failure_code},
                )
                db.commit()
            raise

        capture_status = capture_result.get("status")

        captures = (
            capture_result
            .get("purchase_units", [{}])[0]
            .get("payments", {})
            .get("captures", [])
        )

        capture = captures[0] if captures else {}

        payment.paypal_capture_status = (
            capture.get("status") or capture_status
        )

        if capture_status == "COMPLETED":
            if capture.get("status") != "COMPLETED":
                raise PayPalError(
                    "Provider returned COMPLETED without a completed capture."
                )

            capture_amount = capture.get("amount", {})

            try:
                _validate_amount_fields(capture_amount, payment)
            except AmountMismatchError:
                _persist_amount_mismatch(db, payment, actor_id, capture.get("id"))
                raise AmountMismatchError(
                    "Captured amount or currency does not match payment."
                )

            capture_id = capture.get("id")

            if not capture_id:
                raise PayPalError(
                    "Provider did not return a capture ID."
                )

            payment.paypal_capture_id = capture_id
            payment.captured_at = datetime.now(timezone.utc)

            _transition_payment(
                db=db,
                payment=payment,
                target=PaymentStatus.COMPLETED,
                event_type="CAPTURE_COMPLETED",
                source="API",
                actor_id=actor_id,
                paypal_ref=capture_id,
                details={
                    "amount": str(payment.amount),
                    "currency": payment.currency,
                },
            )

            milestone = payment.milestone
            _mark_milestone_paid(db, payment, actor_id)

            # Notify the freelancer after confirmed capture.
            project = milestone.project

            if project.freelancer_id is not None:
                notifications.notify(
                    db,
                    user_id=project.freelancer_id,
                    event_type="payment.completed",
                    payload={
                        "project_id": project.id,
                        "milestone_id": milestone.id,
                        "payment_id": payment.id,
                        "amount": str(payment.amount),
                        "currency": payment.currency,
                    },
                )

        elif capture_status == "PENDING":
            payment.paypal_capture_status = "PENDING"
            if payment.status != PaymentStatus.CAPTURE_PENDING.value:
                _transition_payment(
                    db=db,
                    payment=payment,
                    target=PaymentStatus.CAPTURE_PENDING,
                    event_type="CAPTURE_PENDING",
                    source="API",
                    actor_id=actor_id,
                    paypal_ref=paypal_order_id,
                )
                notifications.notify(
                    db,
                    user_id=payment.payer_id,
                    event_type="payment.capture_pending",
                    payload={"payment_id": payment.id},
                )
            else:
                _record_event(
                    db=db,
                    payment=payment,
                    event_type="CAPTURE_STILL_PENDING",
                    source="API",
                    from_status=PaymentStatus.CAPTURE_PENDING.value,
                    to_status=PaymentStatus.CAPTURE_PENDING.value,
                    paypal_ref=paypal_order_id,
                )
                audit.record(
                    db,
                    actor_id=actor_id,
                    action="payment.capture_pending",
                    entity_type="payment",
                    entity_id=payment.id,
                    details={"provider": payment.provider},
                )

        elif capture_status in ("DECLINED", "DENIED"):
            payment.failure_code = capture_status
            payment.failure_message = "PayPal declined the payment."
            _transition_payment(
                db=db,
                payment=payment,
                target=PaymentStatus.DENIED,
                event_type="CAPTURE_DENIED",
                source="API",
                actor_id=actor_id,
                paypal_ref=paypal_order_id,
            )
            notifications.notify(
                db, user_id=payment.payer_id, event_type="payment.denied",
                payload={"payment_id": payment.id, "milestone_id": payment.milestone_id},
            )

        else:
            raise PayPalError(
                f"Unexpected capture status: {capture_status}"
            )

        db.commit()
        db.refresh(payment)

        return payment

    except Exception:
        db.rollback()
        raise

    finally:
        if client is not None:
            client.close()

def cancel_payment(
    db: Session,
    *,
    payment_id: int,
    actor_id: int,
) -> Payment:
    """Cancel a payment that is still awaiting buyer approval."""

    try:
        payment = (
            db.query(Payment)
            .filter(Payment.id == payment_id)
            .with_for_update()
            .first()
        )

        if payment is None:
            raise PaymentNotFoundError("Payment not found.")

        if payment.payer_id != actor_id:
            raise PaymentAuthorizationError(
                "Only the payment's client can cancel it."
            )

        if payment.status == PaymentStatus.CANCELLED.value:
            db.commit()
            db.refresh(payment)
            return payment

        if payment.status != PaymentStatus.PENDING_APPROVAL.value:
            raise InvalidPaymentStateError(
                f"Cannot cancel payment in state {payment.status}."
            )

        _transition_payment(
            db=db,
            payment=payment,
            target=PaymentStatus.CANCELLED,
            event_type="ORDER_CANCELLED",
            source="API",
            actor_id=actor_id,
            paypal_ref=payment.paypal_order_id,
        )

        project = payment.milestone.project
        if project.freelancer_id is not None:
            notifications.notify(
                db, user_id=project.freelancer_id, event_type="payment.cancelled",
                payload={"payment_id": payment.id, "milestone_id": payment.milestone_id,
                         "project_id": payment.project_id},
            )

        db.commit()
        db.refresh(payment)

        return payment

    except Exception:
        db.rollback()
        raise


def reject_mock_payment(db: Session, *, order_id: str) -> Payment:
    """Apply an explicit simulated buyer rejection to a mock payment."""
    try:
        payment = (
            db.query(Payment)
            .filter(Payment.paypal_order_id == order_id)
            .with_for_update()
            .first()
        )
        if payment is None or payment.provider != "MOCK":
            raise PaymentNotFoundError("Mock payment not found.")
        if payment.status != PaymentStatus.PENDING_APPROVAL.value:
            raise InvalidPaymentStateError(
                f"Cannot reject payment in state {payment.status}."
            )
        _restore_mock_order(payment)
        MockPaymentClient.reject_order(order_id)
        payment.failure_code = "SIMULATED_REJECTION"
        payment.failure_message = "Buyer rejected this simulated payment."
        _transition_payment(
            db, payment, PaymentStatus.DENIED, "PAYMENT_REJECTED", "USER",
            actor_id=payment.payer_id, paypal_ref=order_id,
            details={"simulated": True},
        )
        notifications.notify(
            db,
            user_id=payment.payer_id,
            event_type="payment.denied",
            payload={"payment_id": payment.id, "simulated": True},
        )
        db.commit()
        db.refresh(payment)
        return payment
    except Exception:
        db.rollback()
        raise


def approve_mock_payment(db: Session, *, order_id: str) -> Payment:
    """Persist simulated buyer approval so it survives an app restart."""
    try:
        payment = (
            db.query(Payment).filter(Payment.paypal_order_id == order_id)
            .with_for_update().first()
        )
        if payment is None or payment.provider != "MOCK":
            raise PaymentNotFoundError("Mock payment not found.")
        if payment.status == PaymentStatus.APPROVED.value:
            return payment
        if payment.status != PaymentStatus.PENDING_APPROVAL.value:
            raise InvalidPaymentStateError(
                f"Cannot approve payment in state {payment.status}."
            )
        _restore_mock_order(payment)
        MockPaymentClient.approve_order(order_id)
        payment.approved_at = datetime.now(timezone.utc)
        payment.paypal_order_status = "APPROVED"
        _transition_payment(
            db, payment, PaymentStatus.APPROVED, "ORDER_APPROVED", "USER",
            actor_id=payment.payer_id, paypal_ref=order_id,
            details={"simulated": True},
        )
        db.commit()
        db.refresh(payment)
        return payment
    except Exception:
        db.rollback()
        raise
def sync_payment(
    db: Session,
    *,
    payment_id: int,
    actor_id: int,
) -> Payment:
    """Reconcile local payment state with the provider's order status."""

    client = None

    try:
        payment = (
            db.query(Payment)
            .filter(Payment.id == payment_id)
            .with_for_update()
            .first()
        )

        if payment is None:
            raise PaymentNotFoundError("Payment not found.")

        project = payment.milestone.project
        if actor_id != payment.payer_id:
            raise PaymentAuthorizationError(
                "Only the payment's client can synchronize it."
            )

        if payment.status in {
            PaymentStatus.COMPLETED.value,
            PaymentStatus.FAILED.value,
            PaymentStatus.DENIED.value,
            PaymentStatus.CANCELLED.value,
        }:
            db.commit()
            db.refresh(payment)
            return payment

        if not payment.paypal_order_id:
            raise PayPalError("Payment has no provider order ID.")

        client = _get_payment_client(payment.provider)
        _restore_mock_order(payment)

        order = client.get_order(payment.paypal_order_id)
        if order.get("id") != payment.paypal_order_id:
            raise PayPalError("Provider returned an unexpected order ID.")
        if order.get("status") in ("APPROVED", "COMPLETED"):
            try:
                _validate_provider_order(order, payment)
            except AmountMismatchError:
                _persist_amount_mismatch(db, payment, actor_id, payment.paypal_order_id)
                raise
        provider_status = order.get("status")

        payment.paypal_order_status = provider_status

        if provider_status == "APPROVED":

            if payment.status == PaymentStatus.PENDING_APPROVAL.value:
                payment.approved_at = datetime.now(timezone.utc)

                _transition_payment(
                    db=db,
                    payment=payment,
                    target=PaymentStatus.APPROVED,
                    event_type="ORDER_APPROVED",
                    source="API",
                    actor_id=actor_id,
                    paypal_ref=payment.paypal_order_id,
                )

            elif payment.status not in (
                PaymentStatus.APPROVED.value,
                PaymentStatus.CAPTURE_PENDING.value,
            ):
                raise InvalidPaymentStateError(
                    f"Cannot synchronize payment in state {payment.status}."
                )

        elif provider_status == "COMPLETED":

            purchase_units = order.get("purchase_units", [])

            captures = (
                purchase_units[0]
                .get("payments", {})
                .get("captures", [])
                if purchase_units
                else []
            )

            if not captures:
                raise PayPalError(
                    "Completed provider order has no capture details."
                )

            capture = captures[0]
            capture_amount = capture.get("amount", {})
            if capture.get("status") == "PENDING":
                try:
                    _validate_amount_fields(capture_amount, payment)
                except AmountMismatchError:
                    _persist_amount_mismatch(db, payment, actor_id, capture.get("id"))
                    raise
                if payment.status == PaymentStatus.PENDING_APPROVAL.value:
                    payment.approved_at = datetime.now(timezone.utc)
                    _transition_payment(
                        db, payment, PaymentStatus.APPROVED, "ORDER_APPROVED",
                        "API", actor_id, paypal_ref=payment.paypal_order_id,
                    )
                if payment.status == PaymentStatus.APPROVED.value:
                    payment.paypal_capture_status = "PENDING"
                    payment.paypal_capture_id = capture.get("id")
                    _transition_payment(
                        db, payment, PaymentStatus.CAPTURE_PENDING,
                        "CAPTURE_PENDING", "API", actor_id,
                        paypal_ref=payment.paypal_order_id,
                    )
                    notifications.notify(
                        db, user_id=payment.payer_id,
                        event_type="payment.capture_pending",
                        payload={"payment_id": payment.id},
                    )
                elif payment.status == PaymentStatus.CAPTURE_PENDING.value:
                    _record_event(
                        db, payment, "CAPTURE_STILL_PENDING", "API",
                        from_status=payment.status, to_status=payment.status,
                        paypal_ref=payment.paypal_order_id,
                    )
                else:
                    raise InvalidPaymentStateError(
                        f"Cannot synchronize payment in state {payment.status}."
                    )
            elif capture.get("status") in {"DENIED", "DECLINED"}:
                payment.failure_code = capture.get("status")
                payment.failure_message = "PayPal declined the capture."
                _transition_payment(
                    db, payment, PaymentStatus.DENIED, "CAPTURE_DENIED", "API",
                    actor_id, paypal_ref=capture.get("id") or payment.paypal_order_id,
                )
                notifications.notify(
                    db, user_id=payment.payer_id, event_type="payment.denied",
                    payload={"payment_id": payment.id, "milestone_id": payment.milestone_id},
                )
            elif capture.get("status") != "COMPLETED":
                raise PayPalError("Provider order is complete without a completed capture.")
            else:
                try:
                    _validate_amount_fields(capture_amount, payment)
                except AmountMismatchError:
                    _persist_amount_mismatch(db, payment, actor_id, capture.get("id"))
                    raise

                capture_id = capture.get("id")
                if not capture_id:
                    raise PayPalError("Provider did not return a capture ID.")
                if payment.status == PaymentStatus.PENDING_APPROVAL.value:
                    payment.approved_at = datetime.now(timezone.utc)
                    _transition_payment(
                        db=db, payment=payment, target=PaymentStatus.APPROVED,
                        event_type="ORDER_APPROVED", source="API",
                        actor_id=actor_id, paypal_ref=payment.paypal_order_id,
                    )
                payment.paypal_capture_id = capture_id
                payment.paypal_capture_status = "COMPLETED"
                payment.captured_at = datetime.now(timezone.utc)
                _transition_payment(
                    db=db, payment=payment, target=PaymentStatus.COMPLETED,
                    event_type="CAPTURE_RECONCILED", source="API",
                    actor_id=actor_id, paypal_ref=capture_id,
                    details={"amount": str(payment.amount), "currency": payment.currency},
                )
                milestone = payment.milestone
                _mark_milestone_paid(db, payment, actor_id)
                project = milestone.project
                if project.freelancer_id is not None:
                    notifications.notify(
                        db, user_id=project.freelancer_id,
                        event_type="payment.completed",
                        payload={"project_id": project.id, "milestone_id": milestone.id,
                                 "payment_id": payment.id, "amount": str(payment.amount),
                                 "currency": payment.currency},
                    )

        elif provider_status == "VOIDED":

            if payment.status == PaymentStatus.PENDING_APPROVAL.value:
                _transition_payment(
                    db=db,
                    payment=payment,
                    target=PaymentStatus.CANCELLED,
                    event_type="ORDER_VOIDED",
                    source="API",
                    actor_id=actor_id,
                    paypal_ref=payment.paypal_order_id,
                )

        elif provider_status in ("CREATED", "PAYER_ACTION_REQUIRED"):
            # Order is still awaiting buyer approval.
            pass

        else:
            raise PayPalError(
                f"Unsupported provider order status: {provider_status}"
            )

        db.commit()
        db.refresh(payment)

        return payment

    except Exception:
        db.rollback()
        raise

    finally:
        if client is not None:
            client.close()
