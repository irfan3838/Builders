# Graph Report - Builders  (2026-11-21)

## Corpus Check
- 168 files · ~194,421 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 5, .example 2, .ini 1)

## Summary
- 3018 nodes · 9296 edges · 153 communities (103 shown, 50 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 796 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `bfe0e8f1`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Phase 3: AWS Deployment and CI/CD
- hygiene
- document
- session_scope
- Ctx
- party
- PurserVoiceController.tsx
- test_budget_months.py
- package.json
- event_stream
- revenue.py
- MUNSHI: Voice-only, agent-centric finance and operations copilot
- Compiled
- DomainError
- Munshi | Product and delivery plan v2
- server.py
- services/proposals.py
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
- records.py
- DomainError
- _write
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
- make_actor
- test_contracts.py
- errors.py
- services/intake.py
- Invoice
- cards.tsx
- ChartCard.tsx
- Rev
- app/money.py
- safe_tool
- client_by
- spec
- metadata.py
- budgeting/__init__.py
- format_inr
- test_ledger_extra.py
- record_turn
- revenue_actions.py
- scan.py
- inv_of
- Ctx
- draft_message
- test_revenue_fx_cycles.py
- services/people.py
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
- build
- ClaimReview.tsx
- FakeSMTP
- add_reminder
- date
- auth.py
- _attention
- fx_months.py
- post
- code_of
- test_people_extra.py
- ViewRouter.tsx
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
- run
- compose
- Deployment (AWS, us-west-2)
- options
- google_oauth.py
- aws_put_secrets.py
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
- get_settings
- date
- PurserSidebar.tsx
- env.py
- row
- test_paused_and_ended_clients_get_no_billing_suggestions
- Ctx
- Any

## God Nodes (most connected - your core abstractions)
1. `session_scope()` - 347 edges
2. `make_actor()` - 299 edges
3. `run()` - 92 edges
4. `Invoice` - 90 edges
5. `Rev` - 79 edges
6. `safe_tool()` - 73 edges
7. `DomainError` - 71 edges
8. `go()` - 70 edges
9. `create()` - 70 edges
10. `Party` - 69 edges

## Surprising Connections (you probably didn't know these)
- `gitleaks Secret Scanning` --semantically_similar_to--> `Secrets via Secrets Manager / SSM`  [INFERRED] [semantically similar]
  README.md → CLAUDE.md
- `go()` --calls--> `Rev`  [INFERRED]
  seed/seed_v1.py → app/services/revenue/core.py
- `add_inspected_document()` --uses--> `Actor`  [INFERRED]
  tests/conftest.py → app/actor.py
- `test_beneficiary_cannot_self_approve()` --uses--> `DomainError`  [INFERRED]
  tests/test_ledger_gates.py → app/errors.py
- `test_cross_workspace_object_ids_not_found()` --uses--> `DomainError`  [INFERRED]
  tests/test_ledger_gates.py → app/errors.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Candidate AWS Hosting Runtimes** — claude_aws_app_runner, claude_aws_lambda_api_gateway, claude_aws_ecs_fargate, claude_s3_cloudfront [EXTRACTED 1.00]
- **Hackathon Delivery Phases 0-4** — claude_phase_0, claude_phase_1, claude_phase_2, claude_phase_3, claude_phase_4 [EXTRACTED 1.00]
- **Secure CI/CD Pipeline** — claude_github_actions, claude_github_oidc, claude_terraform, claude_least_privilege_iam, readme_ci_hygiene_checks [INFERRED 0.85]

## Communities (153 total, 50 thin omitted)

### Community 0 - "Phase 3: AWS Deployment and CI/CD"
Cohesion: 0.07
Nodes (38): Tiny Agent Evaluation Set, Agent Guardrails (step limits, budgets, timeouts, retries), AWS App Runner, AWS ECS Fargate, AWS Lambda + API Gateway, Change-Scope Rules, CLAUDE.md Hackathon Agent Rules, Cost Awareness (+30 more)

### Community 1 - "hygiene"
Cohesion: 0.08
Nodes (24): concurrency, cancel-in-progress, group, GITLEAKS_VERSION, env, name, runs-on, steps (+16 more)

### Community 2 - "document"
Cohesion: 0.15
Nodes (25): close_intake(), correct_extracted_field(), find_reservations(), inspect_document(), Ctx, function_tool, Open budget reservations for an employee that this receipt could replace (e.g.…, Finish intake WITHOUT any finance write, with an explicit outcome (contract,… (+17 more)

### Community 3 - "session_scope"
Cohesion: 0.07
Nodes (69): One transaction; commits on success, rolls back on any exception., session_scope(), add_doc(), _approved_bill(), call(), code_of(), count(), F() (+61 more)

### Community 4 - "Ctx"
Cohesion: 0.13
Nodes (22): complete_reminder(), get_client(), propose_balance_move(), propose_billing_cycle(), propose_end_project(), propose_fx_month_rate(), propose_invoice_change(), propose_invoice_status() (+14 more)

### Community 5 - "party"
Cohesion: 0.13
Nodes (16): Action, _apply(), _approve_bill_inputs(), _approve_claim_inputs(), ApproveBill, ApproveClaim, _budget_effect(), _claim_inputs() (+8 more)

### Community 6 - "PurserVoiceController.tsx"
Cohesion: 0.08
Nodes (24): api, ApiError, call(), Card, headers(), Me, setConversation(), uploadWithProgress() (+16 more)

### Community 7 - "test_budget_months.py"
Cohesion: 0.09
Nodes (38): get_budget_recommendations(), Trend recommendations from the last 3 CLOSED months (consistent overrun or…, The plan for `target`, without steps already applied for that month (same kind,…, still_to_do(), allocated(), allocated_in(), cells(), change() (+30 more)

### Community 8 - "package.json"
Cohesion: 0.05
Nodes (37): echarts, @fontsource/dm-sans, @fontsource/geist-mono, @fontsource/noto-sans-devanagari, @fontsource/source-serif-4, @types/react, @types/react-dom, @types/three (+29 more)

### Community 9 - "event_stream"
Cohesion: 0.12
Nodes (14): In-process event fan-out to the browser (SSE), keyed by conversation. One…, subscribe(), unsubscribe(), domain_error(), event_stream(), no_shared_cache(), DomainError, Request (+6 more)

### Community 10 - "revenue.py"
Cohesion: 0.17
Nodes (20): get_fx_rates(), get_invoice(), get_revenue_overview(), go(), get_revenue_suggestions(), list_client_invoices(), go(), _period() (+12 more)

### Community 11 - "MUNSHI: Voice-only, agent-centric finance and operations copilot"
Cohesion: 0.08
Nodes (25): 0. Planning inputs and research status, 10. Contract liability analysis (re-implemented from the user's guide), 11. Bill and receipt extraction, 12. External integrations, 13. Data model (Postgres; money = BIGINT paise; timestamps UTC, IST display; FY Apr-Mar), 14. Repository layout (this repo, `~/Projects/Builders`), 15. AWS deployment and CI/CD, 16. Security and trust (+17 more)

### Community 12 - "Compiled"
Cohesion: 0.22
Nodes (17): _ageing(), _budget(), _budget_flows(), _claims(), Compiled, _contracts(), _grains(), _month() (+9 more)

### Community 14 - "Munshi | Product and delivery plan v2"
Cohesion: 0.12
Nodes (16): 10. Data design and isolation, 11. Secondary workflows and integrations, 12. Implementation and deployment, 13. Build sequence and cut decisions, 14. Acceptance, evaluation and evidence, 15. Four-minute demonstration and handoff, 16. Definition of done, 1. User, problem and submission (+8 more)

### Community 15 - "server.py"
Cohesion: 0.17
Nodes (11): Bridge, create_session(), get_budget_status(), index(), BaseModel, function_tool, get, Request (+3 more)

### Community 16 - "services/proposals.py"
Cohesion: 0.16
Nodes (26): Proposal, Receipt, cancel(), confirm(), ConfirmOutcome, get_open(), load(), mark_presented() (+18 more)

### Community 17 - "compilerOptions"
Cohesion: 0.13
Nodes (14): compilerOptions, isolatedModules, jsx, lib, module, moduleResolution, noEmit, noUnusedLocals (+6 more)

### Community 18 - "test_charts_v2.py"
Cohesion: 0.10
Nodes (46): sql(), bills(), expect_validation(), finds(), flows(), fy(), fyq(), lines_by_cat() (+38 more)

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
Nodes (39): _cycle_client(), invs_of(), Guide: changing a month clears later explicit settings in the affected span…, fn(ss, rv) on a sync session in one committed transaction; return plain data., run(), rv_of(), test_apply_reprices_ticked_and_leaves_paid_and_part_paid(), go() (+31 more)

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
Cohesion: 0.10
Nodes (35): AuditEvent, BudgetLine, CompanyPayment, Conversation, InvoicePayment, LeaveMovement, Policy, SQLAlchemy models. Money is integer paise; timestamps are UTC; business dates… (+27 more)

### Community 40 - "build"
Cohesion: 0.27
Nodes (11): age_bucket(), build(), ClientLine, Due, Exposure, Insights, Kpis, Month (+3 more)

### Community 41 - "2. Still to do (in priority order)"
Cohesion: 0.07
Nodes (28): 1.10 Commits, 1.1 Voice (hour-0 spike, then productionised), 1.2 Agent (OpenAI Agents SDK), 1.3 Trust boundary: propose → present → confirm → receipt, 1.4 Finance domain, 1.5 People ops (PLAN_v5), 1.6 API and infrastructure (local), 1.7 Web UI (`web/`, React 19 + Vite + TypeScript) (+20 more)

### Community 42 - "records.py"
Cohesion: 0.08
Nodes (45): explain_budget_change(), get_attention_items(), get_audit_history(), get_budget_status(), get_record(), list_budget_categories(), _pos_view(), Ctx (+37 more)

### Community 43 - "DomainError"
Cohesion: 0.07
Nodes (33): DomainError, Any, _bill_inputs(), Execution, _message_inputs(), Plan, SendMessage, SubmitBill (+25 more)

### Community 44 - "_write"
Cohesion: 0.22
Nodes (7): mark_not_yet(), The user says a sent invoice has NOT been paid yet (answer to the weekly 'has…, _write(), Actor, AsyncSession, require_edit(), trial()

### Community 45 - "Settings"
Cohesion: 0.22
Nodes (3): Settings, BaseSettings, field_validator

### Community 46 - "services/budget_months.py"
Cohesion: 0.14
Nodes (41): get_budget_month(), get_budget_year(), This month's (or a given month's) budget per category: budget, spent,…, One category month by month for this financial year: base plan, current budget,…, BudgetPeriod, One category-month. Open months read the ledger; a closed month keeps its…, get_line(), alerts() (+33 more)

### Community 47 - "projection.py"
Cohesion: 0.11
Nodes (20): month_outlook(), Outlook, Where spend is heading (run rate), for the CEO's three bars: allocated, spent,…, budgets / spends: the FY's 12 months in order; current: index of this month (0…, year_outlook(), Change, Month, pace_of() (+12 more)

### Community 48 - "Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST)"
Cohesion: 0.50
Nodes (3): Added capabilities (same agent, same propose → confirm → receipt engine), Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST), Rules

### Community 53 - "main.py"
Cohesion: 0.14
Nodes (33): _staged_view(), one(), audit_feed(), budget_line(), budget_line_months(), contract_clause_context(), contract_deadlines_view(), contract_liabilities() (+25 more)

### Community 55 - "go"
Cohesion: 0.10
Nodes (46): figures(), mk_client(), mk_inr(), Rs 10,000 Oct with Rs 4,000 in; move Rs 6,000 to Nov: moved_paise 600000, Oct…, Rs 10,000 a month, 3-month period from Oct, combined/advance: Rs 30,000 in Oct…, send(), test_allocation_across_two_clients_rejected(), go() (+38 more)

### Community 56 - "test_revenue_core.py"
Cohesion: 0.11
Nodes (34): pinned(), priya(), propose_confirm(), fixture, parametrize, Revenue core: money maths, invoice lifecycle, allocation, reporting figures,…, Revenue clients are customer Parties in the same workspace table (no separate…, Approver with no conversation: grounding is skipped (the on-screen form path). (+26 more)

### Community 57 - "cycles.py"
Cohesion: 0.09
Nodes (53): ClientCycle, A client's billing cycle from a month on: monthly charge, every N months,…, active(), apply(), ChangePlan, check(), _clashes(), combined() (+45 more)

### Community 58 - "services/charts.py"
Cohesion: 0.09
Nodes (43): _auto_chart(), _bad(), ChartSpec, ChartType, CompareMode, Dim, DimensionName, _fetch() (+35 more)

### Community 59 - "tools/budget_months.py"
Cohesion: 0.16
Nodes (21): bm_round(), forecast_budget(), get_budget_alerts(), get_budget_history(), MonthSplit, propose_apply_recommendations(), propose_budget_change(), propose_close_month() (+13 more)

### Community 60 - "make_actor"
Cohesion: 0.10
Nodes (49): make_actor(), build(), client_for(), err(), err_sync(), priya_arjun(), DomainError, parametrize (+41 more)

### Community 61 - "test_contracts.py"
Cohesion: 0.06
Nodes (65): parse_cap(), (cap in paise, basis text). A non-INR or non-numeric cap keeps paise None and…, canonical(), create(), _a_flag(), analyse(), by_type(), contract_by_ref() (+57 more)

### Community 62 - "errors.py"
Cohesion: 0.12
Nodes (20): Agent, PurserContext, Passed to every tool via RunContextWrapper. Identity comes only from here,…, build_agent(), _instructions(), PurserAgent: one conversational agent with typed tools. Same agent for voice…, memory(), Actor (+12 more)

### Community 63 - "services/intake.py"
Cohesion: 0.14
Nodes (31): ensure_extraction(), prefetch(), Actor, Document reading (vision extraction) shared by the upload path and the…, _read(), Document, Extraction, AsyncSession (+23 more)

### Community 64 - "Invoice"
Cohesion: 0.09
Nodes (61): Invoice, date, A customer invoice (revenue). Ported from the copilot Revenue module. Billing…, _date(), conflict(), due_on(), An invoice is due on the last day of the period it covers., Allocation (+53 more)

### Community 65 - "cards.tsx"
Cohesion: 0.10
Nodes (25): AuditCard(), BudgetCard(), Deliveries(), fmt(), InboxCard(), LEAVE_NAME, LeaveCard(), LeaveRequestsCard() (+17 more)

### Community 66 - "ChartCard.tsx"
Cohesion: 0.15
Nodes (19): CATS, ChartCard(), compactInr(), DataTable(), fmtAxis(), fmtChange(), fmtFull(), fullInr() (+11 more)

### Community 67 - "Rev"
Cohesion: 0.10
Nodes (51): Party, A dated in-app reminder ('remind me Friday to chase Acme'), optionally about a…, Reminder, client(), clients(), create_client(), _currency(), find_clients() (+43 more)

### Community 68 - "app/money.py"
Cohesion: 0.21
Nodes (13): build_agent(), Cite, extract(), ExtractedDocument, LineItem, Agent, BaseModel, ExtractorAgent: reads document page images into a typed schema. It has NO… (+5 more)

### Community 69 - "safe_tool"
Cohesion: 0.10
Nodes (33): Convert DomainError into a structured result the agent can explain; log name,…, safe_tool(), propose_contract_details(), propose_contract_status(), propose_create_contract(), propose_rescan_contract(), Propose correcting a contract's details. party_name links it to an existing…, Propose marking a contract active, expired or terminated. (+25 more)

### Community 70 - "client_by"
Cohesion: 0.06
Nodes (44): client_by(), _end(), Kaveri's paid Oct invoice covers Oct-Dec: a monthly cycle from Nov must not…, test_change_cycle_keeps_raised_and_paid_and_skips_their_months(), go(), test_change_cycle_replaces_later_rules_and_updates_client_currency(), go(), test_change_cycle_skips_months_covered_by_a_kept_combined_invoice() (+36 more)

### Community 71 - "spec"
Cohesion: 0.23
Nodes (17): apply_patch(), chart_problem(), ChartSpecPatch, A revision. Anything omitted keeps its current value, so grouping survives…, Why the requested chart type does not fit the spec's shape, or None., spec(), test_add_filters_replaces_and_clear_filters(), test_month_to_customer_with_line_falls_back_to_auto() (+9 more)

### Community 72 - "metadata.py"
Cohesion: 0.13
Nodes (30): add_months(), _clean(), _client(), dates(), Detail, Details, _effective(), end_of_term() (+22 more)

### Community 75 - "format_inr"
Cohesion: 0.17
Nodes (24): Actor, budget_alerts(), claim_review(), _inr(), _line_names(), list_bills(), list_budget_lines(), list_claims() (+16 more)

### Community 76 - "test_ledger_extra.py"
Cohesion: 0.13
Nodes (44): Full settlement only (weekend scope). One per record, enforced by the unique…, Settlement, assert_conservation(), code_of(), code_of_confirm_closed(), count(), create_presented(), line_pos() (+36 more)

### Community 77 - "record_turn"
Cohesion: 0.21
Nodes (17): AsyncSession, Return evidence for confirming `p`, or raise CONFIRMATION_REQUIRED with the…, record_turn(), spoken_confirmation(), _open_approve(), _present_then_turn(), _spoken(), test_client_controlled_source_is_not_accepted_as_evidence() (+9 more)

### Community 78 - "revenue_actions.py"
Cohesion: 0.07
Nodes (40): AddInvoices, _ccy(), _clean_num(), ClientChange, DeleteDraft, EditInvoice, _eff(), EndProject (+32 more)

### Community 79 - "scan.py"
Cohesion: 0.09
Nodes (38): The shipped clause catalogue: copilot `ctr_0001_contracts.py` CLAUSE_TYPES,…, A clause type as the scan sees it., Rule, rules(), _ask(), _dedup(), _join(), locate() (+30 more)

### Community 80 - "inv_of"
Cohesion: 0.07
Nodes (49): FxMonth, A conversion rate set by hand for a currency and month; carries forward until…, inv_of(), priya(), propose_confirm(), Approver with no conversation: grounding skipped (the on-screen form path)., Northwind Oct: $1,500 at 83.90 = Rs 125,850; Rs 60,000 in; Rs 65,850 left =…, test_amount_edit_with_rate_is_a_manual_rate_not_month_rate() (+41 more)

### Community 82 - "draft_message"
Cohesion: 0.20
Nodes (10): function_tool, safe_tool, Next-step suggestion chips. Writes nothing: a clicked chip only sends a normal…, Show 1-3 tappable next-step chips under your reply. The first must match the…, suggest_next_actions(), Suggestion, draft_message(), DraftIn (+2 more)

### Community 83 - "test_revenue_fx_cycles.py"
Cohesion: 0.11
Nodes (26): FxQuote, Cached ECB reference quotes (Frankfurter): INR per unit x 10^6, by publication…, AsyncSession, Fetch and cache the latest quote for each foreign ECB currency. Returns…, refresh(), _aug_ecb(), pinned(), fixture (+18 more)

### Community 84 - "services/people.py"
Cohesion: 0.07
Nodes (54): Actor, The authenticated principal. Always derived from the server session, never from…, Finance approval rights., HR/admin rights: onboarding, company-wide announcements, all leave., find_people(), get_leave_balance(), get_onboarding_status(), list_leave_requests() (+46 more)

### Community 85 - "recommend.py"
Cohesion: 0.15
Nodes (18): ClosedMonth, plan(), slots(), PlannedChange, `closed_chrono`: the category's closed months, oldest first (any number)., Trend recommendations: if a category has over- (or under-) run its budget for…, One budget change that acts on the recommendations, for one month (amounts in…, Act on the recommendations for one month, moving money before adding any: each… (+10 more)

### Community 86 - "revenue/money.py"
Cohesion: 0.09
Nodes (31): currencies_in(), digits(), from_minor(), _indian(), numbers_in(), paise_str(), paise_to(), Decimal (+23 more)

### Community 87 - "tools/charts.py"
Cohesion: 0.10
Nodes (35): build_chart(), _card(), describe_chart_options(), present_view(), Ctx, function_tool, Chart and view tools. The model composes typed specs; every number comes from a…, What can be charted for this user: sources, measures (with units), dimensions,… (+27 more)

### Community 88 - "distribution.py"
Cohesion: 0.20
Nodes (13): by_weights(), even_split(), Divide `total_paise` into `n` parts that sum exactly to it (remainder on the…, Annual -> monthly budget distribution (PRD §3). Integer paise only; no paise is…, Keep the `locked` month indices as given and spread `total_paise - sum(locked)`…, Split `total_paise` in proportion to `weights` (exact fractions, no floats).…, Growing shares: the first month weighs 1 and each next month weighs the one…, The paise each of `months` gets out of `total_paise` (same order, summing to… (+5 more)

### Community 89 - "classify"
Cohesion: 0.18
Nodes (14): Affirmation, classify(), _contains_affirm(), _normalize(), Deterministic classifier for a confirmation utterance (English, Hindi,…, parametrize, test_affirm_variants(), test_devanagari_softener_na_affirms() (+6 more)

### Community 90 - "liability.py"
Cohesion: 0.09
Nodes (38): as_dict(), assess(), _bearer_term(), _beneficiary(), carve_outs_rules(), Deadline, deadlines(), defined_parties() (+30 more)

### Community 91 - "store.py"
Cohesion: 0.10
Nodes (52): contract_deadlines(), get_contract(), list_liabilities(), propose_review_contract_finding(), Ctx, function_tool, Contract tools: review an uploaded agreement, read liabilities / deadlines /…, Liabilities across contracts (risky clauses not rejected), with who bears each,… (+44 more)

### Community 92 - "pacing.py"
Cohesion: 0.24
Nodes (9): compute(), days_in_month(), Pacing, date, The pacing / burn-velocity engine and the proactive alert levels (PRD §4). Pure…, `day` is the current day of the month (1..total_days); use total_days for a…, _round2(), test_pacing_approaching_and_limit() (+1 more)

### Community 93 - "client_for"
Cohesion: 0.06
Nodes (58): add_inspected_document(), client_for(), test_button_confirm_and_replay(), test_employee_cannot_open_other_users_document(), test_exact_replay_returns_existing_document(), test_write_requires_csrf(), test_months_endpoint(), test_months_endpoint_other_workspace_404() (+50 more)

### Community 94 - "part_paid_zed"
Cohesion: 0.10
Nodes (26): mk_client(), mk_invoice(), part_paid_zed(), Guide example: Rs 10,000 invoice, Rs 4,000 received, part paid., test_balance_delete_destination_restores_source_to_part_paid(), go(), test_balance_into_other_currency_month_makes_its_own_balance_invoice(), go() (+18 more)

### Community 95 - "build"
Cohesion: 0.57
Nodes (7): active(), build(), _missing(), _plan(), Session, Ported from copilot services/suggest.py (user's own code), workspace-scoped for…, Suggestion

### Community 96 - "ClaimReview.tsx"
Cohesion: 0.09
Nodes (28): react-dom, dur, ease, easeInOut, palette, reveal, CardView(), UploadCard() (+20 more)

### Community 98 - "add_reminder"
Cohesion: 0.67
Nodes (3): add_reminder(), go(), Set an in-app reminder ('remind me Friday to chase Acme'): due_on YYYY-MM-DD…

### Community 100 - "auth.py"
Cohesion: 0.24
Nodes (12): _actor(), check_write(), current_actor(), current_csrf(), Request, Cookie session auth + CSRF. The Actor is derived from the server session on…, Origin + CSRF header on every state-changing browser request., _serializer() (+4 more)

### Community 102 - "_attention"
Cohesion: 0.13
Nodes (22): _attention(), can_decide(), can_view(), ensure(), our_names(), prefetch(), Actor, AsyncSession (+14 more)

### Community 103 - "fx_months.py"
Cohesion: 0.06
Nodes (54): $1,750.00 a month · Quarterly · in advance · one combined invoice, from Oct'26, summary(), bucket_label(), fy_months(), fy_of(), fy_start(), fy_today(), last_day() (+46 more)

### Community 104 - "post"
Cohesion: 0.13
Nodes (18): mark_read(), login(), Response, agent_text(), cancel_button(), confirm_button(), login(), LoginIn (+10 more)

### Community 105 - "code_of"
Cohesion: 0.17
Nodes (12): ExceptionInfo, code_of(), test_create_cap_and_duplicate_months(), go(), test_duplicate_client_name_and_archive_restore(), go(), test_invoice_ref_from_other_workspace_is_not_found(), go() (+4 more)

### Community 106 - "test_people_extra.py"
Cohesion: 0.09
Nodes (70): LeaveRequest, Message, OnboardingTask, Inbox item and/or email outbox row. Email rows are delivered after the…, User, dispatch(), Send queued emails. Each row is claimed with SKIP LOCKED so concurrent…, propose_and_confirm() (+62 more)

### Community 107 - "ViewRouter.tsx"
Cohesion: 0.18
Nodes (22): lucide-react, PurserComposer(), useAssistant(), AppShell(), PurserSidebar(), SettingsDialog(), ToastManager(), useLoad() (+14 more)

### Community 109 - "code_of"
Cohesion: 0.17
Nodes (8): code_of(), test_balance_delete_requires_unraised_destination(), go(), test_ending_an_ended_client_is_same_state(), test_foreign_and_inr_month_inputs_validated(), unknown(), test_price_aed_is_manual_only_even_with_a_cached_row(), test_price_no_cache_raises_rate_unavailable()

### Community 110 - "purser.md"
Cohesion: 0.15
Nodes (12): Charts and views, Contracts and liabilities, Facts, Language, Monthly budget, alerts, changes and month close, Next step, Other requests, People and HR (+4 more)

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
Cohesion: 0.10
Nodes (25): react, three, setSession(), App(), Login(), cardKey(), ArtifactPanel(), AmbientRibbons() (+17 more)

### Community 116 - "_fmt_date"
Cohesion: 0.13
Nodes (10): Any, ApplyLeave, Approve, DecideLeave, _fmt_date(), _leave_decision_inputs(), _onboard_inputs(), OnboardEmployee (+2 more)

### Community 119 - "run"
Cohesion: 0.13
Nodes (20): Run fn(ss, rv) on a sync session inside one committed transaction; return what…, run(), rv_of(), sugg(), test_chase_for_overdue_sent_invoice(), go(), test_custom_reminder_survives_pause(), go() (+12 more)

### Community 120 - "compose"
Cohesion: 0.28
Nodes (9): address_plan(), compose(), email_plan(), Actor, AsyncSession, User, Where an email to this user would go, and whether it is deliverable in this…, Whether an email to this address is deliverable in this demo (same rule for… (+1 more)

### Community 121 - "Deployment (AWS, us-west-2)"
Cohesion: 0.22
Nodes (8): Architecture, Deployment (AWS, us-west-2), Email and Google Meet, First deploy, Notes, Redeploy (new code), Rollback, Teardown

### Community 123 - "options"
Cohesion: 0.33
Nodes (6): options(), Registry as the model sees it, limited to what this actor may chart., BUG candidate: options() maps every non-paise unit to 'count', so the model is…, test_options_by_role(), test_options_lists_new_chart_types_and_rules(), test_options_reports_pct_unit_distinctly()

### Community 124 - "google_oauth.py"
Cohesion: 0.33
Nodes (6): Path, _client(), main(), One-time Google Calendar login: gets a refresh token for the organizer account…, _set_env(), _wait_for_code()

### Community 138 - "Mail"
Cohesion: 0.22
Nodes (6): Mail, fixture, smtp(), test_multiline_default_subject_can_be_emailed(), test_send_smtp_builds_expected_message(), test_send_smtp_never_allows_header_injection()

### Community 149 - "get_settings"
Cohesion: 0.06
Nodes (51): get_settings(), Base, configure(), engine(), AsyncSession, sessionmaker(), upload(), Meeting (+43 more)

### Community 151 - "PurserSidebar.tsx"
Cohesion: 0.13
Nodes (13): motion, spring, inr(), FinancialDecisionStrip(), ACTION_WORDS, ago(), humanize(), NavDef (+5 more)

### Community 152 - "env.py"
Cohesion: 0.27
Nodes (9): Connection, do_run_migrations(), include_object(), Run migrations in 'offline' mode. This configures the context with just a URL…, In this scenario we need to create an Engine and associate a connection with…, Run migrations in 'online' mode., run_async_migrations(), run_migrations_offline() (+1 more)

### Community 153 - "row"
Cohesion: 0.22
Nodes (8): row(), go(), go(), go(), test_seeded_northwind_nov_priced_at_carried_oct_rate(), go(), go(), test_version_persists_across_sessions()

### Community 154 - "test_paused_and_ended_clients_get_no_billing_suggestions"
Cohesion: 0.60
Nodes (5): test_paused_and_ended_clients_get_no_billing_suggestions(), end(), kinds(), nw_before(), resume()

## Knowledge Gaps
- **244 isolated node(s):** `Voice conversation context`, `Language`, `Next step`, `Facts`, `Workflow for a new document (receipt or bill)` (+239 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 896 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **50 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `session_scope()` connect `session_scope` to `document`, `test_budget_months.py`, `revenue.py`, `services/proposals.py`, `test_charts_v2.py`, `get_settings`, `run`, `records.py`, `_write`, `services/budget_months.py`, `main.py`, `test_revenue_core.py`, `services/charts.py`, `tools/budget_months.py`, `make_actor`, `test_contracts.py`, `errors.py`, `services/intake.py`, `safe_tool`, `spec`, `format_inr`, `test_ledger_extra.py`, `record_turn`, `inv_of`, `draft_message`, `test_revenue_fx_cycles.py`, `services/people.py`, `tools/charts.py`, `store.py`, `client_for`, `part_paid_zed`, `auth.py`, `_attention`, `post`, `code_of`, `test_people_extra.py`, `run`?**
  _High betweenness centrality (0.094) - this node is a cross-community bridge._
- **Why does `make_actor()` connect `make_actor` to `document`, `session_scope`, `test_budget_months.py`, `services/proposals.py`, `test_charts_v2.py`, `get_settings`, `models.py`, `records.py`, `test_revenue_core.py`, `services/charts.py`, `test_contracts.py`, `spec`, `test_ledger_extra.py`, `record_turn`, `inv_of`, `test_revenue_fx_cycles.py`, `services/people.py`, `tools/charts.py`, `store.py`, `client_for`, `_attention`, `test_people_extra.py`, `options`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Why does `Invoice` connect `Invoice` to `row`, `Rev`, `models.py`, `fx_months.py`, `Compiled`, `revenue_actions.py`, `services/proposals.py`, `inv_of`, `test_revenue_fx_cycles.py`, `run`, `go`, `test_revenue_core.py`, `cycles.py`, `services/charts.py`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Are the 71 inferred relationships involving `Invoice` (e.g. with `_receivables()` and `DeleteDraft`) actually correct?**
  _`Invoice` has 71 INFERRED edges - model-reasoned connections that need verification._
- **Are the 54 inferred relationships involving `Rev` (e.g. with `_attention()` and `_read()`) actually correct?**
  _`Rev` has 54 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Voice conversation context`, `Language`, `Next step` to the rest of the system?**
  _244 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Phase 3: AWS Deployment and CI/CD` be split into smaller, more focused modules?**
  _Cohesion score 0.06827880512091039 - nodes in this community are weakly interconnected._