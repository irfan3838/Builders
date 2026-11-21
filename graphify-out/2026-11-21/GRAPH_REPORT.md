# Graph Report - Builders  (2026-11-21)

## Corpus Check
- 166 files · ~191,955 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 5, .example 2, .ini 1)

## Summary
- 3000 nodes · 9321 edges · 169 communities (110 shown, 59 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 817 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a2732e7e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Phase 3: AWS Deployment and CI/CD
- hygiene
- session_scope
- test_intake_extra.py
- live_bridge.py
- ._target
- PurserVoiceController.tsx
- test_budget_months.py
- package.json
- event_stream
- contract_actions.py
- MUNSHI: Voice-only, agent-centric finance and operations copilot
- db.py
- DomainError
- Munshi | Product and delivery plan v2
- server.py
- services/proposals.py
- compilerOptions
- make_actor
- add_inspected_document
- Munshi | Final weekend build plan
- Munshi | Build plan v3 (scope cut for the weekend)
- 5. Agent architecture
- run
- 5. Financial record lifecycles
- Purser architecture decisions
- AUTHORSHIP.md
- builders
- fx.py
- models.py
- build
- 2. Still to do (in priority order)
- finance.py
- Plan
- RevAction
- Settings
- services/budget_months.py
- projection.py
- Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST)
- fresh-sonnet-per-test-set.sh
- tests-only-in-sonnet.sh
- Agent
- main.py
- get
- go
- test_revenue_core.py
- cycles.py
- services/charts.py
- tools/budget_months.py
- test_charts.py
- test_contracts.py
- tools/intake.py
- services/intake.py
- Invoice
- cards.tsx
- ChartCard.tsx
- datetime
- app/money.py
- safe_tool
- client_by
- Message
- metadata.py
- budgeting/__init__.py
- format_inr
- test_ledger_extra.py
- fx_months.py
- revenue_actions.py
- scan.py
- test_revenue_fx_cycles.py
- tools/people.py
- safe_tool
- set_quote
- User
- recommend.py
- revenue/money.py
- tools/charts.py
- distribution.py
- test_ledger_gates.py
- liability.py
- store.py
- pacing.py
- client_for
- part_paid_zed
- project_end.py
- ClaimReview.tsx
- FakeSMTP
- .due_on
- contracts.py
- auth.py
- review.py
- Rev
- upload
- code_of
- test_people_extra.py
- ViewRouter.tsx
- propose_and_confirm
- code_of
- purser.md
- get_settings
- Diwan: the voice-first back office for Indian SMBs
- grounding.py
- make_contract_samples.py
- store.tsx
- DomainError
- test_api_intake.py
- post_move
- run
- messaging.py
- Deployment (AWS, us-west-2)
- Read
- options
- google_oauth.py
- format_inr
- _invoices_by_refs
- aws_put_secrets.py
- _cycle_client
- contracts/__init__.py
- GEMINI_UI_BRIEF.md
- aws_run_task.sh
- safe_tool
- safe_tool
- safe_tool
- safe_tool
- safe_tool
- Mail
- date
- date
- date
- date
- date
- date
- date
- date
- MunshiContext
- Request
- calendar.py
- date
- PurserSidebar.tsx
- env.py
- row
- test_paused_and_ended_clients_get_no_billing_suggestions
- AddInvoices
- EditInvoice
- SetCycle
- FastAPI
- MoveBalance
- RecordPayment
- test_cycle_quarterly_combined_advance_books_in_first_month
- test_history_lists_month_and_invoice_changes_newest_first
- _staged_view
- month_number
- Ctx
- function_tool
- Any

## God Nodes (most connected - your core abstractions)
1. `session_scope()` - 347 edges
2. `make_actor()` - 299 edges
3. `run()` - 92 edges
4. `Invoice` - 90 edges
5. `Rev` - 79 edges
6. `safe_tool()` - 73 edges
7. `Party` - 71 edges
8. `DomainError` - 71 edges
9. `go()` - 70 edges
10. `create()` - 70 edges

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

## Communities (169 total, 59 thin omitted)

### Community 0 - "Phase 3: AWS Deployment and CI/CD"
Cohesion: 0.07
Nodes (38): Tiny Agent Evaluation Set, Agent Guardrails (step limits, budgets, timeouts, retries), AWS App Runner, AWS ECS Fargate, AWS Lambda + API Gateway, Change-Scope Rules, CLAUDE.md Hackathon Agent Rules, Cost Awareness (+30 more)

### Community 1 - "hygiene"
Cohesion: 0.08
Nodes (24): concurrency, cancel-in-progress, group, GITLEAKS_VERSION, env, name, runs-on, steps (+16 more)

### Community 2 - "session_scope"
Cohesion: 0.13
Nodes (35): close_intake(), correct_extracted_field(), find_reservations(), Ctx, function_tool, Open budget reservations for an employee that this receipt could replace (e.g.…, Finish intake WITHOUT any finance write, with an explicit outcome (contract,…, Show the original document page on screen, highlighting where a field was read… (+27 more)

### Community 3 - "test_intake_extra.py"
Cohesion: 0.08
Nodes (47): add_doc(), _approved_bill(), count(), F(), _http_proposal(), _party_id(), _pdf(), Actor (+39 more)

### Community 4 - "live_bridge.py"
Cohesion: 0.18
Nodes (10): bridge_for(), client(), LiveBridge, Actor, GPT-Live sideband bridge: server-observed transcripts -> voice_turns;…, Speak text in the live session if it is still open. Never raises; returns…, say(), session_config() (+2 more)

### Community 5 - "._target"
Cohesion: 0.13
Nodes (12): Any, Action, _apply(), Approve, ApproveBill, ApproveClaim, _budget_effect(), Actor (+4 more)

### Community 6 - "PurserVoiceController.tsx"
Cohesion: 0.08
Nodes (23): ApiError, call(), Card, headers(), Me, setConversation(), setSession(), uploadWithProgress() (+15 more)

### Community 7 - "test_budget_months.py"
Cohesion: 0.10
Nodes (35): allocated(), allocated_in(), cells(), change(), close(), close_oct(), code_of(), count_movements() (+27 more)

### Community 8 - "package.json"
Cohesion: 0.05
Nodes (37): echarts, @fontsource/dm-sans, @fontsource/geist-mono, @fontsource/noto-sans-devanagari, @fontsource/source-serif-4, @types/react, @types/react-dom, @types/three (+29 more)

### Community 9 - "event_stream"
Cohesion: 0.12
Nodes (14): In-process event fan-out to the browser (SSE), keyed by conversation. One…, subscribe(), unsubscribe(), domain_error(), event_stream(), no_shared_cache(), DomainError, Request (+6 more)

### Community 10 - "contract_actions.py"
Cohesion: 0.36
Nodes (6): _details_inputs(), _iso(), Contract writes as propose -> present -> confirm -> receipt actions (the same…, SetContractDetails, _staged(), _type()

### Community 11 - "MUNSHI: Voice-only, agent-centric finance and operations copilot"
Cohesion: 0.08
Nodes (25): 0. Planning inputs and research status, 10. Contract liability analysis (re-implemented from the user's guide), 11. Bill and receipt extraction, 12. External integrations, 13. Data model (Postgres; money = BIGINT paise; timestamps UTC, IST display; FY Apr-Mar), 14. Repository layout (this repo, `~/Projects/Builders`), 15. AWS deployment and CI/CD, 16. Security and trust (+17 more)

### Community 12 - "db.py"
Cohesion: 0.27
Nodes (10): Base, configure(), engine(), AsyncSession, sessionmaker(), async_sessionmaker, AsyncEngine, DeclarativeBase (+2 more)

### Community 14 - "Munshi | Product and delivery plan v2"
Cohesion: 0.12
Nodes (16): 10. Data design and isolation, 11. Secondary workflows and integrations, 12. Implementation and deployment, 13. Build sequence and cut decisions, 14. Acceptance, evaluation and evidence, 15. Four-minute demonstration and handoff, 16. Definition of done, 1. User, problem and submission (+8 more)

### Community 15 - "server.py"
Cohesion: 0.17
Nodes (11): Bridge, create_session(), get_budget_status(), index(), BaseModel, function_tool, get, Request (+3 more)

### Community 16 - "services/proposals.py"
Cohesion: 0.16
Nodes (29): Proposal, cancel(), canonical(), confirm(), ConfirmOutcome, load(), mark_presented(), _now() (+21 more)

### Community 17 - "compilerOptions"
Cohesion: 0.13
Nodes (14): compilerOptions, isolatedModules, jsx, lib, module, moduleResolution, noEmit, noUnusedLocals (+6 more)

### Community 18 - "make_actor"
Cohesion: 0.09
Nodes (70): make_actor(), run(), sql(), test_auto_chart_selection(), test_bills_totals_match_sql(), test_budget_by_category_matches_movements(), test_date_range_filter_matches_sql(), test_filter_exact_case_insensitive() (+62 more)

### Community 19 - "add_inspected_document"
Cohesion: 0.12
Nodes (24): add_inspected_document(), call(), finance_counts(), Invoke a FunctionTool exactly as the SDK would, minus the model. Returns…, test_claimed_document_cannot_be_closed_afterwards(), test_cross_workspace_document_page_is_404(), test_inspect_document_contract_next_step_and_closed_short_circuit(), test_propose_bill_tool_with_new_vendor() (+16 more)

### Community 20 - "Munshi | Final weekend build plan"
Cohesion: 0.17
Nodes (9): 1. Product promise and scope, 2. Intake and accounting decisions, 3. Conversation and confirmation, 4. Architecture and deployment gates, 5. Delivery budget and cut line, 6. Demo and evaluation, Budget fixture and acceptance, Munshi | Final weekend build plan (+1 more)

### Community 21 - "Munshi | Build plan v3 (scope cut for the weekend)"
Cohesion: 0.17
Nodes (12): 0. Why a v3, 1. Product in one sentence, 2. P0: what must work, deployed on AWS, 3. What we cut, and why, 4. Four-minute demo (golden path), 5. Architecture (minimum that ships), 6. Evidence for the submission, 7. Build order (clock times, IST) (+4 more)

### Community 22 - "5. Agent architecture"
Cohesion: 0.25
Nodes (8): 5.1 Topology, 5.2 Agent specification (per CLAUDE.md), 5.3 Prompts (in `backend/app/agent/prompts/`), 5.4 Confirmation protocol (all write tools), 5.5 Proactivity, 5.6 Memory and context, 5.7 Multilingual, 5. Agent architecture

### Community 23 - "run"
Cohesion: 0.05
Nodes (50): Guide: changing a month clears later explicit settings in the affected span…, fn(ss, rv) on a sync session in one committed transaction; return plain data., Kaveri's paid Oct invoice covers Oct-Dec: a monthly cycle from Nov must not…, run(), rv_of(), test_apply_reprices_ticked_and_leaves_paid_and_part_paid(), go(), test_balance_onto_existing_to_raise_month_adds_at_its_rate() (+42 more)

### Community 24 - "5. Financial record lifecycles"
Cohesion: 0.40
Nodes (5): 5. Financial record lifecycles, Budgets, reservations and spend, Employee claims and reimbursements, Revenue, invoicing and collections, Vendor bills and approvals

### Community 25 - "Purser architecture decisions"
Cohesion: 0.50
Nodes (3): Evidence (local spike, `spikes/voice_spike`, synthetic fixture), Purser architecture decisions, Voice transport and confirmation (H0 gate, 2026-11-21) — DECIDED

### Community 38 - "fx.py"
Cohesion: 0.22
Nodes (13): cached(), _frankfurter(), latest(), _newest(), Decimal, Exception, Session, Rate (+5 more)

### Community 39 - "models.py"
Cohesion: 0.09
Nodes (36): AuditEvent, CompanyPayment, Conversation, InvoicePayment, OnboardingTask, Policy, SQLAlchemy models. Money is integer paise; timestamps are UTC; business dates…, INR actually credited against a customer invoice (copilot `cli_receipt`). (+28 more)

### Community 40 - "build"
Cohesion: 0.27
Nodes (11): age_bucket(), build(), ClientLine, Due, Exposure, Insights, Kpis, Month (+3 more)

### Community 41 - "2. Still to do (in priority order)"
Cohesion: 0.07
Nodes (28): 1.10 Commits, 1.1 Voice (hour-0 spike, then productionised), 1.2 Agent (OpenAI Agents SDK), 1.3 Trust boundary: propose → present → confirm → receipt, 1.4 Finance domain, 1.5 People ops (PLAN_v5), 1.6 API and infrastructure (local), 1.7 Web UI (`web/`, React 19 + Vite + TypeScript) (+20 more)

### Community 42 - "finance.py"
Cohesion: 0.13
Nodes (26): explain_budget_change(), get_audit_history(), get_budget_status(), list_budget_categories(), _pos_view(), Ctx, function_tool, Read-only finance tools. Every number returned comes from a fixed, workspace-… (+18 more)

### Community 43 - "Plan"
Cohesion: 0.09
Nodes (19): ApplyLeave, Execution, _message_inputs(), Plan, SendMessage, ApplyRecommendations, BudgetChange, _change_plan() (+11 more)

### Community 44 - "RevAction"
Cohesion: 0.16
Nodes (11): EndProject, FxMonthRate, PlanFY, Actor, AsyncSession, {label: value} the user must have said., Set a currency's conversion rate for months; it carries forward to March.…, Project over: raise each pending invoice (separate), fold them into one… (+3 more)

### Community 45 - "Settings"
Cohesion: 0.22
Nodes (3): Settings, BaseSettings, field_validator

### Community 46 - "services/budget_months.py"
Cohesion: 0.16
Nodes (38): BudgetPeriod, One category-month. Open months read the ledger; a closed month keeps its…, _rec_plans(), alerts(), apply_change(), apply_close(), Cell, ChangePlan (+30 more)

### Community 47 - "projection.py"
Cohesion: 0.11
Nodes (20): month_outlook(), Outlook, Where spend is heading (run rate), for the CEO's three bars: allocated, spent,…, budgets / spends: the FY's 12 months in order; current: index of this month (0…, year_outlook(), Change, Month, pace_of() (+12 more)

### Community 48 - "Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST)"
Cohesion: 0.50
Nodes (3): Added capabilities (same agent, same propose → confirm → receipt engine), Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST), Rules

### Community 53 - "main.py"
Cohesion: 0.16
Nodes (31): audit_feed(), budget_line(), budget_line_months(), contract_clause_context(), contract_deadlines_view(), contract_liabilities(), contract_review_view(), contract_view() (+23 more)

### Community 55 - "go"
Cohesion: 0.11
Nodes (43): figures(), mk_client(), mk_inr(), Rs 10,000 Oct with Rs 4,000 in; move Rs 6,000 to Nov: moved_paise 600000, Oct…, send(), test_allocation_across_two_clients_rejected(), go(), test_allocation_without_amount_pays_each_remaining() (+35 more)

### Community 56 - "test_revenue_core.py"
Cohesion: 0.12
Nodes (33): pinned(), priya(), propose_confirm(), fixture, parametrize, Revenue core: money maths, invoice lifecycle, allocation, reporting figures,…, Revenue clients are customer Parties in the same workspace table (no separate…, Approver with no conversation: grounding is skipped (the on-screen form path). (+25 more)

### Community 57 - "cycles.py"
Cohesion: 0.08
Nodes (58): ClientCycle, A client's billing cycle from a month on: monthly charge, every N months,…, active(), apply(), ChangePlan, check(), _clashes(), combined() (+50 more)

### Community 58 - "services/charts.py"
Cohesion: 0.07
Nodes (60): BudgetLine, _ageing(), _auto_chart(), _bad(), _budget(), _budget_flows(), ChartSpec, ChartType (+52 more)

### Community 59 - "tools/budget_months.py"
Cohesion: 0.12
Nodes (29): bm_round(), forecast_budget(), get_budget_alerts(), get_budget_history(), get_budget_month(), get_budget_recommendations(), get_budget_year(), MonthSplit (+21 more)

### Community 60 - "test_charts.py"
Cohesion: 0.12
Nodes (33): apply_patch(), chart_problem(), ChartSpecPatch, A revision. Anything omitted keeps its current value, so grouping survives…, Why the requested chart type does not fit the spec's shape, or None., build(), client_for(), err() (+25 more)

### Community 61 - "test_contracts.py"
Cohesion: 0.07
Nodes (52): defined_parties(), parse_cap(), (cap in paise, basis text). A non-INR or non-numeric cap keeps paise None and…, {defined term (lower) -> party name} from '(hereinafter referred to as "the…, _a_flag(), analyse(), by_type(), contract_by_ref() (+44 more)

### Community 62 - "tools/intake.py"
Cohesion: 0.15
Nodes (17): Agent, PurserContext, Passed to every tool via RunContextWrapper. Identity comes only from here,…, build_agent(), _instructions(), PurserAgent: one conversational agent with typed tools. Same agent for voice…, memory(), Actor (+9 more)

### Community 63 - "services/intake.py"
Cohesion: 0.11
Nodes (37): ensure_extraction(), prefetch(), Actor, Document reading (vision extraction) shared by the upload path and the…, _read(), inspect_document(), Read an uploaded document (runs extraction the first time). Returns type,…, _view() (+29 more)

### Community 64 - "Invoice"
Cohesion: 0.12
Nodes (51): Invoice, A customer invoice (revenue). Ported from the copilot Revenue module. Billing…, _date(), conflict(), Allocation, BalancePlan, billed_paise(), by_ref() (+43 more)

### Community 65 - "cards.tsx"
Cohesion: 0.07
Nodes (37): api, AuditCard(), BudgetCard(), Deliveries(), fmt(), InboxCard(), LEAVE_NAME, LeaveCard() (+29 more)

### Community 66 - "ChartCard.tsx"
Cohesion: 0.15
Nodes (19): CATS, ChartCard(), compactInr(), DataTable(), fmtAxis(), fmtChange(), fmtFull(), fullInr() (+11 more)

### Community 67 - "datetime"
Cohesion: 0.10
Nodes (31): A dated in-app reminder ('remind me Friday to chase Acme'), optionally about a…, Reminder, Pause, resume, or end (project over). Rows stay as they are; a paused/ended…, set_client_state(), _bump_versions(), invalid(), log(), not_found() (+23 more)

### Community 68 - "app/money.py"
Cohesion: 0.21
Nodes (13): build_agent(), Cite, extract(), ExtractedDocument, LineItem, Agent, BaseModel, ExtractorAgent: reads document page images into a typed schema. It has NO… (+5 more)

### Community 69 - "safe_tool"
Cohesion: 0.05
Nodes (95): Convert DomainError into a structured result the agent can explain; log name,…, safe_tool(), get_attention_items(), What needs attention: pending approvals (claims, bills, leave), bills due…, cancel_pending_proposal(), _confirm(), confirm_pending_proposal(), get_pending_proposal() (+87 more)

### Community 70 - "client_by"
Cohesion: 0.11
Nodes (31): client_by(), _end(), invs_of(), go(), test_change_cycle_keeps_raised_and_paid_and_skips_their_months(), go(), go(), test_change_cycle_replaces_later_rules_and_updates_client_currency() (+23 more)

### Community 71 - "Message"
Cohesion: 0.18
Nodes (17): Message, Inbox item and/or email outbox row. Email rows are delivered after the…, conv(), count(), boom(), present(), Actor, Same user, fresh conversation (a second session). (+9 more)

### Community 72 - "metadata.py"
Cohesion: 0.13
Nodes (30): add_months(), _clean(), _client(), dates(), Detail, Details, _effective(), end_of_term() (+22 more)

### Community 75 - "format_inr"
Cohesion: 0.14
Nodes (29): Actor, budget_alerts(), claim_review(), draft_message(), DraftIn, _inr(), _line_names(), list_bills() (+21 more)

### Community 76 - "test_ledger_extra.py"
Cohesion: 0.11
Nodes (48): Full settlement only (weekend scope). One per record, enforced by the unique…, Settlement, AsyncSession, record_turn(), assert_conservation(), code_of(), count(), line_pos() (+40 more)

### Community 77 - "fx_months.py"
Cohesion: 0.15
Nodes (22): Affected, apply(), carried_months(), Change, effective(), foreign(), history(), _months_text() (+14 more)

### Community 78 - "revenue_actions.py"
Cohesion: 0.17
Nodes (16): _ccy(), _clean_num(), ClientChange, _eff(), _fx_note(), money_minor(), Outcome, parse_date() (+8 more)

### Community 79 - "scan.py"
Cohesion: 0.10
Nodes (33): The shipped clause catalogue: copilot `ctr_0001_contracts.py` CLAUSE_TYPES,…, A clause type as the scan sees it., Rule, rules(), _ask(), _dedup(), _join(), locate() (+25 more)

### Community 80 - "test_revenue_fx_cycles.py"
Cohesion: 0.11
Nodes (46): FxMonth, A conversion rate set by hand for a currency and month; carries forward until…, create(), inv_of(), pinned(), priya(), propose_confirm(), fixture (+38 more)

### Community 81 - "tools/people.py"
Cohesion: 0.17
Nodes (23): find_people(), list_leave_requests(), lookup_policy(), _person(), propose_leave(), propose_leave_decision(), propose_meeting(), propose_message() (+15 more)

### Community 83 - "set_quote"
Cohesion: 0.11
Nodes (20): FxQuote, Cached ECB reference quotes (Frankfurter): INR per unit x 10^6, by publication…, AsyncSession, Fetch and cache the latest quote for each foreign ECB currency. Returns…, refresh(), _aug_ecb(), Upsert the cached ECB quote for (ccy, day) with fetched_at = now - age., set_quote() (+12 more)

### Community 84 - "User"
Cohesion: 0.17
Nodes (26): get_leave_balance(), get_onboarding_status(), Onboarding checklist for a new joiner: each task, owner, due date and status., Leave balance (CL, SL, EL: granted, held for pending requests, used,…, leave_card(), person_card(), LeaveMovement, Append-only leave ledger per user and type. available = granted - reserved -… (+18 more)

### Community 85 - "recommend.py"
Cohesion: 0.15
Nodes (18): ClosedMonth, plan(), slots(), PlannedChange, `closed_chrono`: the category's closed months, oldest first (any number)., Trend recommendations: if a category has over- (or under-) run its budget for…, One budget change that acts on the recommendations, for one month (amounts in…, Act on the recommendations for one month, moving money before adding any: each… (+10 more)

### Community 86 - "revenue/money.py"
Cohesion: 0.10
Nodes (29): currencies_in(), digits(), format_amount(), from_minor(), numbers_in(), paise_to(), Decimal, Ported from copilot clients_mod/money.py (user's own code), unchanged except… (+21 more)

### Community 87 - "tools/charts.py"
Cohesion: 0.10
Nodes (33): build_chart(), _card(), describe_chart_options(), present_view(), Ctx, function_tool, Chart and view tools. The model composes typed specs; every number comes from a…, What can be charted for this user: sources, measures (with units), dimensions,… (+25 more)

### Community 88 - "distribution.py"
Cohesion: 0.20
Nodes (13): by_weights(), even_split(), Divide `total_paise` into `n` parts that sum exactly to it (remainder on the…, Annual -> monthly budget distribution (PRD §3). Integer paise only; no paise is…, Keep the `locked` month indices as given and spread `total_paise - sum(locked)`…, Split `total_paise` in proportion to `weights` (exact fractions, no floats).…, Growing shares: the first month weighs 1 and each next month weighs the one…, The paise each of `months` gets out of `total_paise` (same order, summing to… (+5 more)

### Community 89 - "test_ledger_gates.py"
Cohesion: 0.11
Nodes (24): Typed domain errors. Tools turn these into structured results the agent can…, Affirmation, classify(), _contains_affirm(), _normalize(), Deterministic classifier for a confirmation utterance (English, Hindi,…, Spoken confirmation is valid only from a server-observed user turn that started…, Return evidence for confirming `p`, or raise CONFIRMATION_REQUIRED with the… (+16 more)

### Community 90 - "liability.py"
Cohesion: 0.09
Nodes (37): Deadlines follow the contract's current expiry and its auto-renewal notice…, recompute_deadlines(), as_dict(), assess(), _bearer_term(), _beneficiary(), carve_outs_rules(), Deadline (+29 more)

### Community 91 - "store.py"
Cohesion: 0.16
Nodes (36): get_contract(), One contract by ref (AG3), title or counterparty: liabilities with who bears…, Contract, ContractDeadline, ContractFinding, One agreement. Text is the extracted reading of the original document (kept in…, A clause found in a contract (copilot ctr_clause) plus Purser's liability…, A dated obligation computed by code from the contract (expiry, renewal notice,… (+28 more)

### Community 92 - "pacing.py"
Cohesion: 0.24
Nodes (9): compute(), days_in_month(), Pacing, date, The pacing / burn-velocity engine and the proactive alert levels (PRD §4). Pure…, `day` is the current day of the month (1..total_days); use total_days for a…, _round2(), test_pacing_approaching_and_limit() (+1 more)

### Community 93 - "client_for"
Cohesion: 0.08
Nodes (40): client_for(), test_months_endpoint(), test_http_contract_admin_ok_employee_forbidden(), test_http_deadlines(), test_http_finding_context_marks_span_inside_excerpt(), test_http_injection_in_path_and_params(), test_http_liabilities_bearer_filter(), test_http_review_view_pending_and_staged() (+32 more)

### Community 94 - "part_paid_zed"
Cohesion: 0.10
Nodes (26): mk_client(), mk_invoice(), part_paid_zed(), Guide example: Rs 10,000 invoice, Rs 4,000 received, part paid., test_balance_delete_destination_restores_source_to_part_paid(), go(), test_balance_into_other_currency_month_makes_its_own_balance_invoice(), go() (+18 more)

### Community 95 - "project_end.py"
Cohesion: 0.21
Nodes (11): Price, INR is 1; a typed rate is manual; then the currency's month rate in force for…, apply(), _close(), EndPlan, _later_or_same(), plan(), Session (+3 more)

### Community 96 - "ClaimReview.tsx"
Cohesion: 0.08
Nodes (35): motion, react, react-dom, dur, ease, easeInOut, palette, reveal (+27 more)

### Community 99 - "contracts.py"
Cohesion: 0.14
Nodes (24): contract_deadlines(), list_liabilities(), propose_contract_details(), propose_contract_status(), propose_create_contract(), propose_rescan_contract(), propose_review_contract_finding(), Ctx (+16 more)

### Community 100 - "auth.py"
Cohesion: 0.28
Nodes (12): _actor(), check_write(), current_actor(), current_csrf(), login(), Request, Response, Cookie session auth + CSRF. The Actor is derived from the server session on… (+4 more)

### Community 102 - "review.py"
Cohesion: 0.10
Nodes (30): _attention(), analyse(), can_decide(), can_view(), clean_name(), ensure(), guess_title(), guess_type() (+22 more)

### Community 103 - "Rev"
Cohesion: 0.13
Nodes (35): active(), Rev, bucket_label(), fy_months(), fy_of(), fy_start(), fy_today(), month_label() (+27 more)

### Community 104 - "upload"
Cohesion: 0.14
Nodes (17): agent_text(), cancel_button(), confirm_button(), login(), LoginIn, logout(), new_conversation(), BaseModel (+9 more)

### Community 105 - "code_of"
Cohesion: 0.17
Nodes (12): ExceptionInfo, code_of(), test_create_cap_and_duplicate_months(), go(), test_duplicate_client_name_and_archive_restore(), go(), test_invoice_ref_from_other_workspace_is_not_found(), go() (+4 more)

### Community 106 - "test_people_extra.py"
Cohesion: 0.12
Nodes (38): LeaveRequest, add_employee(), apply(), assert_leave_conservation(), _audit_actions(), bal(), code_of(), People-ops coverage (PLAN_v5): leave ledger and decisions, messaging outbox,… (+30 more)

### Community 107 - "ViewRouter.tsx"
Cohesion: 0.15
Nodes (24): lucide-react, inr(), AmbientRibbons(), PurserComposer(), useAssistant(), FinancialDecisionStrip(), AppShell(), PurserSidebar() (+16 more)

### Community 108 - "propose_and_confirm"
Cohesion: 0.25
Nodes (16): dispatch(), Send queued emails. Each row is claimed with SKIP LOCKED so concurrent…, propose_and_confirm(), messages_for(), set_notify(), test_concurrent_dispatchers_never_double_send(), test_decision_email_states_inbox_always_delivered(), test_dispatch_failure_is_recorded_and_not_retried() (+8 more)

### Community 109 - "code_of"
Cohesion: 0.12
Nodes (12): code_of(), test_apply_rejects_reprice_ids_not_in_preview(), other_ccy(), paid(), part(), test_balance_delete_requires_unraised_destination(), go(), test_ending_an_ended_client_is_same_state() (+4 more)

### Community 110 - "purser.md"
Cohesion: 0.17
Nodes (11): Charts and views, Contracts and liabilities, Facts, Language, Monthly budget, alerts, changes and month close, Other requests, People and HR, Revenue: client invoices and money coming in (+3 more)

### Community 111 - "get_settings"
Cohesion: 0.15
Nodes (15): get_settings(), enabled(), LLMUnavailable, BaseModel, Exception, The only place contract review talks to a model. Small and replaceable:…, No key, provider error, timeout or unparseable answer: the caller falls back to…, Page images -> plain text (a scanned agreement has no text layer). (+7 more)

### Community 112 - "Diwan: the voice-first back office for Indian SMBs"
Cohesion: 0.17
Nodes (11): 10. Beyond the weekend, 1. The problem, 2. The solution, 3. Why AI, and what the AI actually does, 4. The trust boundary: propose → present → confirm → receipt, 5. Architecture, 6. What is already built (Saturday, 21 Nov), 7. Plan to the Sunday 14:00 freeze (+3 more)

### Community 113 - "grounding.py"
Cohesion: 0.22
Nodes (15): _normal(), numbers_spoken(), Actor, AsyncSession, Decimal, A model never supplies a booked amount or rate on its own: the number must…, The user's last few server-observed turns in this conversation, newest last.…, Each non-empty value must appear in the user's recent words, else ask them to… (+7 more)

### Community 114 - "make_contract_samples.py"
Cohesion: 0.25
Nodes (9): docx(), main(), _pdf_escape(), Write the synthetic agreements in seed/contract_samples.py as files under…, A real PDF with a text layer: wrapped lines, 50 per page, Helvetica 10pt on A4., Page images only (no text layer), like a scanned agreement., scanned_pdf(), text_pdf() (+1 more)

### Community 115 - "store.tsx"
Cohesion: 0.12
Nodes (16): three, Props, PurserOrb(), TARGETS, Caption, Ctx, Decision, OrbState (+8 more)

### Community 116 - "DomainError"
Cohesion: 0.09
Nodes (40): Actor, The authenticated principal. Always derived from the server session, never from…, Finance approval rights., HR/admin rights: onboarding, company-wide announcements, all leave., get_record(), Details of a claim (C…) or bill (B…): parties, amount, state, settlement,…, DomainError, Any (+32 more)

### Community 117 - "test_api_intake.py"
Cohesion: 0.18
Nodes (10): _pdf(), parametrize, HTTP layer + intake gates that need no model: auth, CSRF, upload outcomes,…, test_arithmetic_check(), test_button_confirm_and_replay(), test_contract_closes_without_finance_write(), test_employee_cannot_open_other_users_document(), test_exact_replay_returns_existing_document() (+2 more)

### Community 118 - "post_move"
Cohesion: 0.47
Nodes (9): flows(), lines_by_cat(), post_move(), test_budget_flows_conservation_and_directions(), test_budget_flows_does_not_change_budget_source_and_is_workspace_scoped(), test_budget_flows_multi_month_transfer_pairs_per_month(), test_budget_flows_other_dimensions_and_filters(), test_budget_flows_unpaired_leg_makes_no_transfer() (+1 more)

### Community 119 - "run"
Cohesion: 0.13
Nodes (20): Run fn(ss, rv) on a sync session inside one committed transaction; return what…, run(), rv_of(), sugg(), test_chase_for_overdue_sent_invoice(), go(), test_custom_reminder_survives_pause(), go() (+12 more)

### Community 120 - "messaging.py"
Cohesion: 0.18
Nodes (11): compose(), dispatch_soon(), email_plan(), Actor, AsyncSession, Inbox + email outbox. Composing happens inside the confirm transaction; email…, Where an email to this user would go, and whether it is deliverable in this…, _send_smtp() (+3 more)

### Community 121 - "Deployment (AWS, us-west-2)"
Cohesion: 0.22
Nodes (8): Architecture, Deployment (AWS, us-west-2), Email and Google Meet, First deploy, Notes, Redeploy (new code), Rollback, Teardown

### Community 122 - "Read"
Cohesion: 0.29
Nodes (7): docx_text(), _layer(), meaningful(), A contract file -> its plain text. Text layer first (deterministic), the vision…, Paragraphs of a .docx in order (table cells are paragraphs too)., Read, _render()

### Community 123 - "options"
Cohesion: 0.33
Nodes (6): options(), Registry as the model sees it, limited to what this actor may chart., BUG candidate: options() maps every non-paise unit to 'count', so the model is…, test_options_by_role(), test_options_lists_new_chart_types_and_rules(), test_options_reports_pct_unit_distinctly()

### Community 124 - "google_oauth.py"
Cohesion: 0.33
Nodes (6): Path, _client(), main(), One-time Google Calendar login: gets a refresh token for the organizer account…, _set_env(), _wait_for_code()

### Community 125 - "format_inr"
Cohesion: 0.25
Nodes (7): DeleteDraft, format_inr(), _indian(), paise_str(), ₹1,23,456' (Indian grouping); paise shown only when there are some, never with…, API form of rupees: 123456 -> '1234.56'., test_rate_and_paise_formatting()

### Community 126 - "_invoices_by_refs"
Cohesion: 0.29
Nodes (4): _invoices_by_refs(), Session, Foreign currencies whose live quote the run may need (fetched before the sync…, SendInvoices

### Community 129 - "_cycle_client"
Cohesion: 0.29
Nodes (7): _cycle_client(), test_guide_arrears_books_in_december_and_raises_at_period_end(), go(), test_guide_monthly_mode_emits_three_rows_sharing_the_period(), go(), test_guide_quarterly_advance_combined_books_30000_in_october_due_31_dec(), go()

### Community 149 - "calendar.py"
Cohesion: 0.16
Nodes (20): Meeting, A calendar event with a Google Meet link. Queued inside the confirm…, _meeting_inputs(), ScheduleMeeting, _access_token(), CalendarError, create_event(), dispatch() (+12 more)

### Community 151 - "PurserSidebar.tsx"
Cohesion: 0.20
Nodes (9): ACTION_WORDS, ago(), humanize(), NavDef, Note, Notifications(), Profile(), SettingsDialog() (+1 more)

### Community 152 - "env.py"
Cohesion: 0.27
Nodes (9): Connection, do_run_migrations(), include_object(), Run migrations in 'offline' mode. This configures the context with just a URL…, In this scenario we need to create an Engine and associate a connection with…, Run migrations in 'online' mode., run_async_migrations(), run_migrations_offline() (+1 more)

### Community 153 - "row"
Cohesion: 0.22
Nodes (8): row(), go(), go(), go(), test_seeded_northwind_nov_priced_at_carried_oct_rate(), go(), go(), test_version_persists_across_sessions()

### Community 154 - "test_paused_and_ended_clients_get_no_billing_suggestions"
Cohesion: 0.60
Nodes (5): test_paused_and_ended_clients_get_no_billing_suggestions(), end(), kinds(), nw_before(), resume()

### Community 162 - "test_cycle_quarterly_combined_advance_books_in_first_month"
Cohesion: 0.67
Nodes (3): Rs 10,000 a month, 3-month period from Oct, combined/advance: Rs 30,000 in Oct…, test_cycle_quarterly_combined_advance_books_in_first_month(), go()

## Knowledge Gaps
- **242 isolated node(s):** `Voice conversation context`, `Language`, `Facts`, `Workflow for a new document (receipt or bill)`, `Writes: propose, present, confirm` (+237 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 886 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **59 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `session_scope()` connect `session_scope` to `test_intake_extra.py`, `live_bridge.py`, `test_budget_months.py`, `db.py`, `services/proposals.py`, `make_actor`, `add_inspected_document`, `calendar.py`, `run`, `models.py`, `finance.py`, `main.py`, `test_revenue_core.py`, `tools/budget_months.py`, `test_charts.py`, `test_contracts.py`, `tools/intake.py`, `services/intake.py`, `safe_tool`, `Message`, `format_inr`, `test_ledger_extra.py`, `test_revenue_fx_cycles.py`, `tools/people.py`, `set_quote`, `User`, `tools/charts.py`, `test_ledger_gates.py`, `store.py`, `client_for`, `contracts.py`, `auth.py`, `review.py`, `upload`, `code_of`, `test_people_extra.py`, `propose_and_confirm`, `DomainError`, `test_api_intake.py`, `post_move`, `run`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Why does `Invoice` connect `Invoice` to `.due_on`, `datetime`, `row`, `client_by`, `models.py`, `Rev`, `fx_months.py`, `revenue_actions.py`, `services/proposals.py`, `test_revenue_fx_cycles.py`, `set_quote`, `go`, `test_revenue_core.py`, `cycles.py`, `services/charts.py`, `format_inr`, `_invoices_by_refs`, `project_end.py`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Why does `make_actor()` connect `make_actor` to `session_scope`, `test_intake_extra.py`, `test_budget_months.py`, `services/proposals.py`, `add_inspected_document`, `models.py`, `finance.py`, `test_revenue_core.py`, `test_charts.py`, `test_contracts.py`, `services/intake.py`, `Message`, `test_ledger_extra.py`, `test_revenue_fx_cycles.py`, `User`, `tools/charts.py`, `test_ledger_gates.py`, `store.py`, `client_for`, `review.py`, `test_people_extra.py`, `propose_and_confirm`, `DomainError`, `test_api_intake.py`, `post_move`, `options`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Are the 71 inferred relationships involving `Invoice` (e.g. with `_receivables()` and `DeleteDraft`) actually correct?**
  _`Invoice` has 71 INFERRED edges - model-reasoned connections that need verification._
- **Are the 54 inferred relationships involving `Rev` (e.g. with `_attention()` and `_read()`) actually correct?**
  _`Rev` has 54 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Voice conversation context`, `Language`, `Facts` to the rest of the system?**
  _242 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Phase 3: AWS Deployment and CI/CD` be split into smaller, more focused modules?**
  _Cohesion score 0.06827880512091039 - nodes in this community are weakly interconnected._