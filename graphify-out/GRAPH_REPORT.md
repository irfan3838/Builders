# Graph Report - Builders  (2026-11-21)

## Corpus Check
- 203 files · ~231,089 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 5, .example 2, .ini 1)

## Summary
- 3858 nodes · 12202 edges · 199 communities (124 shown, 75 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 1213 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `72243e33`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Phase 3: AWS Deployment and CI/CD
- hygiene
- document
- test_intake_extra.py
- test_b25_briefing.py
- DomainError
- PurserVoiceController.tsx
- test_budget_months.py
- package.json
- events.py
- test_b25_google.py
- MUNSHI: Voice-only, agent-centric finance and operations copilot
- services/charts.py
- DomainError
- Munshi | Product and delivery plan v2
- server.py
- propose_and_confirm
- compilerOptions
- test_charts_v2.py
- ContractCard.tsx
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
- workspace.py
- Plan
- Actor
- test_meetings.py
- services/budget_months.py
- projection.py
- Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST)
- fresh-sonnet-per-test-set.sh
- tests-only-in-sonnet.sh
- Agent
- Actor
- get
- go
- test_revenue_core.py
- cycles.py
- run_spec
- today_ist
- test_charts.py
- test_contracts.py
- test_roles_rbac.py
- services/intake.py
- Invoice
- cards.tsx
- ChartCard.tsx
- Rev
- extractor.py
- _propose
- _end
- spec
- metadata.py
- budgeting/__init__.py
- draft_message
- test_ledger_extra.py
- session_scope
- revenue_actions.py
- scan.py
- create
- Ctx
- test_suggest_email_voice.py
- test_revenue_fx_cycles.py
- User
- recommend.py
- revenue/money.py
- tools/charts.py
- distribution.py
- classify
- liability.py
- store.py
- pacing.py
- client_for
- part_paid_zed
- reads.py
- ClaimReview.tsx
- FakeSMTP
- day
- test_trips.py
- app/auth.py
- role_users.py
- fx_months.py
- post
- run
- test_people_extra.py
- usePurser
- function_tool
- code_of
- purser.md
- llm.py
- Diwan: the voice-first back office for Indian SMBs
- grounding.py
- make_contract_samples.py
- store.tsx
- _fmt_date
- safe_tool
- make_actor
- sugg
- email_plan
- Deployment (AWS, us-west-2)
- call
- options
- google_oauth.py
- services/work.py
- search_flights
- aws_put_secrets.py
- search
- google.py
- GEMINI_UI_BRIEF.md
- aws_run_task.sh
- call
- gmail.py
- google_actions.py
- react
- safe_tool
- Mail
- to_minor
- LeaveRequest
- date
- date
- date
- date
- date
- date
- MunshiContext
- Request
- get_settings
- date
- PurserSidebar.tsx
- env.py
- F
- client_by
- test_perform_each_kind
- invs_of
- FlightCard.tsx
- post_move
- test_injection_strings_are_inert
- analyse
- .due_on
- Action
- isolate
- test_schedule_meeting_non_linked_user_skipped
- Ctx
- Any
- isolate
- conv
- test_cycle_quarterly_combined_advance_books_in_first_month
- isolate
- google/__init__.py
- travel/__init__.py
- Actor
- Ctx
- Ctx
- Ctx
- Ctx
- Actor
- Actor
- Actor
- Actor
- Actor
- Actor
- User
- Actor
- Session
- Actor
- BaseModel
- date
- get
- Reservation
- RunContextWrapper
- StrEnum
- Task
- Actor

## God Nodes (most connected - your core abstractions)
1. `make_actor()` - 436 edges
2. `session_scope()` - 431 edges
3. `Actor` - 185 edges
4. `DomainError` - 98 edges
5. `call()` - 94 edges
6. `get_settings()` - 92 edges
7. `User` - 92 edges
8. `run()` - 92 edges
9. `Invoice` - 90 edges
10. `propose_and_confirm()` - 89 edges

## Surprising Connections (you probably didn't know these)
- `gitleaks Secret Scanning` --semantically_similar_to--> `Secrets via Secrets Manager / SSM`  [INFERRED] [semantically similar]
  README.md → CLAUDE.md
- `linked()` --uses--> `Actor`  [INFERRED]
  tests/b25_helpers.py → app/actor.py
- `add_inspected_document()` --uses--> `Actor`  [INFERRED]
  tests/conftest.py → app/actor.py
- `add_doc()` --uses--> `Actor`  [INFERRED]
  tests/test_intake_extra.py → app/actor.py
- `call()` --uses--> `Actor`  [INFERRED]
  tests/test_intake_extra.py → app/actor.py

## Import Cycles
- 4-file cycle: `web/src/FlightCard.tsx -> web/src/components/assistant/PurserVoiceController.tsx -> web/src/state/store.tsx -> web/src/cards.tsx -> web/src/FlightCard.tsx`

## Hyperedges (group relationships)
- **Candidate AWS Hosting Runtimes** — claude_aws_app_runner, claude_aws_lambda_api_gateway, claude_aws_ecs_fargate, claude_s3_cloudfront [EXTRACTED 1.00]
- **Hackathon Delivery Phases 0-4** — claude_phase_0, claude_phase_1, claude_phase_2, claude_phase_3, claude_phase_4 [EXTRACTED 1.00]
- **Secure CI/CD Pipeline** — claude_github_actions, claude_github_oidc, claude_terraform, claude_least_privilege_iam, readme_ci_hygiene_checks [INFERRED 0.85]

## Communities (199 total, 75 thin omitted)

### Community 0 - "Phase 3: AWS Deployment and CI/CD"
Cohesion: 0.07
Nodes (38): Tiny Agent Evaluation Set, Agent Guardrails (step limits, budgets, timeouts, retries), AWS App Runner, AWS ECS Fargate, AWS Lambda + API Gateway, Change-Scope Rules, CLAUDE.md Hackathon Agent Rules, Cost Awareness (+30 more)

### Community 1 - "hygiene"
Cohesion: 0.08
Nodes (24): concurrency, cancel-in-progress, group, GITLEAKS_VERSION, env, name, runs-on, steps (+16 more)

### Community 2 - "document"
Cohesion: 0.13
Nodes (29): close_intake(), correct_extracted_field(), find_reservations(), Ctx, function_tool, Open budget reservations for an employee that this receipt could replace (e.g.…, Finish intake WITHOUT any finance write, with an explicit outcome (contract,…, Show the original document page on screen, highlighting where a field was read… (+21 more)

### Community 3 - "test_intake_extra.py"
Cohesion: 0.08
Nodes (43): Party, _party(), AsyncSession, Revenue demo rows (ALL SYNTHETIC), written through the revenue services so…, seed(), _seed_revenue(), test_months_endpoint_other_workspace_404(), _approved_bill() (+35 more)

### Community 4 - "test_b25_briefing.py"
Cohesion: 0.07
Nodes (51): meetings(), datetime, The user's meetings for a time window: real Google Calendar for the linked…, Returns (events, source). Google errors propagate (callers decide whether to…, _admin(), build(), _ceo(), _common() (+43 more)

### Community 5 - "DomainError"
Cohesion: 0.11
Nodes (34): DomainError, Any, record_detail(), _approve_bill_inputs(), _approve_claim_inputs(), _bill_inputs(), _require_approver(), _settle_inputs() (+26 more)

### Community 6 - "PurserVoiceController.tsx"
Cohesion: 0.10
Nodes (18): setConversation(), ACCEPT, ACCEPT_ATTR, Assistant, AssistantContext, CONNECT_RETRIES, handsFreeOn(), PurserVoiceController() (+10 more)

### Community 7 - "test_budget_months.py"
Cohesion: 0.14
Nodes (21): Month-end utilisation status: OPEN (no positive budget), UNDERUSED (< 85%),…, allocated(), allocated_in(), cells(), change(), count_movements(), frozen_today(), paise() (+13 more)

### Community 8 - "package.json"
Cohesion: 0.05
Nodes (37): echarts, @fontsource/dm-sans, @fontsource/geist-mono, @fontsource/noto-sans-devanagari, @fontsource/source-serif-4, @types/react, @types/react-dom, @types/three (+29 more)

### Community 9 - "events.py"
Cohesion: 0.40
Nodes (4): In-process event fan-out to the browser (SSE), keyed by conversation. One…, subscribe(), unsubscribe(), Queue

### Community 10 - "test_b25_google.py"
Cohesion: 0.08
Nodes (45): dispatch(), Perform queued Google ops once each (SKIP LOCKED; a failure is kept, never…, build_raw(), actor_by_email(), linked(), ops(), parse(), plan() (+37 more)

### Community 11 - "MUNSHI: Voice-only, agent-centric finance and operations copilot"
Cohesion: 0.08
Nodes (25): 0. Planning inputs and research status, 10. Contract liability analysis (re-implemented from the user's guide), 11. Bill and receipt extraction, 12. External integrations, 13. Data model (Postgres; money = BIGINT paise; timestamps UTC, IST display; FY Apr-Mar), 14. Repository layout (this repo, `~/Projects/Builders`), 15. AWS deployment and CI/CD, 16. Security and trust (+17 more)

### Community 12 - "services/charts.py"
Cohesion: 0.11
Nodes (36): _ageing(), _budget(), _budget_flows(), ChartType, _claims(), CompareMode, Compiled, _contracts() (+28 more)

### Community 14 - "Munshi | Product and delivery plan v2"
Cohesion: 0.12
Nodes (16): 10. Data design and isolation, 11. Secondary workflows and integrations, 12. Implementation and deployment, 13. Build sequence and cut decisions, 14. Acceptance, evaluation and evidence, 15. Four-minute demonstration and handoff, 16. Definition of done, 1. User, problem and submission (+8 more)

### Community 15 - "server.py"
Cohesion: 0.17
Nodes (11): Bridge, create_session(), get_budget_status(), index(), BaseModel, function_tool, get, Request (+3 more)

### Community 16 - "propose_and_confirm"
Cohesion: 0.12
Nodes (28): dispatch(), Send queued emails. Each row is claimed with SKIP LOCKED so concurrent…, close(), close_oct(), test_apply_recommendations_then_nothing_left(), test_claimed_document_cannot_be_closed_afterwards(), test_settle_defaults_to_today_ist(), propose_and_confirm() (+20 more)

### Community 17 - "compilerOptions"
Cohesion: 0.13
Nodes (14): compilerOptions, isolatedModules, jsx, lib, module, moduleResolution, noEmit, noUnusedLocals (+6 more)

### Community 18 - "test_charts_v2.py"
Cohesion: 0.09
Nodes (55): run(), sql(), test_bills_totals_match_sql(), test_budget_by_category_matches_movements(), test_date_range_filter_matches_sql(), test_injection_strings_just_fail_to_match(), test_overdue_total_and_filters_match_sql(), test_receivables_totals_and_rows_match_sql() (+47 more)

### Community 19 - "ContractCard.tsx"
Cohesion: 0.17
Nodes (11): ContractCard(), ContractClauseCard(), ContractDeadlinesCard(), ContractReviewCard(), Deadlines(), fmtDate(), KIND, LiabilitiesCard() (+3 more)

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
Cohesion: 0.06
Nodes (36): _cycle_client(), Guide: changing a month clears later explicit settings in the affected span…, fn(ss, rv) on a sync session in one committed transaction; return plain data., run(), rv_of(), test_carried_months_runs_to_march_not_beyond(), test_fx_cached_returns_micro_or_none(), test_fx_grid_marks_carried_months() (+28 more)

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
Cohesion: 0.07
Nodes (52): AuditEvent, Bill, BudgetPeriod, CompanyPayment, InvoicePayment, LeaveMovement, OnboardingTask, Policy (+44 more)

### Community 40 - "build"
Cohesion: 0.27
Nodes (11): age_bucket(), build(), ClientLine, Due, Exposure, Insights, Kpis, Month (+3 more)

### Community 41 - "2. Still to do (in priority order)"
Cohesion: 0.07
Nodes (29): 1.10 Commits, 1.1 Voice (hour-0 spike, then productionised), 1.2 Agent (OpenAI Agents SDK), 1.3 Trust boundary: propose → present → confirm → receipt, 1.4 Finance domain, 1.5 People ops (PLAN_v5), 1.6 API and infrastructure (local), 1.7 Web UI (`web/`, React 19 + Vite + TypeScript) (+21 more)

### Community 42 - "workspace.py"
Cohesion: 0.07
Nodes (53): explain_budget_change(), get_attention_items(), get_audit_history(), get_briefing(), get_budget_status(), get_record(), list_budget_categories(), _pos_view() (+45 more)

### Community 43 - "Plan"
Cohesion: 0.09
Nodes (22): Execution, Plan, ApplyRecommendations, BudgetChange, _change_plan(), _close_plan(), CloseMonth, _paise() (+14 more)

### Community 45 - "test_meetings.py"
Cohesion: 0.05
Nodes (66): Settings, Meeting, A calendar event with a Google Meet link. Queued inside the confirm…, _meeting_inputs(), ScheduleMeeting, _access_token(), CalendarError, create_event() (+58 more)

### Community 46 - "services/budget_months.py"
Cohesion: 0.12
Nodes (43): get_budget_month(), get_budget_recommendations(), This month's (or a given month's) budget per category: budget, spent,…, Trend recommendations from the last 3 CLOSED months (consistent overrun or…, alerts(), apply_change(), apply_close(), Cell (+35 more)

### Community 47 - "projection.py"
Cohesion: 0.11
Nodes (20): month_outlook(), Outlook, Where spend is heading (run rate), for the CEO's three bars: allocated, spent,…, budgets / spends: the FY's 12 months in order; current: index of this month (0…, year_outlook(), Change, Month, pace_of() (+12 more)

### Community 48 - "Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST)"
Cohesion: 0.50
Nodes (3): Added capabilities (same agent, same propose → confirm → receipt engine), Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST), Rules

### Community 53 - "Actor"
Cohesion: 0.05
Nodes (79): Actor, The authenticated principal. Always derived from the server session, never from…, Finance approval rights., May SEE budget, revenue, payables, receivables and company-wide records (not…, May not make any change at all (no proposals, no direct writes)., The one login whose real Gmail and Google Calendar Purser may use…, HR/admin rights: onboarding, company-wide announcements, all leave., briefing() (+71 more)

### Community 55 - "go"
Cohesion: 0.10
Nodes (45): figures(), mk_client(), mk_inr(), Rs 10,000 Oct with Rs 4,000 in; move Rs 6,000 to Nov: moved_paise 600000, Oct…, send(), test_allocation_across_two_clients_rejected(), go(), test_allocation_without_amount_pays_each_remaining() (+37 more)

### Community 56 - "test_revenue_core.py"
Cohesion: 0.10
Nodes (37): pinned(), priya(), propose_confirm(), fixture, Revenue core: money maths, invoice lifecycle, allocation, reporting figures,…, Revenue clients are customer Parties in the same workspace table (no separate…, Approver with no conversation: grounding is skipped (the on-screen form path)., row() (+29 more)

### Community 57 - "cycles.py"
Cohesion: 0.11
Nodes (44): ClientCycle, A client's billing cycle from a month on: monthly charge, every N months,…, active(), apply(), ChangePlan, check(), _clashes(), combined() (+36 more)

### Community 58 - "run_spec"
Cohesion: 0.09
Nodes (32): _auto_chart(), _bad(), ChartSpec, _fetch(), FilterSpec, fmt_value(), _fold(), fold_by() (+24 more)

### Community 59 - "today_ist"
Cohesion: 0.14
Nodes (27): bm_round(), forecast_budget(), get_budget_alerts(), get_budget_history(), get_budget_year(), MonthSplit, propose_apply_recommendations(), propose_budget_change() (+19 more)

### Community 60 - "test_charts.py"
Cohesion: 0.16
Nodes (20): build(), client_for(), err(), err_sync(), priya_arjun(), DomainError, parametrize, Dynamic charts: validation, chart-type rules, totals vs independent SQL,… (+12 more)

### Community 61 - "test_contracts.py"
Cohesion: 0.05
Nodes (71): _attention(), defined_parties(), {defined term (lower) -> party name} from '(hereinafter referred to as "the…, liabilities(), Copilot's Exposure plus who bears it: risky clauses that are proposed, accepted…, search(), _a_flag(), analyse() (+63 more)

### Community 62 - "test_roles_rbac.py"
Cohesion: 0.10
Nodes (32): Agent, _instructions(), RunContextWrapper, _allowed(), apply(), enabled(), RunContextWrapper, Which tools each role is offered. The model never sees a tool its role cannot… (+24 more)

### Community 63 - "services/intake.py"
Cohesion: 0.12
Nodes (35): ensure_extraction(), prefetch(), Actor, Document reading (vision extraction) shared by the upload path and the…, _read(), inspect_document(), Read an uploaded document (runs extraction the first time). Returns type,…, _view() (+27 more)

### Community 64 - "Invoice"
Cohesion: 0.09
Nodes (71): Invoice, A customer invoice (revenue). Ported from the copilot Revenue module. Billing…, _date(), conflict(), invalid(), log(), Any, DomainError (+63 more)

### Community 65 - "cards.tsx"
Cohesion: 0.08
Nodes (32): AuditCard(), BudgetCard(), Deliveries(), fmt(), InboxCard(), LEAVE_NAME, LeaveCard(), LeaveRequestsCard() (+24 more)

### Community 66 - "ChartCard.tsx"
Cohesion: 0.15
Nodes (19): CATS, ChartCard(), compactInr(), DataTable(), fmtAxis(), fmtChange(), fmtFull(), fullInr() (+11 more)

### Community 67 - "Rev"
Cohesion: 0.10
Nodes (40): go(), A dated in-app reminder ('remind me Friday to chase Acme'), optionally about a…, Reminder, client(), clients(), create_client(), _currency(), find_clients() (+32 more)

### Community 68 - "extractor.py"
Cohesion: 0.24
Nodes (12): build_agent(), Cite, extract(), ExtractedDocument, LineItem, Agent, BaseModel, ExtractorAgent: reads document page images into a typed schema. It has NO… (+4 more)

### Community 69 - "_propose"
Cohesion: 0.05
Nodes (89): Convert DomainError into a structured result the agent can explain; log name,…, safe_tool(), contract_deadlines(), get_contract(), list_liabilities(), propose_contract_details(), propose_contract_status(), propose_create_contract() (+81 more)

### Community 70 - "_end"
Cohesion: 0.10
Nodes (22): _end(), Kaveri's paid Oct invoice covers Oct-Dec: a monthly cycle from Nov must not…, test_change_cycle_skips_months_covered_by_a_kept_combined_invoice(), go(), test_end_combine_merges_sources_into_one_priced_at_the_month_rate(), go(), test_end_combine_send_now_false_leaves_a_draft_and_delete_restores_sources(), go() (+14 more)

### Community 71 - "spec"
Cohesion: 0.13
Nodes (26): apply_patch(), chart_problem(), ChartSpecPatch, A revision. Anything omitted keeps its current value, so grouping survives…, Why the requested chart type does not fit the spec's shape, or None., spec(), test_add_filters_replaces_and_clear_filters(), test_month_to_customer_with_line_falls_back_to_auto() (+18 more)

### Community 72 - "metadata.py"
Cohesion: 0.14
Nodes (29): add_months(), _clean(), _client(), dates(), Detail, Details, _effective(), end_of_term() (+21 more)

### Community 75 - "draft_message"
Cohesion: 0.25
Nodes (8): draft_message(), DraftIn, mark_read(), prepare_approval(), BaseModel, post, Prepare a send_message proposal from the mail composer. Nothing is sent until…, PREPARE_APPROVAL from the UI: builds the same 'approve' proposal the agent…

### Community 76 - "test_ledger_extra.py"
Cohesion: 0.08
Nodes (79): cancel_pending_proposal(), _confirm(), get_pending_proposal(), _proposal_view(), Cancel the open proposal (user said no / cancel / changed their mind)., The current open proposal awaiting the user's decision in this conversation, if…, Execute the open proposal ONLY after the user clearly said yes to its preview…, BudgetMovement (+71 more)

### Community 77 - "session_scope"
Cohesion: 0.16
Nodes (24): One transaction; commits on success, rolls back on any exception., session_scope(), AsyncSession, record_turn(), _open_approve(), _present_then_turn(), _spoken(), test_client_controlled_source_is_not_accepted_as_evidence() (+16 more)

### Community 78 - "revenue_actions.py"
Cohesion: 0.05
Nodes (50): AddInvoices, _ccy(), _clean_num(), ClientChange, DeleteDraft, EditInvoice, _eff(), EndProject (+42 more)

### Community 79 - "scan.py"
Cohesion: 0.09
Nodes (39): The shipped clause catalogue: copilot `ctr_0001_contracts.py` CLAUSE_TYPES,…, A clause type as the scan sees it., Rule, rules(), _ask(), _dedup(), Found, _join() (+31 more)

### Community 80 - "create"
Cohesion: 0.09
Nodes (45): FxMonth, A conversion rate set by hand for a currency and month; carries forward until…, canonical(), create(), inv_of(), priya(), propose_confirm(), Approver with no conversation: grounding skipped (the on-screen form path). (+37 more)

### Community 82 - "test_suggest_email_voice.py"
Cohesion: 0.07
Nodes (43): open_view(), BaseModel, function_tool, safe_tool, Next-step suggestion chips. Writes nothing: a clicked chip only sends a normal…, Show 1-3 tappable next-step chips under your reply. The first must match the…, Open a screen for the user by voice ('open my tasks', 'go home', 'show the…, suggest_next_actions() (+35 more)

### Community 83 - "test_revenue_fx_cycles.py"
Cohesion: 0.12
Nodes (25): FxQuote, Cached ECB reference quotes (Frankfurter): INR per unit x 10^6, by publication…, AsyncSession, Fetch and cache the latest quote for each foreign ECB currency. Returns…, refresh(), _aug_ecb(), pinned(), fixture (+17 more)

### Community 84 - "User"
Cohesion: 0.08
Nodes (53): find_people(), get_leave_balance(), get_onboarding_status(), list_leave_requests(), lookup_policy(), _person(), propose_leave(), propose_leave_decision() (+45 more)

### Community 85 - "recommend.py"
Cohesion: 0.18
Nodes (17): ClosedMonth, plan(), slots(), PlannedChange, `closed_chrono`: the category's closed months, oldest first (any number)., Trend recommendations: if a category has over- (or under-) run its budget for…, One budget change that acts on the recommendations, for one month (amounts in…, Act on the recommendations for one month, moving money before adding any: each… (+9 more)

### Community 86 - "revenue/money.py"
Cohesion: 0.14
Nodes (16): currencies_in(), digits(), from_minor(), _indian(), paise_str(), paise_to(), Ported from copilot clients_mod/money.py (user's own code), unchanged except…, Currencies the user named: codes, symbols or words ('2000 euros', '$1,750', 'in… (+8 more)

### Community 87 - "tools/charts.py"
Cohesion: 0.13
Nodes (28): build_chart(), _card(), describe_chart_options(), present_view(), function_tool, safe_tool, Chart and view tools. The model composes typed specs; every number comes from a…, What can be charted for this user: sources, measures (with units), dimensions,… (+20 more)

### Community 88 - "distribution.py"
Cohesion: 0.20
Nodes (13): by_weights(), even_split(), Divide `total_paise` into `n` parts that sum exactly to it (remainder on the…, Annual -> monthly budget distribution (PRD §3). Integer paise only; no paise is…, Keep the `locked` month indices as given and spread `total_paise - sum(locked)`…, Split `total_paise` in proportion to `weights` (exact fractions, no floats).…, Growing shares: the first month weighs 1 and each next month weighs the one…, The paise each of `months` gets out of `total_paise` (same order, summing to… (+5 more)

### Community 89 - "classify"
Cohesion: 0.06
Nodes (36): Affirmation, classify(), _contains_affirm(), _normalize(), StrEnum, Deterministic classifier for a confirmation utterance (English, Hindi,…, client(), LiveBridge (+28 more)

### Community 90 - "liability.py"
Cohesion: 0.10
Nodes (30): as_dict(), assess(), _bearer_term(), _beneficiary(), carve_outs_rules(), Deadline, deadlines(), Liability (+22 more)

### Community 91 - "store.py"
Cohesion: 0.17
Nodes (28): Contract, ContractDeadline, ContractFinding, One agreement. Text is the extracted reading of the original document (kept in…, A clause found in a contract (copilot ctr_clause) plus Purser's liability…, A dated obligation computed by code from the contract (expiry, renewal notice,…, Contract writes as propose -> present -> confirm -> receipt actions (the same…, Deadlines follow the contract's current expiry and its auto-renewal notice… (+20 more)

### Community 92 - "pacing.py"
Cohesion: 0.24
Nodes (9): compute(), days_in_month(), Pacing, date, The pacing / burn-velocity engine and the proactive alert levels (PRD §4). Pure…, `day` is the current day of the month (1..total_days); use total_days for a…, _round2(), test_pacing_approaching_and_limit() (+1 more)

### Community 93 - "client_for"
Cohesion: 0.06
Nodes (54): client_for(), test_employee_cannot_open_other_users_document(), test_exact_replay_returns_existing_document(), test_write_requires_csrf(), test_location_api_requires_login_and_csrf(), test_months_endpoint(), test_agent_text_requires_conversation_header_and_text(), test_conversation_channel_is_validated_and_api_is_not_cached() (+46 more)

### Community 94 - "part_paid_zed"
Cohesion: 0.10
Nodes (25): mk_client(), mk_invoice(), part_paid_zed(), Guide example: Rs 10,000 invoice, Rs 4,000 received, part paid., test_balance_delete_destination_restores_source_to_part_paid(), go(), test_balance_into_other_currency_month_makes_its_own_balance_invoice(), go() (+17 more)

### Community 95 - "reads.py"
Cohesion: 0.09
Nodes (39): active(), covers(), due_on(), key_ym(), period_end(), period_text(), raise_on(), "Oct'26 to Dec'26" for an invoice of a several-month period, else ''. (+31 more)

### Community 96 - "ClaimReview.tsx"
Cohesion: 0.07
Nodes (33): motion, react-dom, ease, easeInOut, palette, reveal, api, inr() (+25 more)

### Community 98 - "day"
Cohesion: 0.08
Nodes (48): google_hotels_url(), _norm(), date, Hotel search: SerpAPI Google Hotels (real rates, the hotel's own website for…, _safe_link(), _sample(), search(), booking_body() (+40 more)

### Community 99 - "test_trips.py"
Cohesion: 0.15
Nodes (44): GoogleOp, HotelBooking, Outbox for confirmed Gmail / Google Calendar changes on the linked account.…, A hotel stay approved in Purser. Payment happens on the hotel's own website…, BookTrip, pin(), Replace get_settings everywhere it was imported by name, so one patched…, book_trip() (+36 more)

### Community 100 - "app/auth.py"
Cohesion: 0.28
Nodes (12): _actor(), check_write(), current_actor(), current_csrf(), login(), Request, Response, Cookie session auth + CSRF. The Actor is derived from the server session on… (+4 more)

### Community 102 - "role_users.py"
Cohesion: 0.16
Nodes (16): Task, can_decide(), can_view(), ensure(), prefetch(), The staged review. With wait_seconds, returns None if it is still running (it…, _at(), clean_labels() (+8 more)

### Community 103 - "fx_months.py"
Cohesion: 0.11
Nodes (28): fy_months(), fy_of(), fy_start(), quarter_of(), [(2026, 4), (2026, 5), ... (2027, 3)], 0..3: the quarter of the FY a month falls in., Affected, carried_months() (+20 more)

### Community 105 - "run"
Cohesion: 0.12
Nodes (21): ExceptionInfo, code_of(), Run fn(ss, rv) on a sync session inside one committed transaction; return what…, run(), rv_of(), test_create_cap_and_duplicate_months(), go(), test_cycle_monthly_mode_emits_one_row_per_month() (+13 more)

### Community 106 - "test_people_extra.py"
Cohesion: 0.13
Nodes (30): Message, Inbox item and/or email outbox row. Email rows are delivered after the…, code_of(), count(), boom(), present(), parametrize, People-ops coverage (PLAN_v5): leave ledger and decisions, messaging outbox,… (+22 more)

### Community 107 - "usePurser"
Cohesion: 0.12
Nodes (32): lucide-react, PurserComposer(), useAssistant(), Briefing, BriefingView(), Item, Section, useBriefing() (+24 more)

### Community 109 - "code_of"
Cohesion: 0.17
Nodes (8): code_of(), test_balance_delete_requires_unraised_destination(), go(), test_ending_an_ended_client_is_same_state(), test_foreign_and_inr_month_inputs_validated(), unknown(), test_price_aed_is_manual_only_even_with_a_cached_row(), test_price_no_cache_raises_rate_unavailable()

### Community 110 - "purser.md"
Cohesion: 0.12
Nodes (16): Charts and views, Contracts and liabilities, Facts, Language, Mail and calendar, Monthly budget, alerts, changes and month close, Next step, Other requests (+8 more)

### Community 111 - "llm.py"
Cohesion: 0.13
Nodes (18): enabled(), LLMUnavailable, BaseModel, Exception, The only place contract review talks to a model. Small and replaceable:…, No key, provider error, timeout or unparseable answer: the caller falls back to…, Page images -> plain text (a scanned agreement has no text layer)., structured() (+10 more)

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
Cohesion: 0.09
Nodes (23): dur, cardKey(), CardView(), ArtifactPanel(), UploadCard(), Props, TARGETS, Caption (+15 more)

### Community 116 - "_fmt_date"
Cohesion: 0.11
Nodes (11): Any, _apply(), ApplyLeave, Approve, ApproveBill, ApproveClaim, _budget_effect(), DecideLeave (+3 more)

### Community 118 - "make_actor"
Cohesion: 0.12
Nodes (38): make_actor(), ask(), counts(), opts(), parametrize, B3 gate: ask_choice (2-5 options, chart registry validation, per-topic cap of…, Without a conversation there is nowhere to count: every question is allowed…, An employee's registry has no finance sources, so a finance measure cannot be… (+30 more)

### Community 119 - "sugg"
Cohesion: 0.25
Nodes (9): sugg(), test_custom_reminder_survives_pause(), go(), test_paused_client_gets_no_billing_suggestions(), go(), test_raise_when_raise_date_arrived_not_before(), go(), test_reminder_due_today_appears_future_does_not() (+1 more)

### Community 120 - "email_plan"
Cohesion: 0.24
Nodes (11): address_plan(), compose(), email_plan(), AsyncSession, Where an email to this user would go, and whether it is deliverable in this…, Whether an email to this address is deliverable in this demo (same rule for…, external_emails are people outside the workspace: email only (they have no…, parametrize (+3 more)

### Community 121 - "Deployment (AWS, us-west-2)"
Cohesion: 0.22
Nodes (8): Architecture, Deployment (AWS, us-west-2), Email and Google Meet, First deploy, Notes, Redeploy (new code), Rollback, Teardown

### Community 122 - "call"
Cohesion: 0.12
Nodes (38): FlightBooking, A SIMULATED flight booking: no ticket is bought. Real fare data from the search…, BookFlight, _flight_args(), day(), do_search(), fake_search(), one() (+30 more)

### Community 123 - "options"
Cohesion: 0.13
Nodes (15): ask_choice(), Choice, current(), BaseModel, function_tool, safe_tool, Ask ONE short multiple-choice question with 2-5 tappable answers, then STOP and…, _registry_values() (+7 more)

### Community 124 - "google_oauth.py"
Cohesion: 0.33
Nodes (7): Path, _client(), _env(), main(), One-time Google login for the linked account (Gmail + Calendar): gets a refresh…, _set_env(), _wait_for_code()

### Community 125 - "services/work.py"
Cohesion: 0.11
Nodes (32): add_task(), complete_task(), list_tasks(), list_tickets(), propose_assign_task(), propose_ticket(), propose_ticket_update(), function_tool (+24 more)

### Community 126 - "search_flights"
Cohesion: 0.09
Nodes (31): get_my_location(), _here(), propose_flight_booking(), propose_trip_booking(), function_tool, safe_tool, Search hotels for a stay (live Google Hotels rates): name, stars, rating, price…, Propose booking a whole trip: one flight option and/or one hotel option from… (+23 more)

### Community 129 - "search"
Cohesion: 0.10
Nodes (28): checkout_link(), FlightSearchError, google_flights_url(), _hhmm(), _norm_option(), date, Exception, Flight search: SerpAPI Google Flights (real fares) with a 30-minute cache; on… (+20 more)

### Community 130 - "google.py"
Cohesion: 0.17
Nodes (24): _g(), list_meetings(), _need_google(), propose_cancel_meeting(), propose_email(), propose_mail_action(), propose_reschedule_meeting(), datetime (+16 more)

### Community 133 - "call"
Cohesion: 0.16
Nodes (22): _label_id(), perform(), access_token(), call(), error_text(), GoogleError, Exception, Response (+14 more)

### Community 134 - "gmail.py"
Cohesion: 0.13
Nodes (20): addresses(), _decode(), get_thread(), _hdr(), Gmail for the linked account. Message bodies are UNTRUSTED data: stripped to…, Prefer text/plain; fall back to text/html with tags removed., Recipient, subject and threading headers for a reply to the latest message in a…, reply_context() (+12 more)

### Community 135 - "google_actions.py"
Cohesion: 0.20
Nodes (11): CancelEvent, _emails(), _local(), MailAction, datetime, _queue(), Confirmed changes on the linked Google account: send/reply email, inbox…, _require_google() (+3 more)

### Community 136 - "react"
Cohesion: 0.18
Nodes (12): react, three, ApiError, call(), Card, headers(), Me, setSession() (+4 more)

### Community 138 - "Mail"
Cohesion: 0.22
Nodes (6): Mail, fixture, smtp(), test_multiline_default_subject_can_be_emailed(), test_send_smtp_builds_expected_message(), test_send_smtp_never_allows_header_injection()

### Community 139 - "to_minor"
Cohesion: 0.13
Nodes (18): numbers_in(), Decimal, Every number the user wrote, with k / lakh / crore applied ('1.5L' -> 150000,…, The number appears in the user's words (a model never invents an amount)., 2,000.50' EUR -> 200050. Raises ValueError for anything that is not a non-…, 89.12' -> 89_120_000. Must be positive and sane; rounded to six decimals., rupees_to_paise(), said() (+10 more)

### Community 140 - "LeaveRequest"
Cohesion: 0.28
Nodes (15): LeaveRequest, apply(), assert_leave_conservation(), bal(), test_apply_for_someone_else_rights(), test_apply_leave_rejections(), test_apply_leave_reserves_days_and_previews_balance(), test_approve_moves_reserved_to_used_and_notifies() (+7 more)

### Community 149 - "get_settings"
Cohesion: 0.05
Nodes (62): PurserContext, Passed to every tool via RunContextWrapper. Identity comes only from here,…, build_agent(), PurserAgent: one conversational agent with typed tools. Same agent for voice…, memory(), Actor, One user turn through PurserAgent. Shared by the text channel, push-to-talk and…, run_turn() (+54 more)

### Community 151 - "PurserSidebar.tsx"
Cohesion: 0.17
Nodes (12): spring, ACTION_WORDS, ago(), humanize(), NavDef, Note, Notifications(), Profile() (+4 more)

### Community 152 - "env.py"
Cohesion: 0.27
Nodes (9): Connection, do_run_migrations(), include_object(), Run migrations in 'offline' mode. This configures the context with just a URL…, In this scenario we need to create an Engine and associate a connection with…, Run migrations in 'online' mode., run_async_migrations(), run_migrations_offline() (+1 more)

### Community 153 - "F"
Cohesion: 0.16
Nodes (16): add_doc(), F(), parametrize, Document + Extraction with arbitrary fields (no model call)., test_arithmetic_and_breakdown_sum(), test_company_payment_match_found_and_absent(), test_correct_extracted_field_bad_date_is_structured_validation_error(), test_correct_extracted_field_tool() (+8 more)

### Community 154 - "client_by"
Cohesion: 0.09
Nodes (27): client_by(), test_change_cycle_keeps_raised_and_paid_and_skips_their_months(), go(), test_change_cycle_replaces_later_rules_and_updates_client_currency(), go(), test_cycle_active_and_current_rules(), go(), test_end_combine_requires_common_currency_and_something_pending() (+19 more)

### Community 155 - "test_perform_each_kind"
Cohesion: 0.15
Nodes (6): test_perform_each_kind(), create(), modify(), op(), test_perform_label_reuses_existing_or_creates(), test_save_mail_draft_new_requires_to_and_subject()

### Community 156 - "invs_of"
Cohesion: 0.17
Nodes (12): invs_of(), test_apply_reprices_ticked_and_leaves_paid_and_part_paid(), go(), test_change_cycle_midyear_removes_only_to_raise_from_the_change_month(), go(), test_end_separate_sends_each_to_raise_on_the_end_day(), go(), test_plan_balance_preview_writes_nothing() (+4 more)

### Community 157 - "FlightCard.tsx"
Cohesion: 0.25
Nodes (10): dur(), FlightOptionsCard(), Hotel, HotelOptionsCard(), inr(), openPayment(), Opt, Pay (+2 more)

### Community 158 - "post_move"
Cohesion: 0.40
Nodes (10): flows(), lines_by_cat(), post_move(), test_budget_flows_conservation_and_directions(), test_budget_flows_does_not_change_budget_source_and_is_workspace_scoped(), test_budget_flows_empty_on_fresh_seed(), test_budget_flows_multi_month_transfer_pairs_per_month(), test_budget_flows_other_dimensions_and_filters() (+2 more)

### Community 159 - "test_injection_strings_are_inert"
Cohesion: 0.22
Nodes (9): parse_cap(), (cap in paise, basis text). A non-INR or non-numeric cap keeps paise None and…, parametrize, test_injection_strings_are_inert(), test_parse_cap_inr(), test_parse_cap_no_amount(), test_parse_cap_usd_keeps_basis_no_paise(), test_review_finding_validation() (+1 more)

### Community 160 - "analyse"
Cohesion: 0.29
Nodes (8): analyse(), clean_name(), guess_title(), guess_type(), Northwind Labs Inc, a company incorporated in Delaware' -> 'Northwind Labs Inc'., The whole review of a text: findings with liabilities, details, deadlines. Pure…, test_guess_type_and_title(), test_live_demo_clean_name_has_no_company_tail()

### Community 163 - "Action"
Cohesion: 0.50
Nodes (3): Action, AsyncSession, Protocol

### Community 165 - "test_schedule_meeting_non_linked_user_skipped"
Cohesion: 0.50
Nodes (3): margs(), test_schedule_meeting_linked_user_queued(), test_schedule_meeting_non_linked_user_skipped()

### Community 171 - "conv"
Cohesion: 0.67
Nodes (3): conv(), Actor, Same user, fresh conversation (a second session).

### Community 172 - "test_cycle_quarterly_combined_advance_books_in_first_month"
Cohesion: 0.67
Nodes (3): Rs 10,000 a month, 3-month period from Oct, combined/advance: Rs 30,000 in Oct…, test_cycle_quarterly_combined_advance_books_in_first_month(), go()

## Knowledge Gaps
- **261 isolated node(s):** `Voice conversation context`, `Language`, `Next step`, `Facts`, `Workflow for a new document (receipt or bill)` (+256 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1120 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **75 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `session_scope()` connect `session_scope` to `document`, `test_intake_extra.py`, `test_b25_briefing.py`, `DomainError`, `test_budget_months.py`, `test_b25_google.py`, `LeaveRequest`, `propose_and_confirm`, `test_charts_v2.py`, `get_settings`, `run`, `F`, `post_move`, `test_injection_strings_are_inert`, `test_schedule_meeting_non_linked_user_skipped`, `models.py`, `workspace.py`, `conv`, `test_meetings.py`, `services/budget_months.py`, `Actor`, `test_revenue_core.py`, `run_spec`, `today_ist`, `test_charts.py`, `test_contracts.py`, `test_roles_rbac.py`, `services/intake.py`, `_propose`, `spec`, `draft_message`, `test_ledger_extra.py`, `create`, `test_suggest_email_voice.py`, `test_revenue_fx_cycles.py`, `User`, `tools/charts.py`, `store.py`, `client_for`, `day`, `test_trips.py`, `app/auth.py`, `role_users.py`, `run`, `test_people_extra.py`, `make_actor`, `call`, `options`, `services/work.py`, `search_flights`?**
  _High betweenness centrality (0.092) - this node is a cross-community bridge._
- **Why does `make_actor()` connect `make_actor` to `document`, `test_intake_extra.py`, `test_b25_briefing.py`, `DomainError`, `test_budget_months.py`, `test_b25_google.py`, `LeaveRequest`, `propose_and_confirm`, `test_charts_v2.py`, `get_settings`, `F`, `test_perform_each_kind`, `post_move`, `test_injection_strings_are_inert`, `test_schedule_meeting_non_linked_user_skipped`, `test_meetings.py`, `services/budget_months.py`, `Actor`, `test_revenue_core.py`, `run_spec`, `test_charts.py`, `test_contracts.py`, `test_roles_rbac.py`, `spec`, `test_ledger_extra.py`, `session_scope`, `create`, `test_suggest_email_voice.py`, `test_revenue_fx_cycles.py`, `User`, `tools/charts.py`, `client_for`, `day`, `test_trips.py`, `test_people_extra.py`, `call`, `options`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `Actor` connect `Actor` to `document`, `test_intake_extra.py`, `test_b25_briefing.py`, `DomainError`, `test_b25_google.py`, `services/charts.py`, `get_settings`, `F`, `Action`, `models.py`, `workspace.py`, `services/budget_months.py`, `run_spec`, `today_ist`, `test_roles_rbac.py`, `services/intake.py`, `draft_message`, `test_ledger_extra.py`, `session_scope`, `revenue_actions.py`, `create`, `User`, `tools/charts.py`, `classify`, `app/auth.py`, `role_users.py`, `make_actor`, `email_plan`, `call`, `options`, `services/work.py`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Are the 139 inferred relationships involving `Actor` (e.g. with `briefing()` and `budget_alerts()`) actually correct?**
  _`Actor` has 139 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `DomainError` (e.g. with `test_beneficiary_cannot_self_approve()` and `test_cross_workspace_object_ids_not_found()`) actually correct?**
  _`DomainError` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Voice conversation context`, `Language`, `Next step` to the rest of the system?**
  _261 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Phase 3: AWS Deployment and CI/CD` be split into smaller, more focused modules?**
  _Cohesion score 0.06827880512091039 - nodes in this community are weakly interconnected._