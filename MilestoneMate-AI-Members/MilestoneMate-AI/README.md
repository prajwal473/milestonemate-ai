# MilestoneMate AI

> **From Project Agreement to Milestone Payment.**

MilestoneMate AI is an AI-powered freelance **project agreement and payment coordination** platform built for the [PayPal AI Hackathon 2026](https://paypalaihackathon.devpost.com/).

A client describes a project in plain language. The AI turns it into a structured, **editable** agreement with milestones, budget allocation, deadlines and testable acceptance criteria. Both parties approve the exact same version. The freelancer submits deliverables, the AI produces an **evidence-based evaluation report** against the agreed criteria, and the **client makes the final decision**. Accepted milestones are paid through **PayPal (Orders API, sandbox)** with explicit client authorization, verified webhooks and a tamper-evident audit trail.

> ### Important honesty statement
> MilestoneMate AI is **not a legal escrow service** and does **not** claim that PayPal holds funds until milestones are completed.
> Each milestone payment is a separate PayPal order that the **client personally approves** and that is **captured only after the client has accepted the work**. The AI never approves work and never captures a payment.
> This project runs against the **PayPal Sandbox only**. No real money moves.

---

## Status

| Item | State |
|---|---|
| Planning documentation (`/docs`, `/team`) | Complete |
| Application code | Not started — implementation pending. Follow [`START_HERE.md`](START_HERE.md) and the execution roadmap. |
| Hackathon deadline | **Thu Nov 12, 2026, 12:00 PM PT** (= Fri Nov 13, 01:30 IST). Internal submission target: **Wed Nov 11, 22:00 IST** |

The quick-start commands below become usable after the corresponding application files have been implemented. They are planned commands, not evidence that the application already exists.

## Key features

| Area | What it does |
|---|---|
| AI agreement generator | Natural-language brief -> extracted requirements -> missing-information questions -> structured agreement, milestones, budget split, deadlines, acceptance criteria |
| Collaboration | Client/freelancer roles per project, invite link, agreement review, **dual approval bound to a content hash** |
| AI deliverable evaluation | Upload files -> text extraction -> per-criterion verdict with **verified evidence quotes**, missing requirements, next steps. Advisory only |
| PayPal payments | Sandbox Orders API: create order -> buyer approval -> capture -> verified webhooks -> payment ledger. Idempotent |
| Dashboard | Active projects, milestones, deadlines, deliverable status, payment history, notifications, AI project summaries |
| Trust & transparency | Agreement versions, approval history, evaluation history, payment audit trail, hash-chained audit log |

## Architecture at a glance

```
React + Vite + TS + Tailwind  --REST/JSON-->  FastAPI (modular monolith)  --SQL-->  PostgreSQL
                                                 |-- ai/        -> Gemini (or Claude) with schema-validated JSON
                                                 |-- payments/  -> PayPal Sandbox (Orders v2, Webhooks)
```

Full detail: [`docs/03_SYSTEM_ARCHITECTURE.md`](docs/03_SYSTEM_ARCHITECTURE.md).

## Quick start *(available after Day 1)*

### Prerequisites
Python 3.12, Node.js 20+, Docker (for PostgreSQL), Git.

### 1. Clone and configure
```bash
git clone <REPO_URL> MilestoneMate-AI && cd MilestoneMate-AI
cp .env.example .env          # then edit values; NEVER commit .env
```

### 2. Fastest path - no external credentials needed
Set in `.env`:
```
AI_MODE=mock
PAYMENTS_MODE=mock
```
Mock modes are clearly labelled in the UI ("SIMULATED"). They exist so judges can run the full workflow offline.

### 3. Start the database, backend and frontend
```bash
docker compose up -d db
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python -m scripts.seed_demo                             # demo users + sample data
uvicorn app.main:app --reload --port 8000
# new terminal
cd frontend && npm ci && npm run dev                    # http://localhost:5173
```

### 4. Demo accounts (seeded, sandbox/demo only)
| Role | Email | Password |
|---|---|---|
| Client | `client@demo.milestonemate.test` | `Demo-Client-123!` |
| Freelancer | `freelancer@demo.milestonemate.test` | `Demo-Freelancer-123!` |

### 5. Real integrations (optional)
* **Gemini**: create a key at Google AI Studio -> set `AI_MODE=live`, `LLM_PROVIDER=gemini`, `GEMINI_API_KEY`, `GEMINI_MODEL`.
* **PayPal Sandbox**: follow [`docs/07_PAYPAL_INTEGRATION.md`](docs/07_PAYPAL_INTEGRATION.md) -> set `PAYMENTS_MODE=paypal_sandbox`, `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID`.

## Documentation index

| # | Document |
|---|---|
| 01 | [Project Overview](docs/01_PROJECT_OVERVIEW.md) |
| 02 | [Product Requirements](docs/02_PRODUCT_REQUIREMENTS.md) |
| 03 | [System Architecture](docs/03_SYSTEM_ARCHITECTURE.md) |
| 04 | [Database Design](docs/04_DATABASE_DESIGN.md) |
| 05 | [API Specification](docs/05_API_SPECIFICATION.md) |
| 06 | [AI Agent Design](docs/06_AI_AGENT_DESIGN.md) |
| 07 | [PayPal Integration](docs/07_PAYPAL_INTEGRATION.md) |
| 08 | [UI/UX Specification](docs/08_UI_UX_SPECIFICATION.md) |
| 09 | [Team Work Division](docs/09_TEAM_WORK_DIVISION.md) |
| 10 | [Development Workflow](docs/10_DEVELOPMENT_WORKFLOW.md) |
| 11 | [11-Day Execution Roadmap](docs/11_DAY_EXECUTION_ROADMAP.md) |
| 12 | [Testing Strategy](docs/12_TESTING_STRATEGY.md) |
| 13 | [Deployment Guide](docs/13_DEPLOYMENT_GUIDE.md) |
| 14 | [Security & Privacy](docs/14_SECURITY_AND_PRIVACY.md) |
| 15 | [Hackathon Submission](docs/15_HACKATHON_SUBMISSION.md) |
| 16 | [Demo Script](docs/16_DEMO_SCRIPT.md) |
| 17 | [Risk Register](docs/17_RISK_REGISTER.md) |

Personal task files: [`team/MEMBER_1_TASKS.md`](team/MEMBER_1_TASKS.md) - [`team/MEMBER_2_TASKS.md`](team/MEMBER_2_TASKS.md) - [`team/MEMBER_3_TASKS.md`](team/MEMBER_3_TASKS.md) - [`team/MEMBER_4_TASKS.md`](team/MEMBER_4_TASKS.md)

## Team

| Member | Primary ownership |
|---|---|
| **Member 1** | Tech lead - backend platform, database, auth, workflow engine, integration, releases, deployment |
| **Member 2** | AI engineering - agreement generation, deliverable evaluation, summaries, extraction, AI quality |
| **Member 3** | Frontend architecture and UI/UX - app shell, design system, all pages except payment/evaluation components |
| **Member 4** | PayPal integration, payment workflows, webhooks, QA and end-to-end testing |

## License
MIT - see [`LICENSE`](LICENSE).
