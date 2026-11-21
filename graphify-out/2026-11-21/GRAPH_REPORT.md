# Graph Report - Builders  (2026-11-21)

## Corpus Check
- 93 files · ~93,388 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 3, .example 1, .ini 1)

## Summary
- 1420 nodes · 4338 edges · 77 communities (52 shown, 25 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 402 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6858f37e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Phase 3: AWS Deployment and CI/CD
- hygiene
- make_actor
- test_intake_extra.py
- models.py
- format_inr
- App.tsx
- test_budget_months.py
- package.json
- Actor
- tools/intake.py
- MUNSHI: Voice-only, agent-centric finance and operations copilot
- User
- DomainError
- Munshi | Product and delivery plan v2
- server.py
- test_people_extra.py
- compilerOptions
- get_settings
- Actor
- Munshi | Final weekend build plan
- Munshi | Build plan v3 (scope cut for the weekend)
- 5. Agent architecture
- munshi.md
- 5. Financial record lifecycles
- Munshi architecture decisions
- AUTHORSHIP.md
- builders
- tools/proposals.py
- DomainError
- get_line
- 1. Completed
- Conversation
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
- Any
- services/charts.py
- tools/budget_months.py
- test_charts.py
- add_inspected_document
- tools/charts.py
- services/intake.py
- session_scope
- cards.tsx
- ChartCard.tsx
- _payables
- extractor.py
- document
- LiveVoice
- ChartSpecPatch
- WakeWord
- budgeting/__init__.py
- BaseModel
- post

## God Nodes (most connected - your core abstractions)
1. `session_scope()` - 220 edges
2. `make_actor()` - 183 edges
3. `Actor` - 75 edges
4. `propose_and_confirm()` - 62 edges
5. `DomainError` - 51 edges
6. `User` - 48 edges
7. `seed()` - 47 edges
8. `format_inr()` - 39 edges
9. `Proposal` - 38 edges
10. `add_inspected_document()` - 38 edges

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

## Communities (77 total, 25 thin omitted)

### Community 0 - "Phase 3: AWS Deployment and CI/CD"
Cohesion: 0.07
Nodes (38): Tiny Agent Evaluation Set, Agent Guardrails (step limits, budgets, timeouts, retries), AWS App Runner, AWS ECS Fargate, AWS Lambda + API Gateway, Change-Scope Rules, CLAUDE.md Hackathon Agent Rules, Cost Awareness (+30 more)

### Community 1 - "hygiene"
Cohesion: 0.08
Nodes (24): concurrency, cancel-in-progress, group, GITLEAKS_VERSION, env, name, runs-on, steps (+16 more)

### Community 2 - "make_actor"
Cohesion: 0.07
Nodes (106): BudgetMovement, Proposal, Append-only. Balance of each bucket = SUM(amount_paise)., Receipt, Affirmation, classify(), _contains_affirm(), _normalize() (+98 more)

### Community 3 - "test_intake_extra.py"
Cohesion: 0.10
Nodes (36): _approved_bill(), call(), count(), finance_counts(), _http_proposal(), _party_id(), _pdf(), Hours 4-7 coverage: intake service, SubmitBill new-vendor path, agent tools (no… (+28 more)

### Community 4 - "models.py"
Cohesion: 0.15
Nodes (33): Read-only finance tools. Every number returned comes from a fixed, workspace-…, AuditEvent, Bill, Claim, CompanyPayment, Invoice, LeaveMovement, OnboardingTask (+25 more)

### Community 5 - "format_inr"
Cohesion: 0.11
Nodes (15): Any, format_inr(), _apply(), Approve, ApproveBill, ApproveClaim, _budget_effect(), DecideLeave (+7 more)

### Community 6 - "App.tsx"
Cohesion: 0.14
Nodes (15): react, api, ApiError, call(), Card, Me, setSession(), App() (+7 more)

### Community 7 - "test_budget_months.py"
Cohesion: 0.06
Nodes (56): compute(), days_in_month(), Pacing, date, The pacing / burn-velocity engine and the proactive alert levels (PRD §4). Pure…, `day` is the current day of the month (1..total_days); use total_days for a…, _round2(), ClosedMonth (+48 more)

### Community 8 - "package.json"
Cohesion: 0.06
Nodes (31): echarts, @fontsource/dm-sans, @fontsource/geist-mono, @fontsource/noto-sans-devanagari, react-dom, @types/react, @types/react-dom, typescript (+23 more)

### Community 9 - "Actor"
Cohesion: 0.09
Nodes (29): In-process event fan-out to the browser (SSE), keyed by conversation. One…, subscribe(), unsubscribe(), audit_feed(), confirm_button(), document_page(), domain_error(), event_stream() (+21 more)

### Community 10 - "tools/intake.py"
Cohesion: 0.16
Nodes (21): Convert DomainError into a structured result the agent can explain; log name,…, safe_tool(), close_intake(), correct_extracted_field(), find_reservations(), inspect_document(), Ctx, function_tool (+13 more)

### Community 11 - "MUNSHI: Voice-only, agent-centric finance and operations copilot"
Cohesion: 0.08
Nodes (25): 0. Planning inputs and research status, 10. Contract liability analysis (re-implemented from the user's guide), 11. Bill and receipt extraction, 12. External integrations, 13. Data model (Postgres; money = BIGINT paise; timestamps UTC, IST display; FY Apr-Mar), 14. Repository layout (this repo, `~/Projects/Builders`), 15. AWS deployment and CI/CD, 16. Security and trust (+17 more)

### Community 12 - "User"
Cohesion: 0.15
Nodes (20): _actor(), check_write(), current_actor(), current_csrf(), login(), Request, Response, Cookie session auth + CSRF. The Actor is derived from the server session on… (+12 more)

### Community 14 - "Munshi | Product and delivery plan v2"
Cohesion: 0.12
Nodes (16): 10. Data design and isolation, 11. Secondary workflows and integrations, 12. Implementation and deployment, 13. Build sequence and cut decisions, 14. Acceptance, evaluation and evidence, 15. Four-minute demonstration and handoff, 16. Definition of done, 1. User, problem and submission (+8 more)

### Community 15 - "server.py"
Cohesion: 0.17
Nodes (11): Bridge, create_session(), get_budget_status(), index(), BaseModel, function_tool, get, Request (+3 more)

### Community 16 - "test_people_extra.py"
Cohesion: 0.06
Nodes (74): LeaveRequest, Message, Inbox item and/or email outbox row. Email rows are delivered after the…, dispatch(), Send queued emails. Each row is claimed with SKIP LOCKED so concurrent…, fixture, frozen_today(), add_employee() (+66 more)

### Community 17 - "compilerOptions"
Cohesion: 0.13
Nodes (14): compilerOptions, isolatedModules, jsx, lib, module, moduleResolution, noEmit, noUnusedLocals (+6 more)

### Community 18 - "get_settings"
Cohesion: 0.15
Nodes (16): get_settings(), Base, configure(), engine(), AsyncSession, sessionmaker(), health(), Inbox + email outbox. Composing happens inside the confirm transaction; email… (+8 more)

### Community 19 - "Actor"
Cohesion: 0.09
Nodes (24): Actor, The authenticated principal. Always derived from the server session, never from…, Finance approval rights., HR/admin rights: onboarding, company-wide announcements, all leave., ensure_extraction(), prefetch(), Document reading (vision extraction) shared by the upload path and the…, _read() (+16 more)

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
Cohesion: 0.20
Nodes (9): Charts and views, Facts, Language, Monthly budget, alerts, changes and month close, Other requests, People and HR, Voice conversation context, Workflow for a new document (receipt or bill) (+1 more)

### Community 24 - "5. Financial record lifecycles"
Cohesion: 0.40
Nodes (5): 5. Financial record lifecycles, Budgets, reservations and spend, Employee claims and reimbursements, Revenue, invoicing and collections, Vendor bills and approvals

### Community 25 - "Munshi architecture decisions"
Cohesion: 0.50
Nodes (3): Evidence (local spike, `spikes/voice_spike`, synthetic fixture), Munshi architecture decisions, Voice transport and confirmation (H0 gate, 2026-11-21) — DECIDED

### Community 38 - "tools/proposals.py"
Cohesion: 0.06
Nodes (67): find_people(), get_leave_balance(), get_onboarding_status(), list_leave_requests(), lookup_policy(), _person(), propose_leave(), propose_leave_decision() (+59 more)

### Community 39 - "DomainError"
Cohesion: 0.14
Nodes (23): DomainError, Any, Typed domain errors. Tools turn these into structured results the agent can…, _approve_bill_inputs(), _approve_claim_inputs(), _bill_inputs(), _message_inputs(), Business writes, expressed as plan (preview, no side effects) + execute (inside… (+15 more)

### Community 40 - "get_line"
Cohesion: 0.14
Nodes (25): _attention(), explain_budget_change(), get_attention_items(), get_audit_history(), get_budget_status(), get_record(), list_budget_categories(), _pos_view() (+17 more)

### Community 41 - "1. Completed"
Cohesion: 0.08
Nodes (25): 1.10 Commits, 1.1 Voice (hour-0 spike, then productionised), 1.2 Agent (OpenAI Agents SDK), 1.3 Trust boundary: propose → present → confirm → receipt, 1.4 Finance domain, 1.5 People ops (PLAN_v5), 1.6 API and infrastructure (local), 1.7 Web UI (`web/`, React 19 + Vite + TypeScript) (+17 more)

### Community 42 - "Conversation"
Cohesion: 0.15
Nodes (17): Agent, MunshiContext, Passed to every tool via RunContextWrapper. Identity comes only from here,…, build_agent(), _instructions(), MunshiAgent: one conversational agent with typed tools. Same agent for voice…, memory(), One user turn through MunshiAgent. Shared by the text channel, push-to-talk and… (+9 more)

### Community 43 - "Plan"
Cohesion: 0.14
Nodes (15): Action, _claim_inputs(), Execution, Plan, Actor, AsyncSession, SubmitClaim, ApplyRecommendations (+7 more)

### Community 44 - "env.py"
Cohesion: 0.27
Nodes (9): Connection, do_run_migrations(), include_object(), Run migrations in 'offline' mode. This configures the context with just a URL…, In this scenario we need to create an Engine and associate a connection with…, Run migrations in 'online' mode., run_async_migrations(), run_migrations_offline() (+1 more)

### Community 45 - "Settings"
Cohesion: 0.25
Nodes (3): Settings, BaseSettings, field_validator

### Community 46 - "services/budget_months.py"
Cohesion: 0.15
Nodes (41): BudgetLine, BudgetPeriod, One category-month. Open months read the ledger; a closed month keeps its…, _rec_plans(), alerts(), apply_change(), apply_close(), ChangePlan (+33 more)

### Community 47 - "projection.py"
Cohesion: 0.07
Nodes (33): by_weights(), even_split(), Divide `total_paise` into `n` parts that sum exactly to it (remainder on the…, Annual -> monthly budget distribution (PRD §3). Integer paise only; no paise is…, Keep the `locked` month indices as given and spread `total_paise - sum(locked)`…, Split `total_paise` in proportion to `weights` (exact fractions, no floats).…, Growing shares: the first month weighs 1 and each next month weighs the one…, The paise each of `months` gets out of `total_paise` (same order, summing to… (+25 more)

### Community 48 - "Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST)"
Cohesion: 0.50
Nodes (3): Added capabilities (same agent, same propose → confirm → receipt engine), Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST), Rules

### Community 53 - "main.py"
Cohesion: 0.14
Nodes (20): agent_text(), cancel_button(), lifespan(), login(), LoginIn, logout(), new_conversation(), BaseModel (+12 more)

### Community 58 - "services/charts.py"
Cohesion: 0.10
Nodes (35): _auto_chart(), _bad(), ChartSpec, ChartType, Dim, DimensionName, FilterSpec, fmt_value() (+27 more)

### Community 59 - "tools/budget_months.py"
Cohesion: 0.13
Nodes (32): bm_round(), forecast_budget(), get_budget_alerts(), get_budget_history(), get_budget_month(), get_budget_recommendations(), get_budget_year(), MonthSplit (+24 more)

### Community 60 - "test_charts.py"
Cohesion: 0.15
Nodes (29): build(), client_for(), err(), err_sync(), priya_arjun(), DomainError, parametrize, Dynamic charts: validation, chart-type rules, totals vs independent SQL,… (+21 more)

### Community 61 - "add_inspected_document"
Cohesion: 0.11
Nodes (23): add_inspected_document(), client_for(), _pdf(), parametrize, HTTP layer + intake gates that need no model: auth, CSRF, upload outcomes,…, test_arithmetic_check(), test_button_confirm_and_replay(), test_contract_closes_without_finance_write() (+15 more)

### Community 62 - "tools/charts.py"
Cohesion: 0.17
Nodes (23): build_chart(), _card(), describe_chart_options(), present_view(), Ctx, function_tool, safe_tool, Chart and view tools. The model composes typed specs; every number comes from a… (+15 more)

### Community 63 - "services/intake.py"
Cohesion: 0.17
Nodes (23): Document, Extraction, AsyncSession, record(), accept_upload(), check_arithmetic(), close(), company_payment_matches() (+15 more)

### Community 64 - "session_scope"
Cohesion: 0.18
Nodes (22): One transaction; commits on success, rolls back on any exception., session_scope(), add_doc(), F(), Document + Extraction with arbitrary fields (no model call)., _sha(), test_company_payment_match_found_and_absent(), test_company_payment_match_is_workspace_scoped() (+14 more)

### Community 65 - "cards.tsx"
Cohesion: 0.15
Nodes (18): AuditCard(), BudgetCard(), Deliveries(), fmt(), InboxCard(), LEAVE_NAME, LeaveCard(), LeaveRequestsCard() (+10 more)

### Community 66 - "ChartCard.tsx"
Cohesion: 0.18
Nodes (15): ChartCard(), compactInr(), DataTable(), fmtAxis(), fmtFull(), fullInr(), Meta, pivot() (+7 more)

### Community 67 - "_payables"
Cohesion: 0.27
Nodes (14): _ageing(), _budget(), _claims(), Compiled, _month(), options(), _payables(), Actor (+6 more)

### Community 68 - "extractor.py"
Cohesion: 0.24
Nodes (12): build_agent(), Cite, extract(), ExtractedDocument, LineItem, Agent, BaseModel, ExtractorAgent: reads document page images into a typed schema. It has NO… (+4 more)

### Community 69 - "document"
Cohesion: 0.24
Nodes (13): document(), extraction(), code_of(), parametrize, test_arithmetic_and_breakdown_sum(), test_button_confirm_of_stale_proposal_returns_new_proposal_id(), test_claimed_document_cannot_be_closed_afterwards(), test_close_validates_outcome_and_is_single_shot() (+5 more)

### Community 70 - "LiveVoice"
Cohesion: 0.29
Nodes (4): setConversation(), Desk(), cardKey(), LiveVoice

### Community 71 - "ChartSpecPatch"
Cohesion: 0.33
Nodes (10): apply_patch(), chart_problem(), ChartSpecPatch, A revision. Anything omitted keeps its current value, so grouping survives…, Why the requested chart type does not fit the spec's shape, or None., spec(), test_add_filters_replaces_and_clear_filters(), test_month_to_customer_with_line_falls_back_to_auto() (+2 more)

### Community 72 - "WakeWord"
Cohesion: 0.32
Nodes (3): SR, wakeSupported, WakeWord

## Knowledge Gaps
- **178 isolated node(s):** `Voice conversation context`, `Language`, `Facts`, `Workflow for a new document (receipt or bill)`, `Writes: propose, present, confirm` (+173 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 464 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **25 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `session_scope()` connect `session_scope` to `make_actor`, `test_intake_extra.py`, `test_budget_months.py`, `Actor`, `tools/intake.py`, `User`, `test_people_extra.py`, `get_settings`, `Actor`, `tools/proposals.py`, `get_line`, `Conversation`, `services/budget_months.py`, `main.py`, `tools/budget_months.py`, `test_charts.py`, `add_inspected_document`, `tools/charts.py`, `document`, `ChartSpecPatch`?**
  _High betweenness centrality (0.106) - this node is a cross-community bridge._
- **Why does `make_actor()` connect `make_actor` to `session_scope`, `test_intake_extra.py`, `document`, `test_budget_months.py`, `ChartSpecPatch`, `Conversation`, `User`, `services/budget_months.py`, `test_people_extra.py`, `get_settings`, `Actor`, `test_charts.py`, `add_inspected_document`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `DomainError` connect `DomainError` to `make_actor`, `models.py`, `format_inr`, `tools/proposals.py`, `get_line`, `tools/intake.py`, `Plan`, `User`, `services/budget_months.py`, `Actor`, `add_inspected_document`, `services/intake.py`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Are the 44 inferred relationships involving `Actor` (e.g. with `MunshiContext` and `ensure_extraction()`) actually correct?**
  _`Actor` has 44 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `DomainError` (e.g. with `safe_tool()` and `correct_extracted_field()`) actually correct?**
  _`DomainError` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Voice conversation context`, `Language`, `Facts` to the rest of the system?**
  _178 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Phase 3: AWS Deployment and CI/CD` be split into smaller, more focused modules?**
  _Cohesion score 0.06827880512091039 - nodes in this community are weakly interconnected._