# Munshi: build status

Updated 2026-11-21 (IST). Branch `build/munshi-mvp`. Freeze **Sun 2026-11-22 14:00 IST**.
Plans: `docs/PLAN_v4.md` (finance core), `docs/PLAN_v5_people_ops.md` (HR scope).
Deployment status: **LOCAL ONLY**. Nothing is provisioned on AWS.

---

## 1. Completed

### 1.1 Voice (hour-0 spike, then productionised)
- GPT-Live-1.1 over browser WebRTC with **client delegation**. Each delegated request runs the Munshi agent on the server, and the answer goes back through `session.commentary.append` (`app/voice/live_bridge.py`, `POST /api/voice/session`).
- A Python **sideband** connection records server-observed transcripts (`session.input_transcript.delta`) as `VoiceTurn` rows, deduplicated by `event_id`. This is what makes a spoken "haan" count as a confirmation.
- Wake word "Munshi" (`web/src/wake.ts`). The user tested the spike by voice (`spikes/voice_spike`).

### 1.2 Agent (OpenAI Agents SDK)
- A single `MunshiAgent` (`app/agent/munshi.py`, prompt in `app/agent/prompts/munshi.md`) with `RunContextWrapper[MunshiContext]`. Tools read the actor and workspace from that context, never from model arguments.
- Conversation memory is a `SQLAlchemySession` keyed by conversation.
- A vision `ExtractorAgent` (`app/agent/extractor.py`) produces structured output and has no tools. Arithmetic is checked in Python afterwards.
- There are 62 tools (44 below + 18 revenue tools, section 2.3c):
  - **Finance reads:** `get_budget_status`, `list_budget_categories`, `explain_budget_change`, `resolve_party`, `get_attention_items`, `get_record`, `get_audit_history`.
  - **Intake:** `inspect_document`, `correct_extracted_field`, `find_reservations`, `close_intake`, `show_source`.
  - **Finance proposals:** `propose_submit_claim`, `propose_submit_bill`, `propose_approval`, `propose_settlement`.
  - **Proposal handling:** `get_pending_proposal`, `confirm_pending_proposal`, `cancel_pending_proposal`.
  - **Monthly budget:** `get_budget_month`, `get_budget_year`, `get_budget_alerts`, `get_budget_recommendations`, `forecast_budget`, `what_if`, `get_budget_history`, `propose_budget_change`, `propose_close_month`, `propose_apply_recommendations`.
  - **Charts and views:** `describe_chart_options`, `build_chart`, `revise_chart`, `read_chart_value`, `present_view`.
  - **People ops:** `find_people`, `get_leave_balance`, `list_leave_requests`, `propose_leave`, `propose_leave_decision`, `propose_onboarding`, `propose_message`, `read_inbox`, `get_onboarding_status`, `lookup_policy`.
- A text channel (`POST /api/agent/text`) and `scripts/text_harness.py` run the same agent and tools as voice.

### 1.3 Trust boundary: propose → present → confirm → receipt
- Each `propose_*` tool stores a proposal with canonical arguments, the affected rows and their versions, a preview generated on the server, and a 10-minute expiry. Only one proposal per conversation is in the foreground at a time.
- A confirmation counts only when one of these happens:
  - a **server-observed** voice turn after `presented_at` that the deterministic EN/HI/Hinglish classifier (`app/services/affirmation.py`, `confirmation.py`) accepts;
  - the on-screen Confirm button, which requires a cookie session, an Origin check and CSRF.
- Execution happens in one transaction:
  - re-authorise, then `SELECT … FOR UPDATE`;
  - check row versions; a mismatch marks the proposal **stale** and returns a new preview;
  - apply the ledger movements, write the audit events and the receipt.
- An idempotent replay returns the same receipt, so a repeated "yes" does not apply twice.

### 1.4 Finance domain
- **Budget ledger:** append-only (`app/services/budget.py`), with allocation, reserved, committed and spent buckets. The golden path moves Travel from ₹45,000 to ₹45,200: the ₹5,000 reservation is released and ₹4,800 is committed.
- **Claims:** submit, approve and settle. A beneficiary cannot approve their own claim.
- **Vendor bills:** submit (known or new vendor), approve and settle. Settlement is full only, and a second settlement is rejected.
- **Document intake** (`app/services/intake.py`, `storage.py`):
  - size, page count and type sniffing; encrypted or unreadable files are rejected;
  - SHA-256 replay detection and probable-duplicate checks;
  - reservation matching;
  - contracts and unsupported documents close with no finance write.
- **Records and audit trail** (`records.py`, `audit.py`).

### 1.5 People ops (PLAN_v5)
- **Leave:** request, approve and reject on a leave ledger with working-day counting. Overlaps are rejected and balances must stay consistent.
- **Onboarding:** creates the user and the onboarding checklist. Onboarding status can be queried.
- **Inbox:** direct messages and announcements, readable through `read_inbox` and `GET /api/inbox`.
- **Email:** a transactional outbox (`app/services/messaging.py`) sends through Gmail `SMTP_SSL` only after the confirming transaction commits, and only to `EMAIL_ALLOWED_RECIPIENTS`. Deliveries are listed per receipt. The user saw a real email arrive in an earlier check.
- **Policy Q&A:** `lookup_policy`.
- **Migration:** `ae79264e772f_people_ops`.

### 1.6 API and infrastructure (local)
- FastAPI with cookie sessions and CSRF, plus an SSE event stream (`/api/events`) that drives the UI cards. Error handling uses `DomainError`.
- `/health` pings the DB.
- Postgres 16 runs in docker-compose on port 5433, with the `munshi` (dev) and `munshi_test` databases.
- Alembic migrations: `57154705bbe1_init` and `ae79264e772f_people_ops`.
- The seed (`seed/seed_v1.py`) is synthetic and labelled. Characters:
  - Priya, the finance approver, and Arjun, an employee;
  - Neha, whose sample leave L1 is Thu 26 to Fri 27 Nov (2 working days);
  - the Pune trip with a ₹5,000 hotel reservation;
  - vendors, including near-duplicate names;
  - customers with open and overdue invoices.

### 1.7 Web UI (`web/`, React 19 + Vite + TypeScript)
- Ultra-minimal: a 3D orb (`Orb.tsx`), an artifacts panel and the wake word. It uses Equal AI's **palette only**, with no Equal logo or name.
- The cards (`cards.tsx`) are proposal (with Confirm and Cancel), receipt, source document, record, budget, inbox, leave and people. Card content comes from the server; nothing is hardcoded.

### 1.8 Tests (written and run only by Sonnet subagents, hook-enforced)
- There are 5 test files with 174 test functions, which expand to 270 test cases once parameterised: `test_ledger_gates.py`, `test_ledger_extra.py`, `test_intake_extra.py`, `test_api_intake.py` and `test_people_extra.py`.
- **Latest full run (Sonnet re-test, `sonnet-tester-hr-fixes`): 270 passed, 0 failed, 0 xfailed.** The 4 earlier strict xfails were real bugs. They are fixed in the app, and the tests now assert the fixed behaviour:
  1. Seed L1 counted Fri–Sat as 2 days. It is now Thu–Fri.
  2. A multi-line default subject broke `EmailMessage`. The subject header is now flattened to one line and capped at 200 characters.
  3. A subject over 200 characters raised a raw `DataError` at confirm. It is now a `VALIDATION` error at proposal time.
  4. A name over 120 characters raised a raw `DataError` at onboarding. It is now a `VALIDATION` error at proposal time.
- Earlier Sonnet rounds found 7 more bugs, all fixed.
- `ruff check` passes on `app/`, `seed/` and `tests/`.

### 1.9 Process guardrails
- `.claude/hooks/tests-only-in-sonnet.sh` (PreToolUse on Bash) stops the main session from running pytest, vitest, jest or npm test.
- `.claude/hooks/fresh-sonnet-per-test-set.sh` (PreToolUse on Agent and SendMessage) blocks two things:
  - reusing a tester through SendMessage;
  - spawning test work in a fork or on a model other than Sonnet.

  The hook passed piped sample inputs, but it has not yet been seen firing on a real tool call. The user may need to open `/hooks` once to reload it.
- `CLAUDE.md` and `docs/AUTHORSHIP.md` are kept truthful. `.env` is gitignored.

### 1.10 Commits
- `9b3416b feat: Munshi voice finance agent MVP (local)`, the checkpoint commit.
- **The HR round is uncommitted** (see section 2.1).

---

## 2. Still to do (in priority order)

### 2.1 Close out the HR round (now)
- [x] Sonnet re-test of the 4 fixes: 270 passed, xfail markers removed, tests tightened. The overlap tests needed no change, and no new bugs were found.
- [ ] Run a secret scan with `.env` excluded, then commit the HR round on `build/munshi-mvp`. This needs the user's go-ahead.
- [x] Update `docs/AUTHORSHIP.md` with the people-ops rows and the `test_people_extra.py` row (Sonnet).

### 2.2 Latency pass
- [ ] Bring the upload → extraction → spoken answer path down to about **5 s**. Options:
  - render pages smaller;
  - start extraction on upload instead of on the agent's call;
  - pass the "document ready" context to the agent with `thinking.append`;
  - use the fast model for routing.
- [ ] Measure and log each stage's latency: upload, render, extract and agent turn.

### 2.3 Dynamic charts and views: BUILT, Sonnet gate passed
- [x] `app/services/charts.py` contains:
  - `ChartSpec`, `ChartSpecPatch` and `ViewSpec`, all enum-limited;
  - a registry of 4 sources (receivables, payables, claims, budget) with 14 measures and 12 dimensions;
  - a SQLAlchemy Core compiler scoped to the workspace and role. It has a 3 s statement timeout and a 500-group cap, and filter values are matched against real records (ambiguous values return `AMBIGUOUS`);
  - chart-type rules, plus a deterministic `auto` picker;
  - top_n and >3-series folding into "Other", and month gap-fill.
- [x] Tools `build_chart`, `revise_chart`, `read_chart_value`, `describe_chart_options` and `present_view`. The prompt now has a "Charts and views" section that pins down the direction of money.
- [x] `result_snapshots` (the table already existed) drive the chart, the table and the speech. `read_chart_value` reads the stored rows and never queries again. `GET /api/snapshots/{id}` is readable only by the owner.
- [x] `web/src/ChartCard.tsx`:
  - a generic ECharts card built from `snapshotToOption()`;
  - ₹ K/L/Cr axes, a table toggle with source refs, and a highlight for the value that was read;
  - KPI tiles, a `ViewCard`, and the active filters listed under the chart;
  - a revision replaces its earlier card through `lineage`.
- [x] Receivables demo, verified through the real agent (text harness) and in the browser: "kaun paisa dena baaki hai" → ₹5,42,700, then "sirf overdue" → ₹2,34,700 with the customer grouping kept, then "Acme ka amount padho" → ₹1,25,000 with the bar highlighted.
- [x] Sonnet test gate `tests/test_charts.py` (agent `sonnet-tester-charts`):
  - 51 tests, all passing, with no strict-xfail bugs; `ruff check tests/` passes.
  - Full suite: 319 passed and 2 failed. Both failures were mistakes in the tester's own new tests, not app bugs, and are now fixed. With them, `test_charts.py` passes 51/51 on its own.
  - Since confirmed by the 2.3b full-suite run (353 passed).
- Known behaviour (by design):
  - at most 3 measures per chart;
  - filter matching falls back to substring matching;
  - punctuation is stripped before matching, so `Acme%' --` resolves to an ambiguous "acme" (a clean error, no SQL).
- Note: running the Vite dev server on :5173 needs `APP_ORIGIN=http://localhost:5173` for the API's origin check.

### 2.3b Monthly budget brain, ported from the user's copilot (BUILT, Sonnet gate passed)
Gap analysis and plan are in `~/.claude/plans/this-code-was-written-starry-knuth-*.md`. Out of scope before the freeze:
- MIS/type hierarchy;
- reject, send back, two-level and bulk approval;
- payment batches and bank files;
- workbook import/export.

What is built:
- [x] **Migration `3b068d9a8dab_budget_months`:** adds `budget_movements.fiscal_month` (with a backfill) and a `budget_periods` table, where a closed month freezes its actual and status.
- [x] **Ported pure maths:** `app/services/budgeting/` holds the user's own earlier code: pacing, status bands, forecast, projection, distribution and trend + plan.
- [x] **Service:** `app/services/budget_months.py` provides the month grid, alerts, transfer/top-up/reduce with guards, month close with variance reason and carry-over, recommendations with the apply-once plan, forecasts, what-if and history.
- [x] **Actions:** `budget_change`, `close_month` and `apply_recommendations` all go through propose → confirm → receipt.
- [x] **Ten new agent tools** (44 in total), plus a prompt section. The bell (`get_attention_items`) now includes budget alerts, months due for close and open recommendations.
- [x] **Charts:** a `budget_month` dimension and the `budget_actual`/`budget_remaining` measures.
- [x] **UI:** a 12-month strip on the budget card, served by `GET /api/budget/lines/{id}/months`.
- [x] **Seed:**
  - a monthly plan from Jul 2026 with the annual totals unchanged (Travel still ₹45,000 → ₹45,200);
  - Jul–Sep closed as a synthetic imported snapshot, with **October left open on purpose**;
  - Office Supplies at its November limit.
- [x] **Verified through the real agent (text harness, Hinglish):**
  - alert → month budget;
  - "October close karo" (reasons from speech, ₹2,500 Events carry-over) → a recommendation appears (Events −66.7%, IT & Cloud +68.4%; plan: ₹1,666 transfer + ₹8,600 top-up) → applied with "haan";
  - what-if (IT +15% from Dec);
  - a transfer;
  - history.

  The budget card was checked in the browser.
- [x] Sonnet gate `tests/test_budget_months.py` (32 tests, no bugs):
  - Final full-suite run: **353 passed, 0 failed, 0 xfailed**; `ruff check tests/` clean.
  - One existing test was updated for the seed change: `test_ledger_extra.py::test_double_settle_via_two_open_proposals_executes_once` now checks spent before + the bill amount, because of ₹9,400 of imported Jul–Sep actuals.

### 2.3c Client revenue, ported from the user's copilot (BUILT, Sonnet gate running)
Source: `~/Projects/copilot/clients/CLIENT_REVENUE.md`. Plan: `~/.claude/plans/i-have-a-detailed-agile-pebble-*.md`. Excel import/export is out of scope.

What is built:
- [x] **Migration `5f9c0723f1cc_revenue_core`** (Postgres only): `invoices` gains billing month, original currency + `amount_minor`, `fx_rate_micro`/source/date, status, kind, period, cycle, moved balance, `version`; `parties` gains client currency/state/archive/version; new `invoice_payments`, `client_cycles`, `fx_quotes`, `fx_months`, `reminders`. The 6 old invoices are backfilled. Up/down/up verified.
- [x] **Services `app/services/revenue/`**: sync SQLAlchemy run through `AsyncSession.run_sync`, so the copilot code ports with its logic intact. `money.py`/`fiscal.py` copied unchanged. A `before_flush` listener bumps invoice/client versions on any change.
- [x] **13 actions** (`app/services/revenue_actions.py`): add invoices, send/unsend, payment (single or allocated), edit/rate/delete, refresh rate, move balance, client change, billing cycle, plan FY, month FX rate, end project. `plan()` is a real trial run in a SAVEPOINT, rolled back; touched rows become `affected` (stale on change).
- [x] **Grounding**: an amount or rate must appear in the user's recent server-observed turns (digits, 1.5L/30k, and English/Hindi/Hinglish number words).
- [x] **ECB**: async Frankfurter refresh (6 s timeout) before the sync run, cached in `fx_quotes`; stale fallback; `FX_PROVIDER=fixture` for tests/offline.
- [x] **18 agent tools** (62 total) + "Revenue" prompt section; `get_attention_items` now carries revenue chases, raises, check-ins and reminders.
- [x] **Charts**: receivables use the revenue figures (billed less moved, outstanding = sent/part paid only); new measures `to_raise_amount`, `overdue_amount`, `fx_gain`; dims `billing_month`, `currency`, `client_state`.
- [x] **UI**: Revenue card (4 KPIs + client×month grid, word+colour status, opens on the current month), Invoice card (cell click opens it), Conversion-rates card. Endpoints `/api/revenue/overview|invoices/{ref}|fx`. Checked in the browser.
- [x] **Seed**: Northwind Labs (synthetic, USD monthly, hand-set Sep/Oct rates), Kaveri Foods (synthetic, INR quarterly advance), Orbit Design Studio (synthetic, paused), a reminder due today. Old 6 invoices unchanged (still ₹5,42,700 outstanding among them; the whole book is now ₹6,48,550 outstanding / ₹3,40,550 overdue at seed).
- [x] **Real agent (text harness, Hinglish)**: overview → send Northwind Nov → ₹50,000 part payment → (refuses to move the balance before the payment is confirmed) → balance to December → "November ka dollar rate 84.20" reprices 5 invoices → pending items → Friday reminder.
- [ ] Sonnet gate `tests/test_revenue_core.py` (agent `sonnet-tester-revenue-core`), then a second fresh gate for FX / cycles / balance / project end.
- Known: reply latency 7–16 s per turn (see 2.2).

### 2.4 Roles and failure paths (PLAN_v4 H13–15)
- [ ] Confirm the gates already covered by the existing tests:
  - an employee cannot view another person's claim or approve a bill;
  - an object ID from another workspace returns 404;
  - a failed transaction leaves balances unchanged.
- [ ] Add a test for any of these that is missing.
- [ ] Do one uninterrupted session covering every advertised workflow, logged in as Priya and as Arjun.

### 2.5 AWS deployment (needs **explicit spend authorisation** first)
- [ ] Read-only preflight:
  - `aws sts get-caller-identity`, the region, and any ACM certificates or Route 53 zones;
  - service quotas;
  - a cost estimate covering ALB, Fargate at 0.5 vCPU / 1 GB, RDS `db.t4g.micro`, S3, Secrets Manager and CloudWatch, with no NAT.

  The aws-mcp server failed to connect this session, so use the AWS CLI.
- [ ] Ask the user to authorise spend and show them the estimate.
- [ ] Write a multi-stage `Dockerfile` (Vite build served by FastAPI) and `.dockerignore`. Neither exists yet.
- [ ] Terraform in `infra/terraform/`, which does not exist yet:
  - networking: a VPC with public subnets for Fargate and private subnets for RDS;
  - HTTPS: an ALB, with ACM if there is a domain, otherwise CloudFront on its default domain. HTTPS is needed for mic access;
  - compute and storage: ECS Fargate, ECR, RDS Postgres, and a private S3 bucket with a gateway endpoint;
  - Secrets Manager for the OpenAI key, DB credentials, session secret and Gmail app password, plus CloudWatch logs;
  - a one-off migration and seed task.
- [ ] Storage adapter: switch from the local filesystem to S3 in AWS.
- [ ] Gate: `/health` returns 200 over HTTPS, and the spoken golden path works on the live URL. Otherwise record the blocker as **BLOCKED**.

### 2.6 Evaluation set (`evals/`, only `evals/dev/` exists so far)
- [ ] Freeze the expected outcomes in `cases.yaml` **before** running anything.
- [ ] Prepare the material:
  - about 15 text workflows;
  - about 20 recorded commands in Hindi, Hinglish and English;
  - 10 held-out synthetic documents.
- [ ] Write `run_eval.py`. It should report, with denominators:
  - accuracy per language for amount, party and date;
  - extraction field accuracy and error-detection rate;
  - zero unauthorised or duplicate writes;
  - ledger conservation.
- [ ] Save the results to `evals/results/<commit>.json` and `docs/evidence.md`.

### 2.7 CI/CD
- [ ] Extend `.github/workflows/ci.yml` to run ruff, pytest against a Postgres service, `tsc --noEmit`, `vite build`, `terraform fmt -check` and `terraform validate`.
- [ ] Add `deploy.yml`, triggered by `workflow_dispatch`:
  - authenticate with a **GitHub OIDC** least-privilege role;
  - build an image tagged with the commit, migrate and deploy;
  - smoke-test `/health` and the scripted text golden path.
- [ ] Do not mark CI/CD as working until a workflow actually succeeds.

### 2.8 Submission (PLAN_v4 H17–18)
- [ ] Update `README.md` with run, deploy and rollback steps. Add `docs/deployment.md` (URL, commit, migration, seed version) and `docs/demo.md` (a script under 4 minutes with expected results).
- [ ] Make a labelled backup demo recording.
- [ ] Do a timed rehearsal.
- [ ] Finalise `docs/AUTHORSHIP.md` as a truthful honest note.
- [ ] Submit before 14:00 IST on Sunday.

### Cut line, if time runs short
Cut in this order: budget transfer, then slide polish, then the briefing. If voice fails, fall back to push-to-talk. If the deploy slips, demo locally with a labelled recording. Charts can shrink to the receivables measures only.

---

## 3. Needed from the user
1. **A fresh demo hotel receipt** (about ₹4,800, Pune), made outside the repo. It must not be in the eval set.
2. **AWS spend authorisation** after reviewing the preflight cost estimate, plus the region and whether a domain or ACM certificate exists.
3. **Commit go-ahead** for the HR round (the re-test has passed).
4. Optionally, open `/hooks` once so the new fresh-Sonnet hook is definitely loaded.

## 4. Standing constraints
- Never expose `OPENAI_API_KEY` or the Gmail app password. `.env` is never committed. In AWS, secrets come from Secrets Manager.
- Real email goes only to `EMAIL_ALLOWED_RECIPIENTS`.
- No AWS spend or provisioning without explicit authorisation.
- Only Sonnet subagents write or run tests, and each set of tests uses a **new** Sonnet agent.
- Label synthetic data. Use Equal's palette only.
- Commit only when asked, and on a branch.
