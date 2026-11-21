# Graph Report - Builders  (2026-11-21)

## Corpus Check
- 159 files · ~182,693 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 5, .example 2, .ini 1)

## Summary
- 2948 nodes · 9206 edges · 159 communities (110 shown, 49 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 809 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e85f1178`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Phase 3: AWS Deployment and CI/CD
- hygiene
- _propose
- make_actor
- models.py
- actions.py
- PurserVoiceController.tsx
- test_budget_months.py
- package.json
- domain_error
- correct_extracted_field
- MUNSHI: Voice-only, agent-centric finance and operations copilot
- get_settings
- DomainError
- Munshi | Product and delivery plan v2
- server.py
- LeaveRequest
- compilerOptions
- test_charts_v2.py
- event_stream
- Munshi | Final weekend build plan
- Munshi | Build plan v3 (scope cut for the weekend)
- 5. Agent architecture
- run
- 5. Financial record lifecycles
- Purser architecture decisions
- AUTHORSHIP.md
- builders
- compose
- records.py
- budget.py
- 2. Still to do (in priority order)
- finance.py
- DomainError
- record_turn
- Settings
- services/budget_months.py
- projection.py
- Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST)
- fresh-sonnet-per-test-set.sh
- tests-only-in-sonnet.sh
- Agent
- main.py
- get
- mk_inr
- test_revenue_core.py
- cycles.py
- services/charts.py
- tools/budget_months.py
- test_charts.py
- session_scope
- tools/charts.py
- services/intake.py
- Invoice
- cards.tsx
- ChartCard.tsx
- Party
- extractor.py
- safe_tool
- client_by
- spec
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
- fx.py
- User
- recommendations
- revenue/money.py
- test_ledger_gates.py
- distribution.py
- grounding.py
- liability.py
- store.py
- pacing.py
- client_for
- part_paid_zed
- Mail
- ClaimReview.tsx
- FakeSMTP
- date
- Ctx
- auth.py
- review.py
- Rev
- Any
- go
- test_people_extra.py
- ViewRouter.tsx
- Compiled
- code_of
- purser.md
- llm.py
- Diwan: the voice-first back office for Indian SMBs
- invs_of
- make_contract_samples.py
- store.tsx
- Read
- locate
- post_move
- run
- upload
- Deployment (AWS, us-west-2)
- analyse
- options
- messages_for
- test_paused_and_ended_clients_get_no_billing_suggestions
- .as_json
- aws_put_secrets.py
- build
- contracts/__init__.py
- GEMINI_UI_BRIEF.md
- aws_run_task.sh
- safe_tool
- safe_tool
- safe_tool
- safe_tool
- safe_tool
- date
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
- Response
- date
- PurserSidebar.tsx
- env.py
- row
- analyse
- _leave_inputs
- contract_review_view
- compute_status
- conv

## God Nodes (most connected - your core abstractions)
1. `session_scope()` - 346 edges
2. `make_actor()` - 299 edges
3. `run()` - 92 edges
4. `Invoice` - 91 edges
5. `safe_tool()` - 84 edges
6. `Rev` - 81 edges
7. `Party` - 71 edges
8. `DomainError` - 70 edges
9. `go()` - 70 edges
10. `create()` - 70 edges

## Surprising Connections (you probably didn't know these)
- `gitleaks Secret Scanning` --semantically_similar_to--> `Secrets via Secrets Manager / SSM`  [INFERRED] [semantically similar]
  README.md → CLAUDE.md
- `messages_for()` --uses--> `Message`  [INFERRED]
  tests/test_people_extra.py → app/models.py
- `test_create_contract_confirm_persists_everything()` --uses--> `Document`  [INFERRED]
  tests/test_contracts.py → app/models.py
- `test_create_contract_stale_when_document_changes()` --uses--> `Document`  [INFERRED]
  tests/test_contracts.py → app/models.py
- `_sha()` --uses--> `Document`  [INFERRED]
  tests/test_intake_extra.py → app/models.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Candidate AWS Hosting Runtimes** — claude_aws_app_runner, claude_aws_lambda_api_gateway, claude_aws_ecs_fargate, claude_s3_cloudfront [EXTRACTED 1.00]
- **Hackathon Delivery Phases 0-4** — claude_phase_0, claude_phase_1, claude_phase_2, claude_phase_3, claude_phase_4 [EXTRACTED 1.00]
- **Secure CI/CD Pipeline** — claude_github_actions, claude_github_oidc, claude_terraform, claude_least_privilege_iam, readme_ci_hygiene_checks [INFERRED 0.85]

## Communities (159 total, 49 thin omitted)

### Community 0 - "Phase 3: AWS Deployment and CI/CD"
Cohesion: 0.07
Nodes (38): Tiny Agent Evaluation Set, Agent Guardrails (step limits, budgets, timeouts, retries), AWS App Runner, AWS ECS Fargate, AWS Lambda + API Gateway, Change-Scope Rules, CLAUDE.md Hackathon Agent Rules, Cost Awareness (+30 more)

### Community 1 - "hygiene"
Cohesion: 0.08
Nodes (24): concurrency, cancel-in-progress, group, GITLEAKS_VERSION, env, name, runs-on, steps (+16 more)

### Community 2 - "_propose"
Cohesion: 0.18
Nodes (22): cancel_pending_proposal(), _confirm(), confirm_pending_proposal(), get_pending_proposal(), _proposal_view(), _propose(), propose_approval(), propose_settlement() (+14 more)

### Community 3 - "make_actor"
Cohesion: 0.07
Nodes (74): document(), extraction(), make_actor(), add_doc(), _approved_bill(), call(), code_of(), count() (+66 more)

### Community 4 - "models.py"
Cohesion: 0.11
Nodes (36): AuditEvent, Bill, BudgetLine, CompanyPayment, Conversation, InvoicePayment, Policy, SQLAlchemy models. Money is integer paise; timestamps are UTC; business dates… (+28 more)

### Community 5 - "actions.py"
Cohesion: 0.07
Nodes (37): Full settlement only (weekend scope). One per record, enforced by the unique…, Settlement, Action, _apply(), Approve, _approve_bill_inputs(), _approve_claim_inputs(), ApproveBill (+29 more)

### Community 6 - "PurserVoiceController.tsx"
Cohesion: 0.08
Nodes (23): ApiError, call(), Card, headers(), Me, setConversation(), setSession(), uploadWithProgress() (+15 more)

### Community 7 - "test_budget_months.py"
Cohesion: 0.11
Nodes (31): history(), allocated(), allocated_in(), change(), close(), close_oct(), code_of(), count_movements() (+23 more)

### Community 8 - "package.json"
Cohesion: 0.05
Nodes (37): echarts, @fontsource/dm-sans, @fontsource/geist-mono, @fontsource/noto-sans-devanagari, @fontsource/source-serif-4, @types/react, @types/react-dom, @types/three (+29 more)

### Community 9 - "domain_error"
Cohesion: 0.25
Nodes (8): domain_error(), me(), no_shared_cache(), DomainError, Request, exception_handler, JSONResponse, middleware

### Community 10 - "correct_extracted_field"
Cohesion: 0.23
Nodes (12): close_intake(), correct_extracted_field(), find_reservations(), Ctx, function_tool, Open budget reservations for an employee that this receipt could replace (e.g.…, Finish intake WITHOUT any finance write, with an explicit outcome (contract,…, Show the original document page on screen, highlighting where a field was read… (+4 more)

### Community 11 - "MUNSHI: Voice-only, agent-centric finance and operations copilot"
Cohesion: 0.08
Nodes (25): 0. Planning inputs and research status, 10. Contract liability analysis (re-implemented from the user's guide), 11. Bill and receipt extraction, 12. External integrations, 13. Data model (Postgres; money = BIGINT paise; timestamps UTC, IST display; FY Apr-Mar), 14. Repository layout (this repo, `~/Projects/Builders`), 15. AWS deployment and CI/CD, 16. Security and trust (+17 more)

### Community 12 - "get_settings"
Cohesion: 0.08
Nodes (28): Intake tools: inspect an uploaded document, correct fields by voice, match…, get_settings(), Base, configure(), engine(), AsyncSession, sessionmaker(), dispatch_soon() (+20 more)

### Community 14 - "Munshi | Product and delivery plan v2"
Cohesion: 0.12
Nodes (16): 10. Data design and isolation, 11. Secondary workflows and integrations, 12. Implementation and deployment, 13. Build sequence and cut decisions, 14. Acceptance, evaluation and evidence, 15. Four-minute demonstration and handoff, 16. Definition of done, 1. User, problem and submission (+8 more)

### Community 15 - "server.py"
Cohesion: 0.17
Nodes (11): Bridge, create_session(), get_budget_status(), index(), BaseModel, function_tool, get, Request (+3 more)

### Community 16 - "LeaveRequest"
Cohesion: 0.22
Nodes (19): LeaveRequest, add_employee(), apply(), assert_leave_conservation(), _audit_actions(), bal(), test_apply_for_someone_else_rights(), test_apply_leave_reserves_days_and_previews_balance() (+11 more)

### Community 17 - "compilerOptions"
Cohesion: 0.13
Nodes (14): compilerOptions, isolatedModules, jsx, lib, module, moduleResolution, noEmit, noUnusedLocals (+6 more)

### Community 18 - "test_charts_v2.py"
Cohesion: 0.08
Nodes (64): run(), sql(), test_bills_totals_match_sql(), test_budget_by_category_matches_movements(), test_date_range_filter_matches_sql(), test_injection_strings_just_fail_to_match(), test_overdue_total_and_filters_match_sql(), test_receivables_totals_and_rows_match_sql() (+56 more)

### Community 19 - "event_stream"
Cohesion: 0.25
Nodes (6): In-process event fan-out to the browser (SSE), keyed by conversation. One…, subscribe(), unsubscribe(), event_stream(), Server-sent events for this conversation: cards, user/assistant turns., Queue

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
Nodes (40): _cycle_client(), Guide: changing a month clears later explicit settings in the affected span…, fn(ss, rv) on a sync session in one committed transaction; return plain data., run(), rv_of(), test_carried_months_runs_to_march_not_beyond(), test_change_cycle_replaces_later_rules_and_updates_client_currency(), go() (+32 more)

### Community 24 - "5. Financial record lifecycles"
Cohesion: 0.40
Nodes (5): 5. Financial record lifecycles, Budgets, reservations and spend, Employee claims and reimbursements, Revenue, invoicing and collections, Vendor bills and approvals

### Community 25 - "Purser architecture decisions"
Cohesion: 0.50
Nodes (3): Evidence (local spike, `spikes/voice_spike`, synthetic fixture), Purser architecture decisions, Voice transport and confirmation (H0 gate, 2026-11-21) — DECIDED

### Community 38 - "compose"
Cohesion: 0.67
Nodes (3): compose(), Actor, AsyncSession

### Community 39 - "records.py"
Cohesion: 0.14
Nodes (22): get_record(), Details of a claim (C…) or bill (B…): parties, amount, state, settlement,…, record_detail(), Claim, bill_by_ref(), claim_by_ref(), _not_found(), party() (+14 more)

### Community 40 - "budget.py"
Cohesion: 0.43
Nodes (7): month_start(), movements(), post(), AsyncSession, date, Budget ledger. Every balance is computed from the append-only budget_movements…, today_ist()

### Community 41 - "2. Still to do (in priority order)"
Cohesion: 0.07
Nodes (28): 1.10 Commits, 1.1 Voice (hour-0 spike, then productionised), 1.2 Agent (OpenAI Agents SDK), 1.3 Trust boundary: propose → present → confirm → receipt, 1.4 Finance domain, 1.5 People ops (PLAN_v5), 1.6 API and infrastructure (local), 1.7 Web UI (`web/`, React 19 + Vite + TypeScript) (+20 more)

### Community 42 - "finance.py"
Cohesion: 0.09
Nodes (31): Agent, PurserContext, Passed to every tool via RunContextWrapper. Identity comes only from here,…, build_agent(), _instructions(), PurserAgent: one conversational agent with typed tools. Same agent for voice…, memory(), Actor (+23 more)

### Community 43 - "DomainError"
Cohesion: 0.10
Nodes (20): DomainError, Any, Typed domain errors. Tools turn these into structured results the agent can…, _paise(), CreateContract, _details_inputs(), _finding_inputs(), _fmt() (+12 more)

### Community 44 - "record_turn"
Cohesion: 0.18
Nodes (19): AsyncSession, Return evidence for confirming `p`, or raise CONFIRMATION_REQUIRED with the…, record_turn(), spoken_confirmation(), _open_approve(), _present_then_turn(), _spoken(), test_client_controlled_source_is_not_accepted_as_evidence() (+11 more)

### Community 45 - "Settings"
Cohesion: 0.25
Nodes (3): Settings, BaseSettings, field_validator

### Community 46 - "services/budget_months.py"
Cohesion: 0.15
Nodes (38): get_budget_month(), This month's (or a given month's) budget per category: budget, spent,…, BudgetPeriod, One category-month. Open months read the ledger; a closed month keeps its…, _rec_plans(), alerts(), apply_change(), apply_close() (+30 more)

### Community 47 - "projection.py"
Cohesion: 0.11
Nodes (20): month_outlook(), Outlook, Where spend is heading (run rate), for the CEO's three bars: allocated, spent,…, budgets / spends: the FY's 12 months in order; current: index of this month (0…, year_outlook(), Change, Month, pace_of() (+12 more)

### Community 48 - "Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST)"
Cohesion: 0.50
Nodes (3): Added capabilities (same agent, same propose → confirm → receipt engine), Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST), Rules

### Community 53 - "main.py"
Cohesion: 0.16
Nodes (29): audit_feed(), budget_line(), budget_line_months(), contract_clause_context(), contract_deadlines_view(), contract_liabilities(), contract_view(), document_detail() (+21 more)

### Community 55 - "mk_inr"
Cohesion: 0.09
Nodes (33): figures(), mk_inr(), Rs 10,000 Oct with Rs 4,000 in; move Rs 6,000 to Nov: moved_paise 600000, Oct…, Rs 10,000 a month, 3-month period from Oct, combined/advance: Rs 30,000 in Oct…, send(), test_allocation_without_amount_pays_each_remaining(), go(), test_any_invoice_change_bumps_version() (+25 more)

### Community 56 - "test_revenue_core.py"
Cohesion: 0.10
Nodes (37): 2,000.50' EUR -> 200050. Raises ValueError for anything that is not a non-…, to_minor(), pinned(), priya(), propose_confirm(), fixture, parametrize, Revenue core: money maths, invoice lifecycle, allocation, reporting figures,… (+29 more)

### Community 57 - "cycles.py"
Cohesion: 0.08
Nodes (58): ClientCycle, A client's billing cycle from a month on: monthly charge, every N months,…, active(), apply(), ChangePlan, check(), _clashes(), combined() (+50 more)

### Community 58 - "services/charts.py"
Cohesion: 0.09
Nodes (42): _auto_chart(), _bad(), ChartSpec, ChartType, CompareMode, Dim, DimensionName, _fetch() (+34 more)

### Community 59 - "tools/budget_months.py"
Cohesion: 0.12
Nodes (27): bm_round(), forecast_budget(), get_budget_alerts(), get_budget_history(), get_budget_recommendations(), get_budget_year(), MonthSplit, propose_apply_recommendations() (+19 more)

### Community 60 - "test_charts.py"
Cohesion: 0.15
Nodes (21): build(), client_for(), err(), err_sync(), priya_arjun(), DomainError, parametrize, Dynamic charts: validation, chart-type rules, totals vs independent SQL,… (+13 more)

### Community 61 - "session_scope"
Cohesion: 0.07
Nodes (68): One transaction; commits on success, rolls back on any exception., session_scope(), create(), test_button_confirm_and_replay(), cells(), test_apply_recommendations_then_nothing_left(), test_budget_month_chart_for_it_and_cloud(), test_monthly_sums_equal_annual_for_every_line() (+60 more)

### Community 62 - "tools/charts.py"
Cohesion: 0.10
Nodes (34): build_chart(), _card(), describe_chart_options(), present_view(), Ctx, function_tool, Chart and view tools. The model composes typed specs; every number comes from a…, What can be charted for this user: sources, measures (with units), dimensions,… (+26 more)

### Community 63 - "services/intake.py"
Cohesion: 0.13
Nodes (34): ensure_extraction(), prefetch(), Actor, Document reading (vision extraction) shared by the upload path and the…, _read(), inspect_document(), Read an uploaded document (runs extraction the first time). Returns type,…, _view() (+26 more)

### Community 64 - "Invoice"
Cohesion: 0.10
Nodes (53): Invoice, A customer invoice (revenue). Ported from the copilot Revenue module. Billing…, _date(), Allocation, BalancePlan, billed_paise(), by_ref(), _cache() (+45 more)

### Community 65 - "cards.tsx"
Cohesion: 0.07
Nodes (37): api, AuditCard(), BudgetCard(), Deliveries(), fmt(), InboxCard(), LEAVE_NAME, LeaveCard() (+29 more)

### Community 66 - "ChartCard.tsx"
Cohesion: 0.15
Nodes (19): CATS, ChartCard(), compactInr(), DataTable(), fmtAxis(), fmtChange(), fmtFull(), fullInr() (+11 more)

### Community 67 - "Party"
Cohesion: 0.10
Nodes (47): go(), go(), Party, match(), normalize_name(), client(), clients(), create_client() (+39 more)

### Community 68 - "extractor.py"
Cohesion: 0.24
Nodes (12): build_agent(), Cite, extract(), ExtractedDocument, LineItem, Agent, BaseModel, ExtractorAgent: reads document page images into a typed schema. It has NO… (+4 more)

### Community 69 - "safe_tool"
Cohesion: 0.10
Nodes (49): Convert DomainError into a structured result the agent can explain; log name,…, safe_tool(), add_reminder(), complete_reminder(), get_client(), get_fx_rates(), get_invoice(), get_revenue_overview() (+41 more)

### Community 70 - "client_by"
Cohesion: 0.07
Nodes (40): client_by(), _end(), Kaveri's paid Oct invoice covers Oct-Dec: a monthly cycle from Nov must not…, test_change_cycle_keeps_raised_and_paid_and_skips_their_months(), go(), test_change_cycle_skips_months_covered_by_a_kept_combined_invoice(), go(), test_cycle_active_and_current_rules() (+32 more)

### Community 71 - "spec"
Cohesion: 0.24
Nodes (16): apply_patch(), chart_problem(), ChartSpecPatch, A revision. Anything omitted keeps its current value, so grouping survives…, Why the requested chart type does not fit the spec's shape, or None., spec(), test_add_filters_replaces_and_clear_filters(), test_month_to_customer_with_line_falls_back_to_auto() (+8 more)

### Community 72 - "metadata.py"
Cohesion: 0.15
Nodes (29): add_months(), _clean(), _client(), dates(), Detail, Details, _effective(), end_of_term() (+21 more)

### Community 75 - "format_inr"
Cohesion: 0.14
Nodes (29): Actor, budget_alerts(), claim_review(), draft_message(), DraftIn, _inr(), _line_names(), list_bills() (+21 more)

### Community 76 - "test_ledger_extra.py"
Cohesion: 0.10
Nodes (67): BudgetMovement, Proposal, Append-only. Balance of each bucket = SUM(amount_paise)., Receipt, position(), cancel(), confirm(), ConfirmOutcome (+59 more)

### Community 77 - "fx_months.py"
Cohesion: 0.13
Nodes (25): Affected, apply(), carried_months(), Change, effective(), foreign(), grid(), history() (+17 more)

### Community 78 - "revenue_actions.py"
Cohesion: 0.06
Nodes (47): AddInvoices, _ccy(), _clean_num(), ClientChange, DeleteDraft, EditInvoice, _eff(), EndProject (+39 more)

### Community 79 - "scan.py"
Cohesion: 0.11
Nodes (29): The shipped clause catalogue: copilot `ctr_0001_contracts.py` CLAUSE_TYPES,…, A clause type as the scan sees it., Rule, rules(), _ask(), _dedup(), Found, _join() (+21 more)

### Community 80 - "test_revenue_fx_cycles.py"
Cohesion: 0.10
Nodes (45): FxMonth, A conversion rate set by hand for a currency and month; carries forward until…, _aug_ecb(), inv_of(), pinned(), priya(), propose_confirm(), fixture (+37 more)

### Community 81 - "tools/people.py"
Cohesion: 0.14
Nodes (24): find_people(), get_leave_balance(), get_onboarding_status(), list_leave_requests(), lookup_policy(), _person(), propose_leave(), propose_leave_decision() (+16 more)

### Community 83 - "fx.py"
Cohesion: 0.09
Nodes (29): FxQuote, Cached ECB reference quotes (Frankfurter): INR per unit x 10^6, by publication…, cached(), _frankfurter(), latest(), _newest(), AsyncSession, Decimal (+21 more)

### Community 84 - "User"
Cohesion: 0.16
Nodes (25): Actor, The authenticated principal. Always derived from the server session, never from…, Finance approval rights., HR/admin rights: onboarding, company-wide announcements, all leave., leave_card(), person_card(), LeaveMovement, OnboardingTask (+17 more)

### Community 85 - "recommendations"
Cohesion: 0.19
Nodes (17): recommendations(), short(), ClosedMonth, plan(), slots(), PlannedChange, `closed_chrono`: the category's closed months, oldest first (any number)., Trend recommendations: if a category has over- (or under-) run its budget for… (+9 more)

### Community 86 - "revenue/money.py"
Cohesion: 0.10
Nodes (26): currencies_in(), digits(), from_minor(), _indian(), numbers_in(), paise_str(), paise_to(), Decimal (+18 more)

### Community 87 - "test_ledger_gates.py"
Cohesion: 0.13
Nodes (19): Affirmation, classify(), _contains_affirm(), _normalize(), Deterministic classifier for a confirmation utterance (English, Hindi,…, parametrize, test_affirm_variants(), test_devanagari_softener_na_affirms() (+11 more)

### Community 88 - "distribution.py"
Cohesion: 0.20
Nodes (13): by_weights(), even_split(), Divide `total_paise` into `n` parts that sum exactly to it (remainder on the…, Annual -> monthly budget distribution (PRD §3). Integer paise only; no paise is…, Keep the `locked` month indices as given and spread `total_paise - sum(locked)`…, Split `total_paise` in proportion to `weights` (exact fractions, no floats).…, Growing shares: the first month weighs 1 and each next month weighs the one…, The paise each of `months` gets out of `total_paise` (same order, summing to… (+5 more)

### Community 89 - "grounding.py"
Cohesion: 0.22
Nodes (15): _normal(), numbers_spoken(), Actor, AsyncSession, Decimal, A model never supplies a booked amount or rate on its own: the number must…, The user's last few server-observed turns in this conversation, newest last.…, Each non-empty value must appear in the user's recent words, else ask them to… (+7 more)

### Community 90 - "liability.py"
Cohesion: 0.11
Nodes (29): as_dict(), assess(), _bearer_term(), _beneficiary(), carve_outs_rules(), Deadline, deadlines(), Liability (+21 more)

### Community 91 - "store.py"
Cohesion: 0.17
Nodes (34): Contract, ContractDeadline, ContractFinding, One agreement. Text is the extracted reading of the original document (kept in…, A clause found in a contract (copilot ctr_clause) plus Purser's liability…, A dated obligation computed by code from the contract (expiry, renewal notice,…, require_view(), add_findings() (+26 more)

### Community 92 - "pacing.py"
Cohesion: 0.24
Nodes (9): compute(), days_in_month(), Pacing, date, The pacing / burn-velocity engine and the proactive alert levels (PRD §4). Pure…, `day` is the current day of the month (1..total_days); use total_days for a…, _round2(), test_pacing_approaching_and_limit() (+1 more)

### Community 93 - "client_for"
Cohesion: 0.06
Nodes (56): add_inspected_document(), client_for(), test_contract_closes_without_finance_write(), test_months_endpoint(), test_months_endpoint_other_workspace_404(), test_http_contract_admin_ok_employee_forbidden(), test_http_finding_context_marks_span_inside_excerpt(), test_http_liabilities_bearer_filter() (+48 more)

### Community 94 - "part_paid_zed"
Cohesion: 0.10
Nodes (26): mk_client(), mk_invoice(), part_paid_zed(), Guide example: Rs 10,000 invoice, Rs 4,000 received, part paid., test_balance_delete_destination_restores_source_to_part_paid(), go(), test_balance_into_other_currency_month_makes_its_own_balance_invoice(), go() (+18 more)

### Community 95 - "Mail"
Cohesion: 0.22
Nodes (6): Mail, fixture, smtp(), test_multiline_default_subject_can_be_emailed(), test_send_smtp_builds_expected_message(), test_send_smtp_never_allows_header_injection()

### Community 96 - "ClaimReview.tsx"
Cohesion: 0.08
Nodes (35): motion, react, react-dom, dur, ease, easeInOut, palette, reveal (+27 more)

### Community 99 - "Ctx"
Cohesion: 0.12
Nodes (25): contract_deadlines(), get_contract(), list_liabilities(), propose_contract_details(), propose_contract_status(), propose_create_contract(), propose_rescan_contract(), propose_review_contract_finding() (+17 more)

### Community 100 - "auth.py"
Cohesion: 0.21
Nodes (14): _actor(), check_write(), current_actor(), current_csrf(), login(), Request, Response, Cookie session auth + CSRF. The Actor is derived from the server session on… (+6 more)

### Community 102 - "review.py"
Cohesion: 0.23
Nodes (15): _attention(), can_decide(), can_view(), ensure(), our_names(), prefetch(), Actor, AsyncSession (+7 more)

### Community 103 - "Rev"
Cohesion: 0.10
Nodes (44): A dated in-app reminder ('remind me Friday to chase Acme'), optionally about a…, Reminder, active(), Rev, bucket_label(), fy_months(), fy_of(), fy_start() (+36 more)

### Community 105 - "go"
Cohesion: 0.13
Nodes (27): ExceptionInfo, code_of(), mk_client(), test_allocation_across_two_clients_rejected(), go(), test_client_change_bumps_party_version(), go(), test_create_cap_and_duplicate_months() (+19 more)

### Community 106 - "test_people_extra.py"
Cohesion: 0.15
Nodes (29): Message, Inbox item and/or email outbox row. Email rows are delivered after the…, code_of(), count(), boom(), present(), parametrize, People-ops coverage (PLAN_v5): leave ledger and decisions, messaging outbox,… (+21 more)

### Community 107 - "ViewRouter.tsx"
Cohesion: 0.15
Nodes (24): lucide-react, inr(), AmbientRibbons(), PurserComposer(), useAssistant(), FinancialDecisionStrip(), AppShell(), PurserSidebar() (+16 more)

### Community 108 - "Compiled"
Cohesion: 0.20
Nodes (18): _ageing(), _budget(), _budget_flows(), _claims(), Compiled, _contracts(), _grains(), _month() (+10 more)

### Community 109 - "code_of"
Cohesion: 0.12
Nodes (12): code_of(), test_apply_rejects_reprice_ids_not_in_preview(), other_ccy(), paid(), part(), test_balance_delete_requires_unraised_destination(), go(), test_ending_an_ended_client_is_same_state() (+4 more)

### Community 110 - "purser.md"
Cohesion: 0.17
Nodes (11): Charts and views, Contracts and liabilities, Facts, Language, Monthly budget, alerts, changes and month close, Other requests, People and HR, Revenue: client invoices and money coming in (+3 more)

### Community 111 - "llm.py"
Cohesion: 0.23
Nodes (11): enabled(), LLMUnavailable, BaseModel, Exception, The only place contract review talks to a model. Small and replaceable:…, No key, provider error, timeout or unparseable answer: the caller falls back to…, Page images -> plain text (a scanned agreement has no text layer)., structured() (+3 more)

### Community 112 - "Diwan: the voice-first back office for Indian SMBs"
Cohesion: 0.17
Nodes (11): 10. Beyond the weekend, 1. The problem, 2. The solution, 3. Why AI, and what the AI actually does, 4. The trust boundary: propose → present → confirm → receipt, 5. Architecture, 6. What is already built (Saturday, 21 Nov), 7. Plan to the Sunday 14:00 freeze (+3 more)

### Community 113 - "invs_of"
Cohesion: 0.17
Nodes (12): invs_of(), test_apply_reprices_ticked_and_leaves_paid_and_part_paid(), go(), test_change_cycle_midyear_removes_only_to_raise_from_the_change_month(), go(), test_end_separate_sends_each_to_raise_on_the_end_day(), go(), test_plan_balance_preview_writes_nothing() (+4 more)

### Community 114 - "make_contract_samples.py"
Cohesion: 0.25
Nodes (9): docx(), main(), _pdf_escape(), Write the synthetic agreements in seed/contract_samples.py as files under…, A real PDF with a text layer: wrapped lines, 50 per page, Helvetica 10pt on A4., Page images only (no text layer), like a scanned agreement., scanned_pdf(), text_pdf() (+1 more)

### Community 115 - "store.tsx"
Cohesion: 0.12
Nodes (16): three, Props, PurserOrb(), TARGETS, Caption, Ctx, Decision, OrbState (+8 more)

### Community 116 - "Read"
Cohesion: 0.29
Nodes (7): docx_text(), _layer(), meaningful(), A contract file -> its plain text. Text layer first (deterministic), the vision…, Paragraphs of a .docx in order (table cells are paragraphs too)., Read, _render()

### Community 117 - "locate"
Cohesion: 0.31
Nodes (10): locate(), _note_ok(), seg(), test_locate_exactly_eight_chars_ok(), test_locate_offsets_are_absolute(), test_locate_rejects_quote_not_in_segment(), test_locate_rejects_short_quote(), test_locate_tolerates_whitespace_case_and_quotes() (+2 more)

### Community 118 - "post_move"
Cohesion: 0.44
Nodes (9): flows(), lines_by_cat(), post_move(), test_budget_flows_conservation_and_directions(), test_budget_flows_does_not_change_budget_source_and_is_workspace_scoped(), test_budget_flows_empty_on_fresh_seed(), test_budget_flows_multi_month_transfer_pairs_per_month(), test_budget_flows_other_dimensions_and_filters() (+1 more)

### Community 119 - "run"
Cohesion: 0.15
Nodes (18): Run fn(ss, rv) on a sync session inside one committed transaction; return what…, run(), rv_of(), sugg(), test_chase_for_overdue_sent_invoice(), go(), test_custom_reminder_survives_pause(), go() (+10 more)

### Community 120 - "upload"
Cohesion: 0.14
Nodes (17): agent_text(), cancel_button(), confirm_button(), login(), LoginIn, logout(), new_conversation(), BaseModel (+9 more)

### Community 121 - "Deployment (AWS, us-west-2)"
Cohesion: 0.25
Nodes (7): Architecture, Deployment (AWS, us-west-2), First deploy, Notes, Redeploy (new code), Rollback, Teardown

### Community 122 - "analyse"
Cohesion: 0.20
Nodes (16): defined_parties(), {defined term (lower) -> party name} from '(hereinafter referred to as "the…, us | counterparty | mutual | unclear., resolve(), analyse(), by_type(), dl(), one() (+8 more)

### Community 123 - "options"
Cohesion: 0.33
Nodes (6): options(), Registry as the model sees it, limited to what this actor may chart., BUG candidate: options() maps every non-paise unit to 'count', so the model is…, test_options_by_role(), test_options_lists_new_chart_types_and_rules(), test_options_reports_pct_unit_distinctly()

### Community 124 - "messages_for"
Cohesion: 0.22
Nodes (13): dispatch(), Send queued emails. Each row is claimed with SKIP LOCKED so concurrent…, messages_for(), set_notify(), test_decision_email_states_inbox_always_delivered(), test_dispatch_failure_is_recorded_and_not_retried(), test_dispatch_sends_only_after_commit_once_and_records_provider_id(), test_message_channels_and_preview() (+5 more)

### Community 125 - "test_paused_and_ended_clients_get_no_billing_suggestions"
Cohesion: 0.60
Nodes (5): test_paused_and_ended_clients_get_no_billing_suggestions(), end(), kinds(), nw_before(), resume()

### Community 129 - "build"
Cohesion: 0.27
Nodes (11): age_bucket(), build(), ClientLine, Due, Exposure, Insights, Kpis, Month (+3 more)

### Community 151 - "PurserSidebar.tsx"
Cohesion: 0.20
Nodes (9): ACTION_WORDS, ago(), humanize(), NavDef, Note, Notifications(), Profile(), SettingsDialog() (+1 more)

### Community 152 - "env.py"
Cohesion: 0.27
Nodes (9): Connection, do_run_migrations(), include_object(), Run migrations in 'offline' mode. This configures the context with just a URL…, In this scenario we need to create an Engine and associate a connection with…, Run migrations in 'online' mode., run_async_migrations(), run_migrations_offline() (+1 more)

### Community 153 - "row"
Cohesion: 0.22
Nodes (8): row(), go(), go(), go(), test_seeded_northwind_nov_priced_at_carried_oct_rate(), go(), go(), test_version_persists_across_sessions()

### Community 154 - "analyse"
Cohesion: 0.29
Nodes (8): analyse(), clean_name(), guess_title(), guess_type(), Northwind Labs Inc, a company incorporated in Delaware' -> 'Northwind Labs Inc'., The whole review of a text: findings with liabilities, details, deadlines. Pure…, test_guess_type_and_title(), test_live_demo_clean_name_has_no_company_tail()

### Community 155 - "_leave_inputs"
Cohesion: 0.33
Nodes (5): ApplyLeave, _leave_inputs(), date, Monday-Friday count, inclusive. (Holiday calendar is a roadmap item; weekends…, working_days()

### Community 156 - "contract_review_view"
Cohesion: 0.50
Nodes (4): _staged_view(), one(), contract_review_view(), The staged (not yet saved) review of an uploaded contract.

### Community 157 - "compute_status"
Cohesion: 0.50
Nodes (3): compute_status(), Month-end utilisation status: OPEN (no positive budget), UNDERUSED (< 85%),…, test_compute_status_boundaries()

### Community 158 - "conv"
Cohesion: 0.67
Nodes (3): conv(), Actor, Same user, fresh conversation (a second session).

## Knowledge Gaps
- **241 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+236 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 867 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **49 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `session_scope()` connect `session_scope` to `_propose`, `make_actor`, `models.py`, `test_budget_months.py`, `correct_extracted_field`, `get_settings`, `LeaveRequest`, `test_charts_v2.py`, `run`, `contract_review_view`, `conv`, `records.py`, `finance.py`, `record_turn`, `services/budget_months.py`, `main.py`, `test_revenue_core.py`, `tools/budget_months.py`, `test_charts.py`, `tools/charts.py`, `services/intake.py`, `safe_tool`, `spec`, `format_inr`, `test_ledger_extra.py`, `test_revenue_fx_cycles.py`, `tools/people.py`, `fx.py`, `User`, `test_ledger_gates.py`, `store.py`, `client_for`, `Ctx`, `auth.py`, `review.py`, `go`, `test_people_extra.py`, `post_move`, `run`, `upload`, `messages_for`?**
  _High betweenness centrality (0.106) - this node is a cross-community bridge._
- **Why does `Invoice` connect `Invoice` to `row`, `Party`, `models.py`, `Rev`, `go`, `Compiled`, `fx_months.py`, `revenue_actions.py`, `test_revenue_fx_cycles.py`, `invs_of`, `fx.py`, `mk_inr`, `test_revenue_core.py`, `cycles.py`, `services/charts.py`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Why does `get_settings()` connect `get_settings` to `make_actor`, `models.py`, `env.py`, `records.py`, `finance.py`, `Settings`, `main.py`, `test_revenue_core.py`, `session_scope`, `services/intake.py`, `extractor.py`, `test_revenue_fx_cycles.py`, `fx.py`, `Mail`, `auth.py`, `review.py`, `test_people_extra.py`, `llm.py`, `upload`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Are the 71 inferred relationships involving `Invoice` (e.g. with `_receivables()` and `DeleteDraft`) actually correct?**
  _`Invoice` has 71 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _241 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Phase 3: AWS Deployment and CI/CD` be split into smaller, more focused modules?**
  _Cohesion score 0.06827880512091039 - nodes in this community are weakly interconnected._
- **Should `hygiene` be split into smaller, more focused modules?**
  _Cohesion score 0.08 - nodes in this community are weakly interconnected._