from decimal import Decimal
from uuid import uuid4


class MockPaymentClient:
    """
    Simulates PayPal operations without making real transactions.

    Only intended for development and testing.
    """

    def create_order(
        self,
        *,
        amount: Decimal | str,
        currency_code: str,
        reference_id: str,
        custom_id: str,
        invoice_id: str,
        description: str,
        return_url: str,
        cancel_url: str,
        request_id: str,
        payee_email: str | None = None,
    ) -> dict:

        amount = Decimal(str(amount))

        if not amount.is_finite() or amount <= 0:
            raise ValueError("Payment amount must be positive.")

        if not request_id:
            raise ValueError("Request ID is required.")

        order_id = f"MOCK_ORDER_{uuid4().hex[:12].upper()}"

        return {
            "id": order_id,
            "status": "CREATED",
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": reference_id,
                    "custom_id": custom_id,
                    "invoice_id": invoice_id,
                    "description": description,
                    "amount": {
                        "currency_code": currency_code.upper(),
                        "value": f"{amount:.2f}",
                    },
                }
            ],
            "links": [
                {
                    "rel": "approve",
                    "href": (
                        f"http://localhost:5173/mock-payment/"
                        f"{order_id}"
                    ),
                    "method": "GET",
                }
            ],
        }

    def get_order(self, order_id: str) -> dict:

        if not order_id:
            raise ValueError("Order ID is required.")

        return {
            "id": order_id,
            "status": "CREATED",
        }

    def capture_order(
        self,
        order_id: str,
        request_id: str,
    ) -> dict:

        if not order_id or not request_id:
            raise ValueError("Order ID and request ID are required.")

        capture_id = f"MOCK_CAPTURE_{uuid4().hex[:12].upper()}"

        return {
            "id": order_id,
            "status": "COMPLETED",
            "purchase_units": [
                {
                    "payments": {
                        "captures": [
                            {
                                "id": capture_id,
                                "status": "COMPLETED",
                            }
                        ]
                    }
                }
            ],
        }

    def close(self):
        pass