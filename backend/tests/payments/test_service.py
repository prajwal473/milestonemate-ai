from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.payments.errors import PaymentAuthorizationError
from app.payments.service import cancel_payment
from app.db.base import Base
from app.models import (
    AuditLog,
    Milestone,
    Notification,
    Payment,
    PaymentEvent,
    Project,
    User,
)
from app.payments.mock_client import MockPaymentClient
from app.payments.webhook_service import apply_verified_webhook
from app.payments import webhook_service
from app.payments.service import (
    create_order_for_milestone,
    capture_payment,
    cancel_payment,
    sync_payment,
)
from app.payments.service import create_order_for_milestone
from app.payments.service import approve_mock_payment, reject_mock_payment
from app.payments.errors import PayPalError
from app.payments.paypal_client import PayPalResponseError


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def project_data(db):
    client = User(
        name="Test Client",
        email="client@example.com",
        password_hash="test",
        role="client",
    )

    freelancer = User(
        name="Test Freelancer",
        email="freelancer@example.com",
        password_hash="test",
        role="freelancer",
    )

    db.add_all([client, freelancer])
    db.flush()

    project = Project(
        title="Test Project",
        description="Payment service test",
        budget=Decimal("1000.00"),
        currency="USD",
        status="active",
        client_id=client.id,
        freelancer_id=freelancer.id,
    )

    db.add(project)
    db.flush()

    milestone = Milestone(
        project_id=project.id,
        title="Test Milestone",
        description="Test milestone",
        amount=Decimal("500.00"),
        acceptance_criteria=["Completed"],
        status="approved",
    )

    db.add(milestone)
    db.commit()

    return client, freelancer, project, milestone


def test_create_order_for_approved_milestone(
    db,
    project_data,
    monkeypatch,
):
    client, _, _, milestone = project_data

    monkeypatch.setattr(
        "app.payments.service.settings.payments_mode",
        "mock",
    )

    payment = create_order_for_milestone(
        db,
        milestone_id=milestone.id,
        actor_id=client.id,
    )

    assert payment.id is not None
    assert payment.milestone_id == milestone.id
    assert payment.payer_id == client.id
    assert payment.amount == Decimal("500.00")
    assert payment.currency == "USD"
    assert payment.provider == "MOCK"
    assert payment.status == "PENDING_APPROVAL"
    assert payment.paypal_order_id.startswith("MOCK_ORDER_")
    assert payment.approve_url is not None

    assert db.query(PaymentEvent).filter_by(
        payment_id=payment.id
    ).count() == 2
    assert db.query(AuditLog).filter_by(
        entity_id=payment.id,
        entity_type="payment",
    ).count() == 2


def test_repeated_create_reuses_existing_order(db, project_data, monkeypatch):
    client, _, _, milestone = project_data
    monkeypatch.setattr("app.payments.service.settings.payments_mode", "mock")
    first = create_order_for_milestone(db, milestone_id=milestone.id, actor_id=client.id)
    second = create_order_for_milestone(db, milestone_id=milestone.id, actor_id=client.id)
    assert second.id == first.id
    assert getattr(second, "_idempotent_reuse", False)
    assert db.query(Payment).filter_by(milestone_id=milestone.id).count() == 1


@pytest.mark.parametrize("status_code,expected_status", [(503, "CREATED"), (422, "FAILED")])
def test_paypal_order_creation_failure_is_recoverable(db, project_data, monkeypatch, status_code, expected_status):
    client, _, _, milestone = project_data
    monkeypatch.setattr("app.payments.service.settings.payments_mode", "paypal_sandbox")

    class FailingClient:
        def create_order(self, **kwargs):
            raise PayPalResponseError("PAYPAL_ERROR: unavailable", status_code=status_code)
        def close(self):
            pass

    monkeypatch.setattr("app.payments.service._get_payment_client", lambda _: FailingClient())
    with pytest.raises(PayPalError):
        create_order_for_milestone(db, milestone_id=milestone.id, actor_id=client.id)
    failed = db.query(Payment).filter_by(milestone_id=milestone.id).one()
    assert failed.status == expected_status
    assert failed.failure_code == "PAYPAL_ERROR"
    event_type = "ORDER_FAILED" if status_code == 422 else "ORDER_CREATE_RETRYABLE_FAILURE"
    assert db.query(PaymentEvent).filter_by(event_type=event_type).count() == 1


def test_retry_after_ambiguous_create_reuses_provider_request_id(db, project_data, monkeypatch):
    client, _, _, milestone = project_data
    monkeypatch.setattr("app.payments.service.settings.payments_mode", "paypal_sandbox")
    request_ids = []

    class RetryClient:
        def create_order(self, **kwargs):
            request_ids.append(kwargs["request_id"])
            if len(request_ids) == 1:
                raise PayPalResponseError("temporary provider error", status_code=503)
            return {
                "id": "SANDBOX_ORDER_RETRY",
                "status": "PAYER_ACTION_REQUIRED",
                "links": [{"rel": "payer-action", "href": "https://www.sandbox.paypal.com/checkoutnow?token=x"}],
            }
        def close(self):
            pass

    monkeypatch.setattr("app.payments.service._get_payment_client", lambda _: RetryClient())
    with pytest.raises(PayPalError):
        create_order_for_milestone(db, milestone_id=milestone.id, actor_id=client.id)
    payment = create_order_for_milestone(db, milestone_id=milestone.id, actor_id=client.id)
    assert payment.status == "PENDING_APPROVAL"
    assert request_ids[0] == request_ids[1]
    assert db.query(Payment).filter_by(milestone_id=milestone.id).count() == 1


def test_untrusted_provider_checkout_url_is_rejected(db, project_data, monkeypatch):
    client, _, _, milestone = project_data
    monkeypatch.setattr("app.payments.service.settings.payments_mode", "paypal_sandbox")

    class UnsafeLinkClient:
        def create_order(self, **kwargs):
            return {
                "id": "SANDBOX_ORDER_UNSAFE_LINK",
                "status": "CREATED",
                "links": [{"rel": "approve", "href": "https://attacker.invalid/checkout"}],
            }
        def close(self):
            pass

    monkeypatch.setattr("app.payments.service._get_payment_client", lambda _: UnsafeLinkClient())
    with pytest.raises(PayPalError, match="unsafe Sandbox checkout URL"):
        create_order_for_milestone(db, milestone_id=milestone.id, actor_id=client.id)
    payment = db.query(Payment).filter_by(milestone_id=milestone.id).one()
    assert payment.approve_url is None
    assert payment.status == "CREATED"


def test_untrusted_provider_checkout_url_is_rejected(db, project_data, monkeypatch):
    client, _, _, milestone = project_data
    monkeypatch.setattr("app.payments.service.settings.payments_mode", "paypal_sandbox")

    class UnsafeLinkClient:
        def create_order(self, **kwargs):
            return {
                "id": "SANDBOX_ORDER_UNSAFE_LINK",
                "status": "CREATED",
                "links": [{"rel": "approve", "href": "https://attacker.invalid/checkout"}],
            }
        def close(self):
            pass

    monkeypatch.setattr("app.payments.service._get_payment_client", lambda _: UnsafeLinkClient())
    with pytest.raises(PayPalError, match="unsafe Sandbox checkout URL"):
        create_order_for_milestone(db, milestone_id=milestone.id, actor_id=client.id)
    payment = db.query(Payment).filter_by(milestone_id=milestone.id).one()
    assert payment.approve_url is None
    assert payment.status == "CREATED"


def test_mock_rejection_is_audited_and_retryable(db, project_data, monkeypatch):
    client, _, _, milestone = project_data
    monkeypatch.setattr("app.payments.service.settings.payments_mode", "mock")
    payment = create_order_for_milestone(db, milestone_id=milestone.id, actor_id=client.id)
    rejected = reject_mock_payment(db, order_id=payment.paypal_order_id)
    assert rejected.status == "DENIED"
    assert rejected.failure_code == "SIMULATED_REJECTION"
    assert db.query(PaymentEvent).filter_by(event_type="PAYMENT_REJECTED").count() == 1
    assert db.query(AuditLog).filter_by(action="payment.denied").count() == 1
    retry = create_order_for_milestone(db, milestone_id=milestone.id, actor_id=client.id)
    assert retry.id != payment.id
    retry = create_order_for_milestone(db, milestone_id=milestone.id, actor_id=client.id)
    assert retry.id != payment.id


def test_capture_amount_mismatch_fails_without_marking_milestone_paid(
    db, project_data, monkeypatch
):
    from app.payments.errors import AmountMismatchError

    client, _, _, milestone = project_data
    monkeypatch.setattr("app.payments.service.settings.payments_mode", "mock")
    payment = create_order_for_milestone(db, milestone_id=milestone.id, actor_id=client.id)
    MockPaymentClient.approve_order(payment.paypal_order_id)

    class MismatchedCaptureClient:
        def get_order(self, order_id):
            return {"id": order_id, "status": "APPROVED", "purchase_units": [{
                "amount": {"currency_code": "USD", "value": "500.00"}
            }]}

        def capture_order(self, order_id, request_id):
            return {"status": "COMPLETED", "purchase_units": [{"payments": {
                "captures": [{"id": "CAPTURE-X", "status": "COMPLETED",
                    "amount": {"currency_code": "USD", "value": "499.00"}}]
            }}]}

        def close(self):
            pass

    monkeypatch.setattr("app.payments.service._get_payment_client", lambda _: MismatchedCaptureClient())
    with pytest.raises(AmountMismatchError):
        capture_payment(db, payment_id=payment.id, actor_id=client.id, paypal_order_id=payment.paypal_order_id)
    db.refresh(payment)
    db.refresh(milestone)
    assert payment.status == "FAILED"
    assert payment.failure_code == "AMOUNT_MISMATCH"
    assert milestone.status == "approved"

def test_create_order_rejects_freelancer(
    db,
    project_data,
    monkeypatch,
):
    _, freelancer, _, milestone = project_data

    monkeypatch.setattr(
        "app.payments.service.settings.payments_mode",
        "mock",
    )

    with pytest.raises(PermissionError):
        create_order_for_milestone(
            db,
            milestone_id=milestone.id,
            actor_id=freelancer.id,
        )

    assert db.query(Payment).count() == 0

def test_capture_payment_success(
    db,
    project_data,
    monkeypatch,
):
    client, freelancer, _, milestone = project_data

    monkeypatch.setattr(
        "app.payments.service.settings.payments_mode",
        "mock",
    )

    payment = create_order_for_milestone(
        db,
        milestone_id=milestone.id,
        actor_id=client.id,
    )

    # Simulate the client approving the mock checkout.
    MockPaymentClient.approve_order(payment.paypal_order_id)

    captured_payment = capture_payment(
        db,
        payment_id=payment.id,
        actor_id=client.id,
        paypal_order_id=payment.paypal_order_id,
    )

    db.refresh(milestone)

    assert captured_payment.status == "COMPLETED"
    assert captured_payment.paypal_capture_id is not None
    assert captured_payment.captured_at is not None
    assert milestone.status == "paid"

    assert db.query(PaymentEvent).filter_by(
        payment_id=payment.id
    ).count() == 4

    assert db.query(Notification).filter_by(
        user_id=freelancer.id,
        event_type="payment.completed",
    ).count() == 1


def test_capture_payment_rejects_wrong_client(
    db,
    project_data,
    monkeypatch,
):
    client, freelancer, _, milestone = project_data

    monkeypatch.setattr(
        "app.payments.service.settings.payments_mode",
        "mock",
    )

    payment = create_order_for_milestone(
        db,
        milestone_id=milestone.id,
        actor_id=client.id,
    )

    with pytest.raises(PaymentAuthorizationError):
        capture_payment(
            db,
            payment_id=payment.id,
            actor_id=freelancer.id,
            paypal_order_id=payment.paypal_order_id,
        )

    db.refresh(payment)
    assert payment.status == "PENDING_APPROVAL"


def test_capture_payment_is_idempotent(
    db,
    project_data,
    monkeypatch,
):
    client, freelancer, _, milestone = project_data

    monkeypatch.setattr(
        "app.payments.service.settings.payments_mode",
        "mock",
    )

    payment = create_order_for_milestone(
        db,
        milestone_id=milestone.id,
        actor_id=client.id,
    )

    MockPaymentClient.approve_order(payment.paypal_order_id)

    first_result = capture_payment(
        db,
        payment_id=payment.id,
        actor_id=client.id,
        paypal_order_id=payment.paypal_order_id,
    )

    event_count = db.query(PaymentEvent).filter_by(
        payment_id=payment.id
    ).count()

    second_result = capture_payment(
        db,
        payment_id=payment.id,
        actor_id=client.id,
        paypal_order_id=payment.paypal_order_id,
    )

    assert first_result.paypal_capture_id == second_result.paypal_capture_id
    assert second_result.status == "COMPLETED"
    assert db.query(PaymentEvent).filter_by(payment_id=payment.id).count() == event_count
    assert db.query(Notification).filter_by(
        user_id=freelancer.id, event_type="payment.completed"
    ).count() == 1


def test_already_captured_provider_error_reconciles_instead_of_failing(db, project_data, monkeypatch):
    client, _, _, milestone = project_data
    monkeypatch.setattr("app.payments.service.settings.payments_mode", "mock")
    payment = create_order_for_milestone(db, milestone_id=milestone.id, actor_id=client.id)
    order_reads = 0

    class AlreadyCapturedClient:
        def get_order(self, order_id):
            nonlocal order_reads
            order_reads += 1
            if order_reads == 1:
                return {"id": order_id, "status": "APPROVED", "purchase_units": [{
                    "amount": {"currency_code": "USD", "value": "500.00"}
                }]}
            return {"id": order_id, "status": "COMPLETED", "purchase_units": [{
                "amount": {"currency_code": "USD", "value": "500.00"},
                "payments": {"captures": [{"id": "CAPTURE-ALREADY-DONE", "status": "COMPLETED",
                    "amount": {"currency_code": "USD", "value": "500.00"}}]},
            }]}
        def capture_order(self, order_id, request_id):
            raise PayPalResponseError("ORDER_ALREADY_CAPTURED", code="ORDER_ALREADY_CAPTURED", status_code=422)
        def close(self):
            pass

    monkeypatch.setattr("app.payments.service._get_payment_client", lambda _: AlreadyCapturedClient())
    result = capture_payment(
        db, payment_id=payment.id, actor_id=client.id,
        paypal_order_id=payment.paypal_order_id,
    )
    assert result.status == "COMPLETED"
    assert result.paypal_capture_id == "CAPTURE-ALREADY-DONE"


def test_already_captured_provider_error_reconciles_instead_of_failing(db, project_data, monkeypatch):
    client, _, _, milestone = project_data
    monkeypatch.setattr("app.payments.service.settings.payments_mode", "mock")
    payment = create_order_for_milestone(db, milestone_id=milestone.id, actor_id=client.id)
    order_reads = 0

    class AlreadyCapturedClient:
        def get_order(self, order_id):
            nonlocal order_reads
            order_reads += 1
            if order_reads == 1:
                return {"id": order_id, "status": "APPROVED", "purchase_units": [{
                    "amount": {"currency_code": "USD", "value": "500.00"}
                }]}
            return {"id": order_id, "status": "COMPLETED", "purchase_units": [{
                "amount": {"currency_code": "USD", "value": "500.00"},
                "payments": {"captures": [{"id": "CAPTURE-ALREADY-DONE", "status": "COMPLETED",
                    "amount": {"currency_code": "USD", "value": "500.00"}}]},
            }]}
        def capture_order(self, order_id, request_id):
            raise PayPalResponseError("ORDER_ALREADY_CAPTURED", code="ORDER_ALREADY_CAPTURED", status_code=422)
        def close(self):
            pass

    monkeypatch.setattr("app.payments.service._get_payment_client", lambda _: AlreadyCapturedClient())
    result = capture_payment(
        db, payment_id=payment.id, actor_id=client.id,
        paypal_order_id=payment.paypal_order_id,
    )
    assert result.status == "COMPLETED"
    assert result.paypal_capture_id == "CAPTURE-ALREADY-DONE"


def test_mock_approval_and_capture_survive_provider_memory_reset(db, project_data, monkeypatch):
    client, _, _, milestone = project_data
    monkeypatch.setattr("app.payments.service.settings.payments_mode", "mock")
    payment = create_order_for_milestone(db, milestone_id=milestone.id, actor_id=client.id)
    MockPaymentClient._orders.pop(payment.paypal_order_id, None)
    approved = approve_mock_payment(db, order_id=payment.paypal_order_id)
    assert approved.status == "APPROVED"
    MockPaymentClient._orders.pop(payment.paypal_order_id, None)
    result = capture_payment(
        db, payment_id=payment.id, actor_id=client.id,
        paypal_order_id=payment.paypal_order_id,
    )
    assert result.status == "COMPLETED"


def test_approved_webhook_never_captures_automatically(db, project_data, monkeypatch):
    client, _, _, milestone = project_data
    monkeypatch.setattr("app.payments.service.settings.payments_mode", "mock")
    payment = create_order_for_milestone(db, milestone_id=milestone.id, actor_id=client.id)
    MockPaymentClient.approve_order(payment.paypal_order_id)
    result = apply_verified_webhook(db, event={
        "id": "WH-APPROVED", "event_type": "CHECKOUT.ORDER.APPROVED",
        "resource": {"id": payment.paypal_order_id},
    })
    db.refresh(payment)
    db.refresh(milestone)
    assert result == "processed"
    assert payment.status == "APPROVED"
    assert milestone.status == "approved"
    assert db.query(PaymentEvent).filter_by(event_type="CAPTURE_COMPLETED").count() == 0


@pytest.mark.parametrize("event_type", [
    "PAYMENT.CAPTURE.REFUNDED", "PAYMENT.CAPTURE.REVERSED",
])
def test_refund_and_reversal_webhooks_are_audited_without_rewriting_payment_state(
    db, project_data, monkeypatch, event_type
):
    client, _, _, milestone = project_data
    monkeypatch.setattr("app.payments.service.settings.payments_mode", "mock")
    payment = create_order_for_milestone(db, milestone_id=milestone.id, actor_id=client.id)
    MockPaymentClient.approve_order(payment.paypal_order_id)
    completed = capture_payment(
        db, payment_id=payment.id, actor_id=client.id,
        paypal_order_id=payment.paypal_order_id,
    )
    result = apply_verified_webhook(db, event={
        "id": f"WH-{event_type}", "event_type": event_type,
        "resource": {
            "id": f"RESOURCE-{event_type}",
            "amount": {"value": str(completed.amount), "currency_code": "USD"},
            "supplementary_data": {"related_ids": {"capture_id": completed.paypal_capture_id}},
        },
    })
    db.refresh(payment)
    assert result == "processed"
    assert payment.status == "COMPLETED"
    assert db.query(PaymentEvent).filter_by(event_type=event_type).count() == 1
    audit_action = f"payment.capture.{event_type.rsplit('.', 1)[1].lower()}"
    assert db.query(AuditLog).filter_by(action=audit_action).count() == 1
    assert apply_verified_webhook(db, event={
        "id": f"WH-{event_type}", "event_type": event_type,
        "resource": {
            "id": f"RESOURCE-{event_type}",
            "amount": {"value": str(completed.amount), "currency_code": "USD"},
            "supplementary_data": {"related_ids": {"capture_id": completed.paypal_capture_id}},
        },
    }) == "processed"
    assert db.query(PaymentEvent).filter_by(event_type=event_type).count() == 1


def test_partial_refund_records_financial_details_and_preserves_status(db, project_data, monkeypatch):
    client, _, _, milestone = project_data
    monkeypatch.setattr("app.payments.service.settings.payments_mode", "mock")
    payment = create_order_for_milestone(db, milestone_id=milestone.id, actor_id=client.id)
    MockPaymentClient.approve_order(payment.paypal_order_id)
    payment = capture_payment(db, payment_id=payment.id, actor_id=client.id, paypal_order_id=payment.paypal_order_id)
    event = {"id": "WH-PARTIAL-REFUND", "event_type": "PAYMENT.CAPTURE.REFUNDED", "resource": {
        "id": "REFUND-1", "amount": {"value": "12.50", "currency_code": "USD"},
        "supplementary_data": {"related_ids": {"capture_id": payment.paypal_capture_id}},
    }}
    assert apply_verified_webhook(db, event=event) == "processed"
    record = db.query(PaymentEvent).filter_by(event_type="PAYMENT.CAPTURE.REFUNDED").one()
    assert payment.status == "COMPLETED"
    assert record.details["amount"] == "12.50"
    assert record.details["currency"] == "USD"
    assert record.details["provider_event_id"] == "WH-PARTIAL-REFUND"


def test_cumulative_partial_refunds_within_capture_are_recorded(db, project_data, monkeypatch):
    client, _, _, milestone = project_data
    monkeypatch.setattr("app.payments.service.settings.payments_mode", "mock")
    payment = create_order_for_milestone(db, milestone_id=milestone.id, actor_id=client.id)
    MockPaymentClient.approve_order(payment.paypal_order_id)
    payment = capture_payment(db, payment_id=payment.id, actor_id=client.id, paypal_order_id=payment.paypal_order_id)
    for event_id, amount in (("WH-REFUND-A", "30.00"), ("WH-REFUND-B", "40.00")):
        assert apply_verified_webhook(db, event={
            "id": event_id, "event_type": "PAYMENT.CAPTURE.REFUNDED",
            "resource": {"id": f"REFUND-{event_id}", "amount": {"value": amount, "currency_code": "USD"},
                         "supplementary_data": {"related_ids": {"capture_id": payment.paypal_capture_id}}},
        }) == "processed"
    records = db.query(PaymentEvent).filter_by(event_type="PAYMENT.CAPTURE.REFUNDED").all()
    assert sum(Decimal(row.details["amount"]) for row in records) == Decimal("70.00")


def test_cumulative_refunds_over_capture_are_rejected(db, project_data, monkeypatch):
    client, _, _, milestone = project_data
    monkeypatch.setattr("app.payments.service.settings.payments_mode", "mock")
    payment = create_order_for_milestone(db, milestone_id=milestone.id, actor_id=client.id)
    MockPaymentClient.approve_order(payment.paypal_order_id)
    payment = capture_payment(db, payment_id=payment.id, actor_id=client.id, paypal_order_id=payment.paypal_order_id)
    maximum = payment.amount
    for event_id, amount in (("WH-REFUND-A", maximum - Decimal("1.00")), ("WH-REFUND-B", Decimal("1.01"))):
        event = {"id": event_id, "event_type": "PAYMENT.CAPTURE.REFUNDED", "resource": {
            "id": f"REFUND-{event_id}", "amount": {"value": str(amount), "currency_code": "USD"},
            "supplementary_data": {"related_ids": {"capture_id": payment.paypal_capture_id}},
        }}
        if event_id.endswith("A"):
            assert apply_verified_webhook(db, event=event) == "processed"
        else:
            with pytest.raises(PayPalError, match="exceeds the captured amount"):
                apply_verified_webhook(db, event=event)
    assert db.query(PaymentEvent).filter_by(event_type="PAYMENT.CAPTURE.REFUNDED").count() == 1


def test_duplicate_financial_event_does_not_increase_total_or_notify_twice(db, project_data, monkeypatch):
    client, _, _, milestone = project_data
    monkeypatch.setattr("app.payments.service.settings.payments_mode", "mock")
    payment = create_order_for_milestone(db, milestone_id=milestone.id, actor_id=client.id)
    MockPaymentClient.approve_order(payment.paypal_order_id)
    payment = capture_payment(db, payment_id=payment.id, actor_id=client.id, paypal_order_id=payment.paypal_order_id)
    event = {"id": "WH-REFUND-DUP", "event_type": "PAYMENT.CAPTURE.REFUNDED", "resource": {
        "id": "REFUND-DUP", "amount": {"value": "25.00", "currency_code": "USD"},
        "supplementary_data": {"related_ids": {"capture_id": payment.paypal_capture_id}},
    }}
    assert apply_verified_webhook(db, event=event) == "processed"
    initial_notifications = db.query(Notification).filter_by(event_type="payment.capture.refunded").count()
    assert initial_notifications > 0
    assert apply_verified_webhook(db, event=event) == "processed"
    records = db.query(PaymentEvent).filter_by(event_type="PAYMENT.CAPTURE.REFUNDED").all()
    assert sum(Decimal(row.details["amount"]) for row in records) == Decimal("25.00")
    assert db.query(Notification).filter_by(event_type="payment.capture.refunded").count() == initial_notifications


def test_refund_notification_failure_rolls_back_and_retry_notifies_each_recipient(
    db, project_data, monkeypatch
):
    client, freelancer, _, milestone = project_data
    monkeypatch.setattr("app.payments.service.settings.payments_mode", "mock")
    payment = create_order_for_milestone(db, milestone_id=milestone.id, actor_id=client.id)
    MockPaymentClient.approve_order(payment.paypal_order_id)
    payment = capture_payment(
        db, payment_id=payment.id, actor_id=client.id,
        paypal_order_id=payment.paypal_order_id,
    )
    event = {"id": "WH-REFUND-RETRY", "event_type": "PAYMENT.CAPTURE.REFUNDED", "resource": {
        "id": "REFUND-RETRY", "amount": {"value": "25.00", "currency_code": "USD"},
        "supplementary_data": {"related_ids": {"capture_id": payment.paypal_capture_id}},
    }}
    original_notify = webhook_service.notifications.notify
    calls = 0

    def fail_after_one_notification(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("notification storage failed")
        return original_notify(*args, **kwargs)

    monkeypatch.setattr(
        "app.payments.webhook_service.notifications.notify", fail_after_one_notification
    )
    with pytest.raises(RuntimeError, match="notification storage failed"):
        apply_verified_webhook(db, event=event)

    assert db.query(PaymentEvent).filter_by(
        event_type="PAYMENT.CAPTURE.REFUNDED"
    ).count() == 0
    action = "payment.capture.refunded"
    assert db.query(AuditLog).filter_by(action=action).count() == 0
    assert db.query(Notification).filter_by(event_type="payment.capture.refunded").count() == 0

    monkeypatch.setattr(
        "app.payments.webhook_service.notifications.notify", original_notify
    )
    assert apply_verified_webhook(db, event=event) == "processed"
    assert db.query(PaymentEvent).filter_by(
        event_type="PAYMENT.CAPTURE.REFUNDED"
    ).count() == 1
    assert db.query(AuditLog).filter_by(action=action).count() == 1
    notifications = db.query(Notification).filter_by(
        event_type="payment.capture.refunded"
    ).all()
    assert len(notifications) == 2
    assert {notification.user_id for notification in notifications} == {
        client.id, freelancer.id
    }


def test_reversal_cannot_exceed_remaining_capture_amount(db, project_data, monkeypatch):
    client, _, _, milestone = project_data
    monkeypatch.setattr("app.payments.service.settings.payments_mode", "mock")
    payment = create_order_for_milestone(db, milestone_id=milestone.id, actor_id=client.id)
    MockPaymentClient.approve_order(payment.paypal_order_id)
    payment = capture_payment(db, payment_id=payment.id, actor_id=client.id, paypal_order_id=payment.paypal_order_id)
    refund = {"id": "WH-REFUND", "event_type": "PAYMENT.CAPTURE.REFUNDED", "resource": {
        "id": "REFUND", "amount": {"value": str(payment.amount - Decimal("5.00")), "currency_code": "USD"},
        "supplementary_data": {"related_ids": {"capture_id": payment.paypal_capture_id}},
    }}
    assert apply_verified_webhook(db, event=refund) == "processed"
    reversal = {"id": "WH-REVERSAL", "event_type": "PAYMENT.CAPTURE.REVERSED", "resource": {
        "id": "REVERSAL", "amount": {"value": "5.01", "currency_code": "USD"},
        "supplementary_data": {"related_ids": {"capture_id": payment.paypal_capture_id}},
    }}
    with pytest.raises(PayPalError, match="exceeds the captured amount"):
        apply_verified_webhook(db, event=reversal)
    assert db.query(PaymentEvent).filter_by(event_type="PAYMENT.CAPTURE.REVERSED").count() == 0


@pytest.mark.parametrize("amount,currency", [("0", "USD"), ("999999", "USD"), ("1", "EUR")])
def test_invalid_refund_is_not_recorded(db, project_data, monkeypatch, amount, currency):
    client, _, _, milestone = project_data
    monkeypatch.setattr("app.payments.service.settings.payments_mode", "mock")
    payment = create_order_for_milestone(db, milestone_id=milestone.id, actor_id=client.id)
    MockPaymentClient.approve_order(payment.paypal_order_id)
    payment = capture_payment(db, payment_id=payment.id, actor_id=client.id, paypal_order_id=payment.paypal_order_id)
    event = {"id": "WH-INVALID-REFUND", "event_type": "PAYMENT.CAPTURE.REFUNDED", "resource": {
        "id": "REFUND-INVALID", "amount": {"value": amount, "currency_code": currency},
        "supplementary_data": {"related_ids": {"capture_id": payment.paypal_capture_id}},
    }}
    with pytest.raises(Exception):
        apply_verified_webhook(db, event=event)
    assert db.query(PaymentEvent).filter_by(event_type="PAYMENT.CAPTURE.REFUNDED").count() == 0


def test_refund_unknown_capture_is_ignored(db):
    assert apply_verified_webhook(db, event={"id": "WH-UNKNOWN-CAPTURE", "event_type": "PAYMENT.CAPTURE.REFUNDED", "resource": {
        "id": "REFUND-UNKNOWN", "amount": {"value": "1.00", "currency_code": "USD"},
        "supplementary_data": {"related_ids": {"capture_id": "UNKNOWN"}},
    }}) == "ignored"

def test_cancel_pending_payment(db, project_data, monkeypatch):
    client, _, _, milestone = project_data

    monkeypatch.setattr(
        "app.payments.service.settings.payments_mode",
        "mock",
    )

    payment = create_order_for_milestone(
        db,
        milestone_id=milestone.id,
        actor_id=client.id,
    )

    cancelled = cancel_payment(
        db,
        payment_id=payment.id,
        actor_id=client.id,
    )

    assert cancelled.status == "CANCELLED"


def test_cancel_payment_is_idempotent(db, project_data, monkeypatch):
    client, _, _, milestone = project_data

    monkeypatch.setattr(
        "app.payments.service.settings.payments_mode",
        "mock",
    )

    payment = create_order_for_milestone(
        db,
        milestone_id=milestone.id,
        actor_id=client.id,
    )

    first = cancel_payment(
        db,
        payment_id=payment.id,
        actor_id=client.id,
    )

    event_count = db.query(PaymentEvent).filter_by(
        payment_id=payment.id
    ).count()

    second = cancel_payment(
        db,
        payment_id=payment.id,
        actor_id=client.id,
    )

    assert first.status == "CANCELLED"
    assert second.status == "CANCELLED"

    assert db.query(PaymentEvent).filter_by(
        payment_id=payment.id
    ).count() == event_count


def test_cancel_payment_rejects_freelancer(
    db,
    project_data,
    monkeypatch,
):
    client, freelancer, _, milestone = project_data

    monkeypatch.setattr(
        "app.payments.service.settings.payments_mode",
        "mock",
    )

    payment = create_order_for_milestone(
        db,
        milestone_id=milestone.id,
        actor_id=client.id,
    )

    with pytest.raises(PaymentAuthorizationError):
        cancel_payment(
            db,
            payment_id=payment.id,
            actor_id=freelancer.id,
        )

    db.refresh(payment)
    assert payment.status == "PENDING_APPROVAL"

def test_sync_approved_order(db, project_data, monkeypatch):
    client, _, _, milestone = project_data

    monkeypatch.setattr(
        "app.payments.service.settings.payments_mode",
        "mock",
    )

    payment = create_order_for_milestone(
        db,
        milestone_id=milestone.id,
        actor_id=client.id,
    )

    MockPaymentClient.approve_order(payment.paypal_order_id)

    result = sync_payment(
        db,
        payment_id=payment.id,
        actor_id=client.id,
    )

    assert result.status == "APPROVED"
    assert result.approved_at is not None

def test_sync_completed_order(db, project_data, monkeypatch):
    client, freelancer, _, milestone = project_data

    monkeypatch.setattr(
        "app.payments.service.settings.payments_mode",
        "mock",
    )

    payment = create_order_for_milestone(
        db,
        milestone_id=milestone.id,
        actor_id=client.id,
    )

    MockPaymentClient.approve_order(payment.paypal_order_id)

    mock_client = MockPaymentClient()
    mock_client.capture_order(
        payment.paypal_order_id,
        request_id="sync-test-capture",
    )

    result = sync_payment(
        db,
        payment_id=payment.id,
        actor_id=client.id,
    )

    db.refresh(milestone)

    assert result.status == "COMPLETED"
    assert result.paypal_capture_id is not None
    assert milestone.status == "paid"

    assert db.query(Notification).filter_by(
        user_id=freelancer.id,
        event_type="payment.completed",
    ).count() == 1
def test_sync_rejects_wrong_user(db, project_data, monkeypatch):
    client, _, _, milestone = project_data
    outsider = User(name="Outsider", email="outsider@example.com", password_hash="test", role="client")
    db.add(outsider)
    db.commit()

    monkeypatch.setattr(
        "app.payments.service.settings.payments_mode",
        "mock",
    )

    payment = create_order_for_milestone(
        db,
        milestone_id=milestone.id,
        actor_id=client.id,
    )

    with pytest.raises(PaymentAuthorizationError):
        sync_payment(
            db,
            payment_id=payment.id,
            actor_id=outsider.id,
        )
def test_sync_completed_order_is_idempotent(
    db,
    project_data,
    monkeypatch,
):
    client, freelancer, _, milestone = project_data

    monkeypatch.setattr(
        "app.payments.service.settings.payments_mode",
        "mock",
    )

    payment = create_order_for_milestone(
        db,
        milestone_id=milestone.id,
        actor_id=client.id,
    )

    MockPaymentClient.approve_order(payment.paypal_order_id)

    MockPaymentClient().capture_order(
        payment.paypal_order_id,
        request_id="sync-idempotency-test",
    )

    first = sync_payment(
        db,
        payment_id=payment.id,
        actor_id=client.id,
    )

    event_count = db.query(PaymentEvent).filter_by(
        payment_id=payment.id
    ).count()

    second = sync_payment(
        db,
        payment_id=payment.id,
        actor_id=client.id,
    )

    assert first.status == "COMPLETED"
    assert second.status == "COMPLETED"
    assert first.paypal_capture_id == second.paypal_capture_id

    assert db.query(PaymentEvent).filter_by(
        payment_id=payment.id
    ).count() == event_count

    assert db.query(Notification).filter_by(
        user_id=freelancer.id,
        event_type="payment.completed",
    ).count() == 1

def test_webhook_completes_payment(
    db,
    project_data,
    monkeypatch,
):
    client, freelancer, _, milestone = project_data

    monkeypatch.setattr(
        "app.payments.service.settings.payments_mode",
        "mock",
    )

    payment = create_order_for_milestone(
        db,
        milestone_id=milestone.id,
        actor_id=client.id,
    )

    MockPaymentClient.approve_order(payment.paypal_order_id)

    MockPaymentClient().capture_order(
        payment.paypal_order_id,
        request_id="webhook-test-capture",
    )

    event = {
        "id": "WH-TEST-COMPLETED",
        "event_type": "PAYMENT.CAPTURE.COMPLETED",
        "resource": {
            "id": "CAPTURE-TEST",
            "supplementary_data": {
                "related_ids": {
                    "order_id": payment.paypal_order_id,
                },
            },
        },
    }

    result = apply_verified_webhook(db, event=event)

    db.refresh(payment)
    db.refresh(milestone)

    assert result == "processed"
    assert payment.status == "COMPLETED"
    assert payment.paypal_capture_id is not None
    assert milestone.status == "paid"

    assert db.query(Notification).filter_by(
        user_id=freelancer.id,
        event_type="payment.completed",
    ).count() == 1

def test_webhook_completion_is_idempotent(
    db,
    project_data,
    monkeypatch,
):
    client, freelancer, _, milestone = project_data

    monkeypatch.setattr(
        "app.payments.service.settings.payments_mode",
        "mock",
    )

    payment = create_order_for_milestone(
        db,
        milestone_id=milestone.id,
        actor_id=client.id,
    )

    MockPaymentClient.approve_order(payment.paypal_order_id)

    MockPaymentClient().capture_order(
        payment.paypal_order_id,
        request_id="webhook-idempotency-test",
    )

    event = {
        "id": "WH-TEST-IDEMPOTENT",
        "event_type": "PAYMENT.CAPTURE.COMPLETED",
        "resource": {
            "id": "CAPTURE-TEST",
            "supplementary_data": {
                "related_ids": {
                    "order_id": payment.paypal_order_id,
                },
            },
        },
    }

    first = apply_verified_webhook(db, event=event)

    event_count = db.query(PaymentEvent).filter_by(
        payment_id=payment.id,
    ).count()

    second = apply_verified_webhook(db, event=event)

    assert first == "processed"
    assert second == "processed"

    assert db.query(PaymentEvent).filter_by(
        payment_id=payment.id,
    ).count() == event_count

    assert db.query(Notification).filter_by(
        user_id=freelancer.id,
        event_type="payment.completed",
    ).count() == 1

def test_webhook_order_approved_does_not_capture(
    db,
    project_data,
    monkeypatch,
):
    client, _, _, milestone = project_data

    monkeypatch.setattr(
        "app.payments.service.settings.payments_mode",
        "mock",
    )

    payment = create_order_for_milestone(
        db,
        milestone_id=milestone.id,
        actor_id=client.id,
    )

    MockPaymentClient.approve_order(payment.paypal_order_id)

    event = {
        "id": "WH-TEST-APPROVED",
        "event_type": "CHECKOUT.ORDER.APPROVED",
        "resource": {
            "id": payment.paypal_order_id,
        },
    }

    result = apply_verified_webhook(db, event=event)

    db.refresh(payment)

    assert result == "processed"
    assert payment.status == "APPROVED"
    assert payment.approved_at is not None
    assert payment.paypal_capture_id is None

def test_webhook_denied_capture(
    db,
    project_data,
    monkeypatch,
):
    client, _, _, milestone = project_data

    monkeypatch.setattr(
        "app.payments.service.settings.payments_mode",
        "mock",
    )

    payment = create_order_for_milestone(
        db,
        milestone_id=milestone.id,
        actor_id=client.id,
    )

    class FakeClient:
        def get_order(self, order_id):
            return {
                "id": order_id,
                "status": "APPROVED",
                "purchase_units": [
                    {
                        "amount": {
                            "currency_code": "USD",
                            "value": "500.00",
                        },
                        "payments": {
                            "captures": [
                                {
                                    "id": "CAPTURE-DENIED",
                                    "status": "DENIED",
                                        "amount": {"currency_code": "USD", "value": "500.00"},
                                }
                            ]
                        },
                    }
                ],
            }

        def close(self):
            pass

    monkeypatch.setattr(
        "app.payments.webhook_service._get_payment_client",
        lambda provider: FakeClient(),
    )

    event = {
        "id": "WH-TEST-DENIED",
        "event_type": "PAYMENT.CAPTURE.DENIED",
        "resource": {
            "id": "CAPTURE-DENIED",
            "supplementary_data": {
                "related_ids": {
                    "order_id": payment.paypal_order_id,
                },
            },
        },
    }

    result = apply_verified_webhook(db, event=event)

    db.refresh(payment)

    assert result == "processed"
    assert payment.status == "DENIED"
    assert payment.paypal_capture_status == "DENIED"

    assert db.query(Notification).filter_by(
        user_id=client.id,
        event_type="payment.denied",
    ).count() == 1

def test_webhook_pending_capture(
    db,
    project_data,
    monkeypatch,
):
    client, _, _, milestone = project_data

    monkeypatch.setattr(
        "app.payments.service.settings.payments_mode",
        "mock",
    )

    payment = create_order_for_milestone(
        db,
        milestone_id=milestone.id,
        actor_id=client.id,
    )

    class FakeClient:
        def get_order(self, order_id):
            return {
                "id": order_id,
                "status": "APPROVED",
                "purchase_units": [
                    {
                        "amount": {
                            "currency_code": "USD",
                            "value": "500.00",
                        },
                        "payments": {
                            "captures": [
                                {
                                    "id": "CAPTURE-PENDING",
                                    "status": "PENDING",
                                        "amount": {"currency_code": "USD", "value": "500.00"},
                                }
                            ]
                        },
                    }
                ],
            }

        def close(self):
            pass

    monkeypatch.setattr(
        "app.payments.webhook_service._get_payment_client",
        lambda provider: FakeClient(),
    )

    event = {
        "id": "WH-TEST-PENDING",
        "event_type": "PAYMENT.CAPTURE.PENDING",
        "resource": {
            "id": "CAPTURE-PENDING",
            "supplementary_data": {
                "related_ids": {
                    "order_id": payment.paypal_order_id,
                },
            },
        },
    }

    result = apply_verified_webhook(db, event=event)

    db.refresh(payment)

    assert result == "processed"
    assert payment.status == "CAPTURE_PENDING"
    assert payment.paypal_capture_status == "PENDING"
