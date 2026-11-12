# MilestoneMate AI

**From project agreement to milestone payment coordination.**

MilestoneMate AI is a hackathon project exploring how AI can help clients and freelancers turn a project brief into structured milestones, review submitted deliverables against acceptance criteria, and coordinate milestone-related payments.

> **Important:** MilestoneMate AI is not an escrow service. PayPal does not hold funds on behalf of the platform pending milestone completion. The client remains responsible for deciding whether work is accepted and authorizing payment. PayPal Sandbox is used for development and testing; no real money should move during the hackathon demo.

## Project status

This repository currently contains a FastAPI backend and supporting documentation. A frontend application is not present at the repository root in this checkout, and the payment client code is not yet connected to a complete payment API workflow.

| Area | Current implementation in this repository |
|---|---|
| Backend API | FastAPI application |
| Database | SQLAlchemy models and Alembic migrations for PostgreSQL |
| Authentication | User registration and JWT-based authentication routes |
| Projects and agreements | Project, freelancer assignment, agreement and milestone API routes |
| Deliverables and evaluation | Deliverable and evaluation routes; Gemini evaluator module |
| AI | Google Gemini API client used by the deliverable evaluator |
| Payment foundation | PayPal Sandbox REST client, mock payment client and payment state definitions |
| Payment webhooks | PayPal signature-verification client method and webhook-event database model |
| End-to-end payment workflow | Not yet verified as connected through application API routes |
| Frontend | Not included in this repository checkout |

The repository has automated backend tests. Run the test suite using the instructions below to verify the current checkout.

## Core workflow being developed

1. A client creates a project and defines its requirements.
2. The project can be assigned to a freelancer.
3. The parties can work with a structured agreement and milestones.
4. A freelancer submits a deliverable for a milestone.
5. The Gemini evaluator assesses the submission against the milestone's acceptance criteria and returns a structured, advisory evaluation.
6. The client makes the final acceptance decision.
7. Payment coordination is intended to use PayPal Sandbox. The current repository includes PayPal client operations and payment-state definitions, but a complete application-level payment workflow is not yet verified.

**AI does not make the final acceptance decision or independently authorize a payment.**

## Technology

- **Python 3.12** — recommended runtime for the current backend environment
- **FastAPI** — HTTP API
- **SQLAlchemy** — database ORM
- **Alembic** — database migrations
- **PostgreSQL** — relational database
- **Google Gemini API (`google-genai`)** — deliverable evaluation
- **PayPal REST API (Sandbox)** — payment client implementation
- **pytest** — automated tests

## Repository layout

```text
.
├── backend/
│   ├── alembic/
│   ├── app/
│   │   ├── ai/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── payments/
│   │   ├── routers/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── docs/
├── team/
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

## Local setup

The backend reads its `.env` file from the repository root.

### 1. Clone the repository

```bash
git clone https://github.com/prajwal473/milestonemate-ai.git
cd milestonemate-ai
```

### 2. Create and activate a Python environment

Python 3.12 is recommended.

**Windows CMD:**

```cmd
py -3.12 -m venv .venv
.venv\Scripts\activate
```

**Windows PowerShell:**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 3. Install backend dependencies

Run from the repository root:

```bash
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

### 4. Configure environment variables

Copy the example file:

**Windows CMD:**

```cmd
copy .env.example .env
```

**PowerShell / macOS / Linux:**

```bash
cp .env.example .env
```

Edit the root `.env` file and provide values for the settings required by `backend/app/core/config.py`:

```dotenv
DATABASE_URL=postgresql+psycopg://YOUR_USER:YOUR_PASSWORD@localhost:5432/YOUR_DATABASE
JWT_SECRET_KEY=replace-with-a-long-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=60

GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.8-flash

PAYMENTS_MODE=mock
PAYPAL_API_BASE=https://api-m.sandbox.paypal.com
PAYPAL_CLIENT_ID=
PAYPAL_CLIENT_SECRET=
PAYPAL_WEBHOOK_ID=
PAYEE_MODE=demo_merchant
PAYPAL_BRAND_NAME=MilestoneMate AI
FRONTEND_BASE_URL=http://localhost:5173
ALLOW_UNVERIFIED_WEBHOOKS_IN_MOCK=false
```

Use a PostgreSQL database that is already running and accessible from your machine. The database must exist before applying migrations.

The variable names above match the current backend settings. **The checked-in `.env.example` currently uses `JWT_SECRET` and `JWT_EXPIRES_MINUTES`; those names do not match the `jwt_secret_key` and `access_token_expire_minutes` settings in `backend/app/core/config.py`. Use `JWT_SECRET_KEY` and `ACCESS_TOKEN_EXPIRE_MINUTES` as shown above, or update the example file before relying on it as-is.**

Keep `.env` private. Do not commit API keys, database passwords, JWT secrets or PayPal credentials.

### 5. Apply database migrations

From the repository root:

```bash
cd backend
alembic upgrade head
```

### 6. Start the API

Still from the `backend` directory:

```bash
uvicorn app.main:app --reload --port 8000
```

The API should be available at:

- API root: `http://127.0.0.1:8000/`
- Health check: `http://127.0.0.1:8000/api/health`
- Interactive API documentation: `http://127.0.0.1:8000/docs`

The health endpoint checks database connectivity. A healthy response confirms the API can execute a simple database query; it does not verify every integration.

## Running tests

With the virtual environment activated, change to the backend directory and run:

```bash
cd backend
python -m pytest -v
```

The payment-client tests use mocked HTTP responses. Passing those tests does not mean a live PayPal Sandbox transaction has been performed.

## AI evaluation

The backend contains a Gemini-based deliverable evaluator. It evaluates a freelancer's written submission against a milestone title, description and acceptance criteria, and returns structured results including:

- A score
- A summary
- Per-criterion status (`met`, `partially_met`, `not_met` or `unverified`)
- Evidence text
- Missing requirements
- An advisory recommendation

The evaluator is instructed not to assume that a feature exists, not to claim it inspected external URLs, and to leave the final acceptance decision to the client. Its output is decision support, not proof that software or a deliverable was independently inspected.

To use live Gemini evaluation, configure `GEMINI_API_KEY` and a model supported by the Google GenAI API.

## PayPal Sandbox integration

The repository includes a PayPal REST client configured to accept only the official PayPal Sandbox API host. The client contains methods for:

- OAuth access-token retrieval and caching
- Creating an Orders API order
- Retrieving an order
- Capturing an order
- Verifying a webhook signature through PayPal's verification endpoint

A mock payment client and payment-status transition definitions are also included.

**Integration boundary:** These are payment integration building blocks. This checkout does not currently expose a dedicated payment router or demonstrate a complete application-level flow connecting milestone approval, payment persistence, PayPal capture and webhook event processing. Do not treat the presence of the client methods or webhook model as evidence that the end-to-end workflow is complete.

Use PayPal Sandbox credentials only. Never use live credentials for the hackathon demo.

## Security and product boundaries

- Do not commit `.env` or expose credentials in frontend code.
- Use PayPal Sandbox for development and demonstration.
- The platform is not escrow and does not hold client funds.
- AI evaluation is advisory; the client decides whether a deliverable is accepted.
- Payment authorization remains with the client and is subject to the PayPal flow actually integrated into the running application.

## Team responsibilities

The project is organized around four generic team roles:

- **Member 1:** Backend, database, authentication and shared backend services
- **Member 2:** AI integration
- **Member 3:** Frontend and user interface
- **Member 4:** PayPal integration and payment testing

## Documentation

Project planning, architecture, requirements, API, AI, PayPal, security, testing, deployment and demo documentation is maintained in the `docs/` and `team/` directories. Consult the files present in those directories for the current project decisions and implementation notes.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
