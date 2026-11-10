from decimal import Decimal

import pytest

from app.payments.mock_client import MockPaymentClient


@pytest.fixture
def client():
    return MockPaymentClient()


def test_create_mock_order(client):

    result = client.create_order(
        amount=Decimal("500.00"),
        currency_code="USD",
        reference_id="milestone-1",
        custom_id="payment-1",
        invoice_id="invoice-1",
        description="Test milestone",
        return_url="http://localhost:5173/success",
        cancel_url="http://localhost:5173/cancel",
        request_id="request-1",
    )

    assert result["status"] == "CREATED"
    assert result["id"].startswith("MOCK_ORDER_")


def test_capture_mock_order(client):
    order = client.create_order(
        amount=Decimal("500.00"),
        currency_code="USD",
        reference_id="milestone-1",
        custom_id="payment-1",
        invoice_id="invoice-1",
        description="Test milestone",
        return_url="http://localhost:5173/success",
        cancel_url="http://localhost:5173/cancel",
        request_id="request-123",
    )

    order_id = order["id"]

    # Capture must fail before buyer approval.
    with pytest.raises(ValueError, match="approved"):
        client.capture_order(
            order_id=order_id,
            request_id="request-123",
        )

    # Simulate buyer approval.
    approved = client.approve_order(order_id)

    assert approved["status"] == "APPROVED"

    # Capture after approval.
    result = client.capture_order(
        order_id=order_id,
        request_id="request-123",
    )

    assert result["status"] == "COMPLETED"

    capture = result["purchase_units"][0]["payments"]["captures"][0]

    assert capture["status"] == "COMPLETED"
    assert capture["id"].startswith("MOCK_CAPTURE_")

    # Repeated capture should return the same result.
    repeated = client.capture_order(
        order_id=order_id,
        request_id="request-123",
    )

    assert repeated == result


def test_invalid_amount_rejected(client):

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
            request_id="request-1",
        )