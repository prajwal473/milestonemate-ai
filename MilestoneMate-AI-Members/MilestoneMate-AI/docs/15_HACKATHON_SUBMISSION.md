# 15 - Hackathon Submission

Owner: **Member 1** (Representative, subject to D-02). Contributors: Member 2 (AI text), Member 4 (PayPal text), Member 3 (visuals/video).

## 1. Verified hackathon facts (fetched Nov 1, 2026 from the official page and Official Rules)

| Item | Verified content | Source |
|---|---|---|
| Name / host | PayPal AI Hackathon, sponsor PayPal Inc., administered by Devpost | Rules s.2 |
| Submission period | Oct 1, 2026 9:15 AM PT -> **Nov 12, 2026 12:00 PM PT** (= Nov 13, 01:30 IST) | Rules s.1 |
| Judging period | Dec 1, 2026 2:00 PM PT -> Dec 15, 2026 8:00 AM PT; winners on/around Dec 21 | Rules s.1 |
| Core requirement | Build/update an app that **meaningfully integrates PayPal developer platform (free sandbox)** and **meaningfully uses AI** (any AI tool; sponsor tools optional) with PayPal central | Overview, Rules s.4 |
| Project requirements | Meaningful PayPal + AI; working prototype; sufficiently documented; complies with Rules | Overview |
| New vs existing | New, or existing but significantly updated during the period (explain how) | Rules s.4 |
| Submission contents | Text description; functional demo (hosted URL **or** complete setup/run instructions in repo; mockups/static prototypes do not count); tools used + how; public repo (GitHub/GitLab/Bitbucket) with all source/assets/instructions; **open-source license file visible in About**; demo video | Rules s.4 |
| Video | < 3 minutes; shows project functioning on the device it was built for; **public on YouTube**; link on submission form; no third-party trademarks or copyrighted music/material without permission | Rules s.4 |
| Testing access | Free, unrestricted access for Sponsor/Administrator/Judges until judging ends; private sites need credentials; judges may judge from text/images/video only | Rules s.4 |
| Language | English (or English translation) | Rules s.4 |
| Team | One authorized Representative submits for the team; all members eligible; Representative receives prize and allocates | Rules s.3-4, 8 |
| Eligibility | Age of majority; excluded: residents of Brazil, Quebec, Russia, Crimea, Cuba, Iran, North Korea and other OFAC-sanctioned places; employees/affiliates of Sponsor/Administrator/judges | Rules s.3 |
| Judging | Stage 1 pass/fail viability (fits theme, reasonably applies required APIs); Stage 2 equally weighted: Technological Implementation, Design, Potential Impact, Innovation/Idea, Presentation. Judging may include "automated AI-driven analysis" | Rules s.6 |
| Prizes relevant to us | 1st $12,000; 2nd $8,000; 3rd $5,000; Most Creative, Most Impactful, Best Demo Delivery, **Best Use of PayPal + AI**, **Best Use of Agentic Commerce** $5,000 each; sponsor prizes incl. Render credits. A project wins at most one Grand/Honorable prize plus one Sponsor prize | Rules s.8 |
| IP/publicity | Entrant keeps IP; Sponsor gets non-exclusive license to judge; name/likeness may be used for promotion | Rules s.7, 10 |

## 2. Could not be verified (need a human)

1. The exact **Devpost submission form fields** (visible only after login/registration): e.g., required images, "Built with" tags, team-member invitations, character limits.
2. Whether the Devpost page has **team size limits** (not stated in Rules).
3. **Definition of "Agentic Commerce"** for the honorable-mention prize: not defined in the Rules. Our interpretation (stated in this doc, section 5.4) is an assumption.
4. Whether **using Render** (or any sponsor tool) is judged for the Render sponsor prizes beyond hosting: Rules say "all eligible submissions that use any Render tools"; sponsor page mentions Render Workflows. Not verified.
5. Whether all team members' countries/residences are eligible (Rules exclude specific places; India is not listed in the text fetched, but each member must confirm personally).
6. The prize pool figure differs on the page ($67,500 vs "$69,750"): irrelevant to the build; ignore.
7. Whether PayPal screens in the video count as "third-party trademarks" (PayPal is the sponsor; the rule targets other parties' marks/music). Low risk; confirm via the hackathon manager if desired (email link on the Devpost page).
8. PayPal API details marked **VERIFY** in doc 07 (payee override, response paths, simulator behaviour).

## 3. Devpost text (draft, edit after Day 9)

### Project name
MilestoneMate AI

### Tagline
From Project Agreement to Milestone Payment.

### Elevator pitch (<= 200 chars)
AI turns a project brief into an editable, dual-approved agreement, checks deliverables against agreed criteria, and the client pays each accepted milestone through PayPal - all on an auditable timeline.

### Problem statement
Freelance projects fail on unclear scope, subjective acceptance and awkward payment timing. Clients fear paying for the wrong thing; freelancers fear unpaid work. Neither side has a neutral record of what was agreed, delivered and paid.

### Solution
MilestoneMate AI converts a natural-language brief into a structured agreement (requirements, clarifying questions, milestones, budget split, deadlines, acceptance criteria). Both parties approve the same content-hashed version. The freelancer submits work per milestone; an AI evaluator compares it with each criterion and reports evidence, gaps and next steps; the client makes the final decision; accepted milestones are paid through PayPal Sandbox with explicit client authorization and verified webhooks. Dashboard, audit trail and AI summaries keep both sides aligned.

**What it is not:** not a legal escrow service and not legal advice; PayPal is not holding funds against milestones. Sandbox only.

### Innovation
1. Acceptance criteria as machine-checkable first-class objects.
2. Evidence-verified AI evaluation (quotes are checked against the submission; the final label is computed by rules, not by the model).
3. Hash-bound dual approval and a hash-chained audit log.
4. An agentic pipeline (clarify -> draft -> evaluate -> summarize -> payment proposal) whose last step is always human + PayPal authorization.

### Technology stack
React 18, Vite, TypeScript, Tailwind CSS; Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16; Gemini API (structured JSON output) with provider abstraction and mock mode; PayPal Sandbox (OAuth2, Orders v2, Webhooks with signature verification); Render; GitHub Actions.

### PayPal integration explanation (Member 4 finalizes)
OAuth2 client-credentials token cache; **Orders v2** `intent=CAPTURE` created server-side with the amount from the database and a `PayPal-Request-Id`; buyer approval on PayPal via the `payer-action` link; server-side capture only after the client returns and the order is `APPROVED`; `PAYMENT.CAPTURE.*` and `CHECKOUT.ORDER.APPROVED` webhooks verified through PayPal's verify-webhook-signature API, deduplicated and reconciled by re-reading PayPal state; payment state machine, idempotency keys and DB constraints prevent duplicate charges; full ledger of payment events. In this MVP, sandbox payments are received by a configured sandbox merchant (see limitations).

### AI integration explanation (Member 2 finalizes)
Three schema-constrained LLM agents (Clarifier, Agreement Drafter, Deliverable Evaluator) plus a summarizer. Outputs are validated with Pydantic, repaired by deterministic post-processing (budget sums, dates, criteria lint), and evaluations are made trustworthy by quote verification and rule-based recommendations. Prompts treat submissions as untrusted data; the AI cannot change statuses or access payment code. Failures degrade to a template agreement or labelled mock mode.

### Challenges / limitations (be honest)
Sandbox-only; single configured payee in `demo_merchant` mode (production would require PayPal multiparty onboarding); AI sees extracted text only; no email delivery; no refunds/disputes UI.

### What's next
Marketplace payouts via PayPal's multiparty products, change orders, richer evaluators (code, design), dispute assistance, PayPal Agent Toolkit integration.

### How the project was built during the period
Project started Nov 1, 2026 from scratch (confirm D-12: no pre-existing code). Commit history in the public repo shows the timeline.

## 4. Open-source license recommendation
**MIT** (included on Day 1): simple, permissive, widely accepted by hackathons; the Rules only require "an open source license file" visible in the repo's About section. Alternative: **Apache-2.0** if the team wants an explicit patent grant. Do not mix incompatible licensed code; list third-party libraries and their licenses in README "Acknowledgements". Add `LICENSE` at repo root and make sure GitHub's About panel shows "MIT license" (GitHub detects it automatically).

## 5. Competitive positioning (not guarantees)

### 5.1 Technological Implementation
Real Orders v2 + webhooks + idempotency; non-trivial AI with verification layer; test suite and CI.
### 5.2 Design
Complete flows with states, responsive UI, status clarity, trust cues.
### 5.3 Potential Impact
Concrete user (freelancers + small clients), measurable pain (disputes), simple adoption (browser + PayPal).
### 5.4 Innovation / "Best Use of Agentic Commerce" (assumption)
We interpret agentic commerce as AI agents that plan and prepare commercial actions on behalf of people, with proper authorization. Our agents scope the deal, assess fulfilment and prepare a payment proposal; the human authorizes via PayPal. If judges expect autonomous agent-initiated payments, we deliberately differ for safety. **Do not claim** PayPal Agent Toolkit/MCP usage unless it is actually integrated.
### 5.5 Presentation
Scripted <3-minute video (doc 16), live hosted demo, clear README.

## 6. Prize strategy notes
Primary targets: Grand Prizes, Best Use of PayPal + AI, Most Creative, Best Demo Delivery. Optional sponsor prizes: **Render** (host on Render; consider Render Workflows only if time allows - not in MVP). AG Grid would be a cheap fit for the payment ledger/audit tables but adds a dependency: decision D-10 (default: no). Do not distort the product to chase sponsor prizes.

## 7. Submission checklist (use on Day 9-11)

**Repository**
- [ ] Public on GitHub; `LICENSE` detected and visible in About
- [ ] README: description, honesty statement, architecture, **run instructions** (< 10 min, mock modes), demo accounts, env vars, how to get PayPal sandbox creds, Gemini key, tests, limitations, docs links
- [ ] No secrets in current tree or history (gitleaks clean); `.env.example` complete
- [ ] All source, assets and instructions present; tag `v1.0`
**Demo**
- [ ] Hosted URL live and tested from a clean browser/incognito; demo credentials in the submission text (the Rules require login credentials if private)
- [ ] Mock modes verified so judges can test without keys
- [ ] Hosted instance stays up until Dec 15, 2026
**Video**
- [ ] < 3:00 (target 2:45-2:55); shows working project end-to-end; recorded from the real app
- [ ] Public on YouTube (not private/unlisted-only); no third-party trademarks/music (use no music or royalty-free with license)
- [ ] English narration/captions
**Devpost form**
- [ ] Project name, tagline, description (features and functionality), problem/solution
- [ ] Tools used and how (PayPal APIs; Gemini; others)
- [ ] Repo URL, demo URL, YouTube URL, test instructions
- [ ] Images/gallery + thumbnail; "built with" tags
- [ ] Team members added; Representative submitting
- [ ] "How project was updated/created during the period" statement
- [ ] Submitted (not just draft) **by Wed Nov 11 22:00 IST**; confirmation screenshot saved
**Verification (incognito)**
- [ ] Devpost project page public and links work; YouTube plays without login; repo accessible; hosted app loads; README steps verified by a teammate who did not write them

## 8. Final-day timeline (IST)
Nov 11: 12:00 video export -> 14:00 YouTube upload -> 16:00 Devpost complete -> 18:00 teammate review -> **22:00 submit**. Nov 12 (all day) and until 01:30 IST Nov 13: emergency buffer only (the deadline is Nov 12 12:00 PT).
