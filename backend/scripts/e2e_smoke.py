#!/usr/bin/env python3
"""Run the payment API smoke flow against a running MilestoneMate backend.

Required environment: E2E_CLIENT_EMAIL, E2E_CLIENT_PASSWORD,
E2E_MILESTONE_ID. The milestone must already be accepted. Credentials are
read from the environment and never printed.
"""

import argparse
import os
import sys
from getpass import getpass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="Backend base URL, e.g. http://localhost:8000")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--mock", action="store_true", help="Require a mock provider flow")
    mode.add_argument("--sandbox", action="store_true", help="Pause for manual PayPal Sandbox approval")
    parser.add_argument(
        "--scenario", choices=("success", "reject", "cancel", "resubmit"),
        default="success", help="Mock checkout scenario (ignored in --sandbox mode)",
    )
    args = parser.parse_args()
    email = os.environ.get("E2E_CLIENT_EMAIL")
    password = os.environ.get("E2E_CLIENT_PASSWORD") or getpass("Client password: ")
    milestone_id = os.environ.get("E2E_MILESTONE_ID")
    if not email or not milestone_id:
        parser.error("Set E2E_CLIENT_EMAIL and E2E_MILESTONE_ID first.")
    if args.sandbox and args.scenario != "success":
        parser.error("Sandbox mode supports only the manual success scenario.")

    base = args.base_url.rstrip("/")
    with httpx.Client(base_url=base, timeout=30) as client:
        login = client.post("/api/auth/login", json={"email": email, "password": password})
        login.raise_for_status()
        client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"

        created = client.post(f"/api/milestones/{milestone_id}/payments")
        created.raise_for_status()
        payment = created.json()
        payment_id = payment["id"]

        if args.sandbox:
            if payment.get("provider") != "PAYPAL":
                raise RuntimeError("Server did not return a PayPal Sandbox payment.")
            print("Open the approval URL in a Sandbox buyer session:", payment["approve_url"])
            input("After Sandbox redirects back, press Enter to capture... ")
        else:
            if payment.get("provider") != "MOCK" or not str(payment.get("approve_url", "")).startswith("/mock-paypal/"):
                raise RuntimeError("Mock smoke requires PAYMENTS_MODE=mock on the server.")
            if args.scenario in {"reject", "cancel", "resubmit"}:
                action = "cancel" if args.scenario in {"cancel", "resubmit"} else "reject"
                result = client.post(f"/mock-paypal/checkout/{payment['paypal_order_id']}/{action}", follow_redirects=False)
                result.raise_for_status()
                state = client.get(f"/api/payments/{payment_id}").json()["status"]
                expected = "CANCELLED" if action == "cancel" else "DENIED"
                if state != expected:
                    raise AssertionError(f"Expected {expected}; received {state}.")
                print(f"Mock {action}: {state}")
                if args.scenario != "resubmit":
                    return 0
                created = client.post(f"/api/milestones/{milestone_id}/payments")
                created.raise_for_status()
                payment = created.json()
                payment_id = payment["id"]
            approved = client.post(
                f"/mock-paypal/checkout/{payment['paypal_order_id']}/approve",
                follow_redirects=False,
            )
            approved.raise_for_status()

        capture = client.post(
            f"/api/payments/{payment_id}/capture",
            json={"paypal_order_id": payment["paypal_order_id"]},
        )
        capture.raise_for_status()
        result = capture.json()
        if result.get("status") != "COMPLETED":
            raise AssertionError(f"Payment did not complete: {result.get('status')}")
        print(f"Payment smoke passed: status={result['status']} payment_id={payment_id}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (httpx.HTTPError, AssertionError, RuntimeError, KeyError) as exc:
        print(f"Payment smoke failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
