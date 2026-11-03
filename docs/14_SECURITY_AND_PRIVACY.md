# 14 - Security and Privacy

Threat model in one line: an authenticated user or anonymous attacker tries to see another project's data, move money without authorization, forge a payment confirmation, steal keys, or trick the AI.

## 1. API key and secret protection
| Control | Detail |
|---|---|
| No secrets in Git | `.gitignore` excludes `.env*`; `.env.example` has placeholders only; gitleaks in CI and before the repo is made public (Day 9) |
| Storage | Local `.env`; team password manager; Render env vars (`sync: false`) |
| Frontend exposure | No secrets in `VITE_*`; PayPal client ID/secret and LLM keys exist only in the backend; the redirect flow needs no PayPal client ID in the browser |
| Rotation | If any key appears in a commit, chat or log: rotate immediately, rewrite history if public, document in risk register |
| Logging | Never log `Authorization`, passwords, API keys, PayPal secret, access tokens, raw deliverable content |
| Judge access | README tells judges to create their own sandbox app or use mock mode; the REST secret is never published |

## 2. Authentication
Email + password; `argon2id`; password 10-128 chars; generic login errors; rate limit login (10/min/IP) and register; JWT HS256 (`sub`, `exp` 60 min, `iat`); `JWT_SECRET` >= 32 random bytes; token stored in `localStorage` (known XSS trade-off; mitigated by React escaping, no `dangerouslySetInnerHTML`, strict CSP header on the static site where supported). Invitation tokens: 32 random bytes URL-safe, only SHA-256 stored, 14-day expiry, single use, bound to invited email.

## 3. Role-based and object-level access
Per-project roles from `projects.client_id/freelancer_id`. Every project-scoped route resolves the object **through** the project membership check (never by id alone). Non-members get `404`. Role-specific mutations use `require_role`. Tests: RBAC matrix over all routes + IDOR swap tests (doc 12).

## 4. Payment security
* Amounts, currency and payee come from the database; the client request body never carries money values.
* Only the project `CLIENT` can create/capture/cancel; capture requires PayPal order status `APPROVED` (buyer authorization at PayPal) and the client's explicit request.
* The AI package cannot import payments (static test) and holds no PayPal credentials in its code path.
* Idempotency: `PayPal-Request-Id` + DB unique constraints + row locks (doc 07 section 7).
* Captured amount/currency compared with the stored values.
* Only PayPal **sandbox** host is configured; startup check refuses `PAYPAL_API_BASE` equal to the live host unless `APP_ENV=production_live` (not used).
* Honest claims: no "escrow"/"held funds" language anywhere (copy review on Days 7-8, Member 4 checks video).

## 5. Webhook signature verification
Raw body -> PayPal `verify-webhook-signature` with `webhook_id` -> only `SUCCESS` is processed; failures stored and answered `400`; dedupe on event id; state re-read from PayPal rather than trusted from payload; unauthenticated route has a body size cap (1 MB) and rate limit. Mock-mode unverified acceptance flag is ignored outside `PAYMENTS_MODE=mock`.

## 6. File upload validation
| Check | Rule |
|---|---|
| Count/size | <= 5 files, <= 5 MB each (enforced while streaming; `413`) |
| Extension allowlist | `txt md csv json html css js ts tsx jsx py java go rs sql yaml yml xml pdf docx png jpg jpeg` |
| MIME sniffing | Magic-byte check for pdf/docx/png/jpg; text files must decode as UTF-8 (replace errors) and contain no NUL bytes; mismatch -> `415` |
| Filename | Sanitized (basename only, strip path separators/control chars, max 255); stored name is the DB id; original shown escaped |
| Storage | `bytea` in Postgres; never written to a web-served path; never executed |
| Download | `Content-Disposition: attachment`, `X-Content-Type-Options: nosniff`; authenticated members only |
| Archives | Not accepted (no zip handling) |
| Extraction safety | `pypdf`/`python-docx` run with size caps and timeouts; parse errors -> `FAILED`, never crash the request |
| Links | Stored as text, validated `http(s)`, **never fetched** (no SSRF) and rendered with `rel="noopener noreferrer nofollow"` |

## 7. Input validation
Pydantic v2 models on every request; strict enums; length caps (doc 05 section 11); parameterized SQL via SQLAlchemy; JSON size limit 1 MB (non-upload); output encoding by React; no raw HTML rendering of user/AI content (Markdown rendering, if used, through a sanitizing renderer with HTML disabled).

## 8. Data privacy
| Topic | Policy |
|---|---|
| Data collected | Email, display name, optional PayPal sandbox email, project briefs, agreements, deliverables, evaluations, payment metadata |
| AI processing | Brief, criteria and extracted deliverable text are sent to the configured LLM provider (Gemini by default). Users are told in the UI (evaluation panel footer + registration notice). No emails/passwords/payment IDs in prompts. `ai_runs` stores hashes and sizes, not documents |
| PayPal | Sandbox only; no card data ever touches our servers (approval happens on PayPal) |
| Retention | Demo data kept until the end of the judging period; deletion on request via maintainers (README note). Seeded demo users are flagged `is_demo` |
| Minimization | Invitation preview reveals only project title, client name and invited email; error messages don't reveal whether an email exists on login |
| Transport | HTTPS on Render; HSTS via platform |
| Third-party terms | Use of Gemini and PayPal APIs follows their terms (Official Rules require authorization to use third-party APIs) |

## 9. Audit logging
Append-only `audit_log` (DB trigger blocks UPDATE/DELETE), per-project SHA-256 hash chain verifiable through API/UI; actor types USER/SYSTEM/AI/PAYPAL; contains hashes and ids, not secrets. Audit failure in a transaction rolls back the business change (state change and audit are atomic). Payment-specific trail in `payment_events` and `paypal_webhook_events` (doc 04).

## 10. HTTP hardening
CORS allowlist; `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin` on API; CSP and frame protections via static-site headers if Render supports custom headers (otherwise documented limitation); rate limits: auth 10/min, AI 20/hour/user, webhook 120/min; request body limits.

## 11. AI limitations and risks (shown in UI and docs)
1. AI output can be wrong, incomplete or biased; it is **advisory**. The client decides; the freelancer can dispute through comments.
2. Evaluation only sees extracted text. It cannot judge visual design, runtime behaviour, external links or unsupported files; those are reported as `CANNOT_DETERMINE`.
3. Evidence quotes are machine-verified against the text, which prevents fabricated quotes but not wrong interpretation.
4. Prompt injection inside deliverables is mitigated (delimiters, schema, no tools, deterministic recommendation) but not impossible; the AI has no power to change state or move money, which bounds the impact.
5. LLM outputs vary between runs; "confidence" is the model's self-estimate, not a calibrated probability.
6. The agreement is a project record, **not** legal advice or a legally reviewed contract. MilestoneMate is **not** an escrow service.
7. Provider outage or quota exhaustion degrades to template/mock paths with visible labels.

## 12. Security review checklist (Day 8)
RBAC matrix green; IDOR tests; JWT expiry; upload attacks; webhook tamper tests; gitleaks clean; dependency audit triaged; CORS verified from foreign origin; no secrets in logs/bundles (`grep` build output for key prefixes); Render env review; HTTP headers verified; admin/debug routes absent.
