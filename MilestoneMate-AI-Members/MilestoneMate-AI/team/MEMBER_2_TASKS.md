# MEMBER_2 - Task File

**Role:** AI Engineer - Agreement Generation, Deliverable Evaluation, AI Quality

**Mission:** Make the AI useful, verifiable and safe: structured, validated, evidence-checked and always fall-back-able.

> Source documents: doc 09 (ownership and contracts), doc 10 (workflow), doc 11 (roadmap). If this file and a doc disagree, fix both in the same PR.

## 1. Individual responsibilities
- LLM abstraction (Gemini default, optional Claude, Mock) with retries, timeouts, JSON/schema output.
- Prompts and versions: clarify, agreement, evaluate, summary.
- Deterministic post-processing: amount rebalance, date normalization, criteria lint, evidence verification, recommendation rules.
- Text extraction for uploaded files; background evaluation runner; stuck-run reaper.
- AI endpoints: clarify, generate, template, evaluation get/retry, summary.
- Golden sets, regression scripts, injection tests, failure drills.
- `features/evaluation/*` UI components (isolated folder).
- AI portion of Devpost text and docs/06 accuracy.

## 2. Files and modules you own (no one else edits these without your review)
- `backend/app/ai/**`
- `backend/app/routers/ai.py`
- `backend/app/models/{ai_run,evaluation}.py`, `backend/app/schemas/{ai,evaluation}.py`
- `backend/tests/ai/**`, `backend/scripts/{ai_spike,eval_agreements,eval_deliverables}.py`
- `frontend/src/features/evaluation/**`
- `docs/06_AI_AGENT_DESIGN.md` (updates)

## 3. Integration responsibilities
- Commit `ai/schemas.py` on Day 1 (C3).
- Persist drafts only through `services.agreements.create_draft_version`.
- Expose `schedule_evaluation(...)` for Member 1's upload endpoint.
- Never import `app.payments`; never change milestone status (architecture test enforces).
- Mount points for UI: `EvaluationReportPanel` props per doc 09 section 6.

## 4. Testing responsibilities
- Truth-table test for `compute_recommendation`; evidence-verifier tests; extraction tests.
- Golden sets: schema-valid >= 95% first try, sum integrity 100%, evidence verified >= 90%, injection never `MEETS`, eval P95 < 45 s.
- Failure drills: timeout, malformed JSON, 429, empty extraction, outage -> mock switch.

## 5. Daily plan, deliverables and checks

### Day 1 - Sun Nov 1: Foundations, contracts and risk spikes
*Team objective:* Every member can run the stack locally; contracts C1-C3, C9, C10 are frozen; the PayPal payee decision and LLM structured output are proven.

**Your tasks**
- [ ] Obtain Gemini API key (Google AI Studio); look up and pin the current Flash-class model name in `.env.example` notes; put the key in the team password manager.
- [ ] Commit `app/ai/schemas.py` (all Pydantic models from doc 06 section 4) **by 13:00 IST** - this freezes contract C3.
- [ ] Implement `ai/llm/base.py` (`LLMClient`), `gemini.py` (JSON mode + schema), `mock.py` (fixture lookup), retry/timeout wrapper, `ai/runs.py` skeleton.
- [ ] Spike `scripts/ai_spike.py`: run clarify + agreement prompts on 3 sample briefs; save raw outputs in `tests/ai/fixtures/`; note failure patterns.
- [ ] Write 5 golden briefs (`brief_*.txt`) and 5 deliverable fixtures (`good.md`, `partial.md`, `missing.md`, `empty.md`, `injection.md`) for the coffee-landing-page demo project.

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
- [ ] `ai/service.clarify` + `POST /api/projects/{id}/agreement/clarify` (prompt `clarify.v1`, validation, retry, ai_runs logging).
- [ ] `ai/service.generate_agreement` + `POST .../generate` calling `create_draft_version` (prompt `agreement.v1`).
- [ ] `ai/postprocess.py` v1: amount rebalance, date normalization, counts; `ai/fallbacks.template_agreement` + `POST .../template`.
- [ ] Mock provider fixtures for the coffee brief (clarify + agreement) so others can build offline.

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
- [ ] Prompt tuning on the 5 golden briefs: reduce vague criteria, validate sums/dates; implement criteria lint + `warnings` output.
- [ ] Retry-with-feedback loop; failure handling matrix (doc 06 section 6); `AI_UNAVAILABLE` -> template fallback path tested.
- [ ] `scripts/eval_agreements.py` (metrics: schema-valid, sum integrity, lint warnings, latency).
- [ ] `ai/service.summarize_project` skeleton + `POST /api/projects/{id}/summary` returning mock until Day 7.

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
- [ ] `ai/extraction.py` (txt/md/csv/json/html/code, pdf via pypdf, docx via python-docx, truncation flags, unsupported handling).
- [ ] Evaluation pipeline v1: prompt `evaluate.v1`, schema validation, id repair, **evidence verification**, deterministic `compute_recommendation`, `INCONCLUSIVE` without LLM when no text.
- [ ] `GET /api/deliverables/{id}/evaluation`, `POST .../evaluation/retry`, BackgroundTasks runner, stuck-run reaper, audit + notifications.
- [ ] Unit tests: truth table for recommendation; evidence verifier; extraction on sample files; run against fixtures `good`, `partial`, `injection`.

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
- [ ] Build `features/evaluation/EvaluationReportPanel` (+ `CriterionResultRow`, `EvidenceQuote`, `EvaluationHistory`) per doc 08 and contract C8.
- [ ] Wire polling states: running/failed/inconclusive; retry button; confidence labelling and disclaimer.
- [ ] Check AI latency on real runs; tune timeouts; fix prompt issues found during integration.
- [ ] Pair with Member 3 on milestone page integration.

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
- [ ] Evaluation quality: run the 5 deliverable fixtures repeatedly; tune prompt `evaluate.v1` -> `v2` if needed; keep metrics table.
- [ ] Prompt-injection tests; MANUAL-criteria handling; per-criterion evidence display fields.
- [ ] Complete `AI_MODE=mock` fixtures for all three demo briefs and evaluation fixtures (good/partial/missing).
- [ ] Add token/latency logging checks and per-user AI rate limit.

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
- [ ] Project summary generation (`summary.v1`) with state-hash cache and facts-only input; endpoint complete.
- [ ] Surface agreement clarity warnings in API response; improve fallback messaging strings.
- [ ] P1 stretch (only if time): image deliverables via multimodal input.
- [ ] Update `docs/06` with real prompt versions/metrics.

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
- [ ] AI regression on the golden sets with final prompts; record metrics (doc 12 thresholds).
- [ ] Failure drills: timeout, malformed JSON, 429, empty extraction, provider outage -> verify user-facing states and mock switch.
- [ ] Finalize AI limitations copy in UI + docs; confirm no PII in prompts/logs.
- [ ] Quota check: estimate API calls needed for demo + judging; request higher limits if needed.

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
- [ ] Seed demo content: final brief text, deliverable files (`demo-m1-v1.md` with deliberate gap, `demo-m1-v2.md` complete).
- [ ] Write the AI section for Devpost (models, pipeline, safeguards, limitations).
- [ ] Verify AI latency on production; pre-test mock fallback switch procedure.
- [ ] Review docs for AI accuracy.

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
- [ ] Verify AI API quota and keys valid through Dec 15; set budget alerts.
- [ ] Run final AI regression on production data path.
- [ ] Standby to fix prompt-only issues (prompt changes allowed only with version bump + golden re-run).
- [ ] Proofread all AI copy in the UI.

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
- [ ] Proofread the Devpost description and AI section; check claims vs reality (no overclaiming).
- [ ] Watch the final video for AI accuracy.
- [ ] On standby for AI outages: be ready to flip `AI_MODE=mock` on the hosted demo if needed during judging.
- [ ] Document how judges can test AI mode.

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
