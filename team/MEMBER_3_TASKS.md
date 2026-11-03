# MEMBER_3 - Task File

**Role:** Frontend Lead - Architecture, Design System and UI/UX

**Mission:** Deliver a complete, coherent, trustworthy product experience that looks great in a 3-minute video.

> Source documents: doc 09 (ownership and contracts), doc 10 (workflow), doc 11 (roadmap). If this file and a doc disagree, fix both in the same PR.

## 1. Individual responsibilities
- Vite + React + TypeScript + Tailwind scaffold, routing, state/query layer, API client and generated types.
- Design system and all shared components (doc 08).
- Pages: landing, auth, dashboard, new-project wizard, project overview, agreement editor/review, milestone detail, activity, notifications, profile, invite.
- Mount Member 2's and Member 4's feature components via contract C8.
- Loading/error/empty states, responsive and accessibility passes.
- Mock layer (`VITE_USE_MOCKS`) to unblock others and himself.
- Demo visuals: screenshots, title cards, video editing.

## 2. Files and modules you own (no one else edits these without your review)
- `frontend/**` except `src/features/payments/**` (Member 4) and `src/features/evaluation/**` (Member 2)
- `frontend/src/api/**` (incl. generated `schema.d.ts`, mocks)
- `frontend/src/components/**`, `frontend/src/lib/**`

## 3. Integration responsibilities
- Generate types with `npm run gen:api` after every API change; CI fails when stale.
- Register payment routes `/payments/return`, `/payments/cancel` and mount `PayMilestoneCard`, `PaymentLedger`.
- Mount `EvaluationReportPanel` on the milestone page.
- Report API/contract mismatches immediately to the provider with a failing example.

## 4. Testing responsibilities
- Vitest + Testing Library for key components (StatusBadge mapping, budget reconciler, FileDropzone validation).
- Manual checks at 375/768/1280 px; keyboard navigation; Lighthouse sanity.
- Participate in Playwright path (Member 4 owns the spec).

## 5. Daily plan, deliverables and checks

### Day 1 - Sun Nov 1: Foundations, contracts and risk spikes
*Team objective:* Every member can run the stack locally; contracts C1-C3, C9, C10 are frozen; the PayPal payee decision and LLM structured output are proven.

**Your tasks**
- [ ] Scaffold `frontend/` (Vite, React 18, TypeScript strict, Tailwind, React Router, TanStack Query, ESLint/Prettier, Vitest).
- [ ] Implement design tokens from doc 08 (`tailwind.config.ts`), `AppShell` (top bar, left nav, banners), routes map, 404 page.
- [ ] Build `api/client.ts` (fetch wrapper: base URL, bearer token, error-envelope mapping, request id), auth context, `RequireAuth`.
- [ ] Build UI primitives: Button, Card, Badge/StatusBadge, Input, Textarea, Modal, Toast, Skeleton, EmptyState, ErrorState, Banner.
- [ ] Login and Register pages (with `VITE_USE_MOCKS`); create `api/mocks/` fixtures replicating doc 05 examples; add `npm run gen:api`.

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
- [ ] Generate typed API (`schema.d.ts`) from the running backend; build `api/hooks` (projects, auth).
- [ ] Dashboard page v0 (project cards, empty state, skeletons) and Projects list.
- [ ] New Project wizard step 1 (title + brief) and step 2 shell (loading state while clarify runs).
- [ ] Project Overview page shell with tabs and milestone stepper using mock data.

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
- [ ] Wizard step 2 (clarify questions UI, severity styling, skip) and step 3 (generate, error -> template).
- [ ] Agreement editor: sections, milestone cards, criteria editor, live budget reconciler, auto-save, submit button with disabled reasons.
- [ ] Invite panel (copy link) and `/invite/:token` page; Agreement review mode (freelancer) with Approve / Request changes modals.
- [ ] Mount `EvaluationReportPanel` and `PayMilestoneCard` placeholders per contract C8.

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
- [ ] Milestone detail page: header, criteria list, submit-deliverable card (`FileDropzone`, note, links), submission history with downloads.
- [ ] Notifications bell (poll 15 s) + `/notifications` page.
- [ ] Project Overview: functional stepper from real data; role-aware next-action card.
- [ ] Decision card UI (Accept / Request changes modal) wired to mocks, then real API once ready.

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
- [ ] Remove mocks from the main path: wire every page to the real API; fix type mismatches.
- [ ] Integrate `EvaluationReportPanel` and `PayMilestoneCard` into the milestone page; register `/payments/return` and `/payments/cancel` routes.
- [ ] Loading/error handling pass on all P0 pages; toast patterns.
- [ ] Record a rough screen capture of the slice for the team.

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
- [ ] Complete project tabs: Agreement (read-only approved view with approval history), Milestones list, Payments (mount ledger), Activity (timeline from audit).
- [ ] Loading / error / empty states for every P0 page; 404; offline toast.
- [ ] Responsive pass 1 (375 px): dashboard, milestone page, agreement editor.
- [ ] Environment banners (sandbox/simulated) wired to `/api/config`.

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
- [ ] Dashboard v2 components: stat cards, needs-action list, deadlines, AI summary card, recent payments.
- [ ] Activity page with chain-verified badge and filters; version history side panel.
- [ ] Design polish pass (spacing, icons, micro-interactions), favicon/logo.
- [ ] Copy review: remove any word implying escrow/guarantee.

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
- [ ] Responsive pass 2 (375/768/1280) for all pages; accessibility basics (labels, focus, contrast, keyboard).
- [ ] Final empty/error/loading polish; cross-browser check (Chrome, Safari/Firefox quick).
- [ ] Lighthouse sanity (performance and accessibility > 85 on dashboard and milestone page).
- [ ] Freeze UI copy.

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
- [ ] Demo UX polish with seeded data; capture 4-5 screenshots (1920x1080) for the Devpost gallery; project logo/thumbnail.
- [ ] Prepare title cards and lower-thirds for the video (no third-party trademarks or copyrighted music).
- [ ] Pre-arrange windows/profiles for the recording (client window, freelancer window).
- [ ] Final accessibility spot-check.

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
- [ ] Record screen footage (1080p) following doc 16: multiple takes, backup clips of each segment.
- [ ] Prepare mobile-responsive clip (optional 5 seconds).
- [ ] Begin rough edit; add captions.
- [ ] Check video contains no third-party trademarks beyond PayPal's own sandbox UI.

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
- [ ] Finish video edit (target 2:45-2:55), captions, export 1080p; upload to YouTube (public, unlisted is NOT sufficient - must be publicly visible); title and description include repo link.
- [ ] Upload gallery images and thumbnail to Devpost.
- [ ] Final UI check on production.
- [ ] Provide the raw project files of the video to the team drive.

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
