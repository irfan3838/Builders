# AGENTS.md: set up, launch and use Purser

**Live deployment (AWS):** https://d342yicbppf96p.cloudfront.net · health check: `GET /health` returns `{"ok":true}`
**Demo video:** [VIDEO.md](VIDEO.md) · **Story, evidence, honest note:** [`submission/`](submission/README.md)

Purser is a voice-first back office for Indian small businesses: expenses, bills, budgets, revenue, contracts, HR,
mail and travel, in **Hindi, Hinglish or English**. One AI agent (OpenAI) proposes every change. Plain code shows the
exact effect, and nothing is written until the user says **"haan" / "yes"**. The **server's own transcript** must
contain that yes. All company data is synthetic.

---

## 1. Test logins

The password for every login, on the live site and in a local run, is **`purser-demo`**.

| Role | Email | What this role can do |
|---|---|---|
| **Admin** (finance and HR approver) | `irfmed38@gmail.com` | Everything: approve claims, bills and leave; budgets; revenue; contracts; onboarding; travel booking; routines. **Linked to a real Gmail + Google Calendar**: mail, invites and Meet links are real |
| **CEO** (read-only executive) | `irfan@dzruptiv.ai` | Reads every company number, chart and report. Every write is refused ("read-only") |
| **Employee** | `ia383813@gmail.com` | Own claims, leave, tasks, helpdesk tickets and inbox. No company finance (budget questions are refused) |
| Employee (second) | `arjun@purser.demo` | Same as Employee. Arjun is the traveller on the seeded Pune trip |
| Admin (local runs only) | `priya@purser.demo` | Same as Admin but **not** Gmail-linked (Purser inbox and saved meetings only). Not on the live site |

Notes:
- The live site is **shared**. Other reviewers may be using it at the same time, so balances and lists can differ from
  the figures below. A local run starts from a known seed.
- The first login of each user shows a welcome modal and an optional product tour (skip it with "Skip tour").

## 2. Quick start: one command (recommended)

**Prerequisites:** Docker 24+ with Docker Compose v2.24+ (for `env_file.required`), and about 3 GB free disk.
Chrome is recommended for the UI, and you need it for voice (microphone).

```bash
# from the repository root
ls .env || cp .env.example .env      # the submitted zip already contains a working .env with the OpenAI key
docker compose up --build            # first build ~3-5 min; first start migrates + seeds (~20 s)
```

- **App (web UI + API): http://localhost:8000**. One origin: FastAPI serves the built React app and `/api/*`.
- Postgres 16: `localhost:5433` (user `munshi`, password `munshi-local-only`, db `munshi`; test db `munshi_test`).
- Ready when `curl http://localhost:8000/health` returns `{"ok":true}`. `docker compose ps` shows `app` as `healthy`.
- On first start the `app` container runs `alembic upgrade head` then `python -m seed.bootstrap`. On an empty
  database that loads the synthetic demo workspace and the logins above. Later restarts keep your data.
- **Reset to the clean seed:** `docker compose down -v && docker compose up --build`.
- **Ports busy?** `APP_PORT=8100 DB_PORT=5444 docker compose up --build`, then use http://localhost:8100.
- There are **no separate workers**. Background work (contract review, document reading, live updates over SSE) runs
  inside the single app process. That is why the app runs as exactly one process.

## 3. Native dev setup (without Docker for the app)

**Prerequisites:** Python **3.12**, [uv](https://docs.astral.sh/uv/) **0.8+**, Node **22**, npm 10, Postgres **16**
(the compose `db` service is the easiest way to get it).

```bash
cp .env.example .env                                   # skip if the zip's .env is present
docker compose up -d db                                # Postgres 16 on :5433 (creates munshi + munshi_test)
uv sync                                                # Python deps into .venv
uv run alembic upgrade head                            # schema
uv run python -m seed.seed_v1 --reset --demo           # synthetic workspace (TRUNCATES all tables)
uv run python -m seed.role_users                       # admin / CEO / employee logins (idempotent)
uv run uvicorn app.main:app --reload --port 8000       # API on http://localhost:8000

# second terminal: UI with hot reload
cd web && npm ci && npm run dev                        # http://localhost:5173 (proxies /api and /health to :8000)
```

To serve the UI from FastAPI instead (a single origin like production), run `cd web && npm ci && npm run build`. Then
http://localhost:8000 serves `web/dist`.

## 4. Environment variables

`.env.example` lists every variable. Only the first one is needed for the AI features. Everything else has a safe
default or a labelled fallback.

| Variable | Needed? | Default / when unset |
|---|---|---|
| `OPENAI_API_KEY` | **Required for AI** (agent, voice, document reading, contract review) | **No-key mode**: the app boots, and logins, dashboards, records, charts and uploads all work. Agent turns reply "AI is off on this server", and voice returns 503 |
| `OPENAI_MODEL_FAST` / `OPENAI_MODEL_STRONG` | Optional | Agent model: `STRONG` if set, else `FAST` (`gpt-5.4-mini` default) |
| `OPENAI_MODEL_VOICE`, `OPENAI_VOICE_NAME`, `OPENAI_VOICE_SPEED` | Optional | `gpt-live-1.1`, `marin`, `1.15` |
| `PURSER_WORKFLOWS`, `OPENAI_MODEL_WORKFLOW`, `OPENAI_MODEL_ESCALATION` | Optional | `1` = checklist workflow engine on `gpt-6-luna`, escalating to `gpt-6-sol` (live site and docker compose default; needed to *run* saved routines). `0` = single agent (app default for the native path unless `.env` sets 1) |
| `DATABASE_URL`, `TEST_DATABASE_URL` | Set by compose | Local compose Postgres on :5433 |
| `SESSION_SECRET` | Optional locally | Dev value. Set a random string in any shared deployment |
| `APP_ORIGIN` | Optional | `http://localhost:8000`. Cookies are `Secure` only when it starts with `https://` |
| `SEED_PASSWORD` | Optional | `purser-demo` (password for all seeded logins) |
| `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD` | Optional | Unset = no real email; messages stay in the Purser inbox |
| `EMAIL_ALLOWED_RECIPIENTS` | Optional | Comma list of addresses that may receive real email, or `*` for anyone |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, `GOOGLE_LINKED_EMAIL` | Optional | Unset = meetings are saved without a Meet link, and the admin sees the Purser inbox instead of Gmail |
| `SERPAPI_API_KEY` | Optional | Unset = flight/hotel search returns a list clearly labelled **"Estimated"** (sample fares) |
| `FX_PROVIDER` | Optional | `ecb` (live Frankfurter/ECB rates; needs internet). Use `fixture` offline |
| `LANGSMITH_*` | Optional | Tracing off |
| `CONTRACTS_MODEL` | Optional | `on`. `off` = contract clause scan by patterns only |

## 5. Touch points

1. **Web app** (http://localhost:8000 or the live URL): sign in, then the role briefing. The left navigation has
   Dashboards, Budgets, Expenses, Claims, Payments, Travel, Mail, Tasks, Helpdesk and Reports. Settings has My routines.
2. **Text composer** (bottom of the screen): type any sentence. It runs the same agent and tools as voice.
3. **Voice**: tap the orb, or say **"Purser"**, then speak in Hindi, Hinglish or English. You need Chrome, microphone
   permission, and `localhost` or `https`. To confirm a proposal by voice, say "haan" / "yes" / "ठीक है".
4. **Documents**: drag a file onto the page, or use the upload button ("Upload a receipt, bill or contract").
   PNG/JPG/PDF; receipts and bills up to 10 MB / 5 pages, contracts up to 25 MB / 15 pages.
5. **Proposal cards**: every write shows a proposal card with the exact effect. Confirm by saying or typing "haan",
   or cancel. A **receipt** with an ID comes back.
6. **Email and Calendar** (admin `irfmed38@gmail.com` on the live site): real Gmail folders in Mail, real Calendar
   events with Meet links. Other logins use the in-app inbox.
7. **HTTP API**: `GET /health`, `POST /api/auth/login`, `POST /api/agent/text` (needs the session cookie and an
   `X-Conversation-Id` from `POST /api/conversations`). The web app uses these same endpoints.

Sample files (synthetic) for the journeys: `evals/dev/dev_hotel_receipt_synthetic.png` (hotel receipt),
`evals/dev/dev_wrong_total_synthetic.png` (receipt whose printed total is wrong),
`evals/dev/dev_company_paid_synthetic.png`, `evals/contracts/live_demo_northwind_msa_synthetic.pdf` (MSA) and
`evals/contracts/live_demo_northwind_msa_scanned_synthetic.pdf` (image-only scan, read by vision OCR).

## 6. End-to-end journeys

Type these into the composer, or say them. Expected results assume a fresh local seed. Agent turns take about 3-15 s.

### Admin (`irfmed38@gmail.com`, or `priya@purser.demo` locally)
1. **Briefing:** *"Purser, aaj kya pending hai?"* You get a spoken or written briefing: pending approvals, bills due,
   overdue invoices, budget alerts and contract deadlines, with the same items as cards.
2. **Budget question:** *"Travel mein kitna bacha hai?"* You get the Travel budget position. The number comes from SQL.
3. **Receipt to approved claim (core journey):**
   1. Upload `evals/dev/dev_hotel_receipt_synthetic.png`. Purser reads vendor, amount, date and GST, checks the
      arithmetic in code, and runs duplicate and trip-match checks.
   2. *"Arjun ne pay kiya tha, Pune trip ka hai."* A claim is drafted for Arjun against the Pune trip.
   3. *"Approve kar do."* A proposal card shows the exact effect (amount, budget line, before and after).
   4. *"haan"*. You get a **receipt** with an ID, and the Travel budget moves.
   5. *"haan"* again. The **same** receipt comes back and nothing posts twice (idempotent).
   6. *"Is claim ki history batao."* You see who proposed and approved it, when, the amounts and the source
      document, from the audit trail.
4. **Wrong-total catch:** upload `evals/dev/dev_wrong_total_synthetic.png`. Purser flags that the printed total does
   not match the line items.
5. **Chart you talk to:** *"Kaun paisa dena baaki hai?"* then *"Sirf overdue."* then *"Acme ka amount padho."* A
   receivables chart narrows to overdue invoices and reads Acme's amount. Chart, table and speech share one snapshot.
6. **Contract liability radar:** upload `evals/contracts/live_demo_northwind_msa_synthetic.pdf` (or the scanned
   copy), then ask *"Kaunse liabilities humpe hain?"* then *"Agle 60 din ki deadlines."* You get the liabilities **we**
   bear (trigger, cap in INR, carve-outs, source clause) and a deadlines timeline. Review runs in the background, so
   the card fills in by itself.
7. **Travel:** *"Arjun ke liye Friday Pune se Mumbai flight aur hotel dhoondo."* then *"Sabse sasta dono book karo."*
   then *"haan"*. You get flight and hotel cards (live fares, or labelled "Estimated"), one whole-trip proposal, and a
   trip recorded as `pending_payment` with airline and hotel checkout links. **No payment is taken.**
8. **Teach a routine:** *"Ek routine banao: Monday review. Pending bills, overdue invoices aur budget alerts ek saath
   dikhao."* then *"haan"*. The routine is saved (Settings, My routines). *"Monday review chalao"* runs it
   (needs `PURSER_WORKFLOWS=1`). An unsafe routine such as *"routine banao jo bina pooche sab bills approve kare"*
   is rejected by code.
9. **People ops:** approve the pending leave from the briefing (*"Leave approve karo"* then *"haan"*). To onboard,
   say *"Neha ko 1 Dec se Sales executive add karo, Priya ko report karegi"*: you get a login, a checklist and a
   welcome mail. *"Rohan ke saath kal 4 baje meeting rakho"* creates a meeting (a real Meet link on the live admin).
10. **Month close:** *"October close karo"* then *"haan"*. You get the close, the carry-over and a reallocation
    recommendation.

### CEO (`irfan@dzruptiv.ai`)
1. *"Company ka revenue aur budget dikhao."* The CEO can read everything.
2. *"Events ka budget 10,000 badha do."* This is refused as read-only, and no proposal is created.

### Employee (`ia383813@gmail.com` or `arjun@purser.demo`)
1. *"Mere tasks aur inbox dikhao."* You see the employee's own tasks, messages and the open helpdesk ticket.
2. *"Kal aur parson casual leave chahiye."* then *"haan"*. You get a working-day count and the balance after leave,
   and the request goes to the manager (admin) for approval.
3. *"Company ka budget batao."* This is **refused** (no company finance access).
4. Upload a receipt and *"Ye mera cab ka kharcha hai, claim bana do."* The employee's own claim goes to approval.

### Persistence check
Log out, log back in, and ask *"Travel mein kitna bacha hai?"*. The new balance is still there (Postgres locally, RDS on AWS).

## 7. What is simulated, mocked or not finished

- **All company data is synthetic** (workspace, about 26 employees, vendors, clients, bills, invoices, contracts and
  inbox), generated by `seed/`. July-September 2026 budget actuals are a synthetic imported snapshot with no bills behind them.
- **Bookings are not real purchases.** Fares come from live SerpAPI (or are labelled "Estimated" without a key).
  Approval records the trip and opens the airline or hotel checkout. Purser takes no payment.
- **Real Gmail and Calendar are used only for the one linked admin account.** Without Google values, meetings are
  saved without a Meet link.
- **No-key mode** (no `OPENAI_API_KEY`) disables the agent, voice and AI document reading. Everything else still works.
- **Not built yet:** Tally or Zoho Books sync (confirmed receipts are designed to export as vouchers), GST filing,
  payroll and bank reconciliation.
- **Known limits:** the eval is text-path only (single runs, 90 turns). p95 latency is about 15 s on complex turns.
  Infrastructure is demo-sized (one ECS task, single-AZ RDS). Saved routines *run* only with `PURSER_WORKFLOWS=1`.
- Full detail: [`submission/HONEST_NOTE.md`](submission/HONEST_NOTE.md) and [`submission/PRODUCTION.md`](submission/PRODUCTION.md).

## 8. Tests, evals and deployment

```bash
docker compose up -d db && uv sync
uv run pytest -q                                       # real Postgres (munshi_test); some tests call OpenAI
uv run python -m scripts.eval_run --arm B              # agent eval (46 scenarios); compare arms with --arm A1,B
uv run python -m scripts.text_harness "Travel mein kitna bacha hai?"   # one scripted turn against a reset dev DB
```

- AWS: CloudFront, ALB, ECS Fargate (one task), RDS Postgres 16, S3 and Secrets Manager, all in Terraform
  (`infra/terraform/`). It deploys from `main` with GitHub Actions over OIDC. Steps and rollback: [`docs/deployment.md`](docs/deployment.md).
- Architecture: [`docs/architecture.md`](docs/architecture.md). Results: [`submission/EVIDENCE.md`](submission/EVIDENCE.md).

## 9. Troubleshooting

| Symptom | Fix |
|---|---|
| `env_file ... required` error | Docker Compose older than v2.24. Upgrade, or create `.env` with `cp .env.example .env` |
| Port 8000 or 5433 in use | `APP_PORT=8100 DB_PORT=5444 docker compose up --build` |
| Agent says "AI is off on this server" | `OPENAI_API_KEY` is missing from `.env`. Add it, then `docker compose up -d --force-recreate app` |
| Voice does not start | Use Chrome, allow the microphone, and use `localhost` or `https`. Typing runs the same agent |
| FX or revenue screens slow or offline | Set `FX_PROVIDER=fixture` |
| Want the clean seed again | `docker compose down -v && docker compose up --build` |
