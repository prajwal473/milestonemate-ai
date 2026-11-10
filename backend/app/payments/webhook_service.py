import json
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import PayPalWebhookEvent
from app.payments.errors import (
    AmountMismatchError,
    PayPalError,
    WebhookVerificationError,
)
from app.payments.paypal_client import PayPalClient

from decimal import Decimal

from app.models import Payment, PaymentEvent
from app.payments.state import PaymentStatus
from app.services import audit, milestones, notifications
from app.payments.service import (
    _get_payment_client,
    _record_event,
    _transition_payment,
)

def receive_webhook(
    db: Session,
    *,
    headers: dict,
    raw_body: bytes,
) -> dict:
    """Verify, store, and deduplicate an incoming PayPal webhook."""

    client = PayPalClient()

    try:
        verification = client.verify_webhook_signature(
            headers,
            raw_body,
        )
    except Exception as exc:
        raise WebhookVerificationError(
            f"Webhook verification failed: {exc}"
        ) from exc
    finally:
        client.close()

    if verification.get("verification_status") != "SUCCESS":
        raise WebhookVerificationError(
            "PayPal webhook signature is invalid."
        )

    try:
        event = json.loads(raw_body)
    except (UnicodeDecodeError, ValueError) as exc:
        raise WebhookVerificationError(
            "Invalid webhook JSON."
        ) from exc

    event_id = event.get("id")
    event_type = event.get("event_type")

    if not event_id or not event_type:
        raise WebhookVerificationError(
            "Webhook event ID or event type is missing."
        )

    resource = event.get("resource", {})

    webhook_record = PayPalWebhookEvent(
        paypal_event_id=event_id,
        event_type=event_type,
        resource_type=resource.get("resource_type"),
        resource_id=resource.get("id"),
        verification_status="SUCCESS",
        processing_status="RECEIVED",
        payload=event,
        transmission_id=headers.get("paypal-transmission-id")
        or headers.get("PAYPAL-TRANSMISSION-ID"),
    )

    try:
        db.add(webhook_record)
        db.commit()
        db.refresh(webhook_record)

        return {
            "status": "received",
            "event_id": event_id,
        }

    except IntegrityError:
        db.rollback()

        existing = (
            db.query(PayPalWebhookEvent)
            .filter(
                PayPalWebhookEvent.paypal_event_id == event_id
            )
            .first()
        )

        if existing:
            return {
                "status": "duplicate",
                "event_id": event_id,
            }

        raise

    except Exception:
        db.rollback()
        raise

def _get_related_order_id(event: dict) -> str | None:
    """Extract the PayPal order ID from a webhook event."""

    resource = event.get("resource", {})

    if event.get("event_type", "").startswith("CHECKOUT.ORDER."):
        return resource.get("id")

    related_ids = (
        resource
        .get("supplementary_data", {})
        .get("related_ids", {})
    )

    return related_ids.get("order_id")

def _find_payment_for_order(
    db: Session,
    order_id: str,
    order: dict,
) -> Payment | None:
    """Find and lock the local payment associated with a PayPal order."""

    payment = (
        db.query(Payment)
        .filter(Payment.paypal_order_id == order_id)
        .with_for_update()
        .first()
    )

    if payment:
        return payment

    purchase_units = order.get("purchase_units", [])

    if not purchase_units:
        return None

    custom_id = purchase_units[0].get("custom_id")

    if not custom_id or not str(custom_id).isdigit():
        return None

    payment = (
        db.query(Payment)
        .filter(Payment.id == int(custom_id))
        .with_for_update()
        .first()
    )

    if payment and payment.paypal_order_id == order_id:
        return payment

    return None

def _validate_order_amount(
    order: dict,
    payment: Payment,
) -> None:
    """Verify the PayPal order amount matches the local payment."""

    purchase_units = order.get("purchase_units", [])

    if not purchase_units:
        raise PayPalError(
            "PayPal order contains no purchase units."
        )

    amount = purchase_units[0].get("amount", {})

    try:
        provider_amount = Decimal(str(amount.get("value", "0")))
    except Exception as exc:
        raise PayPalError(
            "PayPal order contains an invalid amount."
        ) from exc

    if (
        amount.get("currency_code") != payment.currency
        or provider_amount != payment.amount
    ):
        raise AmountMismatchError(
            "PayPal order amount or currency does not match payment."
        )

def _get_order_capture(order: dict) -> dict | None:
    """Extract the first capture from a PayPal order."""

    purchase_units = order.get("purchase_units", [])

    if not purchase_units:
        return None

    payments = purchase_units[0].get("payments", {})
    captures = payments.get("captures", [])

    return captures[0] if captures else None

def apply_verified_webhook(
    db: Session,
    *,
    event: dict,
) -> str:
    """Reconcile a verified PayPal webhook with the local payment."""

    event_type = event.get("event_type", "")

    supported_events = {
        "CHECKOUT.ORDER.APPROVED",
        "PAYMENT.CAPTURE.COMPLETED",
        "PAYMENT.CAPTURE.PENDING",
        "PAYMENT.CAPTURE.DENIED",
    }

    if event_type not in supported_events:
        return "ignored"

    order_id = _get_related_order_id(event)

    if not order_id:
        return "ignored"

    client = None

    try:
        payment = (
            db.query(Payment)
            .filter(Payment.paypal_order_id == order_id)
            .with_for_update()
            .first()
        )

        if payment is None:
            return "ignored"

        if payment.status == PaymentStatus.COMPLETED.value:
            return "processed"

        if payment.status in {
            PaymentStatus.FAILED.value,
            PaymentStatus.DENIED.value,
            PaymentStatus.CANCELLED.value,
        }:
            return "ignored"

        client = _get_payment_client(payment.provider)
        order = client.get_order(order_id)

        if order.get("id") != order_id:
            raise PayPalError(
                "PayPal returned an unexpected order ID."
            )

        _validate_order_amount(order, payment)

        capture = _get_order_capture(order)

        if event_type == "CHECKOUT.ORDER.APPROVED":
            if order.get("status") != "APPROVED":
                return "ignored"

            if payment.status == PaymentStatus.PENDING_APPROVAL.value:
                payment.approved_at = datetime.now(timezone.utc)
                payment.paypal_order_status = "APPROVED"

                _transition_payment(
                    db=db,
                    payment=payment,
                    target=PaymentStatus.APPROVED,
                    event_type="ORDER_APPROVED",
                    source="WEBHOOK",
                    paypal_ref=order_id,
                )

        elif event_type == "PAYMENT.CAPTURE.COMPLETED":
            if (
                order.get("status") != "COMPLETED"
                or not capture
                or capture.get("status") != "COMPLETED"
            ):
                return "ignored"

            capture_amount = capture.get("amount", {})

            if (
                capture_amount.get("currency_code") != payment.currency
                or Decimal(str(capture_amount.get("value", "0")))
                != payment.amount
            ):
                raise AmountMismatchError(
                    "PayPal capture amount or currency does not match payment."
                )

            capture_id = capture.get("id")

            if not capture_id:
                raise PayPalError(
                    "PayPal capture does not contain an ID."
                )

            if payment.status == PaymentStatus.PENDING_APPROVAL.value:
                payment.approved_at = datetime.now(timezone.utc)

                _transition_payment(
                    db=db,
                    payment=payment,
                    target=PaymentStatus.APPROVED,
                    event_type="ORDER_APPROVED",
                    source="WEBHOOK",
                    paypal_ref=order_id,
                )

            payment.paypal_order_status = "COMPLETED"
            payment.paypal_capture_id = capture_id
            payment.paypal_capture_status = "COMPLETED"
            payment.captured_at = datetime.now(timezone.utc)

            _transition_payment(
                db=db,
                payment=payment,
                target=PaymentStatus.COMPLETED,
                event_type="CAPTURE_COMPLETED",
                source="WEBHOOK",
                paypal_ref=capture_id,
                details={
                    "amount": str(payment.amount),
                    "currency": payment.currency,
                },
            )

            milestone = payment.milestone

            if milestone.project_id != payment.project_id:
                raise PayPalError(
                    "Payment and milestone relationship is inconsistent."
                )

            milestones.mark_paid(db, milestone.id, payment.id)

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

        elif event_type == "PAYMENT.CAPTURE.PENDING":
            if not capture or capture.get("status") != "PENDING":
                return "ignored"

            payment.paypal_capture_status = "PENDING"

            if payment.status in (
                PaymentStatus.PENDING_APPROVAL.value,
                PaymentStatus.APPROVED.value,
            ):
                if payment.status == PaymentStatus.PENDING_APPROVAL.value:
                    payment.approved_at = datetime.now(timezone.utc)

                    _transition_payment(
                        db=db,
                        payment=payment,
                        target=PaymentStatus.APPROVED,
                        event_type="ORDER_APPROVED",
                        source="WEBHOOK",
                        paypal_ref=order_id,
                    )

                _transition_payment(
                    db=db,
                    payment=payment,
                    target=PaymentStatus.CAPTURE_PENDING,
                    event_type="CAPTURE_PENDING",
                    source="WEBHOOK",
                    paypal_ref=order_id,
                )
            else:
                _record_event(
                    db=db,
                    payment=payment,
                    event_type="CAPTURE_STILL_PENDING",
                    source="WEBHOOK",
                    from_status=payment.status,
                    to_status=payment.status,
                    paypal_ref=order_id,
                )

        elif event_type == "PAYMENT.CAPTURE.DENIED":
            if not capture or capture.get("status") != "DENIED":
                return "ignored"

            payment.paypal_capture_status = "DENIED"

            _transition_payment(
                db=db,
                payment=payment,
                target=PaymentStatus.DENIED,
                event_type="CAPTURE_DENIED",
                source="WEBHOOK",
                paypal_ref=capture.get("id") or order_id,
            )

            notifications.notify(
                db,
                user_id=payment.payer_id,
                event_type="payment.denied",
                payload={
                    "payment_id": payment.id,
                    "milestone_id": payment.milestone_id,
                    "project_id": payment.project_id,
                },
            )

        db.commit()
        return "processed"

    except Exception:
        db.rollback()
        raise

    finally:
        if client is not None:
            client.close()