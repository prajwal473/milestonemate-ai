# MEMBER_4 - Task File

**Role:** Payments Engineer and QA Lead - PayPal Integration, Webhooks, Testing

**Mission:** Make every cent-moving path correct, idempotent and verifiable, and prove the whole product works with tests and rehearsals.

> Source documents: doc 09 (ownership and contracts), doc 10 (workflow), doc 11 (roadmap). If this file and a doc disagree, fix both in the same PR.

## 1. Individual responsibilities
- PayPal sandbox setup, credentials, spikes S1-S8 and the payee decision.
- `PayPalClient` (OAuth, create/get/capture, verify webhook), payment state machine, services, routers.
- Webhook receiver: raw body, signature verification, dedupe, reconciliation, sync endpoint.
- Payment mock mode and mock checkout page (SIMULATED).
- `features/payments/*` UI: Pay card, return/cancel pages, ledger, status badge.
- Test strategy ownership: API/integration/E2E tests, sandbox matrix, webhook negative tests, security tests, test reports.
- Demo presenter/narrator and PayPal text for Devpost.

## 2. Files and modules you own (no one else edits these without your review)
- `backend/app/payments/**`
- `backend/app/routers/{payments,webhooks,mock_paypal}.py`
- `backend/app/models/{payment,payment_event,webhook_event}.py`, `backend/app/schemas/payment.py`
- `backend/tests/payments/**`, `backend/tests/e2e/**`, `backend/tests/test_architecture.py`
- `backend/scripts/{paypal_spike,e2e_smoke}.py`
- `frontend/src/features/payments/**`, `frontend/tests/e2e/**`
- `docs/07_PAYPAL_INTEGRATION.md` (updates), `docs/12_TESTING_STRATEGY.md` (results), `docs/test-reports/**`

## 3. Integration responsibilities
- Use `milestones.get_for_payment` and `mark_paid` (C5); never write milestone status directly.
- Use `audit.record` and `notifications.notify` for every payment transition.
- Expose `payments.service` functions per doc 09 (C7).
- Keep `PAYMENTS_MODE=mock` behaviour identical in API shape to sandbox mode.

## 4. Testing responsibilities
- Payment unit tests with mocked PayPal; state-machine table tests; concurrency tests (double click, capture + webhook).
- Sandbox matrix and webhook negative tests; report in `docs/test-reports/`.
- Own `e2e_smoke.py` in CI and the browser E2E spec; verify every member's merged work after integration.

## 5. Daily plan, deliverables and checks

### Day 1 - Sun Nov 1: Foundations, contracts and risk spikes
*Team objective:* Every member can run the stack locally; contracts C1-C3, C9, C10 are frozen; the PayPal payee decision and LLM structured output are proven.

**Your tasks**
- [ ] Create PayPal developer account; sandbox accounts: Demo Merchant (business), Second Merchant (business), Client Buyer A and B (personal); create the sandbox REST app and store credentials in the password manager.
- [ ] Write `scripts/paypal_spike.py`: OAuth -> create order (with `PayPal-Request-Id`) -> print approve link -> manual approval -> show order -> capture -> repeat with same request id.
- [ ] Run spikes S1-S8 from doc 07 section 12; record results; decide `PAYEE_MODE` with Member 1 (sign-off).
- [ ] Start a tunnel (cloudflared/ngrok), register a sandbox webhook, trigger a real capture, save real webhook JSON + headers to `tests/payments/fixtures/`.
- [ ] Draft the Postman collection (optional) and the test-account sheet (private).

**Team deliverables you contribute to**
- Repo + CI green on an empty change.
- Migration 0001 applies cleanly; register/login work via curl.
- `ai/schemas.py` merged (C3 frozen).
- Frontend login page renders with mocks; `npm run gen:api` works against the running backend.
- Spike table in doc 07 filled; `PAYEE_MODE` decided; real capture JSON saved.

**Test requirements today**
- `pytest` smoke (health, register, login, me) in CI.
- Manual: full local setup from README by a second member.
- Spike scripts run end-to-end once.

**End-of-day criteria (team)**
- [ ] All four members ran backend + frontend + DB locally.
- [ ] CI green on `main`.
- [ ] Contracts C1, C2 (shapes), C3, C9, C10 acknowledged by all in chat.
- [ ] PAYEE_MODE decision recorded in doc 07.

### Day 2 - Mon Nov 2: Projects, invitations and AI agreement draft (v0)
*Team objective:* A client can create a project and get a persisted AI-generated draft agreement through the API; PayPal client library is unit-tested.

**Your tasks**
- [ ] `payments/paypal_client.py`: token cache, `create_order`, `get_order`, `capture_order`, `verify_webhook_signature`, error mapping in `payments/errors.py`.
- [ ] SQLAlchemy models: `payment`, `payment_event`, `webhook_event` (match doc 04); `payments/state.py` transition table.
- [ ] Unit tests with `httpx.MockTransport` using the real fixtures saved on Day 1.
- [ ] Write `PAYMENTS_MODE` settings plumbing and `payments/mock_client.py` interface stub.

**Team deliverables you contribute to**
- `curl` flow: register -> create project -> clarify -> generate -> GET agreement shows persisted draft with milestones and criteria.
- Invite link works; audit entries recorded.
- PayPal client passes unit tests.
- Dashboard + wizard step 1 visible.

**Test requirements today**
- pytest: project RBAC, invitation, audit chain, postprocess amounts (table-driven), paypal_client with mocked transport.
- Manual: generate with live Gemini and with mock; compare.

**End-of-day criteria (team)**
- [ ] Agreement draft persisted from AI for the sample brief in both modes.
- [ ] No endpoint reachable by non-members (tests).
- [ ] PayPal client coverage >= 80% lines.

### Day 3 - Tue Nov 3: Agreement review/approval and PayPal order creation
*Team objective:* Both parties can approve a content-hashed agreement in the UI; the backend can create a PayPal sandbox order for an accepted milestone.

**Your tasks**
- [ ] `payments/service.create_order_for_milestone` (DB row first, PayPal order, state transitions, events, audit) and `routers/payments.py`: create, get, list by project.
- [ ] `capture_payment`, `cancel_payment` (DB transaction + `FOR UPDATE`), capture endpoint; idempotency keys wired into `PayPal-Request-Id`.
- [ ] Tests: double-create returns same payment; unique partial index; invalid-state errors; amount mismatch; all with mocked PayPal.
- [ ] Run create-order against real sandbox via curl using a hand-made `ACCEPTED` milestone row.

**Team deliverables you contribute to**
- Two browser sessions complete agreement approval; hash shown on both sides.
- Order created in PayPal sandbox through the API; payment row `PENDING_APPROVAL`.
- Eval script report committed.

**Test requirements today**
- pytest: lifecycle state machine incl. hash mismatch, edit blocked after submit, revise creates version 2, approvals reset.
- pytest: payment service with mocked PayPal; concurrency test of two simultaneous create calls.

**End-of-day criteria (team)**
- [ ] Approval flow demonstrable in UI against the real API.
- [ ] Create-order verified against real sandbox.
- [ ] Contract C4, C5 frozen.

### Day 4 - Wed Nov 4: Deliverables, AI evaluation and PayPal webhooks
*Team objective:* A freelancer uploads work, the AI evaluates it, the client decides, and the client can pay in the sandbox with a verified webhook recorded.

**Your tasks**
- [ ] `routers/webhooks.py`: raw-body read, header capture, verify via `PayPalClient.verify_webhook_signature`, store event, dedupe, process via `apply_verified_webhook`.
- [ ] Reconciliation code shared by capture/webhook/sync; `POST /api/payments/{id}/sync` (P1 stub ok).
- [ ] `features/payments`: `PayMilestoneCard`, `PaymentReturnPage`, `PaymentCancelPage`, `PaymentStatusBadge` (against mocks first).
- [ ] First real sandbox run through the API: create -> approve in browser -> capture -> webhook verified; save evidence (screenshots + event rows).

**Team deliverables you contribute to**
- API flow: upload -> evaluation `COMPLETED` -> decision -> milestone `ACCEPTED`.
- Webhook event row with `verification_status = SUCCESS` from a real sandbox capture.
- Milestone page usable with real upload.

**Test requirements today**
- pytest: truth table, evidence verifier, extraction; webhook tests: valid, invalid signature (400), duplicate event, out-of-order.
- Manual real sandbox payment x1.

**End-of-day criteria (team)**
- [ ] Injection fixture does not produce `MEETS`.
- [ ] Webhook verified end-to-end with PayPal.
- [ ] All P0 backend endpoints exist (even if rough).

### Day 5 - Thu Nov 5: Vertical slice integration (Integration Milestone 1)
*Team objective:* One complete project runs brief -> agreement -> approval -> submission -> AI evaluation -> decision -> PayPal payment -> PAID with no manual DB edits.

**Your tasks**
- [ ] Wire pay flow end-to-end in the UI: redirect, return page, capture, pending polling, failure states.
- [ ] Write `scripts/e2e_smoke.py` (API-level happy path against a running backend in mock modes) and add to CI.
- [ ] Execute the vertical slice 3 times (mock and sandbox), log defects with severity and owner.
- [ ] Verify audit trail and notifications for each step.

**Team deliverables you contribute to**
- `v0.5-slice` tag.
- 3 recorded successful slice runs.
- Defect list with owners and severities.

**Test requirements today**
- `e2e_smoke.py` green in CI (mock mode).
- Manual slice in sandbox mode x1 by someone other than the author of each part.

**End-of-day criteria (team)**
- [ ] Slice passes without DB edits.
- [ ] Every P0 requirement is either done or on the gap list with an owner and a day.

### Day 6 - Fri Nov 6: Complete P0, first deployment
*Team objective:* P0 scope is 100% complete and running on a Render staging deployment with a public webhook URL.

**Your tasks**
- [ ] Register the staging webhook URL in the PayPal dashboard; verify delivery and signature on Render.
- [ ] Failure paths with sandbox negative testing: cancel, declined instrument, duplicate capture, pending capture (simulate), PayPal 5xx.
- [ ] Finish `PAYMENTS_MODE=mock` including `/mock-paypal/checkout` and SIMULATED labelling.
- [ ] `PaymentLedger` with event timeline and webhook-verified tick (v1).

**Team deliverables you contribute to**
- Staging URL working with sandbox payments.
- P0 checklist (doc 02) all ticked.
- Mock modes complete.

**Test requirements today**
- Staging smoke: register -> full slice in mock modes; one full slice in sandbox mode.
- Webhook verified from the Render URL.

**End-of-day criteria (team)**
- [ ] P0 complete on staging.
- [ ] No open `blocker` bugs older than 4 hours.

### Day 7 - Sat Nov 7: P1 features: AI summary, dashboard intelligence, trust UI
*Team objective:* Add the high-value P1 features that differentiate the demo, without destabilizing P0.

**Your tasks**
- [ ] Payment ledger audit view finalized (PayPal IDs, timeline, verification tick); refund/reversal webhooks stored + audited.
- [ ] `POST /api/payments/{id}/sync` complete; reconciliation test (webhook missed).
- [ ] Authorization test matrix for all payment endpoints; concurrency tests (double click, parallel capture + webhook).
- [ ] Update `e2e_smoke.py` to cover rejection -> resubmission -> accept -> pay.

**Team deliverables you contribute to**
- P1 complete (or explicitly cut).
- Seed script producing a convincing demo dashboard.

**Test requirements today**
- Regression of the slice (mock + sandbox).
- Concurrency tests green.

**End-of-day criteria (team)**
- [ ] Demo path rehearsed once end-to-end by the team.
- [ ] Cut list for unfinished P1 agreed.

### Day 8 - Sun Nov 8: Hardening and FEATURE FREEZE
*Team objective:* Make it reliable and safe; stop adding features at 20:00 IST.

**Your tasks**
- [ ] Execute the full sandbox test matrix (doc 12) and webhook negative tests; document results in `docs/test-reports/2026-11-08.md`.
- [ ] Playwright (or scripted) browser E2E of the demo path; run against staging.
- [ ] Security tests for payments (tampered webhook, wrong webhook id, replay, amount tamper attempts).
- [ ] File bugs with owner + severity; verify fixes.

**Team deliverables you contribute to**
- `v0.8-featurefreeze` tag.
- Test report with pass/fail and open bugs.
- All `blocker` bugs have owners.

**Test requirements today**
- Full regression: backend, frontend, e2e, sandbox payments, AI golden set.

**End-of-day criteria (team)**
- [ ] No P0 feature missing.
- [ ] Zero known data-loss/payment-integrity bugs.
- [ ] Freeze announced.

### Day 9 - Mon Nov 9: Demo readiness and release candidate
*Team objective:* Release candidate deployed to production-like environment; repo public; Devpost draft created.

**Your tasks**
- [ ] Three full dry-runs of the demo on production (sandbox payments); fix or log issues.
- [ ] Prepare sandbox account state (funded buyer, saved login); keep the credentials sheet private.
- [ ] Write the PayPal integration section for Devpost; verify webhook delivery on production.
- [ ] Draft narration based on doc 16.

**Team deliverables you contribute to**
- `v0.9-rc1` deployed.
- Repo public with license.
- Devpost draft with text complete.
- 3 successful dry-runs.

**Test requirements today**
- Fresh-clone run by a member who did not write the README.
- Dry-runs on production.

**End-of-day criteria (team)**
- [ ] Anyone can run the project from the README in < 10 minutes in mock mode.
- [ ] Demo path works 3/3 times.

### Day 10 - Tue Nov 10: Code freeze, rehearsals and video recording
*Team objective:* Only blocker fixes; record the demo video; prepare the submission assets.

**Your tasks**
- [ ] Lead 3 rehearsals with timer (< 3:00); finalize narration script and record voice-over.
- [ ] Verify sandbox accounts, balances and PayPal login state before each take.
- [ ] Backup recordings of the PayPal approval segment and mock-mode full flow.
- [ ] Final regression run after the last merge.

**Team deliverables you contribute to**
- Complete raw footage + narration.
- Final regression report.

**Test requirements today**
- Final regression after code freeze (sandbox + mock).

**End-of-day criteria (team)**
- [ ] Video raw footage covers every segment of doc 16.
- [ ] No open blockers.

### Day 11 - Wed Nov 11: Final video, submission and buffer
*Team objective:* Submit by 22:00 IST (Nov 11), about 27 hours before the 01:30 IST Nov 13 deadline; keep Nov 12 as emergency buffer only.

**Your tasks**
- [ ] Final sandbox account/state check; run one last production smoke test before submission.
- [ ] Proofread PayPal section; confirm no escrow/hold-funds claims anywhere.
- [ ] Check the video narration matches the shipped UI.
- [ ] Monitor production and webhook health until the deadline; keep the private test-account sheet accessible.

**Team deliverables you contribute to**
- Submitted entry (screenshot of confirmation).
- Public YouTube link.
- v1.0 tag.

**Test requirements today**
- Incognito verification checklist (doc 15 section 8).

**End-of-day criteria (team)**
- [ ] Submission confirmed.
- [ ] All four members have viewed the live submission page.

## 6. Definition of done (personal checklist before you merge)
- [ ] CI green; ruff/ESLint clean; tests added for new logic.
- [ ] Contract/doc updated if behaviour changed.
- [ ] No secrets or debug output; logs sanitized.
- [ ] Audit entry + notification added where required.
- [ ] Error/loading/empty states handled (UI) or error envelope used (API).
- [ ] Tried in both mock and live modes where applicable.
- [ ] Another member re-ran the feature on `main` after merge.

## 7. Escalation
Blocked > 30 minutes: post in `#blockers` with what you tried. Contract dispute: doc 10 section 7. Member 1 decides unresolved disputes within 30 minutes; Member 4 is backup coordinator.
