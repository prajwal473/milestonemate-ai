# 16 - Demo Script (3-minute video, target 2:50)

Presenter/narrator: **Member 4**. Operator (driving the screen): **Member 3**. Format: 1080p screen recording, two browser windows (Client = Maya, Freelancer = Dev), PayPal sandbox buyer pre-logged-in, voice-over, light captions, **no music** (avoids copyright issues). Record in segments, then edit to < 3:00.

## 1. Sample project (seeded data and fixtures)
**"Ember & Oak" coffee subscription launch** - client Maya Rao (small roaster) hires freelancer Dev Patel.
Brief (pasted live; ~60 words): *"We're a small coffee roaster launching a monthly subscription. We need brand voice and landing-page copy, a one-page responsive landing site with an email signup form, and launch QA. Budget about $1,200, launch in three weeks."*
Expected AI output: 3 milestones - (1) Brand voice and landing copy $300, (2) Responsive landing page $600, (3) Launch QA and handoff $300. Milestone 1 criteria (examples): hero headline, subhead and CTA text; brand voice guide with >= 3 tone rules; FAQ with >= 5 questions; sitemap listing sections; product descriptions for 3 blends.
Fixtures: `demo-m1-v1.md` (CTA text missing) and `demo-m1-v2.md` (complete).

## 2. Timeline and narration

| Time | Screen | Action (operator) | Narration (presenter) |
|---|---|---|---|
| 0:00-0:15 | Title card -> landing page | Show tagline | "Freelance projects break on vague scope and awkward payments. MilestoneMate AI turns promises into trackable, PayPal-powered milestones." |
| 0:15-0:40 | Client: New project | Paste brief; click *Analyze*; show requirement chips and 2 clarifying questions; answer budget/timeline question quickly (prefilled) | "Maya pastes her idea. The AI extracts requirements and asks only what's missing." |
| 0:40-1:00 | Agreement editor | Click *Generate*; show 3 milestones, amounts, dates, criteria; edit one amount; reconciler turns red then green | "In seconds she has milestones, a budget split, deadlines and testable acceptance criteria - and she can edit everything." |
| 1:00-1:15 | Invite + Freelancer window | Copy invite link, switch to Dev, open link, show review page, click *Approve*; show approval hash and history | "Both sides approve the same hashed version. Nothing is final until they agree." |
| 1:15-1:35 | Freelancer: Milestone 1 | Upload `demo-m1-v1.md`; show *evaluating*; AI report appears: 4/5 criteria met, CTA missing with evidence quotes | "Dev submits work. The AI checks every criterion and shows verified evidence - here, the CTA text is missing." |
| 1:35-1:50 | Client window | Show report; click *Request changes* (prefilled from AI next steps). Cut to Dev uploading `demo-m1-v2.md` (pre-recorded clip, 5 s) -> report: all criteria met | "The AI advises; Maya decides. After the fix, every criterion is met." |
| 1:50-2:00 | Client | Click *Accept milestone* | "Maya accepts. The AI never approves work for her." |
| 2:00-2:30 | Pay card -> PayPal sandbox -> return | Click *Pay $300.00 with PayPal*; PayPal sandbox approve; return page shows *Paid*, transaction ID; ledger shows webhook verified tick | "Payment is a real PayPal Sandbox order that Maya approves herself. We capture only after her approval, protect against double charges, and verify PayPal's webhook." |
| 2:30-2:50 | Dashboard + Activity | Dashboard: progress 1/3, AI summary card; open Activity: timeline with *Audit chain verified* | "Everything is on one auditable timeline: agreement versions, approvals, AI evaluations, and payments." |
| 2:50-3:00 | End card | Tagline + repo/demo URL | "MilestoneMate AI. Not escrow - just clear agreements, honest AI, and payments both sides can trust." (target finish <= 2:58) |

Timing tip: if over 3:00, shorten 1:35-1:50 (use only the pre-recorded clips) and 2:30-2:50 (skip the AI summary).

## 3. Detailed demonstration sequence (operator checklist)
1. Windows: Chrome profile A (Maya), profile B (Dev), PayPal sandbox buyer logged in profile A. Zoom 110%. Notifications off.
2. Run `seed_demo --reset-demo` (clears the Ember & Oak project, keeps users).
3. Confirm banners show **SANDBOX**; AI mode live.
4. Take 1 = full run; Take 2 = full run; keep best segments. Always record the PayPal segment separately.
5. After recording: save raw footage and note timestamps.

## 4. What to say (and not say)
Say: "sandbox", "client approves each payment", "AI is advisory", "audit trail". Do **not** say: "escrow", "funds are held/protected until you approve", "guaranteed", "legally binding". The word "Protected" in the tagline refers to process protection; if asked, clarify verbally in the Q&A/README.

## 5. Backup demonstration plan

| Failure | Backup |
|---|---|
| LLM slow/down | Flip `AI_MODE=mock` (banner "SIMULATED AI"); mock fixtures give identical flow. For the video, prefer a pre-recorded live-AI take of generation and evaluation |
| PayPal sandbox slow/down | Use pre-recorded PayPal segment (best of 3 earlier takes); or `PAYMENTS_MODE=mock` and state "simulated checkout" in narration/caption |
| Hosted site down | Run locally (README steps) in mock modes; video shows localhost |
| Webhook not arriving during recording | Click *Sync* (reconciliation) on the payment; or show a previously verified webhook row and say so |
| Presenter error | Segmented recording; edit with cut-aways |
| Complete failure at submission time | Submit the pre-recorded video; README's mock mode guarantees judges can still run it |

## 6. Rehearsal and acceptance
Three timed rehearsals (Day 10); acceptance = < 3:00 including voice-over, no unexplained waits > 3 s (cut or speed up), every judging criterion visibly addressed: Tech (PayPal flow, AI), Design (UI), Impact (problem statement), Innovation (evidence-verified evaluation, hash approvals), Presentation (clear narration).
Upload: YouTube **public**; title "MilestoneMate AI - PayPal AI Hackathon demo"; description with repo and demo links; captions on.
