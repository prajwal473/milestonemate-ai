#!/usr/bin/env python3
"""Manual PayPal Sandbox spike: create, approve, capture, then replay IDs.

This script never uses PayPal Live. It creates a Sandbox order only when
--confirm-sandbox is supplied. Credentials are loaded by Settings and never
printed. Do not run against a buyer/merchant account used for production.
"""

import argparse
import sys
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.payments.paypal_client import PayPalClient


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-sandbox", action="store_true", help="Confirm this will create a Sandbox order")
    parser.add_argument("--amount", default="1.00", help="USD amount for this manual Sandbox check")
    parser.add_argument("--payee-email", help="Optional second Sandbox merchant email for the direct-payee spike")
    parser.add_argument("--return-url", default=f"{settings.frontend_base_url}/payments/return")
    parser.add_argument("--cancel-url", default=f"{settings.frontend_base_url}/payments/cancel")
    args = parser.parse_args()
    if not args.confirm_sandbox:
        parser.error("Pass --confirm-sandbox to explicitly create a PayPal Sandbox order.")

    request_id = f"mm-spike-{uuid4()}"
    invoice_id = f"MM-SPIKE-{uuid4()}"
    capture_request_id = f"mm-spike-capture-{uuid4()}"
    client = PayPalClient()
    try:
        client.get_access_token()
        print("Sandbox OAuth: PASS")
        order = client.create_order(
            amount=Decimal(args.amount),
            currency_code="USD",
            reference_id="spike-milestone",
            custom_id="spike-payment",
            invoice_id=invoice_id,
            description="MilestoneMate Sandbox spike",
            return_url=args.return_url,
            cancel_url=args.cancel_url,
            request_id=request_id,
            payee_email=args.payee_email,
        )
        order_id = order["id"]
        approval_url = next(
            link["href"] for link in order.get("links", [])
            if link.get("rel") in {"approve", "payer-action"}
        )
        print(f"Order created: {order_id} ({order.get('status')})")
        print(f"Approve in a Sandbox buyer session: {approval_url}")
        input("After the buyer is redirected back, press Enter to inspect and capture... ")

        approved = client.get_order(order_id)
        print(f"Order after approval: {approved.get('status')}")
        if approved.get("status") != "APPROVED":
            raise RuntimeError("The Sandbox order is not approved; capture was not attempted.")
        captured = client.capture_order(order_id, request_id=capture_request_id)
        capture = captured.get("purchase_units", [{}])[0].get("payments", {}).get("captures", [{}])[0]
        print(f"Capture result: {capture.get('status')} ({capture.get('id', 'no capture id')})")

        repeated_create = client.create_order(
            amount=Decimal(args.amount), currency_code="USD",
            reference_id="spike-milestone", custom_id="spike-payment",
            invoice_id=invoice_id, description="MilestoneMate Sandbox spike",
            return_url=args.return_url, cancel_url=args.cancel_url,
            request_id=request_id, payee_email=args.payee_email,
        )
        print(f"Repeated create returned same order: {repeated_create.get('id') == order_id}")
        try:
            repeated_capture = client.capture_order(order_id, request_id=capture_request_id)
            print(f"Repeated capture status: {repeated_capture.get('status')}")
        except Exception as exc:
            print(f"Repeated capture response: {type(exc).__name__} (inspect the documented PayPal issue code)")
    finally:
        client.close()


if __name__ == "__main__":
    main()
