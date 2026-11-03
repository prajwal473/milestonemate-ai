# 07 - PayPal Integration

Owner: **Member 4**. Package: `backend/app/payments/`. Router: `backend/app/routers/payments.py`, `webhooks.py`. UI: `frontend/src/features/payments/`.

> **Source of truth:** PayPal's official documentation (<https://developer.paypal.com/docs/api/orders/v2/>, <https://developer.paypal.com/api/rest/>, Webhooks docs). This document uses only endpoints that appear in that documentation. Items marked **VERIFY** must be confirmed against the live sandbox on Day 1 and the result written into section 12 ("Spike results").

## 1. What we use (and what we do not)

| Capability | Used? | Notes |
|---|---|---|
| OAuth 2.0 client credentials | Yes | `POST {base}/v1/oauth2/token` |
| Orders v2 - create | Yes | `POST {base}/v2/checkout/orders` |
| Orders v2 - show details | Yes | `GET {base}/v2/checkout/orders/{id}` |
| Orders v2 - capture | Yes | `POST {base}/v2/checkout/orders/{id}/capture` |
| Webhooks + verify signature | Yes | `POST {base}/v1/notifications/verify-webhook-signature` |
| Sandbox environment | Yes (only) | `https://api-m.sandbox.paypal.com` |
| Authorize-then-capture (`intent=AUTHORIZE`) | **No** | Authorizations expire (honor period) and would imply "held funds" - we do not claim that |
| Escrow / holding funds / payouts / Commerce Platform | **No** | Not claimed, not built |
| PayPal Agent Toolkit / MCP | **P2 only** | Verify tool names at docs.paypal.ai before any use |

Base URLs: sandbox `https://api-m.sandbox.paypal.com`; live `https://api-m.paypal.com` (never configured in this project).

## 2. Developer setup (Day 1, Member 4)

1. Create/log in to a PayPal Developer account at <https://developer.paypal.com/>.
2. Dashboard -> **Testing Tools -> Sandbox Accounts**. Create:
   * **Business** account "MilestoneMate Demo Merchant" (acts as the freelancer/merchant in `demo_merchant` mode; its REST app owns the credentials).
   * **Business** account "Second Merchant" (used only for the direct-payee spike).
   * **Personal** account "Client Buyer A" (fund with a sandbox balance/card as available) and "Client Buyer B" (backup).
3. Dashboard -> **Apps & Credentials** -> **Sandbox** tab -> use the default app or **Create App** (type: Merchant) tied to the Demo Merchant business account. Copy **Client ID** and **Secret** into the team password manager and local `.env` (`PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`). Never commit.
4. Same app page -> **Add Webhook**: URL `https://<tunnel-or-render-host>/api/webhooks/paypal`; events (section 8). Copy the **Webhook ID** into `PAYPAL_WEBHOOK_ID`.
5. Local webhook testing needs a public URL: `cloudflared tunnel --url http://localhost:8000` or `ngrok http 8000`. The tunnel URL changes per run; update the webhook URL in the dashboard (or use the staging Render URL, which is stable).
6. Keep a private sheet (not in Git) with sandbox account emails/passwords for rehearsals.

## 3. Payee model - the one design decision that needs proof on Day 1

A hackathon app has **one** set of REST credentials (the *platform/merchant* app). Orders are created with those credentials, so by default the **payee is the merchant account that owns the app**. Directing money to a *different* merchant normally requires PayPal's partner/multiparty setup (the `PayPal-Auth-Assertion` header and merchant consent; see PayPal "make API requests" docs on first-party vs third-party calls). We therefore support two modes:

| `PAYEE_MODE` | Behaviour | When to use |
|---|---|---|
| `demo_merchant` (**default**) | `purchase_units[0]` has no `payee` override. The sandbox merchant that owns the REST app receives the money. In the demo that merchant **is** the "freelancer" business account. UI text: *"Sandbox demo: payments are received by the project's configured sandbox merchant account."* | Always works; honest limitation |
| `direct_payee` | `purchase_units[0].payee.email_address = freelancer.paypal_email` (a sandbox business email) | **Only if the Day-1 spike (section 12, test S2) proves PayPal accepts it for first-party credentials** |

Do **not** claim multi-freelancer payouts. The submission text says: "MVP routes sandbox payments to a configured sandbox merchant; production would use PayPal's multiparty/marketplace products (onboarding, PayPal-Auth-Assertion) - not implemented."

Also note PayPal's "Cannot pay self" behaviour: the buyer (client) account must differ from the receiving merchant account.

## 4. OAuth 2.0

```
POST https://api-m.sandbox.paypal.com/v1/oauth2/token
Authorization: Basic base64(CLIENT_ID:CLIENT_SECRET)
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
```
Response includes `access_token`, `expires_in` (seconds), `token_type: Bearer`.

Implementation (`paypal_client.py`):
* In-process cache `{token, expires_at}`; refresh when `now > expires_at - 60 s`; a lock prevents concurrent refresh.
* On `401` from any call: drop cache, fetch a new token, retry **once**.
* Credentials only from `Settings`; never logged.
* `httpx.Client(timeout=httpx.Timeout(15.0, connect=5.0))`, 2 retries on connection errors/5xx for idempotent calls (all POSTs carry `PayPal-Request-Id`, see section 7).

## 5. Create order

Backend function: `payments.service.create_order_for_milestone(db, milestone_id, actor) -> Payment`.

Preconditions (all re-checked inside the DB transaction): actor is project `CLIENT`; milestone `ACCEPTED`; no live payment for the milestone (unique partial index also protects).

Steps:
1. Insert `payments` row `CREATED` with `amount = milestone.amount` (from DB), `idempotency_key` (UUID), `payee_mode`.
2. Call PayPal:
```
POST /v2/checkout/orders
Authorization: Bearer <token>
Content-Type: application/json
PayPal-Request-Id: mm-create-<payment.idempotency_key>
Prefer: return=representation
```
```json
{
  "intent": "CAPTURE",
  "purchase_units": [
    {
      "reference_id": "<milestone_id>",
      "custom_id": "<payment_id>",
      "invoice_id": "MM-<payment_id>",
      "description": "MilestoneMate: <milestone title> (<project title>)",
      "amount": { "currency_code": "USD", "value": "300.00" }
      // direct_payee mode only: "payee": { "email_address": "<freelancer sandbox business email>" }
    }
  ],
  "payment_source": {
    "paypal": {
      "experience_context": {
        "brand_name": "MilestoneMate AI",
        "user_action": "PAY_NOW",
        "shipping_preference": "NO_SHIPPING",
        "landing_page": "LOGIN",
        "return_url": "<FRONTEND_BASE_URL>/payments/return?payment_id=<payment_id>",
        "cancel_url": "<FRONTEND_BASE_URL>/payments/cancel?payment_id=<payment_id>"
      }
    }
  }
}
```
Field notes (**VERIFY** each in the sandbox response on Day 1): `payment_source.paypal.experience_context.*` keys follow the current Orders v2 reference; `custom_id` and `invoice_id` are Orders v2 purchase-unit fields (`invoice_id` must be unique per merchant - using the payment id avoids `DUPLICATE_INVOICE_ID`). `amount.value` is a **string with 2 decimals**, never a float.

3. Response: order `id`, `status` (expected `PAYER_ACTION_REQUIRED` for this request shape), `links[]` including the link with `rel = "payer-action"` (older integrations use `rel = "approve"`; code accepts either). Save `paypal_order_id`, `paypal_order_status`, `approve_url`; payment -> `PENDING_APPROVAL`; write `payment_events(ORDER_CREATED)`; audit `PAYMENT_CREATED`.
4. Return payment to the frontend, which does `window.location.assign(approve_url)`.

Errors: PayPal 4xx/5xx -> payment `FAILED` (`failure_code` = PayPal `name`, `failure_message` sanitized, keep `debug_id`), `502 PAYPAL_ERROR`; client may retry (new payment row; unique index allows because `FAILED` is not live).

## 6. Buyer approval and capture

### 6.1 Buyer approval
The client approves on PayPal's sandbox page using a **sandbox personal** account. PayPal redirects the browser to `return_url` with `token=<ORDER_ID>&PayerID=<payer>` query params. The frontend route `/payments/return` extracts `payment_id` (ours) and `token` (PayPal order id) and calls `POST /api/payments/{payment_id}/capture` with `{ "paypal_order_id": token }`.

Cancel: `/payments/cancel?payment_id=` calls `POST /api/payments/{id}/cancel` (-> `CANCELLED`, milestone stays `ACCEPTED`).

### 6.2 Capture (`payments.service.capture_payment`)
```
BEGIN;
SELECT * FROM payments WHERE id = :id FOR UPDATE;       -- serialize concurrent capture/webhook
```
1. Authorization: caller is the project `CLIENT` and `payment.payer_id`.
2. Validate `paypal_order_id == payment.paypal_order_id` (else `422`).
3. If `status = COMPLETED` -> return as is (idempotent).
4. `GET /v2/checkout/orders/{id}`; if `status != APPROVED` -> `409 INVALID_STATE` ("not approved on PayPal yet"); if `COMPLETED` already -> reconcile locally.
5. Set `APPROVED` (+ `approved_at`) if it was `PENDING_APPROVAL`; event `APPROVAL_RETURNED`.
6. `POST /v2/checkout/orders/{id}/capture` with `PayPal-Request-Id: mm-capture-<idempotency_key>`, `Content-Type: application/json`, body `{}`, header `Prefer: return=representation`.
7. Parse `purchase_units[0].payments.captures[0]` -> `id`, `status`, `amount`. **VERIFY** exact response paths in sandbox.
   * `COMPLETED` -> payment `COMPLETED`, `paypal_capture_id`, `captured_at`; call `services.milestones.mark_paid` (milestone `PAID`; project `COMPLETED` if all paid); audit `PAYMENT_COMPLETED`, `MILESTONE_PAID`; notify freelancer.
   * `PENDING` -> `CAPTURE_PENDING`; webhook will finish.
   * Declined/other -> `FAILED`/`DENIED` with message.
8. Amount check: captured `amount.value`/`currency_code` must equal `payment.amount`/`USD`; mismatch -> log `CRITICAL`, mark `FAILED`, do **not** mark milestone paid.
```
COMMIT;
```
The AI package and the frontend never call capture directly; only an authenticated client request reaches this function.

## 7. Idempotency

| Layer | Mechanism |
|---|---|
| PayPal API | `PayPal-Request-Id` on every POST: `mm-create-<idempotency_key>` and `mm-capture-<idempotency_key>`. PayPal stores request ids for a limited window (documented as 6 hours by default) and returns the original result for a repeated id |
| Database | `payments.idempotency_key` UNIQUE; partial unique index (one live payment per milestone); `paypal_order_id` and `paypal_capture_id` UNIQUE |
| State machine | `COMPLETED` is terminal; transitions validated by `payments/state.py::can_transition(from, to)`; illegal transitions are logged and ignored |
| Concurrency | `SELECT ... FOR UPDATE` on the payment row in capture, sync and webhook processing |
| Webhooks | `paypal_webhook_events.paypal_event_id` UNIQUE -> duplicates become `IGNORED` |
| UI | Pay button disabled while pending; backend re-call returns the same `PENDING_APPROVAL` payment |

Because PayPal's request-id window is finite, the **database constraints are the long-term guarantee**; the header protects network retries.

## 8. Webhooks

Subscribe to: `CHECKOUT.ORDER.APPROVED`, `PAYMENT.CAPTURE.COMPLETED`, `PAYMENT.CAPTURE.PENDING`, `PAYMENT.CAPTURE.DENIED`, `PAYMENT.CAPTURE.REFUNDED`, `PAYMENT.CAPTURE.REVERSED`. (Refund/reversal: stored and audited only; no UI action in MVP.)

### 8.1 Receive and verify
`POST /api/webhooks/paypal`:
1. Read the **raw request body** as bytes (do not let a framework re-serialize it).
2. Collect headers `PAYPAL-TRANSMISSION-ID`, `PAYPAL-TRANSMISSION-TIME`, `PAYPAL-TRANSMISSION-SIG`, `PAYPAL-CERT-URL`, `PAYPAL-AUTH-ALGO`.
3. Verify through PayPal:
```
POST /v1/notifications/verify-webhook-signature
Authorization: Bearer <token>
{
  "auth_algo": "<PAYPAL-AUTH-ALGO>",
  "cert_url": "<PAYPAL-CERT-URL>",
  "transmission_id": "<PAYPAL-TRANSMISSION-ID>",
  "transmission_sig": "<PAYPAL-TRANSMISSION-SIG>",
  "transmission_time": "<PAYPAL-TRANSMISSION-TIME>",
  "webhook_id": "<PAYPAL_WEBHOOK_ID>",
  "webhook_event": <the event JSON exactly as received>
}
```
   Success: `{"verification_status": "SUCCESS"}`. Anything else (`FAILURE`, HTTP error) -> not trusted.
   **Implementation tip:** splice the raw body text into the request JSON string instead of `json.loads` -> `json.dumps`, because re-serialization can change the bytes PayPal signed.
4. Insert into `paypal_webhook_events` (`verification_status`, payload). Unverified events: respond `400`, never process. Never trust `event_type` or amounts from an unverified event.
5. Dedupe on `paypal_event_id` (if the insert conflicts, respond `200`).

### 8.2 Process (verified events only)
Do not trust the webhook body for state; **re-fetch** the order/capture from PayPal (`GET /v2/checkout/orders/{id}` using `resource.supplementary_data.related_ids.order_id` for captures, or the `up` link) and then apply the same reconciliation code as capture:

| Event | Action |
|---|---|
| `CHECKOUT.ORDER.APPROVED` | If payment `PENDING_APPROVAL` -> `APPROVED` (do **not** capture automatically; the client's explicit capture request does that) |
| `PAYMENT.CAPTURE.COMPLETED` | Match `custom_id`/order id -> payment; if not `COMPLETED` -> complete (same function as capture success); else `IGNORED` |
| `PAYMENT.CAPTURE.PENDING` | `CAPTURE_PENDING` |
| `PAYMENT.CAPTURE.DENIED` | `DENIED`; notify client |
| `PAYMENT.CAPTURE.REFUNDED` / `REVERSED` | Store + audit + notify; no state change in MVP |
| anything else | `IGNORED` |

Respond `200` quickly; processing errors are stored (`FAILED` + `error`) and PayPal retries are tolerated by idempotency. Out-of-order delivery is safe because processing re-reads PayPal state and respects terminal states.

### 8.3 Known caveats (**VERIFY** on Day 1)
* The Developer Dashboard webhook *simulator* sends sample events that typically do **not** verify against a real webhook id. Use real sandbox transactions to test. In `PAYMENTS_MODE=mock` only, a flag `ALLOW_UNVERIFIED_WEBHOOKS_IN_MOCK=true` may accept simulated payloads; it is ignored in `paypal_sandbox` mode and must never be set in staging/production.
* Webhook delivery to `localhost` requires a tunnel.

## 9. Payment states

| Internal | PayPal source of truth | Transitions in | UI label |
|---|---|---|---|
| `CREATED` | - | row inserted | "Preparing payment..." |
| `PENDING_APPROVAL` | order `PAYER_ACTION_REQUIRED` / `CREATED` | order created | "Waiting for PayPal approval" |
| `APPROVED` | order `APPROVED` | return, webhook | "Approved - finishing payment" |
| `CAPTURE_PENDING` | capture `PENDING` | capture response, webhook | "PayPal is processing" |
| `COMPLETED` | capture `COMPLETED` | capture response, webhook | "Paid" |
| `FAILED` | API error / mismatch | any | "Payment failed - try again" |
| `DENIED` | capture `DECLINED`/`DENIED` | capture, webhook | "Declined by PayPal" |
| `CANCELLED` | buyer cancelled | cancel URL, expiry | "Cancelled" |

## 10. Error handling

| Situation | Handling |
|---|---|
| `401` from PayPal | refresh token once, retry |
| `422 UNPROCESSABLE_ENTITY` (e.g., `ORDER_NOT_APPROVED`, `ORDER_ALREADY_CAPTURED`, `PAYEE_ACCOUNT_RESTRICTED`, `INSTRUMENT_DECLINED`) | map `details[0].issue` to a friendly message; `ORDER_ALREADY_CAPTURED` -> reconcile via GET order; `INSTRUMENT_DECLINED` -> tell client to choose another funding source on PayPal (PayPal supports restarting the approval) |
| `429` / `5xx` / timeouts | retry with backoff (POSTs are idempotent via request id); then `502 PAYPAL_ERROR` |
| Client closes the tab after approving | Webhook `CHECKOUT.ORDER.APPROVED` + dashboard "Resume payment" button; capture still needs the client's click |
| Capture succeeded but local DB commit failed | Webhook `PAYMENT.CAPTURE.COMPLETED` reconciles; `POST /payments/{id}/sync` as manual fix |
| Amount/currency mismatch | `FAILED`, CRITICAL log, no milestone update |
| PayPal outage during demo | Switch `PAYMENTS_MODE=mock`; banner "SIMULATED" |

Error mapping lives in `payments/errors.py`; messages never include secrets; always keep PayPal `debug_id` in `failure_message`/logs for support.

Negative testing: PayPal documents request headers to simulate error responses in the sandbox (see "Simulate negative responses with request headers" in the PayPal Sandbox docs). Use them in tests (doc 12).

## 11. Mock mode (`PAYMENTS_MODE=mock`)

`payments/mock_client.py` implements the same interface as `PayPalClient` (`create_order`, `get_order`, `capture_order`, `verify_webhook_signature`) with an in-DB fake order store. `approve_url` points to `/mock-paypal/checkout`, a page with **"Approve (SIMULATED)"** and **"Cancel"**; the UI shows a persistent yellow "SIMULATED PAYMENTS" banner. Payments created in mock mode have `provider = MOCK` and can never be confused with sandbox transactions in the ledger. Mock mode exists for judges without PayPal credentials and as a demo backup (doc 16).

## 12. Spike results (fill in on Day 1 - Member 4; sign-off by Member 1)

| ID | Test | Expected | Result | Decision |
|---|---|---|---|---|
| S1 | OAuth token with sandbox creds | `200`, `access_token` | _TBD_ | - |
| S2 | Create order with `payee.email_address` of "Second Merchant" using the Demo Merchant app credentials | Either accepted (-> `direct_payee` viable) or rejected with a permission error (-> `demo_merchant`) | _TBD_ | `PAYEE_MODE = ___` |
| S3 | Create order with `payment_source.paypal.experience_context`; confirm status and link `rel` | `PAYER_ACTION_REQUIRED`, `payer-action` | _TBD_ | - |
| S4 | Approve with Buyer A; show order; capture | `APPROVED` -> capture `COMPLETED` | _TBD_ | Save real capture JSON to `backend/tests/payments/fixtures/capture_completed.json` |
| S5 | Repeat create with the same `PayPal-Request-Id` | Same order returned | _TBD_ | - |
| S6 | Repeat capture after completion | `ORDER_ALREADY_CAPTURED` or same result | _TBD_ | map in `errors.py` |
| S7 | Webhook delivered via tunnel; verify-signature returns `SUCCESS` | `SUCCESS` | _TBD_ | Save real event JSON + headers to fixtures |
| S8 | Webhook simulator event verification | Likely `FAILURE` | _TBD_ | document in section 8.3 |

## 13. Sandbox testing checklist (details in doc 12)
Happy path; cancel; decline funding source; double-click Pay; repeat capture; webhook replay; tampered webhook body; wrong `webhook_id`; capture pending (if reproducible); network failure mid-capture; amount mismatch unit test.

## 14. Judge-facing note
README states: sandbox only; to run payments live in sandbox a judge needs their own PayPal sandbox app (instructions in README) **or** can use `PAYMENTS_MODE=mock`. Do not publish the REST secret. Sandbox *buyer* credentials may be shared in the hosted-demo instructions if the team decides (human decision list, doc 15).
