# 05 - API Specification

Base URL (local): `http://localhost:8000` - all routes under `/api` unless noted. JSON in/out; `multipart/form-data` for uploads. FastAPI publishes the machine-readable contract at `/openapi.json`; **this document is the human-readable source of truth until the code exists**, afterwards `openapi.json` wins and this file is updated in the same PR.

## 0. Conventions

| Topic | Rule |
|---|---|
| Auth | `Authorization: Bearer <JWT>` on every route except those marked **Public** |
| IDs | UUID strings |
| Money | Decimal **strings** with 2 decimals (`"300.00"`), currency `"USD"` |
| Dates | `date` = `YYYY-MM-DD`; `datetime` = ISO-8601 UTC (`2026-11-03T09:15:00Z`) |
| Pagination | List endpoints return `{ "items": [...], "next_cursor": null }` (cursor unused in MVP, field reserved) |
| Request id | Server returns `X-Request-Id`; echoed in error envelope |
| Idempotency | Payment endpoints are idempotent server-side (doc 07). Clients may also send `Idempotency-Key` (informational in MVP) |
| Roles | `CLIENT` / `FREELANCER` are per project; "member" = either |
| Non-member | Returns `404 NOT_FOUND` (not 403) for project-scoped objects |

### Error envelope
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Milestone amounts must sum to the agreement total.",
    "details": { "expected": "1200.00", "actual": "1150.00" },
    "request_id": "7f1c2a9e"
  }
}
```

### Error codes
| HTTP | `code` | Meaning |
|---|---|---|
| 400 | `BAD_REQUEST` | Malformed request |
| 400 | `WEBHOOK_SIGNATURE_INVALID` | PayPal webhook failed verification |
| 401 | `AUTH_REQUIRED` | Missing/invalid/expired token |
| 403 | `FORBIDDEN` | Authenticated but wrong role for this action |
| 404 | `NOT_FOUND` | Missing or not visible |
| 409 | `INVALID_STATE` | Action not allowed in current status |
| 409 | `AGREEMENT_HASH_MISMATCH` | Approval hash differs from current content |
| 409 | `PAYMENT_ALREADY_EXISTS` | Live payment already exists for milestone |
| 409 | `EMAIL_TAKEN` | Registration conflict |
| 413 | `FILE_TOO_LARGE` | > `MAX_UPLOAD_MB` |
| 415 | `FILE_REJECTED` | Type/content not allowed |
| 422 | `VALIDATION_ERROR` | Field/business validation failed |
| 429 | `RATE_LIMITED` | Too many requests |
| 502 | `PAYPAL_ERROR` | PayPal call failed (details sanitized, includes PayPal `debug_id`) |
| 503 | `AI_UNAVAILABLE` | LLM failed after retries; fallback offered where applicable |

---

## 1. System

### GET `/api/health` - Public
`200` `{ "status": "ok", "db": "ok", "version": "0.1.0" }`

### GET `/api/config` - Public
```json
{ "ai_mode": "live", "payments_mode": "paypal_sandbox", "payee_mode": "demo_merchant",
  "max_upload_mb": 5, "max_files_per_submission": 5, "currency": "USD", "env": "staging" }
```
UI uses it for the SANDBOX / SIMULATED banners.

## 2. Auth and users

### POST `/api/auth/register` - Public
Validation: email valid; password 10-128 chars; display_name 1-80.
```json
// request
{ "email": "maya@example.com", "password": "S3cure-pass-123", "display_name": "Maya Rao" }
// 201
{ "access_token": "eyJ...", "token_type": "bearer",
  "user": { "id": "0b5c...", "email": "maya@example.com", "display_name": "Maya Rao", "paypal_email": null } }
```
Errors: `409 EMAIL_TAKEN`, `422 VALIDATION_ERROR`, `429 RATE_LIMITED`.

### POST `/api/auth/login` - Public
```json
{ "email": "maya@example.com", "password": "S3cure-pass-123" }
```
`200` same shape as register. Errors: `401 AUTH_REQUIRED` (generic message), `429`.

### GET `/api/auth/me`
`200` `{ "id": "...", "email": "...", "display_name": "...", "paypal_email": null }`

### PATCH `/api/users/me`
```json
{ "display_name": "Maya R.", "paypal_email": "maya-sandbox@business.example.com" }
```
`200` updated user. Validation: `paypal_email` valid email or null.

## 3. Projects and invitations

### POST `/api/projects`
Caller becomes `CLIENT`.
```json
// request
{ "title": "Landing page and copy for Ember & Oak coffee subscription",
  "brief": "We are a small coffee roaster launching a subscription. We need brand copy, a one-page landing site with a signup form, and launch QA. Budget about $1,200, launch in 3 weeks." }
// 201
{ "id": "p1...", "title": "...", "brief": "...", "status": "DRAFT", "role": "CLIENT",
  "client": { "id": "...", "display_name": "Maya Rao" }, "freelancer": null,
  "agreement_status": null, "created_at": "2026-11-02T08:00:00Z" }
```
Validation: title 3-140; brief 40-8000.

### GET `/api/projects`
`200`
```json
{ "items": [ { "id": "p1...", "title": "...", "status": "ACTIVE", "role": "CLIENT",
   "counterparty": { "id": "...", "display_name": "Dev Patel" },
   "agreement_status": "APPROVED", "total_amount": "1200.00",
   "paid_amount": "300.00", "milestones_total": 3, "milestones_paid": 1,
   "next_due_date": "2026-11-17", "needs_action": true } ], "next_cursor": null }
```

### GET `/api/projects/{project_id}` (member)
Returns project + current agreement summary + milestone list (compact) + `role` + `ai_summary` (nullable).
```json
{ "id": "p1...", "title": "...", "brief": "...", "status": "ACTIVE", "role": "FREELANCER",
  "client": {"id":"...","display_name":"Maya Rao"}, "freelancer": {"id":"...","display_name":"Dev Patel"},
  "agreement": { "id": "a1...", "version": 1, "status": "APPROVED", "content_hash": "9f2c...e1", "total_amount": "1200.00" },
  "milestones": [ { "id": "m1...", "position": 1, "title": "Brand copy & sitemap", "amount": "300.00",
                    "due_date": "2026-11-10", "status": "ACTIVE" } ],
  "ai_summary": null, "created_at": "..." }
```

### PATCH `/api/projects/{project_id}` (CLIENT, project `DRAFT`)
`{ "title": "...", "brief": "..." }` -> `200` project. Errors: `409 INVALID_STATE`.

### POST `/api/projects/{project_id}/invitations` (CLIENT)
```json
{ "email": "dev@example.com" }
```
`201`
```json
{ "id": "i1...", "email": "dev@example.com", "status": "PENDING", "expires_at": "2026-11-16T08:00:00Z",
  "invite_url": "http://localhost:5173/invite/3Qv...raw-token" }
```
The raw token is returned **once** (only its SHA-256 is stored). Creating a new invitation revokes the previous pending one. Errors: `409 INVALID_STATE` if a freelancer is already attached.

### GET `/api/invitations/{token}` - Public
Minimal preview: `{ "project_title": "...", "client_name": "Maya Rao", "invited_email": "dev@example.com", "status": "PENDING" }`. `404` for unknown/expired tokens.

### POST `/api/invitations/{token}/accept`
Caller email must equal invited email (case-insensitive) -> else `403 FORBIDDEN`.
`200` `{ "project_id": "p1...", "role": "FREELANCER" }`

### GET `/api/projects/{project_id}/audit` (member)
```json
{ "chain_valid": true,
  "items": [ { "id": 41, "action": "AGREEMENT_APPROVED", "actor_type": "USER", "actor": {"id":"...","display_name":"Dev Patel"},
               "entity_type": "agreement", "entity_id": "a1...", "details": {"content_hash":"9f2c...e1","role":"FREELANCER"},
               "created_at": "2026-11-03T10:02:11Z", "entry_hash": "ab12..." } ] }
```

### POST `/api/projects/{project_id}/summary` (member) - owner: Member 2
Regenerates the AI summary if the state hash changed (else returns cached). `200`
```json
{ "headline": "Milestone 1 paid; milestone 2 due in 6 days",
  "progress": "1 of 3 milestones paid ($300 of $1,200).",
  "risks": ["Milestone 2 deliverable has not been submitted and is due 2026-11-17."],
  "next_actions": [ { "for_role": "FREELANCER", "text": "Submit the landing page files for milestone 2." } ],
  "generated_at": "2026-11-12T09:00:00Z", "ai_mode": "live" }
```
Errors: `503 AI_UNAVAILABLE` (UI shows cached summary if any).

## 4. AI agreement generation (owner: Member 2; router `routers/ai.py`)

### POST `/api/projects/{project_id}/agreement/clarify` (CLIENT)
```json
// request
{ "brief": "(optional override; defaults to project.brief)" }
// 200
{ "ai_run_id": "r1...", "ai_mode": "live",
  "extraction": {
    "project_type": "Website + copywriting",
    "summary": "Brand copy and a one-page landing site for a coffee subscription launch.",
    "requirements": [ { "id": "R1", "text": "Brand copy for the landing page", "category": "content", "explicit": true },
                      { "id": "R2", "text": "One-page responsive landing site with signup form", "category": "development", "explicit": true } ],
    "budget": { "amount": "1200.00", "currency": "USD", "source": "stated" },
    "timeline": { "deadline": null, "duration_days": 21, "source": "stated" },
    "missing_information": [ { "id": "Q1", "question": "Which signup provider should the form connect to (e.g., Mailchimp, Stripe)?",
                              "why_it_matters": "Determines integration effort and acceptance criteria.", "severity": "important" } ],
    "assumptions": [ "Single language (English)" ],
    "risk_flags": [ "No revision limit stated" ] } }
```
Errors: `503 AI_UNAVAILABLE` -> `{ "fallback": "TEMPLATE" }` in `details`; `409 INVALID_STATE` if an approved agreement exists.

### POST `/api/projects/{project_id}/agreement/generate` (CLIENT)
```json
// request
{ "answers": [ { "question_id": "Q1", "answer": "Mailchimp" } ],
  "budget_total": "1200.00",
  "target_end_date": "2026-11-23",
  "extraction_ai_run_id": "r1..." }
// 201
{ "agreement": { "id": "a1...", "version": 1, "status": "DRAFT", "origin": "AI",
    "title": "Ember & Oak Launch Package", "summary": "...",
    "scope_in": ["Brand voice guide", "Landing page copy", "One-page responsive site"],
    "scope_out": ["Logo design", "Paid ads"],
    "assumptions": ["Client supplies product photos"],
    "payment_terms": "Each milestone is paid after the client accepts it, via PayPal, by the client's own approval.",
    "revision_policy": "Two revision rounds per milestone.",
    "total_amount": "1200.00", "currency": "USD", "content_hash": null,
    "milestones": [
      { "id": "m1...", "position": 1, "title": "Brand voice & landing copy", "description": "...",
        "deliverables": ["copy.md"], "amount": "300.00", "due_date": "2026-11-10", "status": "DRAFT",
        "rationale": "25% of budget; copy blocks design.",
        "criteria": [ { "id": "c1...", "position": 1, "text": "Copy includes hero headline, subhead and CTA text", "verification_method": "TEXT_EVIDENCE", "is_required": true } ] } ] },
  "warnings": [ { "code": "VAGUE_CRITERION", "milestone_position": 2, "criterion_position": 3, "message": "Criterion contains subjective wording ('professional')." } ],
  "ai_run_id": "r2...", "ai_mode": "live" }
```
Errors: `503 AI_UNAVAILABLE` (with `details.fallback = "TEMPLATE"`; client may call `POST /agreement/template`), `409 INVALID_STATE` (current agreement is not `DRAFT`/`CHANGES_REQUESTED`/absent), `422`.

### POST `/api/projects/{project_id}/agreement/template` (CLIENT)
Deterministic fallback: 3 milestones 30/40/30 from `budget_total` and `target_end_date`, placeholder criteria. `201` same shape as generate, `origin = "TEMPLATE_FALLBACK"`.

## 5. Agreement lifecycle (owner: Member 1)

### GET `/api/projects/{project_id}/agreement` (member)
Current (non-superseded) agreement with milestones and criteria + approvals:
```json
{ "agreement": { "...same as above...", "status": "IN_REVIEW", "content_hash": "9f2c...e1" },
  "approvals": [ { "user": {"id":"...","display_name":"Maya Rao"}, "role": "CLIENT", "decision": "APPROVED",
                   "content_hash": "9f2c...e1", "comment": null, "created_at": "2026-11-03T09:40:00Z" } ] }
```
`404` if none yet.

### GET `/api/projects/{project_id}/agreements` (member)
Version list: `[ { "id", "version", "status", "origin", "content_hash", "created_at", "submitted_at", "approved_at" } ]`

### GET `/api/agreements/{agreement_id}` (member) -> same as above for a specific version.

### PATCH `/api/agreements/{agreement_id}` (CLIENT, `DRAFT`)
```json
{ "title": "...", "summary": "...", "scope_in": ["..."], "scope_out": ["..."], "assumptions": ["..."],
  "payment_terms": "...", "revision_policy": "...", "total_amount": "1200.00" }
```
`200` agreement. Sets `origin = AI_EDITED` if previously `AI`. Validation: sum of milestone amounts must equal `total_amount` **or** response includes `warnings` (save allowed while editing; submit is blocked).

### POST `/api/agreements/{agreement_id}/milestones` (CLIENT, `DRAFT`)
```json
{ "title": "Launch QA", "description": "...", "deliverables": ["qa-report.md"], "amount": "300.00", "due_date": "2026-11-22",
  "criteria": [ { "text": "QA report lists tested browsers and results", "verification_method": "TEXT_EVIDENCE", "is_required": true } ] }
```
`201` milestone. Position appended; due date must be after the previous milestone's.

### PATCH `/api/milestones/{milestone_id}` (CLIENT, parent agreement `DRAFT`)
Any of `title, description, deliverables, amount, due_date, position`. `200` milestone.

### DELETE `/api/milestones/{milestone_id}` (CLIENT, `DRAFT`, min 2 milestones remain) -> `204`

### PUT `/api/milestones/{milestone_id}/criteria` (CLIENT, `DRAFT`)
Replaces the list (2-6 items). Body: `{ "criteria": [ { "text", "verification_method", "is_required" } ] }` -> `200` list.

### POST `/api/agreements/{agreement_id}/submit` (CLIENT, `DRAFT`)
Preconditions: freelancer attached (invitation accepted); sum of amounts = total; due dates ascending and >= today; each milestone has 2-6 criteria; 2-6 milestones.
`200` `{ "status": "IN_REVIEW", "content_hash": "9f2c...e1" }` and records the CLIENT approval row.
Errors: `422 VALIDATION_ERROR` (details list), `409 INVALID_STATE`.

### POST `/api/agreements/{agreement_id}/approve` (FREELANCER, `IN_REVIEW`)
```json
{ "content_hash": "9f2c...e1" }
```
`200` `{ "status": "APPROVED", "project_status": "ACTIVE", "active_milestone_id": "m1..." }`
Errors: `409 AGREEMENT_HASH_MISMATCH`, `409 INVALID_STATE`.

### POST `/api/agreements/{agreement_id}/request-changes` (FREELANCER, `IN_REVIEW`)
```json
{ "comment": "Milestone 2 deadline is too tight; propose Nov 20." }
```
`200` `{ "status": "CHANGES_REQUESTED" }` (comment min 3 chars).

### POST `/api/agreements/{agreement_id}/revise` (CLIENT, `CHANGES_REQUESTED`)
Copies content into version N+1 `DRAFT`; marks old `SUPERSEDED`. `201` new agreement.

## 6. Deliverables (owner: Member 1; text extraction: Member 2)

### POST `/api/milestones/{milestone_id}/deliverables` (FREELANCER; milestone `ACTIVE` or `CHANGES_REQUESTED`)
`multipart/form-data`: `note` (text, <= 4000), `links` (repeatable URL, http/https, <= 5), `files` (repeatable, <= 5 files, <= 5 MB each).
Allowed extensions: `txt md csv json html css js ts tsx jsx py java go rs sql yaml yml xml pdf docx png jpg jpeg` (images used only when multimodal is enabled; otherwise stored as `UNSUPPORTED` for evaluation but downloadable).
`202`
```json
{ "id": "d1...", "milestone_id": "m1...", "submission_no": 1, "status": "EVALUATING",
  "files": [ { "id": "f1...", "filename": "copy.md", "content_type": "text/markdown", "size_bytes": 8123,
               "sha256": "c0ffee...", "extraction_status": "OK" } ],
  "evaluation": { "id": "e1...", "status": "PENDING" } }
```
Errors: `409 INVALID_STATE`, `413 FILE_TOO_LARGE`, `415 FILE_REJECTED`, `422` (no note and no file and no link).

### GET `/api/milestones/{milestone_id}/deliverables` (member)
List of submissions newest first, each with files metadata, status, latest evaluation summary (`recommendation`, `status`) and `decision` (nullable).

### GET `/api/deliverables/{deliverable_id}` (member) -> one submission (same shape + `milestone`).

### GET `/api/deliverable-files/{file_id}/download` (member)
Streams bytes with `Content-Disposition: attachment` and `X-Content-Type-Options: nosniff`.

## 7. AI evaluation (owner: Member 2)

### GET `/api/deliverables/{deliverable_id}/evaluation` (member)
Latest attempt (`?attempt=n` for history). While running:
`200` `{ "id": "e1...", "status": "RUNNING", "attempt": 1 }`.
When completed:
```json
{ "id": "e1...", "attempt": 1, "status": "COMPLETED", "provider": "gemini", "model": "<GEMINI_MODEL>", "prompt_version": "evaluate.v1",
  "recommendation": "PARTIALLY_MEETS", "confidence": 0.74,
  "report": {
    "overall": { "summary": "4 of 5 required criteria are met; the CTA text is missing.", "recommendation": "PARTIALLY_MEETS", "confidence": 0.74 },
    "criteria_results": [
      { "criterion_id": "c1...", "criterion_text": "Copy includes hero headline, subhead and CTA text", "status": "PARTIALLY_MET",
        "reasoning": "Headline and subhead present; no CTA button text found.",
        "evidence": [ { "file": "copy.md", "quote": "Hero: Roasted to order, delivered to your door.", "verified": true } ],
        "gap": "Add CTA text for the hero section." } ],
    "missing_requirements": [ "CTA text for hero section" ],
    "unverifiable_items": [ "Visual design quality cannot be assessed from text." ],
    "risks": [ ],
    "next_steps": { "for_client": ["Request the CTA text before accepting."], "for_freelancer": ["Add CTA copy to copy.md and resubmit."] },
    "stats": { "evidence_total": 6, "evidence_verified": 5, "evidence_removed": 1 },
    "disclaimer": "AI-generated, advisory only. The client makes the final decision." },
  "created_at": "...", "completed_at": "..." }
```
Failed: `{ "status": "FAILED", "error_code": "AI_TIMEOUT", "error_message": "The AI service timed out. You can retry." }`

### POST `/api/deliverables/{deliverable_id}/evaluation/retry` (member)
Creates attempt n+1 (`PENDING`). `202`. Limits: max 3 attempts per deliverable. Errors: `409 INVALID_STATE` if one is already running, `429`.

## 8. Client decision (owner: Member 1)

### POST `/api/deliverables/{deliverable_id}/decision` (CLIENT)
Preconditions: deliverable status in (`EVALUATED`, `EVALUATION_FAILED`); latest submission only.
```json
{ "decision": "CHANGES_REQUESTED", "comment": "CTA text is missing; please add it." }
```
`200` `{ "deliverable_status": "CHANGES_REQUESTED", "milestone_status": "CHANGES_REQUESTED" }`
or `{ "decision": "ACCEPTED" }` -> `{ "deliverable_status": "ACCEPTED", "milestone_status": "ACCEPTED", "next_milestone_activated": "m2..." }`
Errors: `409 INVALID_STATE` (e.g., evaluation still running), `422` (comment required for changes), `403` for freelancer.

## 9. Payments (owner: Member 4) - see doc 07 for flow details

### POST `/api/milestones/{milestone_id}/payments` (CLIENT; milestone `ACCEPTED`)
Creates the payment row and the PayPal order. Amount comes from the database.
```json
// 201
{ "id": "pay1...", "milestone_id": "m1...", "amount": "300.00", "currency": "USD",
  "status": "PENDING_APPROVAL", "provider": "PAYPAL", "paypal_order_id": "5O190127TN364715T",
  "approve_url": "https://www.sandbox.paypal.com/checkoutnow?token=5O190127TN364715T",
  "payee_mode": "demo_merchant" }
```
Re-calling while a live payment exists in `PENDING_APPROVAL` returns that same payment (`200`), not a new order. `409 PAYMENT_ALREADY_EXISTS` if a payment is `APPROVED`/`CAPTURE_PENDING`/`COMPLETED`. `502 PAYPAL_ERROR` on PayPal failure (payment row `FAILED`, retry allowed).

### POST `/api/payments/{payment_id}/capture` (CLIENT)
Body: `{ "paypal_order_id": "5O190127TN364715T" }` (must match stored order).
Backend: GET order from PayPal; if `APPROVED` -> `POST .../capture`; else `409 INVALID_STATE` with message "Payment not approved on PayPal yet".
```json
// 200
{ "id": "pay1...", "status": "COMPLETED", "paypal_order_id": "5O190127TN364715T",
  "paypal_capture_id": "3C679366HH908993F", "captured_at": "2026-11-05T11:20:00Z",
  "milestone_status": "PAID" }
```
If PayPal returns capture `PENDING`: `200` with `status: "CAPTURE_PENDING"` (webhook completes later). Repeating the call after completion returns the same `200` body (idempotent).

### POST `/api/payments/{payment_id}/cancel` (CLIENT)
Marks `PENDING_APPROVAL` payment `CANCELLED` (called by the cancel return page). `200`.

### POST `/api/payments/{payment_id}/sync` (member, P1)
Fetches the order (and capture if known) from PayPal and reconciles. `200` payment.

### GET `/api/payments/{payment_id}` (member)
Payment + `events: [ { "event_type", "from_status", "to_status", "source", "paypal_ref", "created_at" } ]` + `webhook_verified: true|false`.

### GET `/api/projects/{project_id}/payments` (member)
`{ "items": [ { ...payment summary... } ], "totals": { "paid": "300.00", "pending": "0.00", "remaining": "900.00" } }`

### POST `/api/webhooks/paypal` - **Public** (authenticated only by PayPal signature)
Reads the **raw body**; headers `PAYPAL-TRANSMISSION-ID`, `PAYPAL-TRANSMISSION-TIME`, `PAYPAL-TRANSMISSION-SIG`, `PAYPAL-CERT-URL`, `PAYPAL-AUTH-ALGO`.
Flow: store event (`RECEIVED`) -> verify via PayPal -> on failure `400 WEBHOOK_SIGNATURE_INVALID` (event stored with `FAILURE`, not processed) -> on success process idempotently -> `200 {"received": true}`. Unknown event types: `200`, stored as `IGNORED`.

### Mock PayPal (only when `PAYMENTS_MODE=mock`)
`GET /mock-paypal/checkout?order_id=...&return_url=...&cancel_url=...` (HTML page with "Approve (SIMULATED)" and "Cancel" buttons). Not mounted otherwise.

## 10. Dashboard and notifications (owner: Member 1)

### GET `/api/dashboard`
```json
{ "stats": { "active_projects": 2, "milestones_due_7d": 1, "awaiting_my_action": 2,
             "paid_total": "300.00", "pending_total": "0.00" },
  "needs_action": [ { "project_id": "p1...", "milestone_id": "m1...", "kind": "REVIEW_DELIVERABLE", "label": "Review milestone 1 submission", "due_date": "2026-11-10" } ],
  "upcoming_deadlines": [ { "project_id": "p1...", "milestone_id": "m2...", "title": "Landing page build", "due_date": "2026-11-17", "status": "ACTIVE", "overdue": false } ],
  "recent_payments": [ { "id": "pay1...", "project_title": "...", "milestone_title": "...", "amount": "300.00", "status": "COMPLETED", "captured_at": "..." } ],
  "projects": [ { "...same as GET /api/projects items..." } ] }
```
`needs_action.kind`: `REVIEW_AGREEMENT`, `SUBMIT_AGREEMENT`, `SUBMIT_DELIVERABLE`, `REVIEW_DELIVERABLE`, `PAY_MILESTONE`, `RESUBMIT_DELIVERABLE`, `INVITE_FREELANCER`.

### GET `/api/notifications?unread=true`
`{ "items": [ { "id", "type", "title", "body", "link", "read_at", "created_at" } ], "unread_count": 3 }`

### POST `/api/notifications/{id}/read` -> `204`   |   POST `/api/notifications/read-all` -> `204`

---

## 11. Validation rules summary

| Field | Rule |
|---|---|
| email | RFC-valid, <= 254 chars, case-insensitive unique |
| password | 10-128 chars |
| project.title | 3-140 |
| project.brief | 40-8000 |
| agreement milestones | 2-6; positions contiguous from 1 |
| milestone.amount | > 0, <= 100000.00, 2 decimals |
| sum(milestones.amount) | == agreement.total_amount (enforced at submit; warned while editing) |
| milestone.due_date | >= today (at submit), strictly ascending by position |
| criteria per milestone | 2-6; text 8-500 chars |
| deliverable files | <= 5 files, <= 5 MB each, extension allowlist, MIME sniff must agree |
| links | http/https only, <= 5, <= 2048 chars |
| decision comment | >= 3 chars when `CHANGES_REQUESTED` |
| webhook | verification must return `SUCCESS` |

## 12. Authorization matrix (summary)

| Endpoint group | Public | Client | Freelancer | Notes |
|---|:--:|:--:|:--:|---|
| health, config, invitation preview, webhook | yes | - | - | webhook = signature only |
| Create/patch project, invitations, clarify/generate/template, agreement edit/submit/revise | - | yes | no | |
| Agreement approve/request-changes | - | no | yes | |
| Deliverable submit | - | no | yes | |
| Decision, create/capture/cancel payment | - | yes | no | |
| Read project, agreement, deliverables, evaluation, payments, audit, summary | - | yes | yes | members only |

## 13. Enumeration reference (identical to doc 02 section 1)
* Project: `DRAFT ACTIVE COMPLETED CANCELLED` - Agreement: `DRAFT IN_REVIEW CHANGES_REQUESTED APPROVED SUPERSEDED`
* Milestone: `DRAFT PENDING ACTIVE SUBMITTED CHANGES_REQUESTED ACCEPTED PAID`
* Deliverable: `SUBMITTED EVALUATING EVALUATED EVALUATION_FAILED ACCEPTED CHANGES_REQUESTED`
* Evaluation: `PENDING RUNNING COMPLETED FAILED`; recommendation `MEETS PARTIALLY_MEETS DOES_NOT_MEET INCONCLUSIVE`; criterion result `MET PARTIALLY_MET NOT_MET CANNOT_DETERMINE`
* Payment: `CREATED PENDING_APPROVAL APPROVED CAPTURE_PENDING COMPLETED FAILED DENIED CANCELLED`; provider `PAYPAL MOCK`
