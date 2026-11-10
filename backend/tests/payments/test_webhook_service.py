import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import PayPalWebhookEvent
from app.payments.webhook_service import receive_webhook


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


class FakePayPalClient:
    def verify_webhook_signature(self, headers, raw_body):
        return {"verification_status": "SUCCESS"}

    def close(self):
        pass


def test_receive_verified_webhook(db, monkeypatch):
    monkeypatch.setattr(
        "app.payments.webhook_service.PayPalClient",
        FakePayPalClient,
    )

    headers = {
        "PAYPAL-TRANSMISSION-ID": "test-transmission-123",
    }

    raw_body = (
        b'{"id":"WH-TEST-123",'
        b'"event_type":"PAYMENT.CAPTURE.COMPLETED",'
        b'"resource":{"id":"CAPTURE-123"}}'
    )

    result = receive_webhook(
        db,
        headers=headers,
        raw_body=raw_body,
    )

    assert result["status"] == "received"
    assert result["event_id"] == "WH-TEST-123"

    event = db.query(PayPalWebhookEvent).first()

    assert event.paypal_event_id == "WH-TEST-123"
    assert event.verification_status == "SUCCESS"
    assert event.processing_status == "RECEIVED"
    assert event.resource_id == "CAPTURE-123"

def test_reject_unverified_webhook(db, monkeypatch):
    from app.payments.errors import WebhookVerificationError

    class InvalidPayPalClient:
        def verify_webhook_signature(self, headers, raw_body):
            return {"verification_status": "FAILURE"}

        def close(self):
            pass

    monkeypatch.setattr(
        "app.payments.webhook_service.PayPalClient",
        InvalidPayPalClient,
    )

    with pytest.raises(WebhookVerificationError):
        receive_webhook(
            db,
            headers={},
            raw_body=b'{"id":"WH-INVALID","event_type":"TEST.EVENT"}',
        )

    assert db.query(PayPalWebhookEvent).count() == 0

def test_duplicate_webhook_is_not_stored_twice(db, monkeypatch):
    monkeypatch.setattr(
        "app.payments.webhook_service.PayPalClient",
        FakePayPalClient,
    )

    headers = {
        "PAYPAL-TRANSMISSION-ID": "test-transmission-123",
    }

    raw_body = (
        b'{"id":"WH-DUPLICATE-123",'
        b'"event_type":"PAYMENT.CAPTURE.COMPLETED",'
        b'"resource":{"id":"CAPTURE-123"}}'
    )

    first_result = receive_webhook(
        db,
        headers=headers,
        raw_body=raw_body,
    )

    second_result = receive_webhook(
        db,
        headers=headers,
        raw_body=raw_body,
    )

    assert first_result["status"] == "received"
    assert second_result["status"] == "duplicate"
    assert db.query(PayPalWebhookEvent).count() == 1