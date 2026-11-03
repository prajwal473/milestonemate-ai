# 11 - Day Execution Roadmap (11 days)

**Calendar (IST):** Day 1 = Sun Nov 1 ... Day 11 = Wed Nov 11, 2026. Official deadline: **Thu Nov 12, 2026 12:00 PM PT = Fri Nov 13, 01:30 IST**. Internal submission target: **Wed Nov 11, 22:00 IST**. Nov 12 and the hours before 01:30 IST Nov 13 are emergency buffer only.

**Rituals:** standup 10:00 IST; integration check 20:30 IST (Member 1); sync 21:00 IST. See doc 10.

**Parallelism principle:** every day each member works on a separate module behind a frozen contract (doc 09 section 3) using mocks where a dependency is not ready; integration happens continuously and intensively on Day 5.

## Overview

| Day | Date | Theme | Gate at end of day |
|---|---|---|---|
| 1 | Sun Nov 1 | Foundations, contracts and risk spikes | Local stack + contracts + PayPal decision |
| 2 | Mon Nov 2 | Projects, invitations and AI agreement draft (v0) | AI draft persisted via API |
| 3 | Tue Nov 3 | Agreement review/approval and PayPal order creation | Both parties approve in UI; PayPal order created |
| 4 | Wed Nov 4 | Deliverables, AI evaluation and PayPal webhooks | Upload -> AI eval -> decision -> sandbox pay (API) |
| 5 | Thu Nov 5 | Vertical slice integration (Integration Milestone 1) | **Vertical slice works in UI** |
| 6 | Fri Nov 6 | Complete P0, first deployment | **P0 complete on staging** |
| 7 | Sat Nov 7 | P1 features: AI summary, dashboard intelligence, trust UI | P1 complete |
| 8 | Sun Nov 8 | Hardening and FEATURE FREEZE | **FEATURE FREEZE** |
| 9 | Mon Nov 9 | Demo readiness and release candidate | RC deployed, repo public, Devpost draft |
| 10 | Tue Nov 10 | Code freeze, rehearsals and video recording | **CODE FREEZE**, video footage recorded |
| 11 | Wed Nov 11 | Final video, submission and buffer | **SUBMITTED** |

### Capacity and feasibility check
Assumption: ~7 productive hours/day per member x 11 days = ~77 h each, ~308 h total. Estimated effort of the P0 scope by owner: Member 1 ~70 h, Member 2 ~55 h, Member 3 ~75 h (largest; mitigated by Member 4 owning payment UI and Member 2 owning evaluation UI, plus a small component set), Member 4 ~65 h. Buffer is intentionally concentrated in Days 5-6 (integration) and Day 8-10 (hardening/rehearsal). Verdict: **achievable if P1 items are cut first and the Day-8 freeze is respected.** Cut order if behind: (1) image deliverables, (2) version-history UI, (3) AI summary card, (4) chain-verify badge, (5) sync endpoint UI, (6) notifications page (keep bell only).

---

## Day 1 - Sun Nov 1: Foundations, contracts and risk spikes

**Main objective:** Every member can run the stack locally; contracts C1-C3, C9, C10 are frozen; the PayPal payee decision and LLM structured output are proven.

**Member 1**
- [ ] Create the private GitHub repo, commit `LICENSE` (MIT), `.gitignore`, `.env.example`, docs; enable branch protection, CODEOWNERS, PR template, labels, project board.
- [ ] Scaffold backend: `app/main.py`, `core/{config,errors,logging,deps,security}.py`, `db/{session,base}.py`, `requirements.txt`, `Dockerfile`, ruff + pytest config.
- [ ] `docker-compose.yml` (postgres:16, volume, healthcheck); Alembic init; migration `0001_initial_schema` implementing doc 04 SQL exactly (incl. partial indexes and audit trigger).
- [ ] Auth: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `PATCH /api/users/me` (argon2id, JWT), `GET /api/health`, `GET /api/config`.
- [ ] CI workflow (`backend`, `frontend`, `secrets` jobs); export script `scripts/export_openapi.py`; post stub signatures for `audit.record`, `notifications.notify` (C4).

**Member 2**
- [ ] Obtain Gemini API key (Google AI Studio); look up and pin the current Flash-class model name in `.env.example` notes; put the key in the team password manager.
- [ ] Commit `app/ai/schemas.py` (all Pydantic models from doc 06 section 4) **by 13:00 IST** - this freezes contract C3.
- [ ] Implement `ai/llm/base.py` (`LLMClient`), `gemini.py` (JSON mode + schema), `mock.py` (fixture lookup), retry/timeout wrapper, `ai/runs.py` skeleton.
- [ ] Spike `scripts/ai_spike.py`: run clarify + agreement prompts on 3 sample briefs; save raw outputs in `tests/ai/fixtures/`; note failure patterns.
- [ ] Write 5 golden briefs (`brief_*.txt`) and 5 deliverable fixtures (`good.md`, `partial.md`, `missing.md`, `empty.md`, `injection.md`) for the coffee-landing-page demo project.

**Member 3**
- [ ] Scaffold `frontend/` (Vite, React 18, TypeScript strict, Tailwind, React Router, TanStack Query, ESLint/Prettier, Vitest).
- [ ] Implement design tokens from doc 08 (`tailwind.config.ts`), `AppShell` (top bar, left nav, banners), routes map, 404 page.
- [ ] Build `api/client.ts` (fetch wrapper: base URL, bearer token, error-envelope mapping, request id), auth context, `RequireAuth`.
- [ ] Build UI primitives: Button, Card, Badge/StatusBadge, Input, Textarea, Modal, Toast, Skeleton, EmptyState, ErrorState, Banner.
- [ ] Login and Register pages (with `VITE_USE_MOCKS`); create `api/mocks/` fixtures replicating doc 05 examples; add `npm run gen:api`.

**Member 4**
- [ ] Create PayPal developer account; sandbox accounts: Demo Merchant (business), Second Merchant (business), Client Buyer A and B (personal); create the sandbox REST app and store credentials in the password manager.
- [ ] Write `scripts/paypal_spike.py`: OAuth -> create order (with `PayPal-Request-Id`) -> print approve link -> manual approval -> show order -> capture -> repeat with same request id.
- [ ] Run spikes S1-S8 from doc 07 section 12; record results; decide `PAYEE_MODE` with Member 1 (sign-off).
- [ ] Start a tunnel (cloudflared/ngrok), register a sandbox webhook, trigger a real capture, save real webhook JSON + headers to `tests/payments/fixtures/`.
- [ ] Draft the Postman collection (optional) and the test-account sheet (private).

**Expected files / artefacts**
- `.github/workflows/ci.yml`, `docker-compose.yml`, `backend/alembic/versions/0001_initial_schema.py`
- `backend/app/{main.py,core/*,db/*,routers/{auth,users,health}.py}`
- `backend/app/ai/{schemas.py,llm/*,runs.py}`, `backend/tests/ai/fixtures/*`
- `frontend/{package.json,tailwind.config.ts,src/{App.tsx,routes.tsx,api/client.ts,components/ui/*,features/auth/*}}`
- `backend/scripts/paypal_spike.py`, `backend/tests/payments/fixtures/*`

**Dependencies**
- Member 2 and Member 4 need the repo and `.env.example` (Member 1, morning).
- Member 3 needs doc 05 examples (already written).

**Deliverables**
- Repo + CI green on an empty change.
- Migration 0001 applies cleanly; register/login work via curl.
- `ai/schemas.py` merged (C3 frozen).
- Frontend login page renders with mocks; `npm run gen:api` works against the running backend.
- Spike table in doc 07 filled; `PAYEE_MODE` decided; real capture JSON saved.

**Testing requirements**
- `pytest` smoke (health, register, login, me) in CI.
- Manual: full local setup from README by a second member.
- Spike scripts run end-to-end once.

**End-of-day completion criteria**
- [ ] All four members ran backend + frontend + DB locally.
- [ ] CI green on `main`.
- [ ] Contracts C1, C2 (shapes), C3, C9, C10 acknowledged by all in chat.
- [ ] PAYEE_MODE decision recorded in doc 07.

---

## Day 2 - Mon Nov 2: Projects, invitations and AI agreement draft (v0)

**Main objective:** A client can create a project and get a persisted AI-generated draft agreement through the API; PayPal client library is unit-tested.

**Member 1**
- [ ] Models + routers: `projects` (create/list/get/patch), `invitations` (create, preview, accept; token hash), `require_project_member` / `require_role` dependencies.
- [ ] Agreement/milestone/criteria models and read endpoints; `services/agreements.create_draft_version` and `compute_content_hash` (C4).
- [ ] `services/audit.record` with advisory lock + hash chain; `services/notifications.notify`; `GET /api/projects/{id}/audit` (without verify badge UI).
- [ ] Tests: RBAC for project endpoints, invitation flow, audit chain integrity.

**Member 2**
- [ ] `ai/service.clarify` + `POST /api/projects/{id}/agreement/clarify` (prompt `clarify.v1`, validation, retry, ai_runs logging).
- [ ] `ai/service.generate_agreement` + `POST .../generate` calling `create_draft_version` (prompt `agreement.v1`).
- [ ] `ai/postprocess.py` v1: amount rebalance, date normalization, counts; `ai/fallbacks.template_agreement` + `POST .../template`.
- [ ] Mock provider fixtures for the coffee brief (clarify + agreement) so others can build offline.

**Member 3**
- [ ] Generate typed API (`schema.d.ts`) from the running backend; build `api/hooks` (projects, auth).
- [ ] Dashboard page v0 (project cards, empty state, skeletons) and Projects list.
- [ ] New Project wizard step 1 (title + brief) and step 2 shell (loading state while clarify runs).
- [ ] Project Overview page shell with tabs and milestone stepper using mock data.

**Member 4**
- [ ] `payments/paypal_client.py`: token cache, `create_order`, `get_order`, `capture_order`, `verify_webhook_signature`, error mapping in `payments/errors.py`.
- [ ] SQLAlchemy models: `payment`, `payment_event`, `webhook_event` (match doc 04); `payments/state.py` transition table.
- [ ] Unit tests with `httpx.MockTransport` using the real fixtures saved on Day 1.
- [ ] Write `PAYMENTS_MODE` settings plumbing and `payments/mock_client.py` interface stub.

**Expected files / artefacts**
- `backend/app/{routers/{projects,invitations,agreements}.py,services/{agreements,audit,notifications}.py,models/*}`
- `backend/app/{ai/service.py,ai/prompts/*,ai/postprocess.py,ai/fallbacks.py,routers/ai.py}`
- `frontend/src/{api/schema.d.ts,api/hooks/*,features/dashboard/*,features/projects/*}`
- `backend/app/payments/{paypal_client.py,errors.py,state.py}`, `backend/app/models/{payment,payment_event,webhook_event}.py`

**Dependencies**
- Member 2 needs `create_draft_version` from Member 1 by midday (stub it first).
- Member 3 needs real project endpoints by evening (mocks until then).
- Member 4 needs tables from migration 0001.

**Deliverables**
- `curl` flow: register -> create project -> clarify -> generate -> GET agreement shows persisted draft with milestones and criteria.
- Invite link works; audit entries recorded.
- PayPal client passes unit tests.
- Dashboard + wizard step 1 visible.

**Testing requirements**
- pytest: project RBAC, invitation, audit chain, postprocess amounts (table-driven), paypal_client with mocked transport.
- Manual: generate with live Gemini and with mock; compare.

**End-of-day completion criteria**
- [ ] Agreement draft persisted from AI for the sample brief in both modes.
- [ ] No endpoint reachable by non-members (tests).
- [ ] PayPal client coverage >= 80% lines.

---

## Day 3 - Tue Nov 3: Agreement review/approval and PayPal order creation

**Main objective:** Both parties can approve a content-hashed agreement in the UI; the backend can create a PayPal sandbox order for an accepted milestone.

**Member 1**
- [ ] Agreement lifecycle: `PATCH` agreement, milestone add/patch/delete, criteria `PUT`, `submit`, `approve` (hash check), `request-changes`, `revise` (versioning, `SUPERSEDED`).
- [ ] On approval: project `ACTIVE`, first milestone `ACTIVE`, others `PENDING`; audit + notifications.
- [ ] `GET /api/dashboard` v1 (stats, projects, upcoming deadlines); `GET /api/notifications` + read endpoints.
- [ ] Provide `milestones.get_for_payment` and `mark_paid` (C5) with tests.

**Member 2**
- [ ] Prompt tuning on the 5 golden briefs: reduce vague criteria, validate sums/dates; implement criteria lint + `warnings` output.
- [ ] Retry-with-feedback loop; failure handling matrix (doc 06 section 6); `AI_UNAVAILABLE` -> template fallback path tested.
- [ ] `scripts/eval_agreements.py` (metrics: schema-valid, sum integrity, lint warnings, latency).
- [ ] `ai/service.summarize_project` skeleton + `POST /api/projects/{id}/summary` returning mock until Day 7.

**Member 3**
- [ ] Wizard step 2 (clarify questions UI, severity styling, skip) and step 3 (generate, error -> template).
- [ ] Agreement editor: sections, milestone cards, criteria editor, live budget reconciler, auto-save, submit button with disabled reasons.
- [ ] Invite panel (copy link) and `/invite/:token` page; Agreement review mode (freelancer) with Approve / Request changes modals.
- [ ] Mount `EvaluationReportPanel` and `PayMilestoneCard` placeholders per contract C8.

**Member 4**
- [ ] `payments/service.create_order_for_milestone` (DB row first, PayPal order, state transitions, events, audit) and `routers/payments.py`: create, get, list by project.
- [ ] `capture_payment`, `cancel_payment` (DB transaction + `FOR UPDATE`), capture endpoint; idempotency keys wired into `PayPal-Request-Id`.
- [ ] Tests: double-create returns same payment; unique partial index; invalid-state errors; amount mismatch; all with mocked PayPal.
- [ ] Run create-order against real sandbox via curl using a hand-made `ACCEPTED` milestone row.

**Expected files / artefacts**
- `backend/app/{services/{agreements,milestones,dashboard}.py,routers/{agreements,milestones,dashboard,notifications}.py}`
- `backend/scripts/eval_agreements.py`, `backend/app/ai/{postprocess.py,fallbacks.py}`
- `frontend/src/features/{agreement/*,projects/wizard/*,invitations/*}`
- `backend/app/payments/{service.py}`, `backend/app/routers/payments.py`, `backend/tests/payments/*`

**Dependencies**
- Member 3 needs Member 1's lifecycle endpoints (ship `submit`/`approve` first, by midday).
- Member 4 needs `get_for_payment` (Member 1, morning).

**Deliverables**
- Two browser sessions complete agreement approval; hash shown on both sides.
- Order created in PayPal sandbox through the API; payment row `PENDING_APPROVAL`.
- Eval script report committed.

**Testing requirements**
- pytest: lifecycle state machine incl. hash mismatch, edit blocked after submit, revise creates version 2, approvals reset.
- pytest: payment service with mocked PayPal; concurrency test of two simultaneous create calls.

**End-of-day completion criteria**
- [ ] Approval flow demonstrable in UI against the real API.
- [ ] Create-order verified against real sandbox.
- [ ] Contract C4, C5 frozen.

---

## Day 4 - Wed Nov 4: Deliverables, AI evaluation and PayPal webhooks

**Main objective:** A freelancer uploads work, the AI evaluates it, the client decides, and the client can pay in the sandbox with a verified webhook recorded.

**Member 1**
- [ ] Deliverable upload (`multipart`), allowlist + MIME sniffing + size/count limits, sha256, `bytea` storage; list/get/download endpoints.
- [ ] Milestone transitions: `ACTIVE/CHANGES_REQUESTED -> SUBMITTED`; call `ai.service.schedule_evaluation` (C6); notifications to client.
- [ ] `POST /api/deliverables/{id}/decision` (accept -> activate next milestone; request changes -> comment required).
- [ ] Tests: upload validation (bad type, oversize, too many files), decision permissions and preconditions.

**Member 2**
- [ ] `ai/extraction.py` (txt/md/csv/json/html/code, pdf via pypdf, docx via python-docx, truncation flags, unsupported handling).
- [ ] Evaluation pipeline v1: prompt `evaluate.v1`, schema validation, id repair, **evidence verification**, deterministic `compute_recommendation`, `INCONCLUSIVE` without LLM when no text.
- [ ] `GET /api/deliverables/{id}/evaluation`, `POST .../evaluation/retry`, BackgroundTasks runner, stuck-run reaper, audit + notifications.
- [ ] Unit tests: truth table for recommendation; evidence verifier; extraction on sample files; run against fixtures `good`, `partial`, `injection`.

**Member 3**
- [ ] Milestone detail page: header, criteria list, submit-deliverable card (`FileDropzone`, note, links), submission history with downloads.
- [ ] Notifications bell (poll 15 s) + `/notifications` page.
- [ ] Project Overview: functional stepper from real data; role-aware next-action card.
- [ ] Decision card UI (Accept / Request changes modal) wired to mocks, then real API once ready.

**Member 4**
- [ ] `routers/webhooks.py`: raw-body read, header capture, verify via `PayPalClient.verify_webhook_signature`, store event, dedupe, process via `apply_verified_webhook`.
- [ ] Reconciliation code shared by capture/webhook/sync; `POST /api/payments/{id}/sync` (P1 stub ok).
- [ ] `features/payments`: `PayMilestoneCard`, `PaymentReturnPage`, `PaymentCancelPage`, `PaymentStatusBadge` (against mocks first).
- [ ] First real sandbox run through the API: create -> approve in browser -> capture -> webhook verified; save evidence (screenshots + event rows).

**Expected files / artefacts**
- `backend/app/{routers/{deliverables,decisions}.py,services/{deliverables,decisions}.py}`
- `backend/app/ai/{extraction.py,service.py,postprocess.py}`, `backend/app/routers/ai.py`, `backend/tests/ai/*`
- `frontend/src/features/{milestones/*,notifications/*}`
- `backend/app/{routers/webhooks.py,payments/{webhooks.py,service.py}}`, `frontend/src/features/payments/*`

**Dependencies**
- Member 2 needs the upload service from Member 1 (midday) to trigger evaluation end-to-end; until then he calls `run_evaluation` from a script.
- Member 3 needs decision endpoint (Member 1, afternoon).
- Member 4 needs a public webhook URL (tunnel).

**Deliverables**
- API flow: upload -> evaluation `COMPLETED` -> decision -> milestone `ACCEPTED`.
- Webhook event row with `verification_status = SUCCESS` from a real sandbox capture.
- Milestone page usable with real upload.

**Testing requirements**
- pytest: truth table, evidence verifier, extraction; webhook tests: valid, invalid signature (400), duplicate event, out-of-order.
- Manual real sandbox payment x1.

**End-of-day completion criteria**
- [ ] Injection fixture does not produce `MEETS`.
- [ ] Webhook verified end-to-end with PayPal.
- [ ] All P0 backend endpoints exist (even if rough).

---

## Day 5 - Thu Nov 5: Vertical slice integration (Integration Milestone 1)

**Main objective:** One complete project runs brief -> agreement -> approval -> submission -> AI evaluation -> decision -> PayPal payment -> PAID with no manual DB edits.

**Member 1**
- [ ] Run the integration day: triage board, pair on contract mismatches, merge fixes quickly; own the 20:30 integration check.
- [ ] Fix cross-module bugs (status transitions, audit/notification gaps, CORS, error envelopes).
- [ ] Project completion logic when last milestone `PAID`; `GET /api/projects/{id}` completeness (milestones, summary fields).
- [ ] Tag `v0.5-slice`; write the P0 gap list (what is missing vs doc 02).

**Member 2**
- [ ] Build `features/evaluation/EvaluationReportPanel` (+ `CriterionResultRow`, `EvidenceQuote`, `EvaluationHistory`) per doc 08 and contract C8.
- [ ] Wire polling states: running/failed/inconclusive; retry button; confidence labelling and disclaimer.
- [ ] Check AI latency on real runs; tune timeouts; fix prompt issues found during integration.
- [ ] Pair with Member 3 on milestone page integration.

**Member 3**
- [ ] Remove mocks from the main path: wire every page to the real API; fix type mismatches.
- [ ] Integrate `EvaluationReportPanel` and `PayMilestoneCard` into the milestone page; register `/payments/return` and `/payments/cancel` routes.
- [ ] Loading/error handling pass on all P0 pages; toast patterns.
- [ ] Record a rough screen capture of the slice for the team.

**Member 4**
- [ ] Wire pay flow end-to-end in the UI: redirect, return page, capture, pending polling, failure states.
- [ ] Write `scripts/e2e_smoke.py` (API-level happy path against a running backend in mock modes) and add to CI.
- [ ] Execute the vertical slice 3 times (mock and sandbox), log defects with severity and owner.
- [ ] Verify audit trail and notifications for each step.

**Expected files / artefacts**
- `frontend/src/features/evaluation/*`
- `backend/scripts/e2e_smoke.py`
- bug fixes across modules
- `docs/` contract updates if any

**Dependencies**
- Everyone is blocked on each other today - pair in a call; keep PRs under 150 lines.

**Deliverables**
- `v0.5-slice` tag.
- 3 recorded successful slice runs.
- Defect list with owners and severities.

**Testing requirements**
- `e2e_smoke.py` green in CI (mock mode).
- Manual slice in sandbox mode x1 by someone other than the author of each part.

**End-of-day completion criteria**
- [ ] Slice passes without DB edits.
- [ ] Every P0 requirement is either done or on the gap list with an owner and a day.

---

## Day 6 - Fri Nov 6: Complete P0, first deployment

**Main objective:** P0 scope is 100% complete and running on a Render staging deployment with a public webhook URL.

**Member 1**
- [ ] Create `render.yaml` + Dockerfile/start script (migrations before start); deploy backend, static frontend, Postgres; configure env vars and CORS.
- [ ] Rate limiting on auth + AI endpoints; request-id logging; global exception handler review.
- [ ] Fix P0 gaps assigned from Day 5 list; verify `GET /api/config` banners data.
- [ ] Update `.env.example` and README deployment notes.

**Member 2**
- [ ] Evaluation quality: run the 5 deliverable fixtures repeatedly; tune prompt `evaluate.v1` -> `v2` if needed; keep metrics table.
- [ ] Prompt-injection tests; MANUAL-criteria handling; per-criterion evidence display fields.
- [ ] Complete `AI_MODE=mock` fixtures for all three demo briefs and evaluation fixtures (good/partial/missing).
- [ ] Add token/latency logging checks and per-user AI rate limit.

**Member 3**
- [ ] Complete project tabs: Agreement (read-only approved view with approval history), Milestones list, Payments (mount ledger), Activity (timeline from audit).
- [ ] Loading / error / empty states for every P0 page; 404; offline toast.
- [ ] Responsive pass 1 (375 px): dashboard, milestone page, agreement editor.
- [ ] Environment banners (sandbox/simulated) wired to `/api/config`.

**Member 4**
- [ ] Register the staging webhook URL in the PayPal dashboard; verify delivery and signature on Render.
- [ ] Failure paths with sandbox negative testing: cancel, declined instrument, duplicate capture, pending capture (simulate), PayPal 5xx.
- [ ] Finish `PAYMENTS_MODE=mock` including `/mock-paypal/checkout` and SIMULATED labelling.
- [ ] `PaymentLedger` with event timeline and webhook-verified tick (v1).

**Expected files / artefacts**
- `render.yaml`, `backend/Dockerfile`, `backend/start.sh`
- `backend/tests/ai/{test_eval_fixtures.py}`, `backend/app/ai/llm/mock.py`
- `frontend/src/features/{activity/*,agreement/*}`
- `backend/app/{payments/mock_client.py,routers/mock_paypal.py}`, `frontend/src/features/payments/PaymentLedger.tsx`

**Dependencies**
- Member 4 needs staging URL from Member 1 (midday).
- Member 3 needs audit endpoint stable (done Day 2).

**Deliverables**
- Staging URL working with sandbox payments.
- P0 checklist (doc 02) all ticked.
- Mock modes complete.

**Testing requirements**
- Staging smoke: register -> full slice in mock modes; one full slice in sandbox mode.
- Webhook verified from the Render URL.

**End-of-day completion criteria**
- [ ] P0 complete on staging.
- [ ] No open `blocker` bugs older than 4 hours.

---

## Day 7 - Sat Nov 7: P1 features: AI summary, dashboard intelligence, trust UI

**Main objective:** Add the high-value P1 features that differentiate the demo, without destabilizing P0.

**Member 1**
- [ ] Dashboard v2: `needs_action` kinds, `upcoming_deadlines` overdue flags, totals; query performance check (indexes).
- [ ] Audit chain verification (`chain_valid`) + API polish; notification types complete.
- [ ] `scripts/seed_demo.py` (idempotent, with a `--reset-demo` flag): demo users, a finished project, an in-progress project with a pre-staged submission.
- [ ] Agreement version history endpoint polish (`/agreements`).

**Member 2**
- [ ] Project summary generation (`summary.v1`) with state-hash cache and facts-only input; endpoint complete.
- [ ] Surface agreement clarity warnings in API response; improve fallback messaging strings.
- [ ] P1 stretch (only if time): image deliverables via multimodal input.
- [ ] Update `docs/06` with real prompt versions/metrics.

**Member 3**
- [ ] Dashboard v2 components: stat cards, needs-action list, deadlines, AI summary card, recent payments.
- [ ] Activity page with chain-verified badge and filters; version history side panel.
- [ ] Design polish pass (spacing, icons, micro-interactions), favicon/logo.
- [ ] Copy review: remove any word implying escrow/guarantee.

**Member 4**
- [ ] Payment ledger audit view finalized (PayPal IDs, timeline, verification tick); refund/reversal webhooks stored + audited.
- [ ] `POST /api/payments/{id}/sync` complete; reconciliation test (webhook missed).
- [ ] Authorization test matrix for all payment endpoints; concurrency tests (double click, parallel capture + webhook).
- [ ] Update `e2e_smoke.py` to cover rejection -> resubmission -> accept -> pay.

**Expected files / artefacts**
- `backend/scripts/seed_demo.py`, `backend/app/services/dashboard.py`
- `backend/app/ai/prompts/summary_v1.py`
- `frontend/src/features/{dashboard/*,activity/*}`
- `backend/tests/payments/test_authz.py`, `test_concurrency.py`

**Dependencies**
- Member 3 needs seed data (Member 1, morning) to design with realistic content.

**Deliverables**
- P1 complete (or explicitly cut).
- Seed script producing a convincing demo dashboard.

**Testing requirements**
- Regression of the slice (mock + sandbox).
- Concurrency tests green.

**End-of-day completion criteria**
- [ ] Demo path rehearsed once end-to-end by the team.
- [ ] Cut list for unfinished P1 agreed.

---

## Day 8 - Sun Nov 8: Hardening and FEATURE FREEZE

**Main objective:** Make it reliable and safe; stop adding features at 20:00 IST.

**Member 1**
- [ ] Security pass: RBAC test matrix across all endpoints, upload validation, security headers, JWT expiry, CORS, secrets scan (gitleaks), dependency audit.
- [ ] DB index review, N+1 check on dashboard, error-handling sweep (no 500 on demo path).
- [ ] **Feature freeze at 20:00 IST**, tag `v0.8-featurefreeze`; open the `demo-critical` label.
- [ ] Update docs 03-05 to match final behaviour.

**Member 2**
- [ ] AI regression on the golden sets with final prompts; record metrics (doc 12 thresholds).
- [ ] Failure drills: timeout, malformed JSON, 429, empty extraction, provider outage -> verify user-facing states and mock switch.
- [ ] Finalize AI limitations copy in UI + docs; confirm no PII in prompts/logs.
- [ ] Quota check: estimate API calls needed for demo + judging; request higher limits if needed.

**Member 3**
- [ ] Responsive pass 2 (375/768/1280) for all pages; accessibility basics (labels, focus, contrast, keyboard).
- [ ] Final empty/error/loading polish; cross-browser check (Chrome, Safari/Firefox quick).
- [ ] Lighthouse sanity (performance and accessibility > 85 on dashboard and milestone page).
- [ ] Freeze UI copy.

**Member 4**
- [ ] Execute the full sandbox test matrix (doc 12) and webhook negative tests; document results in `docs/test-reports/2026-11-08.md`.
- [ ] Playwright (or scripted) browser E2E of the demo path; run against staging.
- [ ] Security tests for payments (tampered webhook, wrong webhook id, replay, amount tamper attempts).
- [ ] File bugs with owner + severity; verify fixes.

**Expected files / artefacts**
- `docs/test-reports/2026-11-08.md`
- `backend/tests/test_rbac_matrix.py`
- `frontend/tests/e2e/demo.spec.ts` (Member 4)
- metrics tables in `docs/12`

**Dependencies**
- All hardening fixes route through Member 1's review.

**Deliverables**
- `v0.8-featurefreeze` tag.
- Test report with pass/fail and open bugs.
- All `blocker` bugs have owners.

**Testing requirements**
- Full regression: backend, frontend, e2e, sandbox payments, AI golden set.

**End-of-day completion criteria**
- [ ] No P0 feature missing.
- [ ] Zero known data-loss/payment-integrity bugs.
- [ ] Freeze announced.

---

## Day 9 - Mon Nov 9: Demo readiness and release candidate

**Main objective:** Release candidate deployed to production-like environment; repo public; Devpost draft created.

**Member 1**
- [ ] Deploy `v0.9-rc1`; verify fresh-clone setup on a clean machine (README commands exactly).
- [ ] Run gitleaks on full history; if clean, switch repo to **public**; verify LICENSE shows in About.
- [ ] Finalize README (judge instructions, mock mode, demo accounts, architecture, honesty statement).
- [ ] Create the Devpost draft submission (Representative account) with placeholder video.

**Member 2**
- [ ] Seed demo content: final brief text, deliverable files (`demo-m1-v1.md` with deliberate gap, `demo-m1-v2.md` complete).
- [ ] Write the AI section for Devpost (models, pipeline, safeguards, limitations).
- [ ] Verify AI latency on production; pre-test mock fallback switch procedure.
- [ ] Review docs for AI accuracy.

**Member 3**
- [ ] Demo UX polish with seeded data; capture 4-5 screenshots (1920x1080) for the Devpost gallery; project logo/thumbnail.
- [ ] Prepare title cards and lower-thirds for the video (no third-party trademarks or copyrighted music).
- [ ] Pre-arrange windows/profiles for the recording (client window, freelancer window).
- [ ] Final accessibility spot-check.

**Member 4**
- [ ] Three full dry-runs of the demo on production (sandbox payments); fix or log issues.
- [ ] Prepare sandbox account state (funded buyer, saved login); keep the credentials sheet private.
- [ ] Write the PayPal integration section for Devpost; verify webhook delivery on production.
- [ ] Draft narration based on doc 16.

**Expected files / artefacts**
- `README.md` (final)
- `backend/tests/ai/fixtures/demo/*`
- `docs/assets/screenshots/*` (optional)
- Devpost draft

**Dependencies**
- Public repo flip requires clean secret scan first.

**Deliverables**
- `v0.9-rc1` deployed.
- Repo public with license.
- Devpost draft with text complete.
- 3 successful dry-runs.

**Testing requirements**
- Fresh-clone run by a member who did not write the README.
- Dry-runs on production.

**End-of-day completion criteria**
- [ ] Anyone can run the project from the README in < 10 minutes in mock mode.
- [ ] Demo path works 3/3 times.

---

## Day 10 - Tue Nov 10: Code freeze, rehearsals and video recording

**Main objective:** Only blocker fixes; record the demo video; prepare the submission assets.

**Member 1**
- [ ] Code freeze: approve only `blocker`/`demo-critical` PRs; tag `v1.0-rc2`; monitor production health and logs.
- [ ] Confirm environment variables and Render plan (no cold starts during judging; credits/billing checked).
- [ ] Cross-check Devpost form fields against the rules once more.
- [ ] Prepare rollback (previous tag) plan.

**Member 2**
- [ ] Verify AI API quota and keys valid through Dec 15; set budget alerts.
- [ ] Run final AI regression on production data path.
- [ ] Standby to fix prompt-only issues (prompt changes allowed only with version bump + golden re-run).
- [ ] Proofread all AI copy in the UI.

**Member 3**
- [ ] Record screen footage (1080p) following doc 16: multiple takes, backup clips of each segment.
- [ ] Prepare mobile-responsive clip (optional 5 seconds).
- [ ] Begin rough edit; add captions.
- [ ] Check video contains no third-party trademarks beyond PayPal's own sandbox UI.

**Member 4**
- [ ] Lead 3 rehearsals with timer (< 3:00); finalize narration script and record voice-over.
- [ ] Verify sandbox accounts, balances and PayPal login state before each take.
- [ ] Backup recordings of the PayPal approval segment and mock-mode full flow.
- [ ] Final regression run after the last merge.

**Expected files / artefacts**
- `v1.0-rc2` tag
- video raw footage (outside repo)
- voice-over audio

**Dependencies**
- Recording depends on a stable build: no merges after 16:00 IST except blockers.

**Deliverables**
- Complete raw footage + narration.
- Final regression report.

**Testing requirements**
- Final regression after code freeze (sandbox + mock).

**End-of-day completion criteria**
- [ ] Video raw footage covers every segment of doc 16.
- [ ] No open blockers.

---

## Day 11 - Wed Nov 11: Final video, submission and buffer

**Main objective:** Submit by 22:00 IST (Nov 11), about 27 hours before the 01:30 IST Nov 13 deadline; keep Nov 12 as emergency buffer only.

**Member 1**
- [ ] As the Representative: complete the Devpost form (description, built-with, links, YouTube URL, test instructions, repo, demo URL); submit by **22:00 IST**.
- [ ] Verify in an incognito window: repo public, license visible, README run steps, hosted URL, YouTube public and < 3:00.
- [ ] Tag `v1.0`; protect `main`; confirm the hosted demo stays online until Dec 15 (billing, credits).
- [ ] Archive: export docs, record final state in `docs/15`.

**Member 2**
- [ ] Proofread the Devpost description and AI section; check claims vs reality (no overclaiming).
- [ ] Watch the final video for AI accuracy.
- [ ] On standby for AI outages: be ready to flip `AI_MODE=mock` on the hosted demo if needed during judging.
- [ ] Document how judges can test AI mode.

**Member 3**
- [ ] Finish video edit (target 2:45-2:55), captions, export 1080p; upload to YouTube (public, unlisted is NOT sufficient - must be publicly visible); title and description include repo link.
- [ ] Upload gallery images and thumbnail to Devpost.
- [ ] Final UI check on production.
- [ ] Provide the raw project files of the video to the team drive.

**Member 4**
- [ ] Final sandbox account/state check; run one last production smoke test before submission.
- [ ] Proofread PayPal section; confirm no escrow/hold-funds claims anywhere.
- [ ] Check the video narration matches the shipped UI.
- [ ] Monitor production and webhook health until the deadline; keep the private test-account sheet accessible.

**Expected files / artefacts**
- Devpost submission
- YouTube video
- `v1.0` tag

**Dependencies**
- Video must be uploaded before the Devpost form can be completed.

**Deliverables**
- Submitted entry (screenshot of confirmation).
- Public YouTube link.
- v1.0 tag.

**Testing requirements**
- Incognito verification checklist (doc 15 section 8).

**End-of-day completion criteria**
- [ ] Submission confirmed.
- [ ] All four members have viewed the live submission page.

---

## Contingency rules
- If a day's gate is missed by < 3 h: work through the evening sync. If missed by more: cut P1 scope immediately (order above) rather than slipping later days.
- If PayPal sandbox is unstable on Day 5-6: continue in `PAYMENTS_MODE=mock`, keep sandbox attempts time-boxed to 1 h per issue (Member 4), escalate to the hackathon Discord.
- If LLM output quality blocks progress on Day 3-4: switch to mock fixtures for the UI and keep tuning in parallel (Member 2).
- Any member finishing early picks the next unowned `P0` bug from the board; they do not start new features.
