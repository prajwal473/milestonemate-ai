import asyncio
from fastapi import HTTPException, Request
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.dependencies import get_db
from app.payments.errors import WebhookVerificationError
from app.routers.webhooks import paypal_webhook


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def request_for(body):
    sent = False
    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}
    return Request({"type": "http", "method": "POST", "path": "/api/webhooks/paypal", "headers": []}, receive)


def test_successful_webhook_response(db, monkeypatch):
    monkeypatch.setattr("app.routers.webhooks.process_webhook", lambda *a, **k: {"status": "processed", "event_id": "WH-1"})
    response = asyncio.run(paypal_webhook(request_for(b"{}"), db))
    assert response["status"] == "processed"


def test_invalid_signature_response(db, monkeypatch):
    monkeypatch.setattr("app.routers.webhooks.process_webhook", lambda *a, **k: (_ for _ in ()).throw(WebhookVerificationError("invalid")))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(paypal_webhook(request_for(b"{}"), db))
    assert exc.value.status_code == 400


def test_processing_failure_is_retryable_response(db, monkeypatch):
    monkeypatch.setattr("app.routers.webhooks.process_webhook", lambda *a, **k: {"status": "failed"})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(paypal_webhook(request_for(b"{}"), db))
    assert exc.value.status_code == 503


def test_oversized_webhook_is_rejected(db):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(paypal_webhook(request_for(b"x" * 1_000_001), db))
    assert exc.value.status_code == 413


def test_malformed_payload_response(db, monkeypatch):
    def malformed(db, *, headers, raw_body):
        from app.payments.webhook_service import receive_webhook
        return receive_webhook(db, headers=headers, raw_body=raw_body)
    monkeypatch.setattr("app.routers.webhooks.process_webhook", malformed)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(paypal_webhook(request_for(b"{"), db))
    assert exc.value.status_code == 400
