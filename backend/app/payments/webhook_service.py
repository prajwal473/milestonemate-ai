import json
from urllib.parse import urlsplit
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
from app.core.config import settings

from decimal import Decimal

from app.models import Payment, PaymentEvent
from app.payments.state import PaymentStatus
from app.services import audit, notifications
from app.payments.service import (
    _restore_mock_order,
    _get_payment_client,
    _record_event,
    _transition_payment,
    _persist_amount_mismatch,
    _validate_amount_fields,
    _mark_milestone_paid,
)

def receive_webhook(
    db: Session,
    *,
    headers: dict,
    raw_body: bytes,
) -> dict:
    """Verify, store, and deduplicate an incoming PayPal webhook."""

    try:
        event = json.loads(raw_body)
    except (UnicodeDecodeError, ValueError) as exc:
        raise WebhookVerificationError(
            "Invalid webhook JSON."
        ) from exc

    if not isinstance(event, dict):
        raise WebhookVerificationError("Webhook payload must be a JSON object.")

    event_id = event.get("id")
    event_type = event.get("event_type")

    if not event_id or not event_type:
        raise WebhookVerificationError(
            "Webhook event ID or event type is missing."
        )

    resource = event.get("resource", {})
    if not isinstance(resource, dict):
        raise WebhookVerificationError("Webhook resource must be a JSON object.")

    existing = (db.query(PayPalWebhookEvent).filter_by(
        paypal_event_id=event_id
    ).with_for_update().first())
    if existing and existing.verification_status == "SUCCESS":
        if existing.processing_status != "FAILED":
            return {"status": "duplicate", "event_id": event_id}

    def store_verification(status: str, message: str | None) -> PayPalWebhookEvent:
        record = existing or PayPalWebhookEvent(
            paypal_event_id=event_id,
            event_type=event_type,
            processing_status="RECEIVED",
            received_at=datetime.now(timezone.utc),
        )
        was_verified = record.verification_status == "SUCCESS"
        if not was_verified:
            record.event_type = event_type
            record.resource_type = resource.get("resource_type")
            record.resource_id = resource.get("id")
            record.payload = event
            record.verification_status = status
            record.processing_status = "RECEIVED"
            record.transmission_id = (
                headers.get("paypal-transmission-id")
                or headers.get("PAYPAL-TRANSMISSION-ID")
            )
            record.error = message
        if existing is None:
            db.add(record)
        return record

    try:
        mode = settings.payments_mode.lower()
        if mode == "mock":
            verification = {
                "verification_status": "SUCCESS"
                if settings.allow_unverified_webhooks_in_mock
                else "FAILURE"
            }
        else:
            client = PayPalClient()
            try:
                verification = client.verify_webhook_signature(headers, raw_body)
            finally:
                client.close()
    except Exception as exc:
        verification_status = "FAILURE" if isinstance(exc, ValueError) else "ERROR"
        error_message = (
            "PayPal rejected the webhook signature."
            if isinstance(exc, ValueError)
            else "Webhook verification could not be completed."
        )
        store_verification(verification_status, error_message)
        db.commit()
        raise WebhookVerificationError("Webhook verification failed.") from exc

    if verification.get("verification_status") != "SUCCESS":
        store_verification("FAILURE", "PayPal rejected the webhook signature.")
        db.commit()
        raise WebhookVerificationError("PayPal webhook signature is invalid.")

    webhook_record = store_verification("SUCCESS", None)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(PayPalWebhookEvent).filter_by(
            paypal_event_id=event_id
        ).with_for_update().one()
        if existing.verification_status == "SUCCESS":
            return {"status": "duplicate", "event_id": event_id}
        # A concurrent invalid delivery may have stored this event ID first.
        # A now-verified event replaces its untrusted payload and proceeds.
        existing.event_type = event_type
        existing.resource_type = resource.get("resource_type")
        existing.resource_id = resource.get("id")
        existing.verification_status = "SUCCESS"
        existing.processing_status = "RECEIVED"
        existing.payload = event
        existing.transmission_id = (
            headers.get("paypal-transmission-id")
            or headers.get("PAYPAL-TRANSMISSION-ID")
        )
        existing.error = None
        webhook_record = existing
        db.commit()
    db.refresh(webhook_record)
    return {"status": "received", "event_id": event_id}

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

    order_id = related_ids.get("order_id")
    if order_id:
        return order_id
    for link in resource.get("links", []):
        if link.get("rel") == "up":
            href = link.get("href", "")
            try:
                parsed = urlsplit(href)
                parts = parsed.path.rstrip("/").split("/")
                if (parsed.scheme == "https"
                        and parsed.hostname == "api-m.sandbox.paypal.com"
                        and parsed.username is None and parsed.password is None
                        and len(parts) == 5
                        and parts[1:4] == ["v2", "checkout", "orders"]
                        and parts[4]):
                    return parts[4]
            except (TypeError, ValueError):
                continue
    return None

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
        "PAYMENT.CAPTURE.REFUNDED",
        "PAYMENT.CAPTURE.REVERSED",
    }

    if event_type not in supported_events:
        return "ignored"

    if event_type in {
        "PAYMENT.CAPTURE.REFUNDED", "PAYMENT.CAPTURE.REVERSED"
    }:
        resource = event.get("resource", {})
        related = resource.get("supplementary_data", {}).get("related_ids", {})
        capture_id = related.get("capture_id")
        if not capture_id:
            for link in resource.get("links", []):
                if link.get("rel") in {"up", "related"}:
                    try:
                        parsed = urlsplit(link.get("href", ""))
                        parts = parsed.path.rstrip("/").split("/")
                        if (parsed.scheme == "https"
                                and parsed.hostname == "api-m.sandbox.paypal.com"
                                and parts[-3:-1] == ["payments", "captures"]
                                and parts[-1]):
                            capture_id = parts[-1]
                            break
                    except (TypeError, ValueError):
                        pass
        if event_type == "PAYMENT.CAPTURE.REVERSED" and not capture_id:
            capture_id = resource.get("id")
        amount = resource.get("amount")
        if not isinstance(capture_id, str) or not capture_id or not isinstance(amount, dict):
            raise PayPalError("Refund or reversal details are incomplete.")
        try:
            value = Decimal(str(amount.get("value")))
        except Exception as exc:
            raise PayPalError("Refund or reversal amount is invalid.") from exc
        currency = amount.get("currency_code")
        if not value.is_finite() or value <= 0 or currency != "USD":
            raise PayPalError("Refund or reversal amount or currency is invalid.")
        payment = (
            db.query(Payment)
            .filter(Payment.paypal_capture_id == capture_id)
            .with_for_update()
            .first()
        )
        if payment is None:
            return "ignored"
        event_id = event.get("id")
        financial_types = (
            "PAYMENT.CAPTURE.REFUNDED", "PAYMENT.CAPTURE.REVERSED"
        )
        prior = db.query(PaymentEvent).filter(
            PaymentEvent.payment_id == payment.id,
            PaymentEvent.event_type.in_(financial_types),
            PaymentEvent.paypal_ref == capture_id,
        ).all()
        recorded_ids = set()
        adjusted = Decimal("0")
        for row in prior:
            details = row.details or {}
            provider_event_id = details.get("provider_event_id")
            if not provider_event_id or provider_event_id in recorded_ids:
                continue
            recorded_ids.add(provider_event_id)
            try:
                adjusted += Decimal(str(details.get("amount", "0")))
            except Exception:
                continue
        already_recorded = event_id in recorded_ids
        if adjusted + (Decimal("0") if already_recorded else value) > payment.amount:
            raise PayPalError("Refund or reversal exceeds the captured amount.")
        if not already_recorded:
            try:
                _record_event(
                    db, payment, event_type, "WEBHOOK",
                    from_status=payment.status, to_status=payment.status,
                    paypal_ref=capture_id,
                    details={"provider_event_id": event_id, "capture_id": capture_id,
                             "amount": str(value), "currency": currency,
                             "provider_resource_id": resource.get("id"),
                             "resource": resource},
                )
                audit.record(
                    db, actor_id=None,
                    action=f"payment.{event_type.lower().removeprefix('payment.')}",
                    entity_type="payment", entity_id=payment.id,
                    details={"provider_event_id": event_id, "capture_id": capture_id,
                             "amount": str(value), "currency": currency},
                )
                project = payment.milestone.project
                recipients = {payment.payer_id}
                if project.freelancer_id is not None:
                    recipients.add(project.freelancer_id)
                for recipient_id in recipients:
                    notifications.notify(
                        db, user_id=recipient_id,
                        event_type=event_type.lower(),
                        payload={"payment_id": payment.id, "capture_id": capture_id,
                                 "amount": str(value), "currency": currency},
                    )
                db.commit()
            except Exception:
                db.rollback()
                raise
        return "processed"

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
        _restore_mock_order(payment)
        order = client.get_order(order_id)

        if order.get("id") != order_id:
            raise PayPalError(
                "PayPal returned an unexpected order ID."
            )

        try:
            _validate_order_amount(order, payment)
        except AmountMismatchError:
            _persist_amount_mismatch(db, payment, None, order_id)
            raise

        capture = _get_order_capture(order)
        if event_type.startswith("PAYMENT.CAPTURE.") and capture:
            try:
                _validate_amount_fields(capture.get("amount", {}), payment)
            except AmountMismatchError:
                _persist_amount_mismatch(db, payment, None, capture.get("id") or order_id)
                raise

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

            try:
                _validate_amount_fields(capture_amount, payment)
            except AmountMismatchError:
                _persist_amount_mismatch(db, payment, None, capture.get("id"))
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

            _mark_milestone_paid(db, payment, None)

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


def process_webhook(db: Session, *, headers: dict, raw_body: bytes) -> dict:
    """Receive, verify, deduplicate, reconcile, and persist webhook outcome."""
    receipt = receive_webhook(db, headers=headers, raw_body=raw_body)
    if receipt["status"] == "duplicate":
        return receipt

    record = db.query(PayPalWebhookEvent).filter_by(
        paypal_event_id=receipt["event_id"]
    ).with_for_update().one()
    try:
        if record.verification_status != "SUCCESS":
            return {"status": "failed", "event_id": receipt["event_id"]}
        outcome = apply_verified_webhook(db, event=record.payload)
        record.processing_status = (
            "PROCESSED" if outcome == "processed" else "IGNORED"
        )
        record.processed_at = datetime.now(timezone.utc)
        db.commit()
        return {"status": outcome, "event_id": receipt["event_id"]}
    except Exception as exc:
        db.rollback()
        record = db.query(PayPalWebhookEvent).filter_by(
            paypal_event_id=receipt["event_id"]
        ).with_for_update().one()
        record.processing_status = "FAILED"
        record.error = f"Webhook processing failed: {type(exc).__name__}"
        record.processed_at = datetime.now(timezone.utc)
        db.commit()
        return {"status": "failed", "event_id": receipt["event_id"]}
