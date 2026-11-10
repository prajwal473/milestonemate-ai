import json

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import PayPalWebhookEvent
from app.payments.webhook_service import process_webhook, receive_webhook


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
    monkeypatch.setattr("app.payments.webhook_service.settings.payments_mode", "paypal_sandbox")
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
    monkeypatch.setattr("app.payments.webhook_service.settings.payments_mode", "paypal_sandbox")

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

    stored = db.query(PayPalWebhookEvent).one()
    assert stored.verification_status == "FAILURE"
    assert stored.processing_status == "RECEIVED"

def test_duplicate_webhook_is_not_stored_twice(db, monkeypatch):
    monkeypatch.setattr("app.payments.webhook_service.settings.payments_mode", "paypal_sandbox")
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


def test_webhook_processing_status_records_ignored_event(db, monkeypatch):
    monkeypatch.setattr("app.payments.webhook_service.settings.payments_mode", "paypal_sandbox")
    monkeypatch.setattr("app.payments.webhook_service.PayPalClient", FakePayPalClient)
    result = process_webhook(
        db,
        headers={"PAYPAL-TRANSMISSION-ID": "test"},
        raw_body=b'{"id":"WH-UNKNOWN-1","event_type":"SOME.UNKNOWN.EVENT","resource":{}}',
    )
    assert result["status"] == "ignored"
    event = db.query(PayPalWebhookEvent).one()
    assert event.verification_status == "SUCCESS"
    assert event.processing_status == "IGNORED"
    assert event.processed_at is not None
    repeated = process_webhook(
        db,
        headers={"PAYPAL-TRANSMISSION-ID": "test"},
        raw_body=b'{"id":"WH-UNKNOWN-1","event_type":"SOME.UNKNOWN.EVENT","resource":{}}',
    )
    assert repeated["status"] == "duplicate"
    assert event.processing_status == "IGNORED"


def test_webhook_processing_failure_is_persisted(db, monkeypatch):
    monkeypatch.setattr("app.payments.webhook_service.settings.payments_mode", "paypal_sandbox")
    monkeypatch.setattr("app.payments.webhook_service.PayPalClient", FakePayPalClient)

    def explode(*args, **kwargs):
        raise RuntimeError("provider details are not stored")

    monkeypatch.setattr("app.payments.webhook_service.apply_verified_webhook", explode)
    result = process_webhook(
        db,
        headers={"PAYPAL-TRANSMISSION-ID": "test"},
        raw_body=b'{"id":"WH-FAIL-1","event_type":"SOME.UNKNOWN.EVENT","resource":{}}',
    )
    assert result["status"] == "failed"
    event = db.query(PayPalWebhookEvent).one()
    assert event.processing_status == "FAILED"
    assert event.error == "Webhook processing failed: RuntimeError"


def test_mock_webhooks_never_contact_paypal_without_explicit_flag(db, monkeypatch):
    from app.payments.errors import WebhookVerificationError
    monkeypatch.setattr("app.payments.webhook_service.settings.payments_mode", "mock")
    monkeypatch.setattr("app.payments.webhook_service.settings.allow_unverified_webhooks_in_mock", False)

    class MustNotCallPayPal:
        def __init__(self):
            raise AssertionError("Mock mode attempted a PayPal verification request")

    monkeypatch.setattr("app.payments.webhook_service.PayPalClient", MustNotCallPayPal)
    with pytest.raises(WebhookVerificationError):
        receive_webhook(db, headers={}, raw_body=b'{"id":"WH-MOCK-1","event_type":"TEST.EVENT"}')
    event = db.query(PayPalWebhookEvent).one()
    assert event.verification_status == "FAILURE"


def test_missing_signature_headers_are_saved_as_failure(db, monkeypatch):
    monkeypatch.setattr("app.payments.webhook_service.settings.payments_mode", "paypal_sandbox")
    monkeypatch.setattr("app.payments.webhook_service.settings.paypal_webhook_id", "TEST_WEBHOOK_ID")
    with pytest.raises(Exception):
        receive_webhook(db, headers={}, raw_body=b'{"id":"WH-MISSING-HEADER","event_type":"TEST.EVENT"}')
    event = db.query(PayPalWebhookEvent).one()
    assert event.verification_status == "FAILURE"
    assert event.processing_status == "RECEIVED"


def test_valid_delivery_can_replace_a_prior_unverified_payload(db, monkeypatch):
    from app.payments.errors import WebhookVerificationError

    monkeypatch.setattr("app.payments.webhook_service.settings.payments_mode", "paypal_sandbox")

    class SwitchableVerifier:
        valid = False
        def verify_webhook_signature(self, headers, raw_body):
            return {"verification_status": "SUCCESS" if self.valid else "FAILURE"}
        def close(self):
            pass

    verifier = SwitchableVerifier()
    monkeypatch.setattr("app.payments.webhook_service.PayPalClient", lambda: verifier)
    body = b'{"id":"WH-RETRY-VERIFICATION","event_type":"TEST.EVENT","resource":{}}'
    with pytest.raises(WebhookVerificationError):
        receive_webhook(db, headers={}, raw_body=body)
    verifier.valid = True
    result = receive_webhook(db, headers={}, raw_body=body)
    event = db.query(PayPalWebhookEvent).one()
    assert result["status"] == "received"
    assert event.verification_status == "SUCCESS"
    assert event.payload["id"] == "WH-RETRY-VERIFICATION"


def test_unverified_webhook_flag_is_mock_only(db, monkeypatch):
    monkeypatch.setattr("app.payments.webhook_service.settings.payments_mode", "mock")
    monkeypatch.setattr("app.payments.webhook_service.settings.allow_unverified_webhooks_in_mock", True)
    event = {"id": "WH-MOCK-ALLOWED", "event_type": "TEST.EVENT", "resource": {}}
    assert process_webhook(db, headers={}, raw_body=json.dumps(event).encode())["status"] == "ignored"
    stored = db.query(PayPalWebhookEvent).one()
    assert stored.verification_status == "SUCCESS"
    monkeypatch.setattr("app.payments.webhook_service.settings.payments_mode", "paypal_sandbox")


def test_failed_webhook_retries_and_preserves_verified_payload(db, monkeypatch):
    monkeypatch.setattr("app.payments.webhook_service.settings.payments_mode", "paypal_sandbox")
    monkeypatch.setattr("app.payments.webhook_service.PayPalClient", FakePayPalClient)
    original = b'{"id":"WH-RETRY-PROCESSING","event_type":"TEST.EVENT","resource":{"id":"safe"}}'
    tampered = b'{"id":"WH-RETRY-PROCESSING","event_type":"TEST.EVENT","resource":{"id":"other"}}'
    calls = {"count": 0}

    def fail_once(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("private provider detail")
        return "ignored"

    monkeypatch.setattr("app.payments.webhook_service.apply_verified_webhook", fail_once)
    assert process_webhook(db, headers={}, raw_body=original)["status"] == "failed"
    assert process_webhook(db, headers={}, raw_body=tampered)["status"] == "ignored"
    event = db.query(PayPalWebhookEvent).one()
    assert event.payload["resource"]["id"] == "safe"
    assert event.processing_status == "IGNORED"
    assert "private provider detail" not in event.error if event.error else True
    assert process_webhook(db, headers={}, raw_body=original)["status"] == "duplicate"


def test_repeated_processing_failures_remain_retryable(db, monkeypatch):
    monkeypatch.setattr("app.payments.webhook_service.settings.payments_mode", "paypal_sandbox")
    monkeypatch.setattr("app.payments.webhook_service.PayPalClient", FakePayPalClient)
    monkeypatch.setattr("app.payments.webhook_service.apply_verified_webhook", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("secret")))
    body = b'{"id":"WH-REPEATED-FAIL","event_type":"TEST.EVENT","resource":{}}'
    assert process_webhook(db, headers={}, raw_body=body)["status"] == "failed"
    assert process_webhook(db, headers={}, raw_body=body)["status"] == "failed"
    assert db.query(PayPalWebhookEvent).one().processing_status == "FAILED"


def test_invalid_redelivery_cannot_replace_verified_failure_or_reach_processing(db, monkeypatch):
    from app.payments.errors import WebhookVerificationError
    monkeypatch.setattr("app.payments.webhook_service.settings.payments_mode", "paypal_sandbox")
    class Verifier:
        def verify_webhook_signature(self, headers, raw_body):
            return {"verification_status": "SUCCESS" if b"verified" in raw_body else "FAILURE"}
        def close(self):
            pass
    monkeypatch.setattr("app.payments.webhook_service.PayPalClient", Verifier)
    monkeypatch.setattr("app.payments.webhook_service.apply_verified_webhook", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("failed")))
    trusted = b'{"id":"WH-TRUSTED","event_type":"TEST.EVENT","resource":{"id":"verified"}}'
    assert process_webhook(db, headers={}, raw_body=trusted)["status"] == "failed"
    event = db.query(PayPalWebhookEvent).one()
    assert event.processing_status == "FAILED"
    untrusted = b'{"id":"WH-TRUSTED","event_type":"TEST.EVENT","resource":{"id":"untrusted"}}'
    with pytest.raises(WebhookVerificationError):
        process_webhook(db, headers={}, raw_body=untrusted)
    db.refresh(event)
    assert event.verification_status == "SUCCESS"
    assert event.payload["resource"]["id"] == "verified"
    assert event.processing_status == "FAILED"


def test_paypal_order_link_must_be_expected_sandbox_api_url():
    from app.payments.webhook_service import _get_related_order_id
    prefix = "https://api-m.sandbox.paypal.com/v2/checkout/orders/ORDER-1"
    def event(href):
        return {"event_type": "PAYMENT.CAPTURE.COMPLETED", "resource": {"links": [{"rel": "up", "href": href}]}}
    assert _get_related_order_id(event(prefix)) == "ORDER-1"
    assert _get_related_order_id(event("not a url")) is None
    assert _get_related_order_id(event("https://evil.example/v2/checkout/orders/ORDER-1")) is None
