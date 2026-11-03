# 01 - Project Overview

| | |
|---|---|
| **Project** | MilestoneMate AI |
| **Tagline** | From Project Agreement to Milestone Payment. |
| **Event** | PayPal AI Hackathon 2026 (Devpost) |
| **Team** | Member 1, Member 2, Member 3, Member 4 |
| **Build window** | 11 days: Sun Nov 1 -> Wed Nov 11, 2026 (Devpost deadline Thu Nov 12, 12:00 PT = Fri Nov 13, 01:30 IST) |

---

## 1. Problem statement

Freelance and small-agency work still starts with a vague chat thread and ends with a payment dispute.

* **Vague scope.** Clients describe what they want in a paragraph. Freelancers interpret it differently. Nobody writes down what "done" means.
* **Unstructured payments.** Payment is either 100% upfront (the client carries all the risk) or 100% on delivery (the freelancer carries all the risk).
* **Subjective acceptance.** Reviewing a deliverable against a mental checklist produces disagreement ("that's not what I asked for" / "that's exactly what you asked for").
* **No shared record.** When a disagreement happens, neither party has a neutral, timestamped record of what was agreed, what was submitted and what was paid.

Existing options are either heavyweight (contracts, lawyers), generic (invoice tools that do not understand scope) or platform-locked (marketplaces that take a large commission and own the relationship).

## 2. Target users

| Persona | Description | Core pain | What they get |
|---|---|---|---|
| **Client** (primary) | Founder, small business owner or team lead hiring an independent professional for a bounded project ($200 - $10,000) | Fear of paying for work that does not match the brief; does not know how to write a scope | A clear agreement in minutes, objective review support, payment only after their own acceptance |
| **Freelancer** (primary) | Independent designer, developer, writer, marketer | Scope creep, delayed or disputed payment, unpaid revisions | A written agreement both parties approved, defined acceptance criteria, predictable milestone payments |
| **Agency PM** (secondary) | Coordinates several freelancers | Tracking many milestones and payments | Dashboard of deadlines, statuses and payment history |

## 3. Proposed solution

MilestoneMate AI is a **project agreement and payment coordination layer** around PayPal:

1. **Describe** - the client writes the project in natural language.
2. **Clarify** - the AI extracts requirements and asks for missing information (budget, deadline, format, revision limits).
3. **Agree** - the AI drafts an editable agreement: scope, milestones, budget allocation, realistic deadlines, testable acceptance criteria. Both parties approve the same content-hashed version.
4. **Deliver** - the freelancer uploads work per milestone.
5. **Evaluate** - the AI compares the submission with each acceptance criterion and produces an evidence-based report with gaps and next steps. **It is advisory only.**
6. **Decide** - the client accepts or requests changes.
7. **Pay** - for an accepted milestone the client authorizes a PayPal payment (Orders API). A verified webhook confirms the capture and the ledger and audit trail update.

### What MilestoneMate is **not**
* **Not a legal escrow service.** PayPal is not holding funds against milestones. We make no such claim anywhere in the UI, README, video or Devpost text.
* **Not a legal contract generator.** The agreement is a structured project record; the UI states it is not legal advice.
* **Not an autonomous payment agent.** The AI proposes and explains; humans authorize. The AI package has no access to payment code (enforced by an automated test, see doc 12).

## 4. Product vision

Make *"what was promised"*, *"what was delivered"* and *"what was paid"* a single, shared, verifiable timeline for any small project. Long term: pluggable evaluators (code, design, copy), payouts through PayPal marketplace products, dispute assistance, recurring retainers. None of that is in the MVP.

## 5. Unique selling proposition

> **The freelance workflow where the AI writes the agreement, checks the work against it, and a human-authorized PayPal payment closes the loop, with every step on an auditable timeline.**

## 6. Key differentiators

| # | Differentiator | Why it matters |
|---|---|---|
| 1 | **Acceptance criteria are first-class and checkable** | Turns "is it done?" from opinion into a checklist with evidence |
| 2 | **Evidence-verified AI evaluation** | Every quote the AI cites is programmatically checked against the submitted text; unverifiable quotes are stripped. The overall recommendation is computed by deterministic rules from criterion results, not trusted from the model |
| 3 | **Human-in-the-loop by construction** | AI never approves work or moves money. Client accepts, client authorizes the PayPal approval |
| 4 | **Agreement hash approvals** | Approvals are bound to a SHA-256 of the exact agreement content; any edit invalidates approvals |
| 5 | **Idempotent, webhook-verified payments** | Double-clicks, retries and out-of-order webhooks cannot double-charge or corrupt state |
| 6 | **Hash-chained audit log** | Tamper-evident history the UI can verify |
| 7 | **Agentic workflow ending in a payment *proposal*** | Multi-step agent pipeline (clarify -> draft -> evaluate -> summarize -> propose payment) ending in a human + PayPal authorization step |
| 8 | **Graceful degradation** | `AI_MODE=mock` and `PAYMENTS_MODE=mock` guarantee a working demo if an external API fails |

## 7. Alignment with the hackathon (verified against the official page and rules)

Source of truth: <https://paypalaihackathon.devpost.com/> and its Official Rules (fetched Nov 1, 2026). See [doc 15](15_HACKATHON_SUBMISSION.md) for the full verified-requirements table.

| Judging criterion (equally weighted, Official Rules s.6) | How MilestoneMate addresses it |
|---|---|
| Technological Implementation | Real PayPal Orders v2 + OAuth + webhook signature verification + idempotency; schema-validated LLM pipeline with evidence verification |
| Design | Complete product: auth, dashboard, agreement editor, evaluation report, payment flow, activity trail, responsive, with loading/error/empty states |
| Potential Impact | Specific audience (freelancers + small clients), specific pain (scope and payment disputes) |
| Innovation/Idea | Criteria-driven AI evaluation + hash-bound approvals + human-authorized agentic payment proposal |
| Presentation | Scripted sub-3-minute end-to-end demo ([doc 16](16_DEMO_SCRIPT.md)) |

Prize targets (not guarantees): Grand Prizes (1st/2nd/3rd), Most Creative, Most Impactful, Best Demo Delivery, **Best Use of PayPal + AI**, **Best Use of Agentic Commerce**. The Official Rules do not define "agentic commerce"; our interpretation is stated in doc 15 and flagged as a team assumption. Sponsor prizes (e.g., Render) are optional and noted in docs 13 and 15.

## 8. MVP scope (11 days, 4 developers)

**In scope (P0, must work end-to-end):**
* Email/password auth; per-project roles (client, freelancer)
* Create project from natural-language brief
* AI clarification questions + AI-generated agreement with milestones, budgets, deadlines, acceptance criteria
* Manual editing of every AI-generated field
* Freelancer invitation by link; agreement review; dual approval with content hash; revision versions
* Deliverable upload (text-extractable files) per milestone; submission history
* AI evaluation report; client decision (accept / request changes)
* PayPal Sandbox: create order -> buyer approval -> capture -> webhook verification -> ledger
* Dashboard: projects, milestones, deadlines, deliverable status, payment history, notifications
* Audit trail: agreement versions, approvals, evaluations, decisions, payments
* Mock fallback for AI and PayPal; seed script; README run instructions; Render deployment

**P1 (build if P0 is green by end of Day 6):** AI project summaries, dashboard "needs your action", hash-chain verification badge, agreement version history view, payment reconciliation/sync endpoint, evidence-verification display, image deliverables (multimodal).

## 9. Features excluded from the MVP

| Excluded | Reason |
|---|---|
| Legal escrow / holding funds | Not offered by this architecture; legal and regulatory scope |
| Real money / PayPal Live | Hackathon requires the free sandbox |
| Paying arbitrary third-party freelancers via PayPal Commerce Platform | Requires partner onboarding and `PayPal-Auth-Assertion`; too heavy for 11 days. MVP uses `PAYEE_MODE=demo_merchant` unless the Day-1 spike proves `direct_payee` works (see doc 07) |
| Refund / dispute flows | Webhooks are logged but no UI action |
| Change orders after approval | Approved agreement is immutable; new scope = new project in MVP |
| Email delivery | Invite links are copied in the UI; in-app notifications only |
| Multi-currency | USD only (sandbox default) |
| Freelancer-initiated projects | Client creates projects |
| Real-time websockets | 2-15 s polling is sufficient |
| Fetching/crawling links submitted as deliverables | SSRF and time risk; links are stored, not fetched |
| Legal contract templates / e-signature | Out of scope; disclaimers shown |
