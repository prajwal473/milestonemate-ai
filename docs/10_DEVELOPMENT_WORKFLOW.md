# 10 - Development Workflow

## 1. Repository

* Host: GitHub. **Private until Day 9**, then flipped to **public** after the secret scan (the hackathon requires a public, open-source repo with a license visible in the About section). `LICENSE` (MIT) is committed on Day 1.
* Single monorepo `MilestoneMate-AI`:
```
MilestoneMate-AI/
  backend/            FastAPI app (app/, alembic/, scripts/, tests/, requirements.txt, Dockerfile)
  frontend/           Vite React TS app
  docs/  team/        planning docs (this package)
  .github/workflows/ci.yml
  docker-compose.yml  (postgres:16 for local dev)
  render.yaml         (Render blueprint, Day 6)
  .env.example  .gitignore  LICENSE  README.md
```
* Branch model: **trunk-based**. `main` is always deployable. No long-lived `develop`.
* Branch protection on `main`: require PR, require 1 approval (Member 1, or Member 4 for Member 1's PRs), require status check `ci`, dismiss stale approvals, no force-push, linear history (squash merge).

## 2. Branch naming
`<type>/<owner>-<short-slug>` where type is `feat`, `fix`, `chore`, `docs`, `test`, `refactor`.
Examples: `feat/prajwal-agreement-generate`, `feat/yogesh-webhook-verify`, `fix/skanda-milestone-empty-state`, `chore/bharath-ci`.
Rules: branch from latest `main`; lifetime <= 1 day (max 2); one concern per branch.

## 3. Commit conventions (Conventional Commits)
```
<type>(<scope>): <imperative summary>

feat(ai): validate agreement amounts and rebalance within 5%
fix(payments): ignore duplicate PAYMENT.CAPTURE.COMPLETED
test(api): add RBAC matrix for deliverable endpoints
docs(paypal): record payee spike result
```
Scopes: `api`, `db`, `auth`, `ai`, `payments`, `ui`, `agreement`, `deliverable`, `audit`, `ci`, `deploy`, `docs`. Reference issues (`Refs #12`). Never commit secrets or `.env`.

## 4. Pull request process

1. Push branch; open PR using the template (`.github/pull_request_template.md`, Member 1 adds Day 1):
   * What/why (1-3 lines) - Linked roadmap task (`D4-Y2`) - Screenshots/curl output - Contract changes? (Y/N, doc updated?) - Tests added - Mode tested (mock/live)
2. Self-check: `ruff check`, `pytest -q`, `npm run build`, `npm run test`, `npm run gen:api` clean.
3. Request review from the owner of any file you touched outside your area (CODEOWNERS enforces this).
4. Review SLA: **within 2 working hours** (blockers within 30 min via chat ping). Small PRs (< 300 changed lines) preferred.
5. Squash-merge by the author after approval and green CI; delete branch.
6. After merge, post one line in the team channel if the merge changes a contract or env var.

`CODEOWNERS` (Member 1 creates Day 1):
```
/backend/app/ai/**                 @prajwal
/backend/app/routers/ai.py         @prajwal
/backend/tests/ai/**               @prajwal
/backend/app/payments/**           @yogesh
/backend/app/routers/payments.py   @yogesh
/backend/app/routers/webhooks.py   @yogesh
/backend/tests/payments/**         @yogesh
/frontend/src/features/payments/** @yogesh
/frontend/src/features/evaluation/** @prajwal
/frontend/**                       @skanda
/backend/alembic/**                @bharath
/backend/app/** /.github/** /docs/** /render.yaml @bharath
```
(Replace with real GitHub handles.)

## 5. Code review checklist
* Correctness vs contract (doc 05/06/07); permission checks present; transactions and idempotency where money/state changes.
* No secrets, no PII in logs; input validated; errors use `DomainError`.
* Tests meaningful (not only happy path where risk is high).
* UI: all states; mobile; accessibility basics; no direct `fetch` outside `api/`.
* Naming/consistency with canonical enums (doc 02 section 1).
* Reviewer must run the branch locally if the PR touches payments, auth or migrations.

## 6. Integration procedure

| Cadence | What | Who |
|---|---|---|
| **10:00 IST** daily | 15-min standup: yesterday / today / blockers / contract changes | all |
| Continuous | Merge small PRs to `main` many times a day | all |
| **20:30 IST** daily | **Integration check** on a clean checkout of `main`: backend tests, frontend build, smoke script, manual path of the day. Result posted ("GREEN"/"RED + owner") | Member 1 (Member 4 backup) |
| 21:00 IST | 20-min sync: demo what works, adjust next day | all |
| Day 5 | Vertical-slice integration day (everyone available for pairing) | all |
| Tags | `v0.5-slice` (D5), `v0.8-featurefreeze` (D8), `v0.9-rc1` (D9), `v1.0-rc2` (D10), `v1.0` (D11) | Member 1 |

Rules:
1. `main` must never be red for more than 30 minutes. The author of the breaking merge fixes or reverts immediately.
2. Mocks are an on-ramp, not a destination: by the end of Day 5 the main path uses the real API.
3. **Feature freeze** end of Day 8 (20:00 IST). **Code freeze** Day 10: only bug fixes labelled `blocker` or `demo-critical`, approved by Member 1.

## 7. Conflict resolution

* **Merge conflicts:** the later PR rebases onto `main` (`git fetch && git rebase origin/main`), resolves locally, re-runs tests. Never resolve conflicts in files you don't own without asking the owner.
* **Migrations:** only Member 1 commits to `alembic/versions`; two schema changes in flight are serialized by him.
* **Contract disagreements:** (1) discuss in a 10-minute call, (2) decide by the contract owner of the *provider* side unless it breaks the consumer's day; (3) if unresolved, Member 1 decides within 30 minutes; (4) decision recorded in the doc.
* **Ownership disputes:** the doc 09 file ownership table decides.
* **Priority disputes:** doc 02 priorities decide; P0 beats everything.

## 8. Testing before merging

| Change type | Required before merge |
|---|---|
| Backend | `ruff check .`, `pytest -q` (Postgres via docker compose), new tests for new behaviour |
| Frontend | `npm run lint`, `npm run build`, `npm run test`, manual check at 375 px and 1280 px |
| API shape | `npm run gen:api` committed (types updated) |
| AI prompt/schema | Run `scripts/eval_agreements.py` / `eval_deliverables.py` (golden set) and paste summary in PR; bump `prompt_version` |
| Payments | Sandbox run of create -> approve -> capture, plus unit tests with mocked PayPal; second reviewer runs it |
| Migration | `alembic upgrade head` from empty DB and from previous head |
| Docs/contracts | Update the relevant doc in the same PR |

## 9. CI (`.github/workflows/ci.yml`, Member 1 Day 1)
Jobs: `backend` (Python 3.12, services: postgres:16, `pip install -r requirements.txt`, `ruff check`, `alembic upgrade head`, `pytest --cov`), `frontend` (Node 20, `npm ci`, `npm run lint`, `npm run build`, `npm run test -- --run`), `contract` (start backend, `npm run gen:api`, `git diff --exit-code`), `secrets` (gitleaks action). Environment for CI uses `AI_MODE=mock`, `PAYMENTS_MODE=mock`.

## 10. Tooling and conventions
* Python: `ruff` (lint + format), type hints on public functions, `pydantic` v2 models at boundaries, no wildcard imports.
* TypeScript: ESLint + Prettier (Member 3 configures), `strict: true`, no `any` in `api/`.
* Secrets: local `.env` (git-ignored), team password manager for shared keys, Render environment groups for hosted; rotate immediately if leaked.
* Issues: GitHub Issues with labels `P0`, `P1`, `bug`, `blocker`, `demo-critical`, `contract`; project board columns To do / Doing / In review / Done.
* Communication: one team chat channel + `#blockers` thread; decisions logged in `docs/` not only in chat.
