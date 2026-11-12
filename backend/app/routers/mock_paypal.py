from html import escape
import secrets
import hmac
from urllib.parse import parse_qs
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.dependencies import get_db
from app.models import Payment
from app.payments.errors import InvalidPaymentStateError, PaymentNotFoundError
from app.payments.mock_client import MockPaymentClient
from app.payments.service import (
    approve_mock_payment,
    cancel_payment,
    reject_mock_payment,
    _restore_mock_order,
)

router = APIRouter(prefix="/mock-paypal", tags=["Mock PayPal"])


def _mock_order(db: Session, order_id: str) -> Payment:
    if settings.payments_mode.lower() != "mock":
        raise HTTPException(status_code=404, detail="Mock checkout is disabled.")
    payment = db.query(Payment).filter_by(paypal_order_id=order_id).first()
    if payment is None or payment.provider != "MOCK":
        raise HTTPException(status_code=404, detail="Mock order not found.")
    return payment


@router.get("/checkout", response_class=HTMLResponse)
def checkout(order_id: str, db: Session = Depends(get_db)):
    payment = _mock_order(db, order_id)
    _restore_mock_order(payment)
    try:
        order = MockPaymentClient().get_order(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Mock order not found.") from exc
    if order["status"] != "CREATED":
        raise HTTPException(status_code=409, detail="This mock checkout is no longer open.")
    amount = escape(order["purchase_units"][0]["amount"]["value"])
    order_id_html = escape(order_id, quote=True)
    csrf_token = secrets.token_urlsafe(32)
    csrf_field = f'<input type="hidden" name="csrf_token" value="{escape(csrf_token, quote=True)}">'
    body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Simulated PayPal Checkout</title>
<style>body{{font:16px system-ui,sans-serif;max-width:38rem;margin:4rem auto;padding:1rem;color:#182230}}.banner{{background:#fff3c4;border:1px solid #e6c65b;padding:1rem;font-weight:700}}button{{padding:.8rem 1rem;margin:.5rem .5rem .5rem 0;cursor:pointer}}</style></head>
<body><p class="banner">SIMULATED PAYMENTS — no real PayPal transaction will occur.</p>
<h1>MilestoneMate mock checkout</h1><p>Amount: <strong>{amount} USD</strong></p>
<form method="post" action="/mock-paypal/checkout/{order_id_html}/approve">{csrf_field}<button>Approve (SIMULATED)</button></form>
<form method="post" action="/mock-paypal/checkout/{order_id_html}/reject">{csrf_field}<button>Reject (SIMULATED)</button></form>
<form method="post" action="/mock-paypal/checkout/{order_id_html}/cancel">{csrf_field}<button>Cancel</button></form>
</body></html>"""
    response = HTMLResponse(body)
    response.set_cookie("mock_checkout_csrf", csrf_token, httponly=True, samesite="strict", secure=False, path="/mock-paypal")
    return response


@router.post("/checkout/{order_id}/{action}")
async def checkout_action_route(
    order_id: str,
    action: str,
    request: Request,
    db: Session = Depends(get_db),
):
    form = parse_qs((await request.body()).decode("utf-8", errors="replace"))
    csrf_token = (form.get("csrf_token") or [""])[0]
    csrf_cookie = request.cookies.get("mock_checkout_csrf")
    if not csrf_cookie or not hmac.compare_digest(csrf_cookie, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid checkout request.")
    return checkout_action(order_id, action, db)


def checkout_action(order_id: str, action: str, db: Session):
    payment = _mock_order(db, order_id)
    if action == "approve":
        try:
            approve_mock_payment(db, order_id=order_id)
        except (ValueError, InvalidPaymentStateError, PaymentNotFoundError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        url = (
            f"{settings.frontend_base_url.rstrip('/')}/payments/return"
            f"?payment_id={payment.id}&token={quote(order_id)}"
        )
    elif action == "reject":
        try:
            reject_mock_payment(db, order_id=order_id)
        except (PaymentNotFoundError, InvalidPaymentStateError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        url = f"{settings.frontend_base_url.rstrip('/')}/payments/return?payment_id={payment.id}&rejected=1"
    elif action == "cancel":
        try:
            _restore_mock_order(payment)
            MockPaymentClient.cancel_order(order_id)
            cancel_payment(db, payment_id=payment.id, actor_id=payment.payer_id)
        except (ValueError, InvalidPaymentStateError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        url = f"{settings.frontend_base_url.rstrip('/')}/payments/cancel?payment_id={payment.id}"
    else:
        raise HTTPException(status_code=404, detail="Unknown checkout action.")
    return RedirectResponse(url, status_code=303)
