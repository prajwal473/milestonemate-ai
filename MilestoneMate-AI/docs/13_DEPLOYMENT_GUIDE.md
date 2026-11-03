# 13 - Deployment Guide

Owner: **Member 1**. Target: **Render** (a hackathon sponsor: the Devpost Render page offers $50 credits and lists Render Workflows; using Render is optional and Render prizes require "using Render tools" - confirm requirements on the sponsor page, decision D-09). Everything also runs locally with Docker for judges.

## 1. Environment preparation

| Tool | Version |
|---|---|
| Python | 3.12 |
| Node.js | 20 LTS or newer |
| Docker + Compose | recent |
| Git | recent |
| Accounts | GitHub, Render, Google AI Studio (Gemini), PayPal Developer, YouTube |

## 2. Local development

```bash
git clone <repo> && cd MilestoneMate-AI
cp .env.example .env                       # edit; never commit
docker compose up -d db                    # postgres:16 on localhost:5432
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m scripts.seed_demo                # demo users + data
uvicorn app.main:app --reload --port 8000  # http://localhost:8000/docs
cd ../frontend
npm ci
npm run gen:api                            # types from running backend
npm run dev                                # http://localhost:5173
```
`docker-compose.yml` (Member 1, Day 1):
```yaml
services:
  db:
    image: postgres:16
    environment: { POSTGRES_USER: mm, POSTGRES_PASSWORD: mm, POSTGRES_DB: milestonemate }
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck: { test: ["CMD-SHELL", "pg_isready -U mm -d milestonemate"], interval: 5s, retries: 10 }
volumes: { pgdata: {} }
```
Local `DATABASE_URL=postgresql+psycopg://mm:mm@localhost:5432/milestonemate`.
Webhook testing locally: `cloudflared tunnel --url http://localhost:8000` (or ngrok) and register `<tunnel>/api/webhooks/paypal`.

## 3. Database setup
* Local: `alembic upgrade head` (+ optional seed).
* Render: managed PostgreSQL instance; use the **internal** connection string for the backend. Migrations run automatically on deploy (below). Back up before the final release (`pg_dump` via Render shell or dashboard export).
* Check the Render Postgres plan's retention/expiry rules for the free tier **before** relying on it through Dec 15 (VERIFY on Render docs; the $50 credits can fund a paid instance).

## 4. Backend deployment (Render web service)

`render.yaml` (Blueprint; Member 1 Day 6; adjust names/plans):
```yaml
databases:
  - name: milestonemate-db
    plan: basic-256mb            # VERIFY plan names/prices in Render docs
    databaseName: milestonemate
services:
  - type: web
    name: milestonemate-api
    runtime: python
    rootDir: backend
    plan: starter                # avoids free-tier spin-down during judging (VERIFY)
    buildCommand: pip install -r requirements.txt
    preDeployCommand: alembic upgrade head
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /api/health
    envVars:
      - key: DATABASE_URL
        fromDatabase: { name: milestonemate-db, property: connectionString }
      - key: APP_ENV
        value: staging
      - { key: JWT_SECRET, generateValue: true }
      - { key: CORS_ORIGINS, sync: false }
      - { key: FRONTEND_BASE_URL, sync: false }
      - { key: APP_BASE_URL, sync: false }
      - { key: AI_MODE, value: live }
      - { key: LLM_PROVIDER, value: gemini }
      - { key: GEMINI_API_KEY, sync: false }
      - { key: GEMINI_MODEL, sync: false }
      - { key: PAYMENTS_MODE, value: paypal_sandbox }
      - { key: PAYEE_MODE, value: demo_merchant }
      - { key: PAYPAL_API_BASE, value: "https://api-m.sandbox.paypal.com" }
      - { key: PAYPAL_CLIENT_ID, sync: false }
      - { key: PAYPAL_CLIENT_SECRET, sync: false }
      - { key: PAYPAL_WEBHOOK_ID, sync: false }
  - type: web
    name: milestonemate-web
    runtime: static
    rootDir: frontend
    buildCommand: npm ci && npm run build
    staticPublishPath: dist
    routes:
      - { type: rewrite, source: /*, destination: /index.html }
    envVars:
      - { key: VITE_API_BASE_URL, sync: false }
```
Notes: the `DATABASE_URL` from Render may start with `postgres://`; the config loader normalizes to `postgresql+psycopg://`. Secrets (`sync: false`) are entered in the Render dashboard, never in Git. If `preDeployCommand` is unavailable on the chosen plan, run `alembic upgrade head && uvicorn ...` in the start command.

Order: create Postgres -> deploy API -> note API URL -> set `VITE_API_BASE_URL` -> deploy web -> note web URL -> set `CORS_ORIGINS`, `FRONTEND_BASE_URL` on API -> redeploy API -> register the PayPal webhook URL `<API_URL>/api/webhooks/paypal` -> copy Webhook ID to `PAYPAL_WEBHOOK_ID`.

## 5. Frontend deployment
Static site build: `npm ci && npm run build` -> `dist/`. SPA rewrite to `/index.html` is mandatory (React Router). Vite env vars (`VITE_*`) are baked at build time: redeploy the static site after changing them. Never put secrets in `VITE_*` variables (they are public).

## 6. Environment variables (see `.env.example`)

| Variable | Used by | Notes |
|---|---|---|
| `APP_ENV` | backend | `local`, `staging`, `production`; `/api/config.env` |
| `APP_BASE_URL`, `FRONTEND_BASE_URL`, `CORS_ORIGINS` | backend | return/cancel URLs and CORS |
| `DATABASE_URL` | backend | |
| `JWT_SECRET`, `JWT_EXPIRES_MINUTES` | backend | >= 32 random chars |
| `MAX_UPLOAD_MB`, `MAX_FILES_PER_SUBMISSION` | backend | defaults 5 / 5 |
| `AI_MODE`, `LLM_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `AI_TIMEOUT_SECONDS`, `AI_MAX_RETRIES` | backend | |
| `PAYMENTS_MODE`, `PAYEE_MODE`, `PAYPAL_API_BASE`, `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID`, `ALLOW_UNVERIFIED_WEBHOOKS_IN_MOCK` | backend | |
| `SEED_DEMO_DATA` | backend | `true` only for staging/demo |
| `VITE_API_BASE_URL`, `VITE_USE_MOCKS` | frontend | build-time |

## 7. Production configuration checklist
- [ ] `APP_ENV` not `local`; `JWT_SECRET` unique; debug/reload off; docs UI (`/docs`) allowed (useful for judges) but no secrets in OpenAPI examples.
- [ ] CORS limited to the web origin.
- [ ] Rate limiting active; request-id logging on.
- [ ] `PAYPAL_API_BASE` is the **sandbox** host; no live credentials anywhere.
- [ ] Webhook registered to the deployed URL; `PAYPAL_WEBHOOK_ID` matches that webhook.
- [ ] Instance does not spin down during judging (paid plan or keep-alive); cold-start tested.
- [ ] Postgres retention verified through Dec 15, 2026; backup taken.
- [ ] Gemini key quota and billing alerts set.
- [ ] Demo data seeded (`SEED_DEMO_DATA=true` once) and credentials documented in README.

## 8. Deployment verification
1. `GET <API>/api/health` -> `{"status":"ok","db":"ok"}`; `GET <API>/api/config` shows expected modes.
2. Open web URL: banners match modes; register; login.
3. Run `python backend/scripts/e2e_smoke.py <API>` (mock) or manual slice.
4. Real sandbox payment once; confirm `paypal_webhook_events` row `SUCCESS`.
5. Check Render logs for errors and absence of secrets.
6. Cold-start timing; browser console free of errors; 404 deep link (e.g., `/projects/x`) loads via SPA rewrite.

## 9. Rollback and recovery
Redeploy previous tag from Render dashboard; migrations are additive after Day 5 so rollback is safe. AI outage: set `AI_MODE=mock` and redeploy/restart (banner "SIMULATED AI"). PayPal outage: `PAYMENTS_MODE=mock`. Keep a printed one-page runbook with these three actions.

## 10. Keeping the demo alive
Rules require judges to be able to test until the judging period ends (Dec 15, 2026, per Official Rules s.1/Testing). Also commit to README run instructions (always valid even if the host dies). Owner of uptime after submission: Member 1; calendar reminder to check weekly.
