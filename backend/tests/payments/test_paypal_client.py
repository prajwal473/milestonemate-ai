from decimal import Decimal

import httpx
import pytest

from app.core.config import settings
from app.payments.paypal_client import PayPalClient


@pytest.fixture
def paypal_client(monkeypatch):
    monkeypatch.setattr(settings, "paypal_client_id", "test_client")
    monkeypatch.setattr(settings, "paypal_client_secret", "test_secret")
    monkeypatch.setattr(settings, "paypal_api_base", "https://api-m.sandbox.paypal.com")
    monkeypatch.setattr(settings, "payee_mode", "demo_merchant")

    requests = []

    def handler(request):
        requests.append(request)

        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(
                200,
                json={
                    "access_token": "fake_access_token",
                    "expires_in": 3600,
                },
            )

        if request.url.path == "/v2/checkout/orders":
            return httpx.Response(
                201,
                json={
                    "id": "TEST_ORDER_123",
                    "status": "CREATED",
                },
            )

        if request.url.path.endswith("/capture"):
            return httpx.Response(
                201,
                json={
                    "id": "TEST_ORDER_123",
                    "status": "COMPLETED",
                },
            )

        return httpx.Response(404)

    transport = httpx.MockTransport(handler)

    client = PayPalClient(transport=transport)

    yield client, requests

    client.close()


def test_oauth_authentication_and_token_caching(paypal_client):
    client, requests = paypal_client

    token1 = client.get_access_token()
    token2 = client.get_access_token()

    assert token1 == "fake_access_token"
    assert token2 == "fake_access_token"

    oauth_requests = [
        r for r in requests
        if r.url.path == "/v1/oauth2/token"
    ]

    assert len(oauth_requests) == 1


def test_create_order(paypal_client):
    client, requests = paypal_client

    result = client.create_order(
        amount=Decimal("100.00"),
        currency_code="USD",
        reference_id="milestone-1",
        custom_id="payment-1",
        invoice_id="invoice-1",
        description="Milestone payment",
        return_url="http://localhost:5173/payment/success",
        cancel_url="http://localhost:5173/payment/cancel",
        request_id="unique-request-123",
    )

    assert result["id"] == "TEST_ORDER_123"
    assert result["status"] == "CREATED"

    order_request = next(
        r for r in requests
        if r.url.path == "/v2/checkout/orders"
    )

    assert order_request.headers["PayPal-Request-Id"] == "unique-request-123"

    import json

    payload = json.loads(order_request.content)

    purchase_unit = payload["purchase_units"][0]

    assert purchase_unit["amount"]["value"] == "100.00"
    assert purchase_unit["amount"]["currency_code"] == "USD"


def test_capture_order(paypal_client):
    client, requests = paypal_client

    result = client.capture_order(
        order_id="TEST_ORDER_123",
        request_id="capture-request-123",
    )

    assert result["status"] == "COMPLETED"

    capture_request = next(
        r for r in requests
        if r.url.path.endswith("/capture")
    )

    assert capture_request.headers["PayPal-Request-Id"] == "capture-request-123"


def test_invalid_amount_rejected(paypal_client):
    client, requests = paypal_client

    with pytest.raises(ValueError):
        client.create_order(
            amount=Decimal("-100"),
            currency_code="USD",
            reference_id="milestone-1",
            custom_id="payment-1",
            invoice_id="invoice-1",
            description="Invalid payment",
            return_url="http://localhost:5173/success",
            cancel_url="http://localhost:5173/cancel",
            request_id="request-123",
        )

    assert len(requests) == 0

def test_accepts_genuine_paypal_sandbox_url(monkeypatch):
    monkeypatch.setattr(
        settings,
        "paypal_api_base",
        "https://api-m.sandbox.paypal.com",
    )

    client = PayPalClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200)
        )
    )

    assert client.api_base == "https://api-m.sandbox.paypal.com"
    client.close()


@pytest.mark.parametrize(
    "unsafe_url",
    [
        "https://api-m.sandbox.paypal.com.evil.com",
        "https://api-m.sandbox.paypal.com@evil.com",
        "http://api-m.sandbox.paypal.com",
        "https://api-m.sandbox.paypal.com:8443",
    ],
)
def test_rejects_unsafe_paypal_api_urls(monkeypatch, unsafe_url):
    monkeypatch.setattr(
        settings,
        "paypal_api_base",
        unsafe_url,
    )

    with pytest.raises(ValueError, match="Only PayPal Sandbox"):
        PayPalClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200)
            )
        )

def test_401_refreshes_token_and_retries_request(monkeypatch):
    monkeypatch.setattr(settings, "paypal_client_id", "test_client")
    monkeypatch.setattr(settings, "paypal_client_secret", "test_secret")
    monkeypatch.setattr(
        settings,
        "paypal_api_base",
        "https://api-m.sandbox.paypal.com",
    )

    token_requests = []
    order_requests = []

    def handler(request):
        if request.url.path == "/v1/oauth2/token":
            token_requests.append(request)

            token_number = len(token_requests)

            return httpx.Response(
                200,
                json={
                    "access_token": f"token_{token_number}",
                    "expires_in": 3600,
                },
            )

        if request.url.path == "/v2/checkout/orders/TEST_ORDER_123":
            order_requests.append(request)

            if len(order_requests) == 1:
                return httpx.Response(
                    401,
                    json={"name": "AUTHENTICATION_FAILURE"},
                )

            return httpx.Response(
                200,
                json={
                    "id": "TEST_ORDER_123",
                    "status": "CREATED",
                },
            )

        return httpx.Response(404)

    client = PayPalClient(
        transport=httpx.MockTransport(handler)
    )

    try:
        result = client.get_order("TEST_ORDER_123")

        assert result["id"] == "TEST_ORDER_123"
        assert len(token_requests) == 2
        assert len(order_requests) == 2

        assert (
            order_requests[0].headers["Authorization"]
            == "Bearer token_1"
        )

        assert (
            order_requests[1].headers["Authorization"]
            == "Bearer token_2"
        )

    finally:
        client.close()

def test_500_error_retries_request(monkeypatch):
    monkeypatch.setattr(settings, "paypal_client_id", "test_client")
    monkeypatch.setattr(settings, "paypal_client_secret", "test_secret")
    monkeypatch.setattr(
        settings,
        "paypal_api_base",
        "https://api-m.sandbox.paypal.com",
    )

    order_requests = []

    def handler(request):
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(
                200,
                json={
                    "access_token": "test_token",
                    "expires_in": 3600,
                },
            )

        if request.url.path == "/v2/checkout/orders/TEST_ORDER_123":
            order_requests.append(request)

            if len(order_requests) < 3:
                return httpx.Response(
                    500,
                    json={"name": "INTERNAL_SERVER_ERROR"},
                )

            return httpx.Response(
                200,
                json={
                    "id": "TEST_ORDER_123",
                    "status": "CREATED",
                },
            )

        return httpx.Response(404)

    client = PayPalClient(
        transport=httpx.MockTransport(handler)
    )

    try:
        result = client.get_order("TEST_ORDER_123")

        assert result["id"] == "TEST_ORDER_123"
        assert len(order_requests) == 3
    finally:
        client.close()

def test_webhook_signature_verification(monkeypatch):
    monkeypatch.setattr(settings, "paypal_client_id", "test_client")
    monkeypatch.setattr(settings, "paypal_client_secret", "test_secret")
    monkeypatch.setattr(settings, "paypal_webhook_id", "WEBHOOK_TEST_123")
    monkeypatch.setattr(
        settings,
        "paypal_api_base",
        "https://api-m.sandbox.paypal.com",
    )

    requests = []

    def handler(request):
        requests.append(request)

        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(
                200,
                json={
                    "access_token": "test_token",
                    "expires_in": 3600,
                },
            )

        if request.url.path == "/v1/notifications/verify-webhook-signature":
            return httpx.Response(
                200,
                json={"verification_status": "SUCCESS"},
            )

        return httpx.Response(404)

    client = PayPalClient(
        transport=httpx.MockTransport(handler)
    )

    headers = {
        "PAYPAL-AUTH-ALGO": "SHA256withRSA",
        "PAYPAL-CERT-URL": "https://api.paypal.com/cert",
        "PAYPAL-TRANSMISSION-ID": "test-transmission",
        "PAYPAL-TRANSMISSION-SIG": "test-signature",
        "PAYPAL-TRANSMISSION-TIME": "2026-11-09T12:00:00Z",
    }

    raw_body = b'{"id":"WH-123","event_type":"PAYMENT.CAPTURE.COMPLETED"}'

    try:
        result = client.verify_webhook_signature(headers, raw_body)

        assert result["verification_status"] == "SUCCESS"

        import json

        verification_request = next(
            request for request in requests
            if request.url.path
            == "/v1/notifications/verify-webhook-signature"
        )

        payload = json.loads(verification_request.content)

        assert payload["webhook_id"] == "WEBHOOK_TEST_123"
        assert payload["webhook_event"]["id"] == "WH-123"
        assert payload["auth_algo"] == "SHA256withRSA"

    finally:
        client.close()


def test_invalid_webhook_json_rejected(monkeypatch):
    monkeypatch.setattr(settings, "paypal_webhook_id", "WEBHOOK_TEST_123")

    client = PayPalClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200)
        )
    )

    headers = {
        "PAYPAL-AUTH-ALGO": "SHA256withRSA",
        "PAYPAL-CERT-URL": "https://api.paypal.com/cert",
        "PAYPAL-TRANSMISSION-ID": "test-transmission",
        "PAYPAL-TRANSMISSION-SIG": "test-signature",
        "PAYPAL-TRANSMISSION-TIME": "2026-11-09T12:00:00Z",
    }

    try:
        with pytest.raises(ValueError, match="Invalid webhook JSON"):
            client.verify_webhook_signature(
                headers,
                b"this is not valid JSON",
            )
    finally:
        client.close()


def test_missing_webhook_header_rejected(monkeypatch):
    monkeypatch.setattr(settings, "paypal_webhook_id", "WEBHOOK_TEST_123")

    client = PayPalClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200)
        )
    )

    headers = {
        "PAYPAL-AUTH-ALGO": "SHA256withRSA",
        "PAYPAL-TRANSMISSION-ID": "test-transmission",
    }

    try:
        with pytest.raises(ValueError, match="Missing PayPal header"):
            client.verify_webhook_signature(
                headers,
                b'{"id":"WH-123"}',
            )
    finally:
        client.close()

@pytest.mark.parametrize(
    "invalid_order_id",
    [
        "",
        "../admin",
        "order/123",
        "order 123",
        "order?test=1",
    ],
)
def test_get_order_rejects_invalid_order_id(
    paypal_client,
    invalid_order_id,
):
    client, requests = paypal_client

    with pytest.raises(ValueError, match="Invalid PayPal order ID"):
        client.get_order(invalid_order_id)

    assert len(requests) == 0


@pytest.mark.parametrize(
    "invalid_order_id",
    [
        "",
        "../admin",
        "order/123",
        "order 123",
        "order?test=1",
    ],
)
def test_capture_order_rejects_invalid_order_id(
    paypal_client,
    invalid_order_id,
):
    client, requests = paypal_client

    with pytest.raises(ValueError, match="Invalid PayPal order ID"):
        client.capture_order(
            order_id=invalid_order_id,
            request_id="test-request-123",
        )

    assert len(requests) == 0