# 08 - UI/UX Specification

Owner: **Member 3** (app shell, design system, all pages). Exceptions with isolated directories: `frontend/src/features/payments/` -> **Member 4**; `frontend/src/features/evaluation/` -> **Member 2**.

## 1. Design principles
1. **Trust first.** Calm, clear, no dark patterns. Every money action shows amount, payee label, and what happens next.
2. **Status is always visible.** Every project/milestone/payment has a colour-coded badge and a "next action" line.
3. **AI is labelled and editable.** AI output carries a small "AI-generated" chip; nothing AI-made is final.
4. **One primary action per screen.**
5. **Honest wording.** Never "escrow", "protected funds", "guaranteed". Use "Paid via PayPal after your approval". The tagline "Protected" is product branding only; the UI footer states: *"MilestoneMate coordinates agreements and PayPal payments. It is not an escrow service and not legal advice."*
6. **Sandbox/mock transparency.** Persistent banners when `payments_mode != live` or `ai_mode = mock`.

## 2. Design system

### Colour palette (Tailwind tokens in `tailwind.config.ts`)
| Token | Hex | Use |
|---|---|---|
| `brand-600` | `#4F46E5` | Primary buttons, links, active nav |
| `brand-50` / `brand-100` | `#EEF2FF` / `#E0E7FF` | Tints, selected rows |
| `ink-900` | `#0F172A` | Headings |
| `ink-600` | `#475569` | Body text |
| `ink-300` | `#CBD5E1` | Borders |
| `surface` | `#FFFFFF` | Cards |
| `canvas` | `#F8FAFC` | App background |
| `success-600` / `success-50` | `#059669` / `#ECFDF5` | Accepted, Paid, Met |
| `warning-600` / `warning-50` | `#D97706` / `#FFFBEB` | Pending, Partially met, sandbox banner |
| `danger-600` / `danger-50` | `#DC2626` / `#FEF2F2` | Failed, Not met, destructive |
| `ai-600` / `ai-50` | `#7C3AED` / `#F5F3FF` | AI chip, AI panels |
Contrast: text on `brand-600` is white (AA); never use `warning-600` text on white for body copy below 18 px (use `#B45309`).

### Typography
Inter (system fallback `ui-sans-serif`). Scale: `text-xs 12`, `sm 14` (default UI), `base 16`, `lg 18`, `xl 20`, `2xl 24` (page titles), `3xl 30` (hero). Numerals for money: `tabular-nums`, `font-semibold`. Monospace (`ui-monospace`) for hashes and PayPal IDs.

### Spacing, shape, motion
4-px grid; card padding `p-5`; radius `rounded-xl` (cards), `rounded-lg` (inputs/buttons); shadow `shadow-sm`; focus ring `ring-2 ring-brand-600 ring-offset-2`; transitions 150 ms; respect `prefers-reduced-motion`.

### Component library (`frontend/src/components/ui/`)
`Button` (primary/secondary/ghost/danger, loading), `Card`, `Badge` (variant by status), `StatusBadge` (maps every status enum to colour+label), `Input`, `Textarea`, `Select`, `MoneyInput` (string-safe), `DateInput`, `Modal`, `ConfirmDialog`, `Toast`, `Tabs`, `Stepper` (milestone progress), `Skeleton`, `EmptyState`, `ErrorState` (with retry and request id), `FileDropzone`, `Table`, `Banner` (info/warning/sandbox), `Copyable` (hash, link), `AiChip`, `MoneyText`, `DateText`, `Avatar`.

Status -> badge mapping (single file `statusStyles.ts`):
| Status | Label | Colour |
|---|---|---|
| Agreement `DRAFT` | Draft | gray |
| `IN_REVIEW` | Awaiting freelancer | warning |
| `CHANGES_REQUESTED` | Changes requested | warning |
| `APPROVED` | Approved | success |
| Milestone `PENDING` | Locked | gray |
| `ACTIVE` | In progress | brand |
| `SUBMITTED` | Submitted | brand |
| `CHANGES_REQUESTED` | Needs changes | warning |
| `ACCEPTED` | Accepted - payment due | success |
| `PAID` | Paid | success (filled) |
| Payment statuses | per doc 07 section 9 | warning / success / danger |
| Criterion `MET / PARTIALLY_MET / NOT_MET / CANNOT_DETERMINE` | Met / Partial / Not met / Can't tell | success / warning / danger / gray |

## 3. Navigation and layout

* **Top bar:** logo (left), project quick-switcher (optional P1), notification bell with unread count (polls 15 s), user menu (Profile, Sign out).
* **Environment banners (below top bar):** yellow "SANDBOX - no real money moves" always when `payments_mode = paypal_sandbox`; "SIMULATED PAYMENTS" for mock; purple "SIMULATED AI" when `ai_mode = mock`.
* **Left nav (>= 1024 px):** Dashboard, Projects, Notifications. On mobile: bottom tab bar (Dashboard, Projects, Alerts, Profile).
* **Project page tabs:** Overview - Agreement - Milestones - Payments - Activity.
* **Footer:** honesty disclaimer + links (GitHub, docs).

### Route map
| Route | Page | Auth |
|---|---|---|
| `/` | Landing (value prop, "Get started", demo accounts hint in non-prod) | public |
| `/login`, `/register` | Auth pages | public |
| `/invite/:token` | Invitation preview + accept | public preview, login to accept |
| `/dashboard` | Dashboard | yes |
| `/projects/new` | New project wizard | yes |
| `/projects/:id` | Project Overview | member |
| `/projects/:id/agreement` | Agreement view/editor/review | member |
| `/projects/:id/milestones/:mid` | Milestone detail | member |
| `/projects/:id/payments` | Payment ledger | member |
| `/projects/:id/activity` | Audit timeline | member |
| `/payments/return`, `/payments/cancel` | PayPal return handlers | client |
| `/notifications` | Notification list | yes |
| `/profile` | Name, PayPal email | yes |
| `*` | 404 | - |

## 4. Pages in detail

### 4.1 Landing `/`
Hero: tagline, 3-step "Describe -> Agree -> Deliver & Pay" illustration (CSS/SVG), CTA "Start a project". Section: "How AI helps" (agreement, evaluation) and "How payments work" (PayPal, you approve each payment). Honesty strip. No fake testimonials or logos.

### 4.2 Login / Register
Single-column card; inline validation; password visibility toggle; errors from `error.message`; link between pages; after login redirect to `?next=` or `/dashboard`.

### 4.3 Dashboard
Layout (desktop): 4 stat cards -> two columns.
* **Stat cards:** Active projects - Milestones due in 7 days - Awaiting my action - Paid to date.
* **Needs your action** (list with CTA buttons, e.g., "Review submission", "Pay $300.00").
* **Upcoming deadlines** (milestone, project, due date, overdue in red).
* **Projects** (cards: title, role chip, counterparty, progress bar milestones paid/total, next due, status badge).
* **Recent payments** (compact table).
* **AI summary card (P1)** for the selected/most recent active project: headline, progress, risks, next actions; "Refresh" button; `AiChip`.
States: loading skeletons (4 stat + 3 cards); empty ("No projects yet - describe your first project" + CTA); error with retry.

### 4.4 New Project wizard `/projects/new` (client)
Step 1 **Describe**: title, large brief textarea (counter 40-8000), helper text with example, optional "Use sample brief" button (non-prod). Button "Analyze with AI".
Step 2 **Clarify**: AI summary of understood requirements (chips) + question cards (severity colour); answer textareas; "Skip questions". Loading state: stepper animation "Reading your brief... Finding gaps...". Also fields: total budget (prefilled if detected) and target end date.
Step 3 **Draft**: "Generate agreement" -> navigates to Agreement editor. If AI fails: error with "Use template instead" button.

### 4.5 Project Overview
Header: title, status badge, role chip, counterparty, total/paid/remaining. **Milestone stepper** (horizontal on desktop, vertical on mobile) with amount, due date, status. **Next action card** (single primary CTA). **AI summary** panel. Quick links to Agreement and Activity. Invite panel for client while no freelancer: invite form -> shows copyable link with note "Email is not sent in this demo; share the link."

### 4.6 Agreement page (3 modes by status and role)
* **Editor (client, `DRAFT`)**: sections Summary, Scope in/out (editable lists), Assumptions, Payment terms, Revision policy; **Milestones** as expandable cards (title, description, deliverables list, amount, due date, criteria list with add/remove, `verification_method` select, required toggle); live **budget reconciler** ("Allocated $1,150.00 of $1,200.00 - $50.00 unallocated", red until equal) with "Auto-balance" button; AI warnings inline (vague wording); `AiChip` "Drafted by AI - review everything". Buttons: Save (auto-save debounce 800 ms), **Submit for review** (disabled with reasons tooltip).
* **Review (freelancer, `IN_REVIEW`)**: read-only layout, sticky action bar: Approve (confirm dialog shows hash prefix and total) / Request changes (comment modal).
* **Read-only (`APPROVED`)**: approval history panel (who, when, hash), "Agreement hash" `Copyable`.
* **Version history (P1)**: side panel listing versions with status and changed fields.

### 4.7 Milestone detail (core screen)
Header: title, `StatusBadge`, amount, due date. Left column: description, expected deliverables, **Acceptance criteria** (each with verdict chips after evaluation). Right column (role-aware):
* Freelancer, `ACTIVE`/`CHANGES_REQUESTED`: **Submit deliverable** card (`FileDropzone` up to 5 files, note, links), shows client's change-request comment if any.
* After submit: **Submission history** (accordion per `submission_no`: files with download, note, evaluation chip, decision).
* **Evaluation report panel** (Member 2's `EvaluationReportPanel`): states: *Queued/Running* (animated steps, "usually 10-40 s"), *Completed*, *Failed* (retry), *Inconclusive*. Completed layout: overall chip (`MEETS`...), summary, confidence meter (labelled "model confidence, not a guarantee"), **criteria table** (status, reasoning, evidence quotes with "verified" tick and file name, gap), "Missing requirements", "Could not be verified", "Recommended next steps" (tabs: For client / For freelancer), disclaimer, "Evaluation history" dropdown for earlier attempts.
* Client, `SUBMITTED` + evaluation terminal: **Decision card**: "Accept milestone" (primary), "Request changes" (opens comment modal prefilled with AI next steps the client can edit). Copy: "You make the final decision. AI is advisory."
* Client, `ACCEPTED`: **Payment card** (Member 4's `PayMilestoneCard`): amount, "Payee: sandbox merchant (demo)", evidence summary link, button "Pay $300.00 with PayPal", small text "You'll approve this payment on PayPal. Nothing is charged until you approve."

### 4.8 Payment screens (Member 4)
* **Pay card** (above).
* **Redirecting overlay**: "Taking you to PayPal..." with spinner; button to reopen link if popup/redirect blocked.
* **Return page `/payments/return`**: states: *Finalizing payment* (capture in progress) -> *Success* (check animation, amount, PayPal transaction ID `Copyable`, "Back to milestone") | *Pending* ("PayPal is processing; we'll update this automatically", polls payment every 3 s up to 60 s) | *Not approved yet* (button "Return to PayPal") | *Failed* (reason, "Try again").
* **Cancel page**: "Payment cancelled - nothing was charged" + back button.
* **Payment ledger `/projects/:id/payments`**: totals header (Paid, Pending, Remaining); table: milestone, amount, status badge, PayPal order id, capture id, created, completed, "Webhook verified" tick; row expand = event timeline (`payment_events`). Mock payments show a "SIMULATED" tag.

### 4.9 Activity page (trust)
Vertical timeline from `/audit`: icon by actor type (user, AI, PayPal, system), action text, time, details drawer (hash values). Header badge: **"Audit chain verified"** (green) or "Chain check failed" (red). Filters: All / Agreement / Deliverables / Payments.

### 4.10 Notifications
List with unread dot; click navigates to `link` and marks read; "Mark all read".

### 4.11 Invite accept `/invite/:token`
Shows project title, client name, invited email. If logged out: "Log in or register as dev@..." buttons preserving token. If wrong email: explanatory error. On accept -> agreement review page.

### 4.12 Profile
Display name, PayPal email (helper: "Only used if direct payee mode is enabled; in this demo payments go to the sandbox merchant").

## 5. Client vs freelancer experience (summary)

| Moment | Client sees | Freelancer sees |
|---|---|---|
| After project creation | Wizard -> editor | Nothing yet |
| Agreement `IN_REVIEW` | "Waiting for freelancer approval" | Review screen with Approve / Request changes |
| Milestone `ACTIVE` | Waiting card + deadline | Submit deliverable card |
| `SUBMITTED` | Evaluation + Decision card | Evaluation (read-only) + "Awaiting client decision" |
| `CHANGES_REQUESTED` | Waiting for resubmission | Comment + resubmit card |
| `ACCEPTED` | Pay card | "Awaiting payment" |
| `PAID` | Receipt | Receipt + notification |

## 6. Responsive design
Breakpoints: `sm 640`, `md 768`, `lg 1024`, `xl 1280`. Mobile (375 px): single column; tables become stacked cards; sticky bottom action bars; stepper vertical; dropzone becomes "Choose files" button; tap targets >= 44 px. Test widths 375, 768, 1280.

## 7. Loading, error and empty states (required for every page)
| State | Pattern |
|---|---|
| Loading | `Skeleton` shaped like content; no layout shift; AI waits use progress steps and elapsed timer |
| Error | `ErrorState`: message from API, `request_id` in small text with copy, "Retry" |
| Empty | `EmptyState`: icon, one sentence, primary CTA |
| Forbidden / not found | 404 page with "Back to dashboard" |
| Offline / API down | Toast "Can't reach the server" + retry on focus |
| Long AI wait (> 60 s) | Message "Taking longer than usual", option to retry; for evaluation, option to proceed with manual review |

## 8. Accessibility and content
Semantic HTML, labelled inputs, `aria-live` for toasts and AI status, focus trap in modals, keyboard operable stepper/tabs, colour never the only status signal (icon + text), alt text for icons used as content.
Copy rules: sentence case; verbs on buttons ("Submit for review", "Pay $300.00 with PayPal"); money always `$1,200.00`; dates `Nov 10, 2026`.

## 9. Frontend structure and ownership
```
frontend/src/
  main.tsx, App.tsx, routes.tsx                 (Member 3)
  api/ client.ts, schema.d.ts (generated), hooks/*.ts, mocks/*   (Member 3)
  components/ui/*, components/layout/*           (Member 3)
  features/auth/*, dashboard/*, projects/*, agreement/*, milestones/*, notifications/*, activity/*   (Member 3)
  features/payments/*                            (Member 4)  PayMilestoneCard, PaymentReturnPage, PaymentCancelPage, PaymentLedger, PaymentStatusBadge
  features/evaluation/*                          (Member 2) EvaluationReportPanel, CriterionResultRow, EvidenceQuote, EvaluationHistory
  lib/ format.ts, statusStyles.ts, env.ts        (Member 3)
```
Public props contracts for the two foreign features are defined in doc 09 section 6 so Member 3 can mount them with mocks on Day 2.

## 10. Additional status mappings
Deliverable: `SUBMITTED` Submitted (brand) - `EVALUATING` AI reviewing (ai) - `EVALUATED` Ready for decision (brand) - `EVALUATION_FAILED` AI unavailable - retry (danger) - `ACCEPTED` Accepted (success) - `CHANGES_REQUESTED` Needs changes (warning).
Recommendation chip: `MEETS` success - `PARTIALLY_MEETS` warning - `DOES_NOT_MEET` danger - `INCONCLUSIVE` gray.
Payment: `CREATED`/`PENDING_APPROVAL` warning - `APPROVED`/`CAPTURE_PENDING` brand - `COMPLETED` success - `FAILED`/`DENIED` danger - `CANCELLED` gray. Agreement `SUPERSEDED`: gray "Replaced by vN".
