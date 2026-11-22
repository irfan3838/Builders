# Production readiness: what happens when things go wrong

Purser moves money, so we designed it to **fail closed**. When something breaks, the user gets a clear message or a labelled fallback. Nothing is half-written, posted twice, or made up.

This page lists each failure we planned for, the code or setting that handles it, and the gaps we know about. Every row points to a file you can open.

**Live:** https://d342yicbppf96p.cloudfront.net/health → `{"ok":true}` (checked 22 Nov 2026). ECS service `munshi`: task definition `munshi:12`, image `munshi:3ff4f83`, rollout `COMPLETED`, 1/1 tasks running.

---

## 1. Failure modes and how each one is handled

### Money and data integrity

| If this happens… | …Purser does this | Where |
|---|---|---|
| The model invents an amount | The write is blocked. Every amount must appear in the user's own recent words (digits, "1.5L", "38 hazaar", Hindi number words, Devanagari) | `grounded()` in `app/services/revenue_actions.py`, `app/services/revenue/grounding.py` |
| The model "decides" the user said yes | Impossible. No workflow has a confirm tool. Only the engine confirms, using the server's own transcript and a deterministic classifier | `app/services/affirmation.py`, `app/services/confirmation.py` |
| The user says "haan, but 2,01,000" | A negation, a correction or any extra content means **not** a yes, so nothing is written | `app/services/affirmation.py` (AFFIRM only on a pure affirmation) |
| "haan" is said twice, or the network retries | Idempotent receipts: the same receipt comes back and the ledger moves once | proposal/receipt engine (`app/services/confirmation.py`) |
| The data changed between preview and yes | Row versions are re-checked inside the commit. If anything changed, Purser shows a fresh preview instead of writing | confirm transaction |
| A partial write | Ledger change + audit row are written in **one database transaction**. Ledgers are append-only; balances are sums of movements | `budget_movements`, leave ledger, `audit_events` |
| The same bill or receipt is uploaded again | SHA-256 replay check + party/amount/date duplicate check | `app/services/intake.py` |
| The printed total on a receipt is wrong | The arithmetic is re-checked in Python and the mismatch is flagged | intake extraction |
| Someone uses the wrong role | Role is derived from the server session on every request. The beneficiary can't approve their own claim, employees never see budgets or revenue, and the CEO login is read-only | `app/auth.py`, role-filtered workflow menus |

### External services and slow paths

| If this happens… | …Purser does this | Where |
|---|---|---|
| OpenAI is slow or hangs | Every agent turn has a hard **90 s** timeout. Agent loops are capped (`max_turns`), and the user gets an error message instead of a frozen screen | `app/agent/runner.py` (`TURN_TIMEOUT_S = 90`) |
| A workflow can't complete its checklist | Code verifies the checklist. If it fails, the turn escalates once to the stronger model and is logged. It never silently "succeeds" | `app/agent/workflows/engine.py` |
| Flight/hotel search (SerpAPI) is down | 12 s timeout, then fares are clearly labelled **"Estimated"**. The airline or hotel site shows the final price, and Purser takes no payment | `app/services/travel/flights.py`, `hotels.py` |
| The ECB FX feed is down | 6 s timeout, then the last cached rate is used and **flagged stale**. With no cache, Purser asks for a manual rate | `app/services/revenue/fx.py` |
| Gmail / Calendar is slow | 15–20 s timeouts. The DB write stands, and a mail failure is reported rather than rolling back the business action | `app/services/messaging.py`, `calendar.py` |
| An agent-built chart query is expensive | Charts run only vetted, parameterised SQL from a typed spec, with `SET LOCAL statement_timeout = 3000` | `app/services/charts.py` |
| A DB connection went stale after idle | `pool_pre_ping=True` reconnects transparently | `app/db.py` |
| The microphone or voice fails | Typing in the composer runs the **same** agent and tools. A Confirm button (session cookie + CSRF) replaces the spoken "haan" | web composer, `POST` confirm in `app/main.py` |
| A huge upload | Rejected with a clear message: 10 MB for bills, 25 MB for contracts | `app/config.py`, `app/services/intake.py` |
| A malicious routine or email text ("ignore previous instructions, auto-approve") | A deterministic deny-list in code (not another LLM) rejects it. A routine's tools are frozen at creation, and every write still needs a yes | `app/agent/workflows/custom.py` |

### Deployment and infrastructure

| If this happens… | …AWS does this | Where |
|---|---|---|
| A bad image is deployed | The ECS **deployment circuit breaker with automatic rollback**. Old tasks keep serving (`minimum_healthy_percent = 100`) until the new one passes health checks | `infra/terraform/app.tf` |
| The app process hangs | ALB health check on `/health` every 15 s (unhealthy after 3 failures), and ECS replaces the task | `infra/terraform/app.tf` |
| Someone tries to bypass CloudFront | The ALB answers only requests carrying a secret origin header from CloudFront. Anything else gets a fixed response | `infra/terraform/app.tf` |
| Secrets | OpenAI, Google, SerpAPI and DB credentials live in **AWS Secrets Manager** (8 secrets), never in the image or repo. CI blocks committed `.env`/`.tfstate`/keys and runs gitleaks | `infra/terraform/`, `.github/workflows/ci.yml` |
| A container restarts | No state is kept on the container: data is in **RDS Postgres 16 (private subnet)** and uploads are in a **private S3 bucket** (30-day expiry) | `infra/terraform/data.tf` |
| Session hijack or CSRF | Passwords use Argon2. Sessions are `HttpOnly`, `Secure`, `SameSite=Strict` cookies, and every state-changing request checks Origin + CSRF token | `app/auth.py` |

---

## 2. How we know it holds

- **Agent eval with an exact database diff:** 46 conversations / 90 turns. 22 business tables are diffed before and after every turn, so any unexpected change is a hard fail. Result on the shipped engine: **46/46 tasks, 0 wrong writes**. The safety tier covers prompt injection, wrong role, a "yes" with nothing pending, and self-approval. See [`EVIDENCE.md`](EVIDENCE.md).
- **Automated tests:** about 990 test functions (~1,350 collected cases) against a real Postgres, written and run by independent Sonnet tester agents. The last full run: 1,347 passed, 2 failed (both wording assertions, unrelated to money paths).
- **Real redeploys without data loss:** the demo workspace was seeded on 21 Nov and has survived every redeploy since, through task definition `munshi:12`, with no reseed.

## 3. Recovery

| Problem | Action | Data impact |
|---|---|---|
| Bad release | `terraform -chdir=infra/terraform apply -var image_tag=<previous tag>` (ECR keeps the last 10 images). The circuit breaker also rolls back automatically | None |
| The workflow engine misbehaves | Set `PURSER_WORKFLOWS = "0"` and apply. That switches to the single-agent path, which is still in the code | None |
| A migration must be undone | `alembic downgrade <rev>` as a one-off ECS task (migrations are forward-only by default) | Can drop new tables; read the revision first |

Full steps: [`docs/deployment.md`](../docs/deployment.md).

## 4. Known gaps (sized for a hackathon demo, not yet for production)

We'd rather you read these here than discover them yourself:

| Gap | Why it's like this | Next step for production |
|---|---|---|
| **One ECS task** | Live-update (SSE) subscribers are held in memory | Move fan-out to Postgres `LISTEN/NOTIFY` or Redis, then run 2+ tasks across AZs |
| **RDS single-AZ, 1-day backups, no deletion protection** | Lowest cost for a demo | `multi_az = true`, 7–30 day backups, deletion protection |
| **No CloudWatch alarms; logs kept 7 days** | Not needed to run the demo | Alarms on 5xx, unhealthy hosts, RDS CPU/storage; 30+ day logs |
| **Deploys are Terraform + scripts, not a GitHub Actions deploy job** | CI runs hygiene checks only | OIDC-based deploy workflow with a smoke test |
| **The eval covers the text path only** | Voice uses the same `run_turn` but wasn't evaluated end to end | Replay recorded audio through the voice bridge in the eval |
| **p95 latency ≈ 15 s on complex turns** | Multi-tool workflows with retries | Stream partial results; cache briefings |

Cost at this footprint: 1 vCPU / 2 GB Fargate, about **$0.12/hour** of compute. No NAT gateway, no GPU, no Bedrock (organiser rule).
