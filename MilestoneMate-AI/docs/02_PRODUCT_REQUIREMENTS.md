# 02 - Product Requirements

Priorities: **P0** = required for the end-to-end demo; **P1** = high value, built only if P0 is green; **P2** = not scheduled (post-hackathon).

## 1. Canonical vocabulary (used identically in every document)

| Entity | Statuses |
|---|---|
| Project | `DRAFT`, `ACTIVE`, `COMPLETED`, `CANCELLED` |
| Agreement | `DRAFT`, `IN_REVIEW`, `CHANGES_REQUESTED`, `APPROVED`, `SUPERSEDED` |
| Milestone | `DRAFT`, `PENDING`, `ACTIVE`, `SUBMITTED`, `CHANGES_REQUESTED`, `ACCEPTED`, `PAID` |
| Deliverable (a submission) | `SUBMITTED`, `EVALUATING`, `EVALUATED`, `EVALUATION_FAILED`, `ACCEPTED`, `CHANGES_REQUESTED` |
| Evaluation | `PENDING`, `RUNNING`, `COMPLETED`, `FAILED` |
| Evaluation recommendation | `MEETS`, `PARTIALLY_MEETS`, `DOES_NOT_MEET`, `INCONCLUSIVE` |
| Criterion result | `MET`, `PARTIALLY_MET`, `NOT_MET`, `CANNOT_DETERMINE` |
| Payment | `CREATED`, `PENDING_APPROVAL`, `APPROVED`, `CAPTURE_PENDING`, `COMPLETED`, `FAILED`, `DENIED`, `CANCELLED` |
| Roles (per project) | `CLIENT`, `FREELANCER` |

## 2. Functional requirements

### Authentication and profile
| ID | Requirement | Pri |
|---|---|---|
| FR-A1 | Register and log in with email + password; JWT bearer sessions | P0 |
| FR-A2 | Profile with display name and optional PayPal email (display only unless `PAYEE_MODE=direct_payee`) | P0 |
| FR-A3 | Roles are per project: the creator is `CLIENT`; the invitee who accepts is `FREELANCER`. One user can be client on one project and freelancer on another | P0 |

### Projects and collaboration
| ID | Requirement | Pri |
|---|---|---|
| FR-P1 | Client creates a project with title and natural-language brief (min 40 chars, max 8,000) | P0 |
| FR-P2 | Client creates an invitation (freelancer email) and receives a copyable invite link; token stored hashed, expires in 14 days | P0 |
| FR-P3 | Freelancer opens link, logs in/registers with the invited email, accepts; becomes project `FREELANCER` | P0 |
| FR-P4 | Project list and detail visible only to project members | P0 |
| FR-P5 | Project status tracking derived from agreement + milestone states | P0 |

### AI agreement generator
| ID | Requirement | Pri |
|---|---|---|
| FR-G1 | `clarify`: AI extracts requirements, deliverables, budget/timeline signals from the brief | P0 |
| FR-G2 | `clarify` returns at most 6 prioritized missing-information questions with `blocking`/`important`/`nice` severity; the client may answer or skip | P0 |
| FR-G3 | `generate`: AI produces a structured agreement (title, summary, scope in/out, assumptions, payment terms, revision policy, 2-6 milestones) | P0 |
| FR-G4 | Each milestone has amount; amounts sum **exactly** to the total (server-enforced) | P0 |
| FR-G5 | Each milestone has a suggested due date: in the future, strictly increasing, realistic for the scope | P0 |
| FR-G6 | Each milestone has 2-6 acceptance criteria, each testable, flagged `TEXT_EVIDENCE` or `MANUAL` | P0 |
| FR-G7 | Every AI-generated field is editable by the client while the agreement is `DRAFT` | P0 |
| FR-G8 | Server validates totals, dates, counts, currency (`USD`) on every save | P0 |
| FR-G9 | Client submits the agreement for review (`DRAFT` -> `IN_REVIEW`); content hash computed; client approval recorded | P0 |
| FR-G10 | Freelancer approves or requests changes; agreement becomes `APPROVED` only when **both** approvals match the same content hash | P0 |
| FR-G11 | After `CHANGES_REQUESTED` the client creates a new version (`revise`); previous version becomes `SUPERSEDED`; approvals do not carry over | P0 |
| FR-G12 | Version history view with who/when/what changed | P1 |
| FR-G13 | If AI fails after retries, a rule-based template agreement (3 milestones, 30/40/30) is offered with an "AI unavailable" notice | P0 |

### Deliverables
| ID | Requirement | Pri |
|---|---|---|
| FR-D1 | Freelancer submits a deliverable for an `ACTIVE` or `CHANGES_REQUESTED` milestone: note, up to 5 files (<= 5 MB each), optional links | P0 |
| FR-D2 | File allowlist, size, MIME sniffing, SHA-256 recorded; rejected files return a clear error | P0 |
| FR-D3 | Submission history per milestone (`submission_no` 1..n) | P0 |
| FR-D4 | Both parties can download submitted files | P0 |

### AI deliverable evaluation
| ID | Requirement | Pri |
|---|---|---|
| FR-E1 | Evaluation runs asynchronously after submission; UI polls status | P0 |
| FR-E2 | Report contains a verdict per acceptance criterion with evidence (file + quote/locator) and reasoning | P0 |
| FR-E3 | Report lists missing requirements, unverifiable items, risks, and recommended next steps for each party | P0 |
| FR-E4 | Quoted evidence is verified against extracted text; unverifiable quotes are removed and counted | P1 |
| FR-E5 | On failure, the deliverable shows `EVALUATION_FAILED` with a retry button; client may still decide manually | P0 |
| FR-E6 | Client decision: `ACCEPTED` or `CHANGES_REQUESTED` (comment required for changes) | P0 |
| FR-E7 | The AI recommendation never changes a milestone status by itself | P0 |
| FR-E8 | Overall recommendation is computed by deterministic rules from criterion results (doc 06) | P0 |

### PayPal payments
| ID | Requirement | Pri |
|---|---|---|
| FR-Y1 | Client can start payment only for an `ACCEPTED` milestone; backend creates a PayPal order (`intent=CAPTURE`) using the amount stored in the database | P0 |
| FR-Y2 | Client is redirected to PayPal to approve; returns to the app | P0 |
| FR-Y3 | Backend captures only after the order is `APPROVED` and only at the client's request | P0 |
| FR-Y4 | `POST /api/webhooks/paypal` verifies signature through PayPal's verification endpoint before processing | P0 |
| FR-Y5 | All PayPal POSTs carry a deterministic `PayPal-Request-Id`; DB constraints prevent two active payments per milestone | P0 |
| FR-Y6 | `PAYMENT.CAPTURE.COMPLETED` (or successful capture response) sets payment `COMPLETED` and milestone `PAID` exactly once | P0 |
| FR-Y7 | Payment history per project with PayPal order/capture IDs and timeline | P0 |
| FR-Y8 | Reconciliation: `POST /api/payments/{id}/sync` fetches order/capture state from PayPal | P1 |
| FR-Y9 | `PAYMENTS_MODE=mock` simulates the flow with a visible "SIMULATED" label | P0 |
| FR-Y10 | User-friendly handling of cancel, decline, `PENDING` capture, PayPal outage | P0 |

### Dashboard and notifications
| ID | Requirement | Pri |
|---|---|---|
| FR-H1 | Dashboard lists the user's projects with role, progress, next action | P0 |
| FR-H2 | Upcoming and overdue milestone deadlines | P0 |
| FR-H3 | In-app notifications (bell + page) for invites, approvals, submissions, evaluations, decisions, payments | P0 |
| FR-H4 | AI project summary card (headline, progress, risks, next actions), cached by state hash | P1 |
| FR-H5 | "Needs your action" list | P1 |

### Trust and transparency
| ID | Requirement | Pri |
|---|---|---|
| FR-T1 | Append-only audit log of every state-changing action (user, system, AI, PayPal) | P0 |
| FR-T2 | Hash chain per project with a verify endpoint and UI badge | P1 |
| FR-T3 | Approval history with timestamp, user, content hash | P0 |
| FR-T4 | Evaluation history per deliverable (all attempts) | P0 |
| FR-T5 | Payment audit trail: `payment_events` + webhook events with PayPal IDs | P0 |

### P2 (not scheduled)
Email notifications; change orders; freelancer-initiated projects; refunds/disputes UI; multi-currency; PayPal Agent Toolkit/MCP integration; AG Grid ledger; Render Workflows; real third-party payee through PayPal Commerce Platform; link crawling; zip upload; e-signature.

## 3. Non-functional requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-1 | Performance | P95 API latency < 400 ms for non-AI endpoints; AI clarify < 15 s, generate < 25 s, evaluate < 45 s (P95) |
| NFR-2 | Reliability | Any external failure (LLM, PayPal) yields a user-visible, recoverable state; no unhandled 500 in demo path |
| NFR-3 | Consistency | Payment and milestone state changes are transactional; capture and webhook processing are idempotent |
| NFR-4 | Security | Secrets only in env; bcrypt/argon2 password hashing; RBAC on every endpoint; webhook verification; upload validation (doc 14) |
| NFR-5 | Privacy | Deliverable content sent to the LLM only for evaluation; no PII beyond name/email in prompts; AI runs log metadata and hashes, not raw documents |
| NFR-6 | Usability | Primary flows reachable in <= 3 clicks from dashboard; WCAG AA contrast for text |
| NFR-7 | Responsiveness | Works from 375 px to 1440 px |
| NFR-8 | Observability | Structured JSON logs with `request_id`; AI run latency/tokens recorded |
| NFR-9 | Portability | Runs locally with Docker Postgres in < 10 minutes following README; mock modes need no external credentials |
| NFR-10 | Testability | `pytest` runs against Postgres; CI on every PR |
| NFR-11 | Compliance wording | No UI/README/video text may use the word "escrow" except to say we are not one |
| NFR-12 | Accessibility | Keyboard-operable forms, visible focus, labels on all inputs |

## 4. User stories and acceptance criteria

### Client
| ID | Story | Acceptance criteria |
|---|---|---|
| US-C1 | As a client I paste my project idea and get a structured agreement so I do not have to write a contract | **Given** a brief >= 40 chars **When** I click "Generate" **Then** I see clarifying questions (or skip) and then a draft with 2-6 milestones whose amounts sum to the total and whose criteria are listed |
| US-C2 | As a client I edit anything the AI produced | **Given** a `DRAFT` agreement **When** I change an amount **Then** the sum indicator updates and Save is blocked until total matches |
| US-C3 | As a client I invite my freelancer | **When** I enter an email **Then** I get a link; the invitation is `PENDING` until accepted |
| US-C4 | As a client I only approve what the freelancer also sees | **Then** approvals display the same 8-char hash prefix on both sides |
| US-C5 | As a client I see how the work compares to the criteria | **Given** a submission **Then** within 60 s I see a report with a verdict per criterion, evidence, gaps, next steps |
| US-C6 | As a client I decide on the work | **When** I click Accept **Then** milestone becomes `ACCEPTED`; **When** I click Request changes with a comment **Then** milestone becomes `CHANGES_REQUESTED` and freelancer is notified |
| US-C7 | As a client I pay an accepted milestone safely | **When** I click "Pay with PayPal" **Then** I am sent to PayPal sandbox; after approval and return I see `COMPLETED`; clicking twice never creates two payments |
| US-C8 | As a client I see everything that happened | **Then** Activity tab lists agreements, approvals, evaluations, decisions, payments in time order |

### Freelancer
| ID | Story | Acceptance criteria |
|---|---|---|
| US-F1 | As a freelancer I review the agreement before committing | **When** I open the invite **Then** I see full scope, milestones, criteria, amounts, dates, and can approve or request changes with a comment |
| US-F2 | As a freelancer I know exactly what "done" means | **Then** each milestone page lists its acceptance criteria |
| US-F3 | As a freelancer I submit work and see the AI report too | **Then** the same report as the client is visible; I see which criteria need work |
| US-F4 | As a freelancer I see when payment completes | **Then** milestone shows `PAID` with PayPal transaction ID and a notification |

### Platform
| ID | Story | Acceptance criteria |
|---|---|---|
| US-S1 | As an operator I can prove a payment event is authentic | **Then** each webhook event row shows `verification_status = SUCCESS` |
| US-S2 | As an operator I can demo when an API is down | **Then** `AI_MODE=mock` / `PAYMENTS_MODE=mock` run the whole flow |

## 5. User journeys

### Journey A - Happy path (the demo)
```
Client: Register -> New project (paste brief) -> Answer clarifying questions -> Review AI draft
      -> Edit one amount -> Invite freelancer -> Submit for review (client approval recorded)
Freelancer: Open invite link -> Review -> Approve (agreement APPROVED, milestone 1 ACTIVE)
Freelancer: Submit deliverable (milestone 1) -> AI evaluation (1 criterion NOT_MET)
Client: Read report -> Request changes
Freelancer: Resubmit -> AI evaluation (MEETS)
Client: Accept -> Pay with PayPal (sandbox approve) -> Return -> COMPLETED -> milestone PAID
Both: Dashboard shows progress, payment ledger, audit trail, AI summary
```

### Journey B - Disagreement
Freelancer requests changes to the agreement -> client revises (version 2, version 1 `SUPERSEDED`) -> both approve version 2 (new hash).

### Journey C - Failure handling
* LLM timeout -> retry x2 -> fallback template + banner -> client edits manually.
* PayPal approval cancelled -> payment `CANCELLED` -> milestone stays `ACCEPTED` -> client can retry (new payment row).
* Capture returns `PENDING` -> `CAPTURE_PENDING` -> webhook completes it -> UI updates.
* Duplicate webhook -> second delivery is recorded as `IGNORED`, no state change.

## 6. Feature priority matrix

| Feature | Pri | Owner (doc 09) | Day target |
|---|---|---|---|
| Auth, profile | P0 | Member 1 | 1 |
| Projects, invitations | P0 | Member 1 | 2 |
| AI clarify + generate | P0 | Member 2 | 2-3 |
| Agreement edit/approve/versions | P0 | Member 1 (API), Member 3 (UI) | 3 |
| Order create/capture | P0 | Member 4 | 3-4 |
| Deliverable upload | P0 | Member 1 | 4 |
| AI evaluation | P0 | Member 2 | 4-5 |
| Webhooks | P0 | Member 4 | 4 |
| Vertical slice integrated | P0 | All | 5 |
| Audit trail, ledger UI | P0 | Member 3 + Member 4 | 6 |
| AI summary, needs-action, chain verify | P1 | Member 2, Member 1, Member 3 | 7 |
| Mock modes | P0 (fallback) | Member 2 (AI), Member 4 (payments) | 6-7 |
