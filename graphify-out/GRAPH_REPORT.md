# Graph Report - Builders  (2026-11-21)

## Corpus Check
- 160 files · ~186,504 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 5, .example 2, .ini 1)

## Summary
- 2960 nodes · 9235 edges · 159 communities (104 shown, 55 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 811 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ab0e4b47`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Phase 3: AWS Deployment and CI/CD
- hygiene
- _propose
- make_actor
- confirmation.py
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
- RevAction
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
- build
- Actor
- budget.py
- 2. Still to do (in priority order)
- finance.py
- Plan
- session_scope
- Settings
- services/budget_months.py
- projection.py
- Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST)
- fresh-sonnet-per-test-set.sh
- tests-only-in-sonnet.sh
- Agent
- main.py
- get
- mk_client
- test_revenue_core.py
- cycles.py
- services/charts.py
- Ctx
- test_charts.py
- test_contracts.py
- tools/charts.py
- models.py
- Invoice
- cards.tsx
- ChartCard.tsx
- Rev
- app/money.py
- safe_tool
- _end
- spec
- metadata.py
- budgeting/__init__.py
- format_inr
- test_ledger_extra.py
- fx_months.py
- DomainError
- scan.py
- inv_of
- Ctx
- safe_tool
- test_revenue_fx_cycles.py
- User
- recommendations
- revenue/money.py
- store
- distribution.py
- grounding.py
- liability.py
- store.py
- pacing.py
- client_for
- part_paid_zed
- Price
- ClaimReview.tsx
- FakeSMTP
- date
- Ctx
- auth.py
- review.py
- reads.py
- Any
- go
- test_people_extra.py
- ViewRouter.tsx
- _date
- client_by
- purser.md
- llm.py
- Diwan: the voice-first back office for Indian SMBs
- invs_of
- make_contract_samples.py
- store.tsx
- _claim_inputs
- _fmt_date
- post_move
- run
- upload
- Deployment (AWS, us-west-2)
- get_budget_year
- options
- _message_inputs
- AddInvoices
- EditInvoice
- aws_put_secrets.py
- SetCycle
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
- .__init__
- enrich_core
- RecordPayment
- test_cycle_quarterly_combined_advance_books_in_first_month
- month_number

## God Nodes (most connected - your core abstractions)
1. `session_scope()` - 346 edges
2. `make_actor()` - 299 edges
3. `run()` - 92 edges
4. `Invoice` - 90 edges
5. `safe_tool()` - 84 edges
6. `Rev` - 79 edges
7. `Party` - 71 edges
8. `DomainError` - 70 edges
9. `go()` - 70 edges
10. `create()` - 70 edges

## Surprising Connections (you probably didn't know these)
- `gitleaks Secret Scanning` --semantically_similar_to--> `Secrets via Secrets Manager / SSM`  [INFERRED] [semantically similar]
  README.md → CLAUDE.md
- `seed()` --calls--> `Actor`  [INFERRED]
  seed/seed_v1.py → app/actor.py
- `go()` --calls--> `Rev`  [INFERRED]
  seed/seed_v1.py → app/services/revenue/core.py
- `test_contract_closes_without_finance_write()` --uses--> `Claim`  [INFERRED]
  tests/test_api_intake.py → app/models.py
- `test_confirm_tool_reports_stale_with_new_preview_and_executes_nothing()` --uses--> `Claim`  [INFERRED]
  tests/test_intake_extra.py → app/models.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Candidate AWS Hosting Runtimes** — claude_aws_app_runner, claude_aws_lambda_api_gateway, claude_aws_ecs_fargate, claude_s3_cloudfront [EXTRACTED 1.00]
- **Hackathon Delivery Phases 0-4** — claude_phase_0, claude_phase_1, claude_phase_2, claude_phase_3, claude_phase_4 [EXTRACTED 1.00]
- **Secure CI/CD Pipeline** — claude_github_actions, claude_github_oidc, claude_terraform, claude_least_privilege_iam, readme_ci_hygiene_checks [INFERRED 0.85]

## Communities (159 total, 55 thin omitted)

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
Cohesion: 0.08
Nodes (77): document(), extraction(), add_inspected_document(), make_actor(), add_doc(), call(), code_of(), count() (+69 more)

### Community 4 - "confirmation.py"
Cohesion: 0.16
Nodes (11): Spoken confirmation is valid only from a server-observed user turn that started…, bridge_for(), client(), LiveBridge, Actor, GPT-Live sideband bridge: server-observed transcripts -> voice_turns;…, Speak text in the live session if it is still open. Never raises; returns…, say() (+3 more)

### Community 5 - "actions.py"
Cohesion: 0.18
Nodes (9): _apply(), Approve, ApproveBill, ApproveClaim, _budget_effect(), Any, Business writes, expressed as plan (preview, no side effects) + execute (inside…, Dispatch approval by record ref prefix (C = claim, B = bill). (+1 more)

### Community 6 - "PurserVoiceController.tsx"
Cohesion: 0.08
Nodes (23): ApiError, call(), Card, headers(), Me, setConversation(), setSession(), uploadWithProgress() (+15 more)

### Community 7 - "test_budget_months.py"
Cohesion: 0.09
Nodes (37): allocated(), allocated_in(), cells(), change(), close(), close_oct(), code_of(), count_movements() (+29 more)

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
Cohesion: 0.06
Nodes (40): Agent, PurserContext, Passed to every tool via RunContextWrapper. Identity comes only from here,…, build_agent(), _instructions(), PurserAgent: one conversational agent with typed tools. Same agent for voice…, memory(), Actor (+32 more)

### Community 14 - "Munshi | Product and delivery plan v2"
Cohesion: 0.12
Nodes (16): 10. Data design and isolation, 11. Secondary workflows and integrations, 12. Implementation and deployment, 13. Build sequence and cut decisions, 14. Acceptance, evaluation and evidence, 15. Four-minute demonstration and handoff, 16. Definition of done, 1. User, problem and submission (+8 more)

### Community 15 - "server.py"
Cohesion: 0.17
Nodes (11): Bridge, create_session(), get_budget_status(), index(), BaseModel, function_tool, get, Request (+3 more)

### Community 16 - "RevAction"
Cohesion: 0.10
Nodes (16): EndProject, FxMonthRate, MoveBalance, PlanFY, Actor, AsyncSession, Session, {label: value} the user must have said. (+8 more)

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
Cohesion: 0.07
Nodes (29): _cycle_client(), fn(ss, rv) on a sync session in one committed transaction; return plain data., run(), rv_of(), test_carried_months_runs_to_march_not_beyond(), test_change_cycle_replaces_later_rules_and_updates_client_currency(), go(), test_fx_cached_returns_micro_or_none() (+21 more)

### Community 24 - "5. Financial record lifecycles"
Cohesion: 0.40
Nodes (5): 5. Financial record lifecycles, Budgets, reservations and spend, Employee claims and reimbursements, Revenue, invoicing and collections, Vendor bills and approvals

### Community 25 - "Purser architecture decisions"
Cohesion: 0.50
Nodes (3): Evidence (local spike, `spikes/voice_spike`, synthetic fixture), Purser architecture decisions, Voice transport and confirmation (H0 gate, 2026-11-21) — DECIDED

### Community 38 - "build"
Cohesion: 0.16
Nodes (20): active(), cached(), _frankfurter(), latest(), _newest(), Decimal, Exception, Session (+12 more)

### Community 39 - "Actor"
Cohesion: 0.20
Nodes (19): Actor, The authenticated principal. Always derived from the server session, never from…, Finance approval rights., HR/admin rights: onboarding, company-wide announcements, all leave., _approve_bill_inputs(), _approve_claim_inputs(), _bill_inputs(), _require_approver() (+11 more)

### Community 40 - "budget.py"
Cohesion: 0.43
Nodes (7): month_start(), movements(), post(), AsyncSession, date, Budget ledger. Every balance is computed from the append-only budget_movements…, today_ist()

### Community 41 - "2. Still to do (in priority order)"
Cohesion: 0.07
Nodes (28): 1.10 Commits, 1.1 Voice (hour-0 spike, then productionised), 1.2 Agent (OpenAI Agents SDK), 1.3 Trust boundary: propose → present → confirm → receipt, 1.4 Finance domain, 1.5 People ops (PLAN_v5), 1.6 API and infrastructure (local), 1.7 Web UI (`web/`, React 19 + Vite + TypeScript) (+20 more)

### Community 42 - "finance.py"
Cohesion: 0.18
Nodes (18): explain_budget_change(), get_attention_items(), get_audit_history(), get_budget_status(), get_record(), list_budget_categories(), _pos_view(), Ctx (+10 more)

### Community 43 - "Plan"
Cohesion: 0.12
Nodes (16): Execution, Plan, ApplyRecommendations, BudgetChange, _change_plan(), _close_plan(), CloseMonth, _paise() (+8 more)

### Community 44 - "session_scope"
Cohesion: 0.08
Nodes (55): One transaction; commits on success, rolls back on any exception., session_scope(), record_turn(), create(), seed(), bill(), test_button_confirm_and_replay(), test_contract_closes_without_finance_write() (+47 more)

### Community 45 - "Settings"
Cohesion: 0.25
Nodes (3): Settings, BaseSettings, field_validator

### Community 46 - "services/budget_months.py"
Cohesion: 0.17
Nodes (36): get_budget_month(), This month's (or a given month's) budget per category: budget, spent,…, BudgetLine, BudgetPeriod, One category-month. Open months read the ledger; a closed month keeps its…, _rec_plans(), alerts(), apply_change() (+28 more)

### Community 47 - "projection.py"
Cohesion: 0.11
Nodes (20): month_outlook(), Outlook, Where spend is heading (run rate), for the CEO's three bars: allocated, spent,…, budgets / spends: the FY's 12 months in order; current: index of this month (0…, year_outlook(), Change, Month, pace_of() (+12 more)

### Community 48 - "Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST)"
Cohesion: 0.50
Nodes (3): Added capabilities (same agent, same propose → confirm → receipt engine), Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST), Rules

### Community 53 - "main.py"
Cohesion: 0.14
Nodes (31): _staged_view(), one(), audit_feed(), budget_line_months(), contract_clause_context(), contract_deadlines_view(), contract_liabilities(), contract_review_view() (+23 more)

### Community 55 - "mk_client"
Cohesion: 0.11
Nodes (33): figures(), mk_client(), mk_inr(), Rs 10,000 Oct with Rs 4,000 in; move Rs 6,000 to Nov: moved_paise 600000, Oct…, send(), test_allocation_without_amount_pays_each_remaining(), go(), test_any_invoice_change_bumps_version() (+25 more)

### Community 56 - "test_revenue_core.py"
Cohesion: 0.12
Nodes (33): AuditEvent, pinned(), priya(), propose_confirm(), fixture, parametrize, Revenue core: money maths, invoice lifecycle, allocation, reporting figures,…, Revenue clients are customer Parties in the same workspace table (no separate… (+25 more)

### Community 57 - "cycles.py"
Cohesion: 0.08
Nodes (57): ClientCycle, A client's billing cycle from a month on: monthly charge, every N months,…, active(), apply(), ChangePlan, check(), _clashes(), combined() (+49 more)

### Community 58 - "services/charts.py"
Cohesion: 0.09
Nodes (40): _auto_chart(), _bad(), ChartSpec, ChartType, CompareMode, Dim, DimensionName, _fetch() (+32 more)

### Community 59 - "Ctx"
Cohesion: 0.14
Nodes (20): bm_round(), forecast_budget(), get_budget_alerts(), get_budget_history(), MonthSplit, propose_apply_recommendations(), propose_budget_change(), propose_close_month() (+12 more)

### Community 60 - "test_charts.py"
Cohesion: 0.13
Nodes (25): load(), Look a value up in the stored rows (never a new query), so speech matches what…, A snapshot is readable only by the actor who made it (its rows were scoped to…, read_value(), match(), build(), client_for(), err() (+17 more)

### Community 61 - "test_contracts.py"
Cohesion: 0.09
Nodes (47): _attention(), _a_flag(), analyse(), by_type(), contract_by_ref(), deadlines_of(), dl(), findings_of() (+39 more)

### Community 62 - "tools/charts.py"
Cohesion: 0.23
Nodes (15): build_chart(), _card(), describe_chart_options(), present_view(), Ctx, function_tool, Chart and view tools. The model composes typed specs; every number comes from a…, What can be charted for this user: sources, measures (with units), dimensions,… (+7 more)

### Community 63 - "models.py"
Cohesion: 0.07
Nodes (67): ensure_extraction(), prefetch(), Actor, Document reading (vision extraction) shared by the upload path and the…, _read(), inspect_document(), Read an uploaded document (runs extraction the first time). Returns type,…, _view() (+59 more)

### Community 64 - "Invoice"
Cohesion: 0.11
Nodes (51): Invoice, A customer invoice (revenue). Ported from the copilot Revenue module. Billing…, Allocation, BalancePlan, billed_paise(), by_ref(), _cache(), check_due_on() (+43 more)

### Community 65 - "cards.tsx"
Cohesion: 0.07
Nodes (37): api, AuditCard(), BudgetCard(), Deliveries(), fmt(), InboxCard(), LEAVE_NAME, LeaveCard() (+29 more)

### Community 66 - "ChartCard.tsx"
Cohesion: 0.15
Nodes (19): CATS, ChartCard(), compactInr(), DataTable(), fmtAxis(), fmtChange(), fmtFull(), fullInr() (+11 more)

### Community 67 - "Rev"
Cohesion: 0.09
Nodes (60): go(), go(), Party, A dated in-app reminder ('remind me Friday to chase Acme'), optionally about a…, Reminder, normalize_name(), client(), clients() (+52 more)

### Community 68 - "app/money.py"
Cohesion: 0.21
Nodes (13): build_agent(), Cite, extract(), ExtractedDocument, LineItem, Agent, BaseModel, ExtractorAgent: reads document page images into a typed schema. It has NO… (+5 more)

### Community 69 - "safe_tool"
Cohesion: 0.10
Nodes (49): Convert DomainError into a structured result the agent can explain; log name,…, safe_tool(), add_reminder(), complete_reminder(), get_client(), get_fx_rates(), get_invoice(), get_revenue_overview() (+41 more)

### Community 70 - "_end"
Cohesion: 0.10
Nodes (22): _end(), Kaveri's paid Oct invoice covers Oct-Dec: a monthly cycle from Nov must not…, test_change_cycle_skips_months_covered_by_a_kept_combined_invoice(), go(), test_end_combine_merges_sources_into_one_priced_at_the_month_rate(), go(), test_end_combine_send_now_false_leaves_a_draft_and_delete_restores_sources(), go() (+14 more)

### Community 71 - "spec"
Cohesion: 0.23
Nodes (17): apply_patch(), chart_problem(), ChartSpecPatch, A revision. Anything omitted keeps its current value, so grouping survives…, Why the requested chart type does not fit the spec's shape, or None., spec(), test_add_filters_replaces_and_clear_filters(), test_month_to_customer_with_line_falls_back_to_auto() (+9 more)

### Community 72 - "metadata.py"
Cohesion: 0.13
Nodes (30): add_months(), _clean(), _client(), dates(), Detail, Details, _effective(), end_of_term() (+22 more)

### Community 75 - "format_inr"
Cohesion: 0.12
Nodes (32): Actor, budget_alerts(), claim_review(), draft_message(), DraftIn, _inr(), _line_names(), list_bills() (+24 more)

### Community 76 - "test_ledger_extra.py"
Cohesion: 0.07
Nodes (85): BudgetMovement, Proposal, Append-only. Balance of each bucket = SUM(amount_paise)., Full settlement only (weekend scope). One per record, enforced by the unique…, Receipt, Settlement, Affirmation, classify() (+77 more)

### Community 77 - "fx_months.py"
Cohesion: 0.12
Nodes (26): fy_of(), Affected, apply(), carried_months(), Change, effective(), foreign(), grid() (+18 more)

### Community 78 - "DomainError"
Cohesion: 0.15
Nodes (22): DomainError, _ccy(), _clean_num(), ClientChange, DeleteDraft, _eff(), _fx_note(), _invoices_by_refs() (+14 more)

### Community 79 - "scan.py"
Cohesion: 0.10
Nodes (34): The shipped clause catalogue: copilot `ctr_0001_contracts.py` CLAUSE_TYPES,…, A clause type as the scan sees it., Rule, rules(), _ask(), _dedup(), Found, _join() (+26 more)

### Community 80 - "inv_of"
Cohesion: 0.06
Nodes (51): FxMonth, A conversion rate set by hand for a currency and month; carries forward until…, inv_of(), priya(), propose_confirm(), Guide: changing a month clears later explicit settings in the affected span…, Approver with no conversation: grounding skipped (the on-screen form path)., Northwind Oct: $1,500 at 83.90 = Rs 125,850; Rs 60,000 in; Rs 65,850 left =… (+43 more)

### Community 81 - "Ctx"
Cohesion: 0.12
Nodes (23): find_people(), get_leave_balance(), get_onboarding_status(), list_leave_requests(), lookup_policy(), _person(), propose_leave(), propose_leave_decision() (+15 more)

### Community 83 - "test_revenue_fx_cycles.py"
Cohesion: 0.11
Nodes (25): FxQuote, Cached ECB reference quotes (Frankfurter): INR per unit x 10^6, by publication…, AsyncSession, Fetch and cache the latest quote for each foreign ECB currency. Returns…, refresh(), _aug_ecb(), pinned(), fixture (+17 more)

### Community 84 - "User"
Cohesion: 0.23
Nodes (19): leave_card(), person_card(), OnboardingTask, User, _onboard_inputs(), OnboardEmployee, balance(), can_view_person_private() (+11 more)

### Community 85 - "recommendations"
Cohesion: 0.12
Nodes (24): get_budget_recommendations(), Trend recommendations from the last 3 CLOSED months (consistent overrun or…, step_id(), The plan for `target`, without steps already applied for that month (same kind,…, recommendations(), short(), still_to_do(), ClosedMonth (+16 more)

### Community 86 - "revenue/money.py"
Cohesion: 0.09
Nodes (31): currencies_in(), digits(), from_minor(), _indian(), numbers_in(), paise_str(), paise_to(), Decimal (+23 more)

### Community 87 - "store"
Cohesion: 0.22
Nodes (13): fmt_value(), public(), The card payload: numbers as integers plus display strings computed here, not…, store(), summarize(), test_budget_available_after_golden_path(), summarize() must not crash on pct rows that lack 'parts' (e.g. an older…, test_fmt_value_pct() (+5 more)

### Community 88 - "distribution.py"
Cohesion: 0.20
Nodes (13): by_weights(), even_split(), Divide `total_paise` into `n` parts that sum exactly to it (remainder on the…, Annual -> monthly budget distribution (PRD §3). Integer paise only; no paise is…, Keep the `locked` month indices as given and spread `total_paise - sum(locked)`…, Split `total_paise` in proportion to `weights` (exact fractions, no floats).…, Growing shares: the first month weighs 1 and each next month weighs the one…, The paise each of `months` gets out of `total_paise` (same order, summing to… (+5 more)

### Community 89 - "grounding.py"
Cohesion: 0.22
Nodes (15): _normal(), numbers_spoken(), Actor, AsyncSession, Decimal, A model never supplies a booked amount or rate on its own: the number must…, The user's last few server-observed turns in this conversation, newest last.…, Each non-empty value must appear in the user's recent words, else ask them to… (+7 more)

### Community 90 - "liability.py"
Cohesion: 0.07
Nodes (43): as_dict(), assess(), _bearer_term(), _beneficiary(), carve_outs_rules(), Deadline, deadlines(), defined_parties() (+35 more)

### Community 91 - "store.py"
Cohesion: 0.10
Nodes (48): Contract, ContractDeadline, ContractFinding, One agreement. Text is the extracted reading of the original document (kept in…, A clause found in a contract (copilot ctr_clause) plus Purser's liability…, A dated obligation computed by code from the contract (expiry, renewal notice,…, _details_inputs(), _iso() (+40 more)

### Community 92 - "pacing.py"
Cohesion: 0.24
Nodes (9): compute(), days_in_month(), Pacing, date, The pacing / burn-velocity engine and the proactive alert levels (PRD §4). Pure…, `day` is the current day of the month (1..total_days); use total_days for a…, _round2(), test_pacing_approaching_and_limit() (+1 more)

### Community 93 - "client_for"
Cohesion: 0.06
Nodes (51): client_for(), _pdf(), parametrize, HTTP layer + intake gates that need no model: auth, CSRF, upload outcomes,…, test_arithmetic_check(), test_employee_cannot_open_other_users_document(), test_exact_replay_returns_existing_document(), test_upload_explicit_outcomes() (+43 more)

### Community 94 - "part_paid_zed"
Cohesion: 0.09
Nodes (29): mk_client(), mk_invoice(), part_paid_zed(), Guide example: Rs 10,000 invoice, Rs 4,000 received, part paid., test_balance_delete_destination_restores_source_to_part_paid(), go(), test_balance_delete_requires_unraised_destination(), go() (+21 more)

### Community 95 - "Price"
Cohesion: 0.20
Nodes (8): Price, INR is 1; a typed rate is manual; then the currency's month rate in force for…, enrich_revenue(), Five more clients, written through the revenue services (sync session, inside…, AsyncSession, Revenue demo rows (ALL SYNTHETIC), written through the revenue services so…, _seed_revenue(), go()

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
Cohesion: 0.16
Nodes (21): analyse(), can_decide(), can_view(), clean_name(), ensure(), guess_title(), guess_type(), our_names() (+13 more)

### Community 103 - "reads.py"
Cohesion: 0.10
Nodes (33): bucket_label(), from_index(), fy_months(), fy_start(), fy_today(), last_day(), month_label(), period_label() (+25 more)

### Community 105 - "go"
Cohesion: 0.13
Nodes (22): ExceptionInfo, code_of(), test_allocation_across_two_clients_rejected(), go(), test_create_cap_and_duplicate_months(), go(), test_delete_only_when_to_raise(), go() (+14 more)

### Community 106 - "test_people_extra.py"
Cohesion: 0.08
Nodes (69): LeaveRequest, Message, Inbox item and/or email outbox row. Email rows are delivered after the…, dispatch(), Send queued emails. Each row is claimed with SKIP LOCKED so concurrent…, propose_and_confirm(), add_employee(), apply() (+61 more)

### Community 107 - "ViewRouter.tsx"
Cohesion: 0.15
Nodes (24): lucide-react, inr(), AmbientRibbons(), PurserComposer(), useAssistant(), FinancialDecisionStrip(), AppShell(), PurserSidebar() (+16 more)

### Community 108 - "_date"
Cohesion: 0.16
Nodes (22): _ageing(), _budget(), _budget_flows(), _claims(), Compiled, _contracts(), _grains(), _month() (+14 more)

### Community 109 - "client_by"
Cohesion: 0.08
Nodes (30): client_by(), code_of(), test_change_cycle_keeps_raised_and_paid_and_skips_their_months(), go(), test_cycle_active_and_current_rules(), go(), test_end_combine_requires_common_currency_and_something_pending(), no_month() (+22 more)

### Community 110 - "purser.md"
Cohesion: 0.17
Nodes (11): Charts and views, Contracts and liabilities, Facts, Language, Monthly budget, alerts, changes and month close, Other requests, People and HR, Revenue: client invoices and money coming in (+3 more)

### Community 111 - "llm.py"
Cohesion: 0.13
Nodes (18): enabled(), LLMUnavailable, BaseModel, Exception, The only place contract review talks to a model. Small and replaceable:…, No key, provider error, timeout or unparseable answer: the caller falls back to…, Page images -> plain text (a scanned agreement has no text layer)., structured() (+10 more)

### Community 112 - "Diwan: the voice-first back office for Indian SMBs"
Cohesion: 0.17
Nodes (11): 10. Beyond the weekend, 1. The problem, 2. The solution, 3. Why AI, and what the AI actually does, 4. The trust boundary: propose → present → confirm → receipt, 5. Architecture, 6. What is already built (Saturday, 21 Nov), 7. Plan to the Sunday 14:00 freeze (+3 more)

### Community 113 - "invs_of"
Cohesion: 0.22
Nodes (9): invs_of(), test_apply_reprices_ticked_and_leaves_paid_and_part_paid(), go(), test_change_cycle_midyear_removes_only_to_raise_from_the_change_month(), go(), test_end_separate_sends_each_to_raise_on_the_end_day(), go(), test_plan_balance_preview_writes_nothing() (+1 more)

### Community 114 - "make_contract_samples.py"
Cohesion: 0.25
Nodes (9): docx(), main(), _pdf_escape(), Write the synthetic agreements in seed/contract_samples.py as files under…, A real PDF with a text layer: wrapped lines, 50 per page, Helvetica 10pt on A4., Page images only (no text layer), like a scanned agreement., scanned_pdf(), text_pdf() (+1 more)

### Community 115 - "store.tsx"
Cohesion: 0.12
Nodes (16): three, Props, PurserOrb(), TARGETS, Caption, Ctx, Decision, OrbState (+8 more)

### Community 116 - "_claim_inputs"
Cohesion: 0.29
Nodes (6): Action, _claim_inputs(), Actor, AsyncSession, SubmitClaim, Protocol

### Community 117 - "_fmt_date"
Cohesion: 0.28
Nodes (4): DecideLeave, _fmt_date(), _leave_decision_inputs(), SubmitBill

### Community 118 - "post_move"
Cohesion: 0.44
Nodes (9): flows(), lines_by_cat(), post_move(), test_budget_flows_conservation_and_directions(), test_budget_flows_does_not_change_budget_source_and_is_workspace_scoped(), test_budget_flows_empty_on_fresh_seed(), test_budget_flows_multi_month_transfer_pairs_per_month(), test_budget_flows_other_dimensions_and_filters() (+1 more)

### Community 119 - "run"
Cohesion: 0.13
Nodes (20): Run fn(ss, rv) on a sync session inside one committed transaction; return what…, run(), rv_of(), sugg(), test_chase_for_overdue_sent_invoice(), go(), test_custom_reminder_survives_pause(), go() (+12 more)

### Community 120 - "upload"
Cohesion: 0.14
Nodes (17): agent_text(), cancel_button(), confirm_button(), login(), LoginIn, logout(), new_conversation(), BaseModel (+9 more)

### Community 121 - "Deployment (AWS, us-west-2)"
Cohesion: 0.25
Nodes (7): Architecture, Deployment (AWS, us-west-2), First deploy, Notes, Redeploy (new code), Rollback, Teardown

### Community 122 - "get_budget_year"
Cohesion: 0.40
Nodes (4): get_budget_year(), One category month by month for this financial year: base plan, current budget,…, Cell, _sum_cells()

### Community 123 - "options"
Cohesion: 0.33
Nodes (6): options(), Registry as the model sees it, limited to what this actor may chart., BUG candidate: options() maps every non-paise unit to 'count', so the model is…, test_options_by_role(), test_options_lists_new_chart_types_and_rules(), test_options_reports_pct_unit_distinctly()

### Community 151 - "PurserSidebar.tsx"
Cohesion: 0.20
Nodes (9): ACTION_WORDS, ago(), humanize(), NavDef, Note, Notifications(), Profile(), SettingsDialog() (+1 more)

### Community 152 - "env.py"
Cohesion: 0.27
Nodes (9): Connection, do_run_migrations(), include_object(), Run migrations in 'offline' mode. This configures the context with just a URL…, In this scenario we need to create an Engine and associate a connection with…, Run migrations in 'online' mode., run_async_migrations(), run_migrations_offline() (+1 more)

### Community 153 - "row"
Cohesion: 0.22
Nodes (8): row(), go(), go(), go(), test_seeded_northwind_nov_priced_at_carried_oct_rate(), go(), go(), test_version_persists_across_sessions()

### Community 155 - "enrich_core"
Cohesion: 0.17
Nodes (11): ApplyLeave, _leave_inputs(), date, Monday-Friday count, inclusive. (Holiday calendar is a roadmap item; weekends…, working_days(), BudgetLine, _email(), enrich_core() (+3 more)

### Community 157 - "test_cycle_quarterly_combined_advance_books_in_first_month"
Cohesion: 0.67
Nodes (3): Rs 10,000 a month, 3-month period from Oct, combined/advance: Rs 30,000 in Oct…, test_cycle_quarterly_combined_advance_books_in_first_month(), go()

## Knowledge Gaps
- **241 isolated node(s):** `aws_run_task.sh script`, `Props`, `Caption`, `Ctx`, `Decision` (+236 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 874 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **55 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `session_scope()` connect `session_scope` to `_propose`, `make_actor`, `confirmation.py`, `test_budget_months.py`, `correct_extracted_field`, `get_settings`, `test_charts_v2.py`, `run`, `finance.py`, `services/budget_months.py`, `main.py`, `test_revenue_core.py`, `Ctx`, `test_charts.py`, `test_contracts.py`, `tools/charts.py`, `models.py`, `safe_tool`, `spec`, `format_inr`, `test_ledger_extra.py`, `inv_of`, `Ctx`, `test_revenue_fx_cycles.py`, `User`, `recommendations`, `store`, `store.py`, `client_for`, `part_paid_zed`, `Ctx`, `auth.py`, `review.py`, `go`, `test_people_extra.py`, `post_move`, `run`, `upload`, `get_budget_year`?**
  _High betweenness centrality (0.121) - this node is a cross-community bridge._
- **Why does `make_actor()` connect `make_actor` to `test_budget_months.py`, `test_charts_v2.py`, `Actor`, `session_scope`, `test_revenue_core.py`, `services/charts.py`, `test_charts.py`, `test_contracts.py`, `models.py`, `spec`, `test_ledger_extra.py`, `inv_of`, `User`, `store`, `store.py`, `client_for`, `test_people_extra.py`, `post_move`, `options`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Why does `Party` connect `Rev` to `make_actor`, `actions.py`, `build`, `Actor`, `finance.py`, `test_revenue_core.py`, `cycles.py`, `services/charts.py`, `test_contracts.py`, `models.py`, `Invoice`, `test_ledger_extra.py`, `fx_months.py`, `DomainError`, `test_revenue_fx_cycles.py`, `User`, `store.py`, `part_paid_zed`, `test_people_extra.py`, `_date`, `client_by`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Are the 71 inferred relationships involving `Invoice` (e.g. with `_receivables()` and `DeleteDraft`) actually correct?**
  _`Invoice` has 71 INFERRED edges - model-reasoned connections that need verification._
- **What connects `aws_run_task.sh script`, `Props`, `Caption` to the rest of the system?**
  _241 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Phase 3: AWS Deployment and CI/CD` be split into smaller, more focused modules?**
  _Cohesion score 0.06827880512091039 - nodes in this community are weakly interconnected._
- **Should `hygiene` be split into smaller, more focused modules?**
  _Cohesion score 0.08 - nodes in this community are weakly interconnected._