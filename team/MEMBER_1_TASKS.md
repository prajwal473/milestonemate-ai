# MEMBER_1 - Task File

**Role:** Tech Lead - Backend Platform, Database, Integration and Release Coordinator

**Mission:** Make the platform solid and keep four parallel streams converging on `main`.

> Source documents: doc 09 (ownership and contracts), doc 10 (workflow), doc 11 (roadmap). If this file and a doc disagree, fix both in the same PR.

## 1. Individual responsibilities
- Repository, CI, branch protection, CODEOWNERS, releases and tags.
- PostgreSQL schema and **all** Alembic migrations (nobody else commits migrations).
- Auth, users, RBAC dependencies, error envelope, config, logging, rate limiting.
- Projects, invitations, agreement lifecycle (edit/submit/approve/revise, content hash), milestones, criteria.
- Deliverable upload/storage/download, client decisions, milestone state transitions.
- Audit log (hash chain), notifications, dashboard API, seed script.
- Render deployment, environment variables, production configuration.
- README, final doc consistency, Devpost submission (as Representative, subject to decision D-02).

## 2. Files and modules you own (no one else edits these without your review)
- `backend/app/{main.py,core/**,db/**}`
- `backend/app/models/{user,project,invitation,agreement,milestone,deliverable,decision,audit,notification}.py`
- `backend/app/routers/{auth,users,projects,invitations,agreements,milestones,deliverables,decisions,dashboard,notifications,audit,health}.py`
- `backend/app/services/**`, `backend/app/schemas/` (non-AI, non-payment)
- `backend/alembic/**`, `backend/requirements.txt`, `backend/Dockerfile`, `backend/scripts/seed_demo.py`
- `.github/**`, `docker-compose.yml`, `render.yaml`, `README.md`, `LICENSE`, `.env.example`
- `backend/tests/{test_auth,test_projects,test_agreements,test_deliverables,test_rbac,test_audit}*.py`

## 3. Integration responsibilities
- Provide `audit.record`, `notifications.notify`, `create_draft_version`, `get_for_payment`, `mark_paid` (contracts C4, C5) exactly as in doc 09.
- Call `ai.service.schedule_evaluation` after upload (C6).
- Run the 20:30 IST daily integration check and publish GREEN/RED.
- Approve/merge PRs; resolve contract disputes within 30 min; cut tags.

## 4. Testing responsibilities
- Unit/integration tests for every service function and endpoint (happy path + permission + invalid state).
- RBAC matrix test across all endpoints; upload validation tests; audit-chain tests.
- Fresh-clone setup test on Day 9; secret scan before the repo goes public.

## 5. Daily plan, deliverables and checks

### Day 1 - Sun Nov 1: Foundations, contracts and risk spikes
*Team objective:* Every member can run the stack locally; contracts C1-C3, C9, C10 are frozen; the PayPal payee decision and LLM structured output are proven.

**Your tasks**
- [ ] Create the private GitHub repo, commit `LICENSE` (MIT), `.gitignore`, `.env.example`, docs; enable branch protection, CODEOWNERS, PR template, labels, project board.
- [ ] Scaffold backend: `app/main.py`, `core/{config,errors,logging,deps,security}.py`, `db/{session,base}.py`, `requirements.txt`, `Dockerfile`, ruff + pytest config.
- [ ] `docker-compose.yml` (postgres:16, volume, healthcheck); Alembic init; migration `0001_initial_schema` implementing doc 04 SQL exactly (incl. partial indexes and audit trigger).
- [ ] Auth: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `PATCH /api/users/me` (argon2id, JWT), `GET /api/health`, `GET /api/config`.
- [ ] CI workflow (`backend`, `frontend`, `secrets` jobs); export script `scripts/export_openapi.py`; post stub signatures for `audit.record`, `notifications.notify` (C4).

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
- [ ] Models + routers: `projects` (create/list/get/patch), `invitations` (create, preview, accept; token hash), `require_project_member` / `require_role` dependencies.
- [ ] Agreement/milestone/criteria models and read endpoints; `services/agreements.create_draft_version` and `compute_content_hash` (C4).
- [ ] `services/audit.record` with advisory lock + hash chain; `services/notifications.notify`; `GET /api/projects/{id}/audit` (without verify badge UI).
- [ ] Tests: RBAC for project endpoints, invitation flow, audit chain integrity.

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
- [ ] Agreement lifecycle: `PATCH` agreement, milestone add/patch/delete, criteria `PUT`, `submit`, `approve` (hash check), `request-changes`, `revise` (versioning, `SUPERSEDED`).
- [ ] On approval: project `ACTIVE`, first milestone `ACTIVE`, others `PENDING`; audit + notifications.
- [ ] `GET /api/dashboard` v1 (stats, projects, upcoming deadlines); `GET /api/notifications` + read endpoints.
- [ ] Provide `milestones.get_for_payment` and `mark_paid` (C5) with tests.

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
- [ ] Deliverable upload (`multipart`), allowlist + MIME sniffing + size/count limits, sha256, `bytea` storage; list/get/download endpoints.
- [ ] Milestone transitions: `ACTIVE/CHANGES_REQUESTED -> SUBMITTED`; call `ai.service.schedule_evaluation` (C6); notifications to client.
- [ ] `POST /api/deliverables/{id}/decision` (accept -> activate next milestone; request changes -> comment required).
- [ ] Tests: upload validation (bad type, oversize, too many files), decision permissions and preconditions.

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
- [ ] Run the integration day: triage board, pair on contract mismatches, merge fixes quickly; own the 20:30 integration check.
- [ ] Fix cross-module bugs (status transitions, audit/notification gaps, CORS, error envelopes).
- [ ] Project completion logic when last milestone `PAID`; `GET /api/projects/{id}` completeness (milestones, summary fields).
- [ ] Tag `v0.5-slice`; write the P0 gap list (what is missing vs doc 02).

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
- [ ] Create `render.yaml` + Dockerfile/start script (migrations before start); deploy backend, static frontend, Postgres; configure env vars and CORS.
- [ ] Rate limiting on auth + AI endpoints; request-id logging; global exception handler review.
- [ ] Fix P0 gaps assigned from Day 5 list; verify `GET /api/config` banners data.
- [ ] Update `.env.example` and README deployment notes.

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
- [ ] Dashboard v2: `needs_action` kinds, `upcoming_deadlines` overdue flags, totals; query performance check (indexes).
- [ ] Audit chain verification (`chain_valid`) + API polish; notification types complete.
- [ ] `scripts/seed_demo.py` (idempotent, with a `--reset-demo` flag): demo users, a finished project, an in-progress project with a pre-staged submission.
- [ ] Agreement version history endpoint polish (`/agreements`).

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
- [ ] Security pass: RBAC test matrix across all endpoints, upload validation, security headers, JWT expiry, CORS, secrets scan (gitleaks), dependency audit.
- [ ] DB index review, N+1 check on dashboard, error-handling sweep (no 500 on demo path).
- [ ] **Feature freeze at 20:00 IST**, tag `v0.8-featurefreeze`; open the `demo-critical` label.
- [ ] Update docs 03-05 to match final behaviour.

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
- [ ] Deploy `v0.9-rc1`; verify fresh-clone setup on a clean machine (README commands exactly).
- [ ] Run gitleaks on full history; if clean, switch repo to **public**; verify LICENSE shows in About.
- [ ] Finalize README (judge instructions, mock mode, demo accounts, architecture, honesty statement).
- [ ] Create the Devpost draft submission (Representative account) with placeholder video.

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
- [ ] Code freeze: approve only `blocker`/`demo-critical` PRs; tag `v1.0-rc2`; monitor production health and logs.
- [ ] Confirm environment variables and Render plan (no cold starts during judging; credits/billing checked).
- [ ] Cross-check Devpost form fields against the rules once more.
- [ ] Prepare rollback (previous tag) plan.

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
- [ ] As the Representative: complete the Devpost form (description, built-with, links, YouTube URL, test instructions, repo, demo URL); submit by **22:00 IST**.
- [ ] Verify in an incognito window: repo public, license visible, README run steps, hosted URL, YouTube public and < 3:00.
- [ ] Tag `v1.0`; protect `main`; confirm the hosted demo stays online until Dec 15 (billing, credits).
- [ ] Archive: export docs, record final state in `docs/15`.

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
