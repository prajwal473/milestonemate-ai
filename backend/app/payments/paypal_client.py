import json
import re
import threading
import time
from urllib.parse import urlsplit
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

import httpx

from app.core.config import settings
from app.payments.errors import PayPalError


class PayPalClient:
    """Client for PayPal REST API (Sandbox only)."""

    def __init__(
        self,
        transport: httpx.BaseTransport | None = None,
    ):
        self.api_base = settings.paypal_api_base.rstrip("/")
        self.client_id = settings.paypal_client_id
        self.client_secret = settings.paypal_client_secret

        parsed_url = urlsplit(self.api_base)

        if (
            parsed_url.scheme != "https"
            or parsed_url.hostname != "api-m.sandbox.paypal.com"
            or parsed_url.port not in (None, 443)
            or parsed_url.username is not None
            or parsed_url.password is not None
        ):
            raise ValueError("Only PayPal Sandbox is supported.")
        self.http = httpx.Client(           
            base_url=self.api_base,
            timeout=httpx.Timeout(15.0, connect=5.0),
            transport=transport,
        )

        self._access_token: str | None = None
        self._token_expires_at = 0.0
        self._token_lock = threading.Lock()

    # --------------------------------------------------
    # OAuth Authentication
    # --------------------------------------------------

    def get_access_token(self, force_refresh: bool = False) -> str:
        """Get and cache a PayPal OAuth access token."""

        with self._token_lock:

            if (
                not force_refresh
                and self._access_token
                and time.monotonic() < self._token_expires_at - 60
            ):
                return self._access_token

            if not self.client_id or not self.client_secret:
                raise PayPalError(
                    "PayPal Sandbox credentials are not configured."
                )

            try:
                response = self.http.post(
                    "/v1/oauth2/token",
                    auth=(self.client_id, self.client_secret),
                    data={"grant_type": "client_credentials"},
                    headers={
                        "Accept": "application/json",
                        "Accept-Language": "en_US",
                    },
                )

                response.raise_for_status()
                data = response.json()

            except (httpx.HTTPError, ValueError) as exc:
                raise PayPalError(
                    "PayPal OAuth authentication failed."
                ) from exc

            token = data.get("access_token")
            expires_in = data.get("expires_in")

            if not token or not isinstance(expires_in, (int, float)):
                raise PayPalError(
                    "Invalid OAuth response from PayPal."
                )

            self._access_token = token
            self._token_expires_at = (
                time.monotonic() + expires_in
            )

            return token

    # --------------------------------------------------
    # Common API Request Handler
    # --------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
        content: str | None = None,
        headers: dict | None = None,
    ) -> dict[str, Any]:

        request_headers = {
            "Accept": "application/json",
            **(headers or {}),
        }

        auth_retried = False
        transient_retries = 0

        while True:

            token = self.get_access_token(
                force_refresh=auth_retried
            )

            request_headers["Authorization"] = f"Bearer {token}"

            try:
                response = self.http.request(
                    method,
                    path,
                    json=json_body,
                    content=content,
                    headers=request_headers,
                )

            except httpx.TransportError as exc:

                if transient_retries < 2:
                    transient_retries += 1
                    time.sleep(0.25 * transient_retries)
                    continue

                raise PayPalError(
                    "Unable to connect to PayPal."
                ) from exc

            if response.status_code == 401 and not auth_retried:
                auth_retried = True
                continue

            if response.status_code >= 500 and transient_retries < 2:
                transient_retries += 1
                time.sleep(0.25 * transient_retries)
                continue

            if response.is_error:
                try:
                    error_data = response.json()
                except ValueError:
                    error_data = {}

                details = error_data.get("details") or []
                issue = (
                    details[0].get("issue")
                    if details and isinstance(details[0], dict)
                    else None
                )

                name = error_data.get("name", "PAYPAL_ERROR")
                message = error_data.get(
                    "message", "PayPal request failed."
                )
                debug_id = error_data.get("debug_id", "unknown")

                raise PayPalError(
                    f"{name}: {issue or message} "
                    f"(debug_id={debug_id})"
                )

            try:
                return response.json()
            except ValueError:
                return {}

    # --------------------------------------------------
    # Create Order
    # --------------------------------------------------

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
    ) -> dict[str, Any]:

        try:
            amount_value = Decimal(str(amount)).quantize(
                Decimal("0.01")
            )
        except InvalidOperation as exc:
            raise ValueError("Invalid payment amount.") from exc

        if not amount_value.is_finite() or amount_value <= 0:
            raise ValueError("Payment amount must be positive.")

        currency_code = currency_code.upper()

        if not re.fullmatch(r"[A-Z]{3}", currency_code):
            raise ValueError("Invalid currency code.")

        if not request_id:
            raise ValueError("A request ID is required.")

        purchase_unit = {
            "reference_id": reference_id,
            "custom_id": custom_id,
            "invoice_id": invoice_id,
            "description": description,
            "amount": {
                "currency_code": currency_code,
                "value": f"{amount_value:.2f}",
            },
        }

        if settings.payee_mode == "direct_payee":
            if not payee_email:
                raise ValueError(
                    "Payee email is required in direct_payee mode."
                )

            purchase_unit["payee"] = {
                "email_address": payee_email
            }

        elif settings.payee_mode != "demo_merchant":
            raise ValueError("Unsupported PayPal payee mode.")

        payload = {
            "intent": "CAPTURE",
            "purchase_units": [purchase_unit],
            "payment_source": {
                "paypal": {
                    "experience_context": {
                        "brand_name": settings.paypal_brand_name,
                        "user_action": "PAY_NOW",
                        "shipping_preference": "NO_SHIPPING",
                        "landing_page": "LOGIN",
                        "return_url": return_url,
                        "cancel_url": cancel_url,
                    }
                }
            },
        }

        return self._request(
            "POST",
            "/v2/checkout/orders",
            json_body=payload,
            headers={
                "PayPal-Request-Id": request_id,
                "Prefer": "return=representation",
            },
        )
    @staticmethod
    def _validate_order_id(order_id: str) -> None:
        if not isinstance(order_id, str) or not re.fullmatch(
            r"[A-Za-z0-9_-]{1,100}",
            order_id,
        ):
            raise ValueError("Invalid PayPal order ID.")
    # --------------------------------------------------
    # Get Order
    # --------------------------------------------------

    def get_order(self, order_id: str) -> dict[str, Any]:

        self._validate_order_id(order_id)

        return self._request(
            "GET",
            f"/v2/checkout/orders/{order_id}",
        )

    # --------------------------------------------------
    # Capture Order
    # --------------------------------------------------

    def capture_order(
        self,
        order_id: str,
        request_id: str,
    ) -> dict[str, Any]:

        self._validate_order_id(order_id)

        if not request_id:
            raise ValueError("Request ID is required.")

        return self._request(
            "POST",
            f"/v2/checkout/orders/{order_id}/capture",
            json_body={},
            headers={
                "PayPal-Request-Id": request_id,
                "Prefer": "return=representation",
            },
        )

    # --------------------------------------------------
    # Verify Webhook Signature
    # --------------------------------------------------

    def verify_webhook_signature(
        self,
        headers: Mapping[str, str],
        raw_body: bytes,
    ) -> dict[str, Any]:

        webhook_id = settings.paypal_webhook_id

        if not webhook_id:
            raise PayPalError(
                "PayPal webhook ID is not configured."
            )

        normalized = {
            key.lower(): value
            for key, value in headers.items()
        }

        required_headers = {
            "auth_algo": "paypal-auth-algo",
            "cert_url": "paypal-cert-url",
            "transmission_id": "paypal-transmission-id",
            "transmission_sig": "paypal-transmission-sig",
            "transmission_time": "paypal-transmission-time",
        }

        verification_data = {}

        for field, header_name in required_headers.items():
            value = normalized.get(header_name)

            if not value:
                raise ValueError(
                    f"Missing PayPal header: {header_name}"
                )

            verification_data[field] = value

        try:
            webhook_event = json.loads(raw_body)
        except (UnicodeDecodeError, ValueError) as exc:
            raise ValueError("Invalid webhook JSON.") from exc

        payload = {
            **verification_data,
            "webhook_id": webhook_id,
            "webhook_event": webhook_event,
        }

        return self._request(
            "POST",
            "/v1/notifications/verify-webhook-signature",
            json_body=payload,
        )

    # --------------------------------------------------
    # Cleanup
    # --------------------------------------------------

    def close(self):
        self.http.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()