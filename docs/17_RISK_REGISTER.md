# 17 - Risk Register

Scale: Likelihood (L) and Impact (I) 1-5; score = L x I. Review daily at the 21:00 IST sync; owner updates status.

| ID | Category | Risk | L | I | Score | Owner | Mitigation | Fallback / contingency |
|---|---|---|:-:|:-:|:-:|---|---|---|
| R1 | PayPal | Third-party payee not allowed with first-party credentials; multi-freelancer payouts impossible | 4 | 3 | 12 | Member 4 | Day-1 spike S2; default `demo_merchant`; honest wording | Submit with `demo_merchant`, state limitation; do not claim payouts |
| R2 | PayPal | Sandbox instability / slow / account funding issues | 3 | 4 | 12 | Member 4 | Create 2 buyers; test early (Day 1/4); keep time-boxes | `PAYMENTS_MODE=mock` + pre-recorded real sandbox segment |
| R3 | PayPal | Webhook verification fails (raw body re-serialization, wrong webhook id, tunnel changes) | 3 | 3 | 9 | Member 4 | Splice raw body; save real fixtures; staging URL stable from Day 6; `sync` endpoint | Reconcile through sync; show capture response as primary confirmation |
| R4 | PayPal | Double charge / inconsistent state | 2 | 5 | 10 | Member 4 | Request ids, DB unique indexes, row locks, state machine, concurrency tests | Manual reconcile; sandbox only so no real loss |
| R5 | PayPal | API details differ from assumptions (response paths, link rel, experience_context fields) | 3 | 3 | 9 | Member 4 | Items marked VERIFY in doc 07; fixtures from real responses on Day 1 | Adjust parser; fall back to `rel=approve` handling |
| R6 | AI | Poor/unstable LLM output (invalid JSON, vague criteria) | 4 | 3 | 12 | Member 2 | Schema mode, retry with feedback, post-processing, golden sets | Template agreement, mock fixtures |
| R7 | AI | Hallucinated evidence / wrong verdicts erode trust | 3 | 4 | 12 | Member 2 | Quote verification, rule-based recommendation, MANUAL criteria, disclaimer | Mark `CANNOT_DETERMINE`; client decides |
| R8 | AI | Prompt injection in deliverables | 3 | 3 | 9 | Member 2 | Delimiters, schema, no tools, injection fixture test | Cap impact: AI cannot change state |
| R9 | AI | Quota/rate limits/cost during demo or judging | 3 | 4 | 12 | Member 2 | Per-user limits, quota check Day 8/10, budget alerts, mock switch | `AI_MODE=mock` on hosted demo |
| R10 | AI | Latency too high for video | 3 | 2 | 6 | Member 2 | Concise prompts, caps, pre-recorded takes | Speed-ramp/cut in edit |
| R11 | AI | Model name/API changes (retired model) | 2 | 3 | 6 | Member 2 | Model in env var; pin on Day 1; provider abstraction | Switch provider/model via env |
| R12 | Technical | Contract drift between frontend and backend | 4 | 3 | 12 | Member 1 | OpenAPI type generation in CI, contracts frozen per day | Daily integration check |
| R13 | Technical | Background evaluation lost on restart | 3 | 2 | 6 | Member 2 | Reaper marks stale runs FAILED; retry | Manual retry button |
| R14 | Technical | Render free-tier spin-down, DB expiry, cold starts during judging | 3 | 4 | 12 | Member 1 | Use paid starter with $50 credits; verify DB retention; keep-alive check | Judges can run locally in mock mode; README is primary |
| R15 | Technical | Secrets leaked in Git | 2 | 5 | 10 | Member 1 | `.gitignore`, gitleaks CI + pre-public scan, key rotation procedure | Rotate keys immediately; rewrite history before going public |
| R16 | Technical | Migration conflicts / schema churn | 3 | 3 | 9 | Member 1 | Only Member 1 commits migrations; additive after Day 5 | Reset DB locally; seeds are idempotent |
| R17 | Technical | File extraction failures on odd PDFs/DOCX | 3 | 2 | 6 | Member 2 | Limits, try/except, `FAILED` status; focus on text/markdown for demo | `INCONCLUSIVE` with manual review |
| R18 | Team | Frontend overload on Member 3 (largest scope) | 4 | 4 | 16 | Member 1 | Payment UI to Member 4, evaluation UI to Member 2, small component set, mocks, cut list | Cut P1 UI first (doc 11); Member 1/Member 4 pick up P0 UI bugs |
| R19 | Team | Integration slips on Day 5 (many dependencies) | 4 | 4 | 16 | Member 1 | Frozen contracts, mocks, dedicated integration day, small PRs | Extend into Day 6; defer P1 |
| R20 | Team | Illness/unavailability of a member | 2 | 5 | 10 | Member 1 | Backup pairs: Member 1<->Member 4 (backend/payments), Member 2<->Member 1 (AI services), Member 3<->Member 4 (UI) ; docs are the handoff | Re-scope to P0 only |
| R21 | Team | Merge conflicts / broken `main` | 3 | 3 | 9 | Member 1 | Trunk-based, CODEOWNERS, CI, 30-minute red-main rule | Revert quickly |
| R22 | Team | Communication gaps / unknown blockers | 3 | 3 | 9 | Member 1 | Standup, `#blockers`, 21:00 sync | Escalation rule: 30 min |
| R23 | Time | Scope creep | 4 | 4 | 16 | Member 1 | P0/P1/P2 discipline; feature freeze Day 8; "no new features" rule after Day 5 unless P0 | Cut list order (doc 11) |
| R24 | Time | Underestimated polish/video time | 4 | 4 | 16 | Member 3 | Video prep Day 9-10; segmented recording; script fixed | Submit simpler edit; pre-recorded segments |
| R25 | Time | Last-minute submission problems (Devpost form, YouTube processing) | 3 | 5 | 15 | Member 1 | Draft on Day 9; submit by 22:00 IST Nov 11 (~27 h buffer); upload video early | Use buffer until 01:30 IST Nov 13 only if needed |
| R26 | Compliance | Eligibility issue for a member (residence/age) | 1 | 5 | 5 | All | Each member verifies Rules s.3 on Day 1 | Escalate to hackathon manager |
| R27 | Compliance | Misleading claims (escrow/protection/legal) | 2 | 4 | 8 | Member 4 | Copy review Day 7-8; honesty statement everywhere | Edit text/video before submission |
| R28 | Compliance | Video includes disallowed trademarks/music | 2 | 3 | 6 | Member 3 | No music; only app UI and PayPal sandbox | Re-edit |
| R29 | Compliance | Rules/judging text changes after Nov 1 | 2 | 3 | 6 | Member 1 | Re-read Rules on Day 5, 9, 10 | Adjust submission |
| R30 | Product | "Protected" tagline interpreted as escrow | 3 | 3 | 9 | Member 1 | Disclaimer in README/UI/Devpost; narration | Decision D-06: keep tagline vs soften |
| R31 | Product | Demo too complex for 3 minutes | 3 | 4 | 12 | Member 4 | Pre-staged resubmission, cut segments, rehearsals | Shorten flow to one milestone |

## Top risks (score >= 15): R18, R19, R23, R24, R25
Standing actions: daily check of cut-list readiness; Day-5 gate decision at 21:00 IST (go/cut); Day-8 freeze enforced by Member 1.

## Fallback implementations (summary)
| Dependency | Fallback | Switch | UX label |
|---|---|---|---|
| LLM | Mock provider fixtures; template agreement | `AI_MODE=mock` | "SIMULATED AI" banner |
| PayPal checkout | Mock checkout page + mock client | `PAYMENTS_MODE=mock` | "SIMULATED PAYMENTS" banner |
| Hosting | Local run via README | n/a | n/a |
| Webhook delivery | `POST /payments/{id}/sync` | UI button "Check status" | - |
| Video recording | Pre-recorded segments | n/a | n/a |
