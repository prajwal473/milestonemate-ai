from copy import deepcopy
from decimal import Decimal, InvalidOperation
from threading import RLock
from uuid import uuid4


class MockPaymentClient:
    """In-memory provider simulator; durable status is reconstructed from Payment rows."""

    _orders: dict[str, dict] = {}
    _request_orders: dict[str, str] = {}
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
        try:
            amount_value = Decimal(str(amount))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("Invalid payment amount.") from exc
        if not amount_value.is_finite() or amount_value <= 0:
            raise ValueError("Payment amount must be positive.")
        try:
            rounded = amount_value.quantize(Decimal("0.01"))
        except InvalidOperation as exc:
            raise ValueError("Payment amount is outside the supported range.") from exc
        if amount_value != rounded:
            raise ValueError("Payment amount cannot have more than two decimals.")
        if currency_code.upper() != "USD":
            raise ValueError("Only USD mock payments are supported.")
        if not request_id:
            raise ValueError("Request ID is required.")

        with self._lock:
            previous = self._request_orders.get(request_id)
            if previous:
                return deepcopy(self._orders[previous])
            order_id = f"MOCK_ORDER_{uuid4().hex.upper()}"
            order = {
                "id": order_id,
                "status": "CREATED",
                "intent": "CAPTURE",
                "purchase_units": [{
                    "reference_id": reference_id,
                    "custom_id": custom_id,
                    "invoice_id": invoice_id,
                    "description": description,
                    "amount": {
                        "currency_code": "USD",
                        "value": f"{amount_value:.2f}",
                    },
                }],
                "links": [{
                    "rel": "approve",
                    "href": f"/mock-paypal/checkout?order_id={order_id}",
                    "method": "GET",
                }],
            }
            self._orders[order_id] = order
            self._request_orders[request_id] = order_id
            return deepcopy(order)

    @classmethod
    def restore_order(cls, order_id: str, payment) -> dict:
        """Rebuild the mock provider view after an application restart."""
        state_map = {
            "CREATED": "CREATED", "PENDING_APPROVAL": "CREATED",
            "APPROVED": "APPROVED", "CAPTURE_PENDING": "COMPLETED",
            "COMPLETED": "COMPLETED", "FAILED": "DENIED",
            "DENIED": "DENIED", "CANCELLED": "VOIDED",
        }
        amount = {
            "currency_code": payment.currency,
            "value": f"{Decimal(str(payment.amount)):.2f}",
        }
        order = {
            "id": order_id,
            "status": state_map.get(payment.status, "CREATED"),
            "intent": "CAPTURE",
            "purchase_units": [{
                "reference_id": str(payment.milestone_id),
                "custom_id": str(payment.id),
                "amount": amount,
            }],
            "links": [{"rel": "approve", "href": f"/mock-paypal/checkout?order_id={order_id}"}],
        }
        if payment.status in {"CAPTURE_PENDING", "COMPLETED"}:
            capture_status = "COMPLETED" if payment.status == "COMPLETED" else "PENDING"
            order["capture_result"] = {
                "id": order_id,
                "status": "COMPLETED",
                "purchase_units": [{"payments": {"captures": [{
                    "id": payment.paypal_capture_id or f"MOCK_CAPTURE_{payment.id}",
                    "status": capture_status,
                    "amount": amount,
                }]}}],
            }
        with cls._lock:
            # The database is authoritative across process restarts and also
            # repairs stale process-local state after a failed transaction.
            current = cls._orders.get(order_id)
            if current is None:
                cls._orders[order_id] = order
            else:
                # The durable row reconstructs missing state. If a provider
                # action advanced first, preserve that state for reconciliation.
                rank = {"CREATED": 0, "APPROVED": 1, "DENIED": 2,
                        "VOIDED": 2, "COMPLETED": 3}
                if rank.get(current.get("status"), 0) <= rank.get(order["status"], 0):
                    cls._orders[order_id] = order
            return deepcopy(cls._orders[order_id])

    def get_order(self, order_id: str) -> dict:
        if not order_id:
            raise ValueError("Order ID is required.")
        with self._lock:
            order = self._orders.get(order_id)
            if order is None:
                raise ValueError("Mock order not found.")
            result = deepcopy(order)
            if order["status"] == "COMPLETED":
                result["purchase_units"][0]["payments"] = deepcopy(
                    order["capture_result"]["purchase_units"][0]["payments"]
                )
            return result

    @classmethod
    def approve_order(cls, order_id: str) -> dict:
        return cls._set_checkout_state(order_id, "APPROVED")

    @classmethod
    def reject_order(cls, order_id: str) -> dict:
        return cls._set_checkout_state(order_id, "DENIED")

    @classmethod
    def cancel_order(cls, order_id: str) -> dict:
        return cls._set_checkout_state(order_id, "VOIDED")

    @classmethod
    def _set_checkout_state(cls, order_id: str, target: str) -> dict:
        with cls._lock:
            order = cls._orders.get(order_id)
            if order is None:
                raise ValueError("Mock order not found.")
            if order["status"] == target:
                return deepcopy(order)
            if order["status"] != "CREATED":
                raise ValueError("Order is no longer awaiting checkout.")
            order["status"] = target
            return deepcopy(order)

    def capture_order(self, order_id: str, request_id: str) -> dict:
        if not order_id or not request_id:
            raise ValueError("Order ID and request ID are required.")
        with self._lock:
            order = self._orders.get(order_id)
            if order is None:
                raise ValueError("Mock order not found.")
            if order["status"] == "COMPLETED":
                return deepcopy(order["capture_result"])
            if order["status"] != "APPROVED":
                raise ValueError("Order must be approved before capture.")
            capture_result = {
                "id": order_id,
                "status": "COMPLETED",
                "purchase_units": [{"payments": {"captures": [{
                    "id": f"MOCK_CAPTURE_{uuid4().hex[:12].upper()}",
                    "status": "COMPLETED",
                    "amount": deepcopy(order["purchase_units"][0]["amount"]),
                }]}}],
            }
            order["status"] = "COMPLETED"
            order["capture_result"] = capture_result
            return deepcopy(capture_result)

    def verify_webhook_signature(self, headers: dict, raw_body: bytes) -> dict:
        # Mock webhook acceptance is controlled by the explicit setting in the
        # webhook service. The client itself never pretends to verify a signature.
        return {"verification_status": "FAILURE"}

    def close(self) -> None:
        pass
