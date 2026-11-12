from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import Milestone, Payment, Project, User, PayPalWebhookEvent
from app.payments.service import create_order_for_milestone
from app.payments.service import capture_payment
from app.models import AuditLog, Notification, PaymentEvent
from app.routers.mock_paypal import checkout, checkout_action
from app.routers.payments import project_payment_ledger


@pytest.fixture
def checkout_context(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine)
    db = factory()
    client_user = User(name="Client", email="client@mock.test", password_hash="x", role="client")
    freelancer = User(name="Freelancer", email="freelancer@mock.test", password_hash="x", role="freelancer")
    db.add_all([client_user, freelancer])
    db.flush()
    project = Project(title="Demo", description="Demo", budget=Decimal("300"), currency="USD", status="active", client_id=client_user.id, freelancer_id=freelancer.id)
    db.add(project)
    db.flush()
    milestone = Milestone(project_id=project.id, title="Landing page", description="Demo", amount=Decimal("300"), acceptance_criteria=["Done"], status="approved")
    db.add(milestone)
    db.commit()
    monkeypatch.setattr("app.routers.mock_paypal.settings.payments_mode", "mock")
    monkeypatch.setattr("app.payments.service.settings.payments_mode", "mock")

    yield db, client_user, milestone
    db.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _new_payment(db, user, milestone):
    return create_order_for_milestone(db, milestone_id=milestone.id, actor_id=user.id)


def test_checkout_is_labeled_and_approval_redirects(checkout_context):
    db, user, milestone = checkout_context
    payment = _new_payment(db, user, milestone)
    page = checkout(payment.paypal_order_id, db)
    assert "SIMULATED PAYMENTS" in page.body.decode()
    assert "Approve (SIMULATED)" in page.body.decode()
    response = checkout_action(payment.paypal_order_id, "approve", db)
    assert response.status_code == 303
    assert "payments/return" in response.headers["location"]
    assert f"payment_id={payment.id}" in response.headers["location"]


def test_checkout_rejection_and_cancel_update_payment_state(checkout_context):
    db, user, milestone = checkout_context
    rejected = _new_payment(db, user, milestone)
    response = checkout_action(rejected.paypal_order_id, "reject", db)
    assert response.status_code == 303
    db.refresh(rejected)
    assert rejected.status == "DENIED"

    cancelled = _new_payment(db, user, milestone)
    response = checkout_action(cancelled.paypal_order_id, "cancel", db)
    assert response.status_code == 303
    db.refresh(cancelled)
    assert cancelled.status == "CANCELLED"


def test_complete_mock_checkout_lifecycle(checkout_context):
    db, user, milestone = checkout_context
    payment = _new_payment(db, user, milestone)
    page = checkout(payment.paypal_order_id, db)
    assert "SIMULATED PAYMENTS" in page.body.decode()
    approved = checkout_action(payment.paypal_order_id, "approve", db)
    assert approved.status_code == 303
    db.refresh(payment)
    assert payment.status == "APPROVED"
    payment = capture_payment(db, payment_id=payment.id, actor_id=user.id, paypal_order_id=payment.paypal_order_id)
    db.refresh(milestone)
    assert payment.status == "COMPLETED"
    assert milestone.status == "paid"
    assert {"ORDER_REQUESTED", "ORDER_CREATED", "ORDER_APPROVED", "CAPTURE_COMPLETED"}.issubset(
        {event.event_type for event in db.query(PaymentEvent).filter_by(payment_id=payment.id)}
    )
    assert db.query(AuditLog).filter_by(entity_type="payment", entity_id=payment.id).count() >= 3
    assert db.query(Notification).filter_by(event_type="payment.completed").count() == 1


def test_checkout_is_disabled_outside_mock_mode(checkout_context, monkeypatch):
    from fastapi import HTTPException

    db, user, milestone = checkout_context
    payment = _new_payment(db, user, milestone)
    monkeypatch.setattr("app.routers.mock_paypal.settings.payments_mode", "paypal_sandbox")
    with pytest.raises(HTTPException) as exc:
        checkout(payment.paypal_order_id, db)
    assert exc.value.status_code == 404


def test_payment_ledger_includes_timeline_fields_and_totals(checkout_context):
    db, user, milestone = checkout_context
    payment = _new_payment(db, user, milestone)
    result = project_payment_ledger(milestone.project_id, db, user)
    payload = result.model_dump()
    assert payload["items"][0]["id"] == payment.id
    assert payload["items"][0]["milestone_title"] == milestone.title
    assert [event["event_type"] for event in payload["items"][0]["events"]] == [
        "ORDER_REQUESTED", "ORDER_CREATED",
    ]
    assert payload["items"][0]["webhook_verified"] is False
    assert payload["totals"]["pending"] == Decimal("300.00")
    assert payload["totals"]["remaining"] == Decimal("0.00")


@pytest.mark.parametrize(("adjustments", "expected_paid"), [
    ([], Decimal("300.00")),
    ([("PAYMENT.CAPTURE.REFUNDED", "100.00", "refund-1")], Decimal("200.00")),
    ([("PAYMENT.CAPTURE.REFUNDED", "300.00", "refund-1")], Decimal("0.00")),
    ([("PAYMENT.CAPTURE.REVERSED", "300.00", "reverse-1")], Decimal("0.00")),
    ([("PAYMENT.CAPTURE.REFUNDED", "50.00", "refund-1"),
      ("PAYMENT.CAPTURE.REFUNDED", "75.00", "refund-2")], Decimal("175.00")),
    ([("PAYMENT.CAPTURE.REFUNDED", "100.00", "same-event"),
      ("PAYMENT.CAPTURE.REFUNDED", "100.00", "same-event")], Decimal("200.00")),
])
def test_ledger_net_paid_accounts_for_unique_refunds_and_reversals(
    checkout_context, adjustments, expected_paid,
):
    db, user, milestone = checkout_context
    payment = _new_payment(db, user, milestone)
    payment.status = "COMPLETED"
    payment.paypal_capture_id = "CAPTURE-1"
    for index, (kind, amount, event_id) in enumerate(adjustments):
        db.add(PaymentEvent(
            payment_id=payment.id,
            event_type=kind,
            source="WEBHOOK",
            paypal_ref="CAPTURE-1",
            details={"amount": amount, "currency": "USD", "provider_event_id": event_id},
        ))
    db.commit()

    result = project_payment_ledger(milestone.project_id, db, user)
    assert result.totals.paid == expected_paid


def test_ledger_webhook_verification_ignores_unrelated_payment(checkout_context):
    db, user, milestone = checkout_context
    payment = _new_payment(db, user, milestone)
    db.add(PayPalWebhookEvent(
        paypal_event_id="unrelated-event",
        event_type="CHECKOUT.ORDER.APPROVED",
        resource_type="order",
        resource_id="UNRELATED-ORDER",
        verification_status="SUCCESS",
        processing_status="PROCESSED",
        payload={"resource": {"id": "UNRELATED-ORDER"}},
    ))
    db.commit()

    result = project_payment_ledger(milestone.project_id, db, user)
    assert result.items[0].webhook_verified is False


def test_ledger_remaining_balance_reopens_after_partial_refund(checkout_context):
    db, user, milestone = checkout_context
    payment = _new_payment(db, user, milestone)
    payment.status = "COMPLETED"
    db.add(PaymentEvent(
        payment_id=payment.id,
        event_type="PAYMENT.CAPTURE.REFUNDED",
        source="WEBHOOK",
        details={"amount": "100.00", "currency": "USD", "provider_event_id": "refund-1"},
    ))
    db.commit()

    result = project_payment_ledger(milestone.project_id, db, user)
    assert result.totals.paid == Decimal("200.00")
    assert result.totals.remaining == Decimal("100.00")
