# Graph Report - Builders  (2026-11-21)

## Corpus Check
- 113 files · ~123,131 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 3, .example 1, .ini 1)

## Summary
- 1894 nodes · 5959 edges · 105 communities (75 shown, 30 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 576 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e3d276ed`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Phase 3: AWS Deployment and CI/CD
- hygiene
- test_ledger_gates.py
- session_scope
- models.py
- ._target
- App.tsx
- test_budget_months.py
- package.json
- event_stream
- document
- MUNSHI: Voice-only, agent-centric finance and operations copilot
- get_settings
- DomainError
- Munshi | Product and delivery plan v2
- server.py
- test_people_extra.py
- compilerOptions
- Conversation
- live_bridge.py
- Munshi | Final weekend build plan
- Munshi | Build plan v3 (scope cut for the weekend)
- 5. Agent architecture
- munshi.md
- 5. Financial record lifecycles
- Munshi architecture decisions
- AUTHORSHIP.md
- builders
- tools/proposals.py
- records.py
- format_inr
- 2. Still to do (in priority order)
- errors.py
- Plan
- env.py
- Settings
- services/budget_months.py
- projection.py
- Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST)
- fresh-sonnet-per-test-set.sh
- tests-only-in-sonnet.sh
- Agent
- main.py
- get
- Request
- Response
- cycles.py
- services/charts.py
- tools/budget_months.py
- test_charts.py
- test_api_intake.py
- tools/charts.py
- Actor
- Invoice
- cards.tsx
- ChartCard.tsx
- Rev
- extractor.py
- revenue.py
- LiveVoice
- ChartSpecPatch
- WakeWord
- budgeting/__init__.py
- BaseModel
- test_ledger_extra.py
- month_label
- DomainError
- RevAction
- fx_months.py
- User
- tools/people.py
- fx.py
- actions.py
- recommendations
- revenue/money.py
- classify
- distribution.py
- grounding.py
- run_spec
- .plan
- pacing.py
- RevenueCard.tsx
- read_value
- Mail
- Action
- FakeSMTP
- .due_on
- .__init__
- lifespan
- close_oct
- .total_paise
- Any

## God Nodes (most connected - your core abstractions)
1. `session_scope()` - 223 edges
2. `make_actor()` - 183 edges
3. `Rev` - 77 edges
4. `Invoice` - 75 edges
5. `Actor` - 68 edges
6. `DomainError` - 65 edges
7. `Party` - 64 edges
8. `propose_and_confirm()` - 62 edges
9. `seed()` - 49 edges
10. `User` - 48 edges

## Surprising Connections (you probably didn't know these)
- `gitleaks Secret Scanning` --semantically_similar_to--> `Secrets via Secrets Manager / SSM`  [INFERRED] [semantically similar]
  README.md → CLAUDE.md
- `_party_id()` --uses--> `Party`  [INFERRED]
  tests/test_intake_extra.py → app/models.py
- `test_bill_needs_a_vendor_and_prefers_existing_id()` --uses--> `Party`  [INFERRED]
  tests/test_intake_extra.py → app/models.py
- `test_new_vendor_bill_creates_vendor_only_on_confirm()` --uses--> `Party`  [INFERRED]
  tests/test_intake_extra.py → app/models.py
- `test_new_vendor_name_matching_existing_vendor_does_not_create_duplicate()` --uses--> `Party`  [INFERRED]
  tests/test_intake_extra.py → app/models.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Candidate AWS Hosting Runtimes** — claude_aws_app_runner, claude_aws_lambda_api_gateway, claude_aws_ecs_fargate, claude_s3_cloudfront [EXTRACTED 1.00]
- **Hackathon Delivery Phases 0-4** — claude_phase_0, claude_phase_1, claude_phase_2, claude_phase_3, claude_phase_4 [EXTRACTED 1.00]
- **Secure CI/CD Pipeline** — claude_github_actions, claude_github_oidc, claude_terraform, claude_least_privilege_iam, readme_ci_hygiene_checks [INFERRED 0.85]

## Communities (105 total, 30 thin omitted)

### Community 0 - "Phase 3: AWS Deployment and CI/CD"
Cohesion: 0.07
Nodes (38): Tiny Agent Evaluation Set, Agent Guardrails (step limits, budgets, timeouts, retries), AWS App Runner, AWS ECS Fargate, AWS Lambda + API Gateway, Change-Scope Rules, CLAUDE.md Hackathon Agent Rules, Cost Awareness (+30 more)

### Community 1 - "hygiene"
Cohesion: 0.08
Nodes (24): concurrency, cancel-in-progress, group, GITLEAKS_VERSION, env, name, runs-on, steps (+16 more)

### Community 2 - "test_ledger_gates.py"
Cohesion: 0.12
Nodes (46): Proposal, position(), cancel(), canonical(), confirm(), ConfirmOutcome, create(), get_open() (+38 more)

### Community 3 - "session_scope"
Cohesion: 0.07
Nodes (84): One transaction; commits on success, rolls back on any exception., session_scope(), Document, add_inspected_document(), make_actor(), cells(), test_budget_month_chart_for_it_and_cloud(), test_employee_is_forbidden() (+76 more)

### Community 4 - "models.py"
Cohesion: 0.13
Nodes (33): AuditEvent, Bill, BudgetLine, CompanyPayment, InvoicePayment, Policy, SQLAlchemy models. Money is integer paise; timestamps are UTC; business dates…, Full settlement only (weekend scope). One per record, enforced by the unique… (+25 more)

### Community 5 - "._target"
Cohesion: 0.18
Nodes (8): _apply(), Approve, ApproveBill, ApproveClaim, _budget_effect(), Any, Dispatch approval by record ref prefix (C = claim, B = bill)., Settle

### Community 6 - "App.tsx"
Cohesion: 0.14
Nodes (15): react, api, ApiError, call(), Card, Me, setSession(), App() (+7 more)

### Community 7 - "test_budget_months.py"
Cohesion: 0.11
Nodes (28): compute_status(), Month-end utilisation status: OPEN (no positive budget), UNDERUSED (< 85%),…, allocated(), allocated_in(), change(), code_of(), count_movements(), paise() (+20 more)

### Community 8 - "package.json"
Cohesion: 0.06
Nodes (31): echarts, @fontsource/dm-sans, @fontsource/geist-mono, @fontsource/noto-sans-devanagari, react-dom, @types/react, @types/react-dom, typescript (+23 more)

### Community 9 - "event_stream"
Cohesion: 0.12
Nodes (14): In-process event fan-out to the browser (SSE), keyed by conversation. One…, subscribe(), unsubscribe(), domain_error(), event_stream(), no_shared_cache(), DomainError, Server-sent events for this conversation: cards, user/assistant turns. (+6 more)

### Community 10 - "document"
Cohesion: 0.15
Nodes (28): Convert DomainError into a structured result the agent can explain; log name,…, safe_tool(), ensure_extraction(), prefetch(), Document reading (vision extraction) shared by the upload path and the…, _read(), close_intake(), correct_extracted_field() (+20 more)

### Community 11 - "MUNSHI: Voice-only, agent-centric finance and operations copilot"
Cohesion: 0.08
Nodes (25): 0. Planning inputs and research status, 10. Contract liability analysis (re-implemented from the user's guide), 11. Bill and receipt extraction, 12. External integrations, 13. Data model (Postgres; money = BIGINT paise; timestamps UTC, IST display; FY Apr-Mar), 14. Repository layout (this repo, `~/Projects/Builders`), 15. AWS deployment and CI/CD, 16. Security and trust (+17 more)

### Community 12 - "get_settings"
Cohesion: 0.11
Nodes (25): _actor(), check_write(), current_actor(), current_csrf(), login(), Request, Response, Cookie session auth + CSRF. The Actor is derived from the server session on… (+17 more)

### Community 14 - "Munshi | Product and delivery plan v2"
Cohesion: 0.12
Nodes (16): 10. Data design and isolation, 11. Secondary workflows and integrations, 12. Implementation and deployment, 13. Build sequence and cut decisions, 14. Acceptance, evaluation and evidence, 15. Four-minute demonstration and handoff, 16. Definition of done, 1. User, problem and submission (+8 more)

### Community 15 - "server.py"
Cohesion: 0.17
Nodes (11): Bridge, create_session(), get_budget_status(), index(), BaseModel, function_tool, get, Request (+3 more)

### Community 16 - "test_people_extra.py"
Cohesion: 0.08
Nodes (69): LeaveMovement, LeaveRequest, Message, Append-only leave ledger per user and type. available = granted - reserved -…, Inbox item and/or email outbox row. Email rows are delivered after the…, dispatch(), Send queued emails. Each row is claimed with SKIP LOCKED so concurrent…, propose_and_confirm() (+61 more)

### Community 17 - "compilerOptions"
Cohesion: 0.13
Nodes (14): compilerOptions, isolatedModules, jsx, lib, module, moduleResolution, noEmit, noUnusedLocals (+6 more)

### Community 18 - "Conversation"
Cohesion: 0.27
Nodes (10): configure(), engine(), AsyncSession, sessionmaker(), Conversation, async_sessionmaker, AsyncEngine, main() (+2 more)

### Community 19 - "live_bridge.py"
Cohesion: 0.19
Nodes (9): bridge_for(), client(), LiveBridge, GPT-Live sideband bridge: server-observed transcripts -> voice_turns;…, Speak text in the live session if it is still open. Never raises; returns…, say(), session_config(), start() (+1 more)

### Community 20 - "Munshi | Final weekend build plan"
Cohesion: 0.17
Nodes (9): 1. Product promise and scope, 2. Intake and accounting decisions, 3. Conversation and confirmation, 4. Architecture and deployment gates, 5. Delivery budget and cut line, 6. Demo and evaluation, Budget fixture and acceptance, Munshi | Final weekend build plan (+1 more)

### Community 21 - "Munshi | Build plan v3 (scope cut for the weekend)"
Cohesion: 0.17
Nodes (12): 0. Why a v3, 1. Product in one sentence, 2. P0: what must work, deployed on AWS, 3. What we cut, and why, 4. Four-minute demo (golden path), 5. Architecture (minimum that ships), 6. Evidence for the submission, 7. Build order (clock times, IST) (+4 more)

### Community 22 - "5. Agent architecture"
Cohesion: 0.25
Nodes (8): 5.1 Topology, 5.2 Agent specification (per CLAUDE.md), 5.3 Prompts (in `backend/app/agent/prompts/`), 5.4 Confirmation protocol (all write tools), 5.5 Proactivity, 5.6 Memory and context, 5.7 Multilingual, 5. Agent architecture

### Community 23 - "munshi.md"
Cohesion: 0.18
Nodes (10): Charts and views, Facts, Language, Monthly budget, alerts, changes and month close, Other requests, People and HR, Revenue: client invoices and money coming in, Voice conversation context (+2 more)

### Community 24 - "5. Financial record lifecycles"
Cohesion: 0.40
Nodes (5): 5. Financial record lifecycles, Budgets, reservations and spend, Employee claims and reimbursements, Revenue, invoicing and collections, Vendor bills and approvals

### Community 25 - "Munshi architecture decisions"
Cohesion: 0.50
Nodes (3): Evidence (local spike, `spikes/voice_spike`, synthetic fixture), Munshi architecture decisions, Voice transport and confirmation (H0 gate, 2026-11-21) — DECIDED

### Community 38 - "tools/proposals.py"
Cohesion: 0.17
Nodes (22): cancel_pending_proposal(), _confirm(), confirm_pending_proposal(), get_pending_proposal(), _proposal_view(), propose_approval(), propose_settlement(), propose_submit_bill() (+14 more)

### Community 39 - "records.py"
Cohesion: 0.22
Nodes (20): record_detail(), _approve_bill_inputs(), _approve_claim_inputs(), _bill_inputs(), _require_approver(), _settle_inputs(), get_line(), movements() (+12 more)

### Community 40 - "format_inr"
Cohesion: 0.15
Nodes (24): _attention(), explain_budget_change(), get_attention_items(), get_audit_history(), get_budget_status(), get_record(), list_budget_categories(), _pos_view() (+16 more)

### Community 41 - "2. Still to do (in priority order)"
Cohesion: 0.07
Nodes (26): 1.10 Commits, 1.1 Voice (hour-0 spike, then productionised), 1.2 Agent (OpenAI Agents SDK), 1.3 Trust boundary: propose → present → confirm → receipt, 1.4 Finance domain, 1.5 People ops (PLAN_v5), 1.6 API and infrastructure (local), 1.7 Web UI (`web/`, React 19 + Vite + TypeScript) (+18 more)

### Community 42 - "errors.py"
Cohesion: 0.15
Nodes (15): Agent, MunshiContext, Passed to every tool via RunContextWrapper. Identity comes only from here,…, build_agent(), _instructions(), MunshiAgent: one conversational agent with typed tools. Same agent for voice…, memory(), One user turn through MunshiAgent. Shared by the text channel, push-to-talk and… (+7 more)

### Community 43 - "Plan"
Cohesion: 0.19
Nodes (10): Execution, Plan, SubmitBill, ApplyRecommendations, BudgetChange, _change_plan(), _close_plan(), CloseMonth (+2 more)

### Community 44 - "env.py"
Cohesion: 0.27
Nodes (9): Connection, do_run_migrations(), include_object(), Run migrations in 'offline' mode. This configures the context with just a URL…, In this scenario we need to create an Engine and associate a connection with…, Run migrations in 'online' mode., run_async_migrations(), run_migrations_offline() (+1 more)

### Community 45 - "Settings"
Cohesion: 0.25
Nodes (3): Settings, BaseSettings, field_validator

### Community 46 - "services/budget_months.py"
Cohesion: 0.17
Nodes (35): BudgetPeriod, One category-month. Open months read the ledger; a closed month keeps its…, _rec_plans(), alerts(), apply_change(), apply_close(), Cell, ChangePlan (+27 more)

### Community 47 - "projection.py"
Cohesion: 0.11
Nodes (20): month_outlook(), Outlook, Where spend is heading (run rate), for the CEO's three bars: allocated, spent,…, budgets / spends: the FY's 12 months in order; current: index of this month (0…, year_outlook(), Change, Month, pace_of() (+12 more)

### Community 48 - "Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST)"
Cohesion: 0.50
Nodes (3): Added capabilities (same agent, same propose → confirm → receipt engine), Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST), Rules

### Community 53 - "main.py"
Cohesion: 0.11
Nodes (40): agent_text(), audit_feed(), budget_line(), budget_line_months(), cancel_button(), confirm_button(), document_page(), get_proposal() (+32 more)

### Community 57 - "cycles.py"
Cohesion: 0.08
Nodes (63): ClientCycle, A client's billing cycle from a month on: monthly charge, every N months,…, active(), active(), apply(), ChangePlan, check(), _clashes() (+55 more)

### Community 58 - "services/charts.py"
Cohesion: 0.12
Nodes (32): _ageing(), _bad(), _budget(), ChartType, _claims(), Compiled, Dim, DimensionName (+24 more)

### Community 59 - "tools/budget_months.py"
Cohesion: 0.13
Nodes (33): bm_round(), forecast_budget(), get_budget_alerts(), get_budget_history(), get_budget_month(), get_budget_recommendations(), get_budget_year(), MonthSplit (+25 more)

### Community 60 - "test_charts.py"
Cohesion: 0.16
Nodes (28): build(), client_for(), err(), err_sync(), priya_arjun(), DomainError, parametrize, Dynamic charts: validation, chart-type rules, totals vs independent SQL,… (+20 more)

### Community 61 - "test_api_intake.py"
Cohesion: 0.09
Nodes (25): BudgetMovement, Append-only. Balance of each bucket = SUM(amount_paise)., client_for(), _pdf(), parametrize, HTTP layer + intake gates that need no model: auth, CSRF, upload outcomes,…, test_arithmetic_check(), test_button_confirm_and_replay() (+17 more)

### Community 62 - "tools/charts.py"
Cohesion: 0.19
Nodes (21): build_chart(), _card(), describe_chart_options(), present_view(), Ctx, function_tool, safe_tool, Chart and view tools. The model composes typed specs; every number comes from a… (+13 more)

### Community 63 - "Actor"
Cohesion: 0.13
Nodes (25): Actor, The authenticated principal. Always derived from the server session, never from…, Finance approval rights., HR/admin rights: onboarding, company-wide announcements, all leave., AsyncSession, record(), accept_upload(), breakdown_sum() (+17 more)

### Community 64 - "Invoice"
Cohesion: 0.10
Nodes (59): Invoice, A customer invoice (revenue). Ported from the copilot Revenue module. Billing…, Allocation, BalancePlan, billed_paise(), by_ref(), _cache(), check_due_on() (+51 more)

### Community 65 - "cards.tsx"
Cohesion: 0.15
Nodes (18): AuditCard(), BudgetCard(), Deliveries(), fmt(), InboxCard(), LEAVE_NAME, LeaveCard(), LeaveRequestsCard() (+10 more)

### Community 66 - "ChartCard.tsx"
Cohesion: 0.18
Nodes (15): ChartCard(), compactInr(), DataTable(), fmtAxis(), fmtFull(), fullInr(), Meta, pivot() (+7 more)

### Community 67 - "Rev"
Cohesion: 0.10
Nodes (54): Party, A dated in-app reminder ('remind me Friday to chase Acme'), optionally about a…, Reminder, client(), clients(), create_client(), _currency(), find_clients() (+46 more)

### Community 68 - "extractor.py"
Cohesion: 0.24
Nodes (12): build_agent(), Cite, extract(), ExtractedDocument, LineItem, Agent, BaseModel, ExtractorAgent: reads document page images into a typed schema. It has NO… (+4 more)

### Community 69 - "revenue.py"
Cohesion: 0.09
Nodes (51): _propose(), add_reminder(), go(), complete_reminder(), get_client(), get_fx_rates(), get_invoice(), get_revenue_overview() (+43 more)

### Community 70 - "LiveVoice"
Cohesion: 0.29
Nodes (4): setConversation(), Desk(), cardKey(), LiveVoice

### Community 71 - "ChartSpecPatch"
Cohesion: 0.33
Nodes (10): apply_patch(), chart_problem(), ChartSpecPatch, A revision. Anything omitted keeps its current value, so grouping survives…, Why the requested chart type does not fit the spec's shape, or None., spec(), test_add_filters_replaces_and_clear_filters(), test_month_to_customer_with_line_falls_back_to_auto() (+2 more)

### Community 72 - "WakeWord"
Cohesion: 0.32
Nodes (3): SR, wakeSupported, WakeWord

### Community 76 - "test_ledger_extra.py"
Cohesion: 0.12
Nodes (43): Receipt, AsyncSession, Return evidence for confirming `p`, or raise CONFIRMATION_REQUIRED with the…, record_turn(), spoken_confirmation(), assert_conservation(), code_of(), count() (+35 more)

### Community 77 - "month_label"
Cohesion: 0.10
Nodes (32): bucket_label(), fy_months(), fy_of(), fy_start(), fy_today(), month_label(), period_label(), period_months() (+24 more)

### Community 78 - "DomainError"
Cohesion: 0.15
Nodes (23): DomainError, _clean_num(), _eff(), _fx_note(), _invoices_by_refs(), money_minor(), Outcome, parse_date() (+15 more)

### Community 79 - "RevAction"
Cohesion: 0.07
Nodes (18): AddInvoices, _ccy(), ClientChange, DeleteDraft, EditInvoice, MoveBalance, Session, {label: value} the user must have said. (+10 more)

### Community 80 - "fx_months.py"
Cohesion: 0.12
Nodes (28): FxMonth, A conversion rate set by hand for a currency and month; carries forward until…, Affected, apply(), carried_months(), Change, effective(), foreign() (+20 more)

### Community 81 - "User"
Cohesion: 0.19
Nodes (24): get_leave_balance(), get_onboarding_status(), Onboarding checklist for a new joiner: each task, owner, due date and status., Leave balance (CL, SL, EL: granted, held for pending requests, used,…, leave_card(), person_card(), User, _leave_inputs() (+16 more)

### Community 82 - "tools/people.py"
Cohesion: 0.19
Nodes (21): find_people(), list_leave_requests(), lookup_policy(), _person(), propose_leave(), propose_leave_decision(), propose_message(), propose_onboarding() (+13 more)

### Community 83 - "fx.py"
Cohesion: 0.14
Nodes (21): FxQuote, Cached ECB reference quotes (Frankfurter): INR per unit x 10^6, by publication…, cached(), _frankfurter(), latest(), _newest(), AsyncSession, date (+13 more)

### Community 84 - "actions.py"
Cohesion: 0.16
Nodes (11): OnboardingTask, ApplyLeave, DecideLeave, _fmt_date(), _leave_decision_inputs(), _message_inputs(), _onboard_inputs(), OnboardEmployee (+3 more)

### Community 85 - "recommendations"
Cohesion: 0.17
Nodes (19): The plan for `target`, without steps already applied for that month (same kind,…, recommendations(), short(), still_to_do(), ClosedMonth, plan(), slots(), PlannedChange (+11 more)

### Community 86 - "revenue/money.py"
Cohesion: 0.15
Nodes (19): currencies_in(), digits(), from_minor(), _indian(), numbers_in(), paise_str(), paise_to(), Decimal (+11 more)

### Community 87 - "classify"
Cohesion: 0.18
Nodes (14): Affirmation, classify(), _contains_affirm(), _normalize(), Deterministic classifier for a confirmation utterance (English, Hindi,…, parametrize, test_affirm_variants(), test_devanagari_softener_na_affirms() (+6 more)

### Community 88 - "distribution.py"
Cohesion: 0.20
Nodes (13): by_weights(), even_split(), Divide `total_paise` into `n` parts that sum exactly to it (remainder on the…, Annual -> monthly budget distribution (PRD §3). Integer paise only; no paise is…, Keep the `locked` month indices as given and spread `total_paise - sum(locked)`…, Split `total_paise` in proportion to `weights` (exact fractions, no floats).…, Growing shares: the first month weighs 1 and each next month weighs the one…, The paise each of `months` gets out of `total_paise` (same order, summing to… (+5 more)

### Community 89 - "grounding.py"
Cohesion: 0.26
Nodes (13): _normal(), numbers_spoken(), Actor, AsyncSession, Decimal, A model never supplies a booked amount or rate on its own: the number must…, The user's last few server-observed turns in this conversation, newest last.…, Each non-empty value must appear in the user's recent words, else ask them to… (+5 more)

### Community 90 - "run_spec"
Cohesion: 0.22
Nodes (13): _auto_chart(), ChartSpec, _fold(), fold_by(), _month_label(), _month_range(), _order(), k() (+5 more)

### Community 91 - ".plan"
Cohesion: 0.22
Nodes (8): EndProject, FxMonthRate, Actor, AsyncSession, Set a currency's conversion rate for months; it carries forward to March.…, Project over: raise each pending invoice (separate), fold them into one…, require_edit(), trial()

### Community 92 - "pacing.py"
Cohesion: 0.24
Nodes (9): compute(), days_in_month(), Pacing, date, The pacing / burn-velocity engine and the proactive alert levels (PRD §4). Pure…, `day` is the current day of the month (1..total_days); use total_days for a…, _round2(), test_pacing_approaching_and_limit() (+1 more)

### Community 93 - "RevenueCard.tsx"
Cohesion: 0.31
Nodes (6): FxRatesCard(), InvoiceCard(), RevenueCard(), SHORT, STATUS, useLoad()

### Community 94 - "read_value"
Cohesion: 0.29
Nodes (7): fmt_value(), public(), Look a value up in the stored rows (never a new query), so speech matches what…, The card payload: numbers as integers plus display strings computed here, not…, read_value(), match(), test_read_value_does_not_requery()

### Community 95 - "Mail"
Cohesion: 0.29
Nodes (4): fixture, frozen_today(), Mail, boom()

### Community 96 - "Action"
Cohesion: 0.47
Nodes (4): Action, Actor, AsyncSession, Protocol

### Community 102 - "close_oct"
Cohesion: 0.67
Nodes (3): close(), close_oct(), test_recommendations_and_still_to_do_after_close()

## Knowledge Gaps
- **182 isolated node(s):** `Voice conversation context`, `Language`, `Facts`, `Workflow for a new document (receipt or bill)`, `Writes: propose, present, confirm` (+177 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 613 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **30 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `session_scope()` connect `session_scope` to `test_ledger_gates.py`, `test_budget_months.py`, `document`, `get_settings`, `test_people_extra.py`, `Conversation`, `live_bridge.py`, `tools/proposals.py`, `records.py`, `format_inr`, `errors.py`, `main.py`, `tools/budget_months.py`, `test_charts.py`, `test_api_intake.py`, `tools/charts.py`, `revenue.py`, `ChartSpecPatch`, `test_ledger_extra.py`, `User`, `tools/people.py`, `read_value`, `close_oct`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Why does `Invoice` connect `Invoice` to `.due_on`, `test_ledger_gates.py`, `models.py`, `Rev`, `DomainError`, `RevAction`, `fx_months.py`, `cycles.py`, `services/charts.py`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Why does `Party` connect `Rev` to `Invoice`, `test_ledger_gates.py`, `session_scope`, `models.py`, `records.py`, `format_inr`, `test_ledger_extra.py`, `DomainError`, `fx_months.py`, `test_people_extra.py`, `actions.py`, `cycles.py`, `services/charts.py`, `Actor`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Are the 53 inferred relationships involving `Rev` (e.g. with `_attention()` and `_read()`) actually correct?**
  _`Rev` has 53 INFERRED edges - model-reasoned connections that need verification._
- **Are the 57 inferred relationships involving `Invoice` (e.g. with `_receivables()` and `DeleteDraft`) actually correct?**
  _`Invoice` has 57 INFERRED edges - model-reasoned connections that need verification._
- **Are the 38 inferred relationships involving `Actor` (e.g. with `MunshiContext` and `ensure_extraction()`) actually correct?**
  _`Actor` has 38 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Voice conversation context`, `Language`, `Facts` to the rest of the system?**
  _182 weakly-connected nodes found - possible documentation gaps or missing edges._