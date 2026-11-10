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
from app.payments.service import (
    create_order_for_milestone,
    capture_payment,
    cancel_payment,
    sync_payment,
)
from app.payments.service import create_order_for_milestone


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
    ).count() == 1

    assert db.query(AuditLog).filter_by(
        entity_id=payment.id,
        entity_type="payment",
    ).count() == 1


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
    ).count() == 3

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

    assert db.query(PaymentEvent).filter_by(
        payment_id=payment.id
    ).count() == event_count

    assert db.query(Notification).filter_by(
        user_id=freelancer.id,
        event_type="payment.completed",
    ).count() == 1

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
        sync_payment(
            db,
            payment_id=payment.id,
            actor_id=freelancer.id,
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
