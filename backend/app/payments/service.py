from decimal import Decimal
from datetime import datetime, timezone
from app.payments.errors import AmountMismatchError

from sqlalchemy.orm import Session

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

    if mode == "paypal":
        return "PAYPAL"

    raise ValueError(f"Unsupported payment mode: {mode}")


def _get_payment_client(provider: str):
    """Create the configured payment client."""

    if provider == "MOCK":
        return MockPaymentClient()

    if provider == "PAYPAL":
        return PayPalClient()

    raise ValueError(f"Unsupported payment provider: {provider}")


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

        if project.freelancer_id is None:
            raise ValueError(
                "Cannot create payment without an assigned freelancer."
            )

        provider = _get_provider()

        # Create the local payment record.
        payment = Payment(
            milestone_id=milestone.id,
            project_id=project.id,
            payer_id=actor_id,
            amount=Decimal(str(milestone.amount)).quantize(
                Decimal("0.01")
            ),
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

        db.commit()
        db.refresh(payment)

        return payment

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

        # Ask the provider for the authoritative order status.
        order = client.get_order(paypal_order_id)

        if order.get("status") != "APPROVED":
            raise InvalidPaymentStateError(
                "PayPal order has not been approved."
            )

        # Validate the order amount before capturing.
        purchase_units = order.get("purchase_units", [])

        if not purchase_units:
            raise AmountMismatchError(
                "PayPal order does not contain purchase unit details."
            )

        order_amount = purchase_units[0].get("amount", {})

        if (
            order_amount.get("currency_code") != payment.currency
            or Decimal(str(order_amount.get("value", "0")))
            != payment.amount
        ):
            raise AmountMismatchError(
                "PayPal order amount or currency does not match payment."
            )

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
        capture_result = client.capture_order(
            paypal_order_id,
            request_id=f"mm-capture-{payment.idempotency_key}",
        )

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

            if (
                capture_amount.get("currency_code") != payment.currency
                or Decimal(str(capture_amount.get("value", "0")))
                != payment.amount
            ):
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

            # Verify the payment-to-milestone relationship before
            # invoking the shared milestone service.
            milestone = payment.milestone

            if (
                milestone.id != payment.milestone_id
                or milestone.project_id != payment.project_id
            ):
                raise PayPalError(
                    "Payment and milestone relationship is inconsistent."
                )

            milestones.mark_paid(
                db,
                milestone.id,
                payment.id,
            )

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
            _transition_payment(
                db=db,
                payment=payment,
                target=PaymentStatus.DENIED,
                event_type="CAPTURE_DENIED",
                source="API",
                actor_id=actor_id,
                paypal_ref=paypal_order_id,
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

        if payment.payer_id != actor_id:
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

        order = client.get_order(payment.paypal_order_id)
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

            if (
                capture.get("status") != "COMPLETED"
                or capture_amount.get("currency_code") != payment.currency
                or Decimal(str(capture_amount.get("value", "0")))
                != payment.amount
            ):
                raise AmountMismatchError(
                    "Provider capture does not match the expected payment."
                )

            capture_id = capture.get("id")

            if not capture_id:
                raise PayPalError(
                    "Provider did not return a capture ID."
                )

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

            payment.paypal_capture_id = capture_id
            payment.paypal_capture_status = "COMPLETED"
            payment.captured_at = datetime.now(timezone.utc)

            _transition_payment(
                db=db,
                payment=payment,
                target=PaymentStatus.COMPLETED,
                event_type="CAPTURE_RECONCILED",
                source="API",
                actor_id=actor_id,
                paypal_ref=capture_id,
                details={
                    "amount": str(payment.amount),
                    "currency": payment.currency,
                },
            )

            milestone = payment.milestone

            if (
                milestone.id != payment.milestone_id
                or milestone.project_id != payment.project_id
            ):
                raise PayPalError(
                    "Payment and milestone relationship is inconsistent."
                )

            milestones.mark_paid(
                db,
                milestone.id,
                payment.id,
            )

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