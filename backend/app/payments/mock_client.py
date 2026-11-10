from decimal import Decimal
from threading import RLock
from uuid import uuid4


class MockPaymentClient:
    """
    Simulates PayPal operations without making real transactions.

    Only intended for development and testing.
    """

    # Shared across instances so separate API requests see the same orders.
    _orders: dict[str, dict] = {}
    _lock = RLock()

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

        order = {
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
                        f"http://localhost:5173/mock-payment/{order_id}"
                    ),
                    "method": "GET",
                }
            ],
        }

        with self._lock:
            self._orders[order_id] = order

        return order.copy()

    def get_order(self, order_id: str) -> dict:
     if not order_id:
        raise ValueError("Order ID is required.")

     with self._lock:
        order = self._orders.get(order_id)

        if order is None:
            raise ValueError("Mock order not found.")

        result = {
            **order,
            "purchase_units": [
                {
                    **unit,
                    "amount": dict(unit["amount"]),
                }
                for unit in order["purchase_units"]
            ],
        }

        if order["status"] == "COMPLETED":
            capture_result = order["capture_result"]

            result["purchase_units"][0]["payments"] = (
                capture_result["purchase_units"][0]["payments"]
            )

        return result

    @classmethod
    def approve_order(cls, order_id: str) -> dict:
        """Simulate the buyer approving a mock order."""

        with cls._lock:
            order = cls._orders.get(order_id)

            if order is None:
                raise ValueError("Mock order not found.")

            if order["status"] != "CREATED":
                raise ValueError("Order cannot be approved in its current state.")

            order["status"] = "APPROVED"

            return order.copy()

    def capture_order(
        self,
        order_id: str,
        request_id: str,
    ) -> dict:

        if not order_id or not request_id:
            raise ValueError("Order ID and request ID are required.")

        with self._lock:
            order = self._orders.get(order_id)

            if order is None:
                raise ValueError("Mock order not found.")

            # Return the existing result for repeated capture requests.
            if order["status"] == "COMPLETED":
                return order["capture_result"]

            if order["status"] != "APPROVED":
                raise ValueError("Order must be approved before capture.")

            capture_id = f"MOCK_CAPTURE_{uuid4().hex[:12].upper()}"

            order["status"] = "COMPLETED"

            capture_result = {
                "id": order_id,
                "status": "COMPLETED",
                "purchase_units": [
                    {
                        "payments": {
                            "captures": [
                                {
                                    "id": capture_id,
                                    "status": "COMPLETED",
                                    "amount": order["purchase_units"][0]["amount"],
                                }
                            ]
                        }
                    }
                ],
            }

            order["capture_result"] = capture_result

            return capture_result

    def close(self):
        pass