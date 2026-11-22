# Graph Report - Builders  (2026-11-22)

## Corpus Check
- 258 files · ~368,411 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 5, .example 2, .ini 1)

## Summary
- 4424 nodes · 13622 edges · 237 communities (152 shown, 85 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 1265 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d8746963`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Phase 3: AWS Deployment and CI/CD
- hygiene
- test_ledger_extra.py
- session_scope
- test_b25_briefing.py
- User
- PurserVoiceController.tsx
- test_budget_months.py
- package.json
- run
- test_b25_google.py
- MUNSHI: Voice-only, agent-centric finance and operations copilot
- services/charts.py
- app/auth.py
- Munshi | Product and delivery plan v2
- server.py
- purser.py
- compilerOptions
- make_actor
- registry.py
- Munshi | Final weekend build plan
- Munshi | Build plan v3 (scope cut for the weekend)
- 5. Agent architecture
- run
- 5. Financial record lifecycles
- Purser architecture decisions
- PRESENTATION.md
- builders
- fx.py
- _fakes
- RevAction
- 2. Still to do (in priority order)
- DomainError
- contract_actions.py
- ContractCard.tsx
- Meeting
- services/budget_months.py
- projection.py
- Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST)
- fresh-sonnet-per-test-set.sh
- tests-only-in-sonnet.sh
- Agent
- main.py
- fx_months.py
- mk_client
- test_revenue_core.py
- cycles.py
- models.py
- workspace.py
- tools/contracts.py
- test_contracts.py
- test_roles_rbac.py
- services/intake.py
- Invoice
- cards.tsx
- ChartCard.tsx
- Party
- extractor.py
- _propose
- client_by
- tools/proposals.py
- metadata.py
- budgeting/__init__.py
- today_ist
- services/proposals.py
- test_workflows_engine.py
- revenue_actions.py
- scan.py
- test_revenue_fx_cycles.py
- code_of
- test_suggest_email_voice.py
- set_quote
- finance.py
- recommend.py
- revenue/money.py
- test_charts.py
- analyse
- classify
- liability.py
- store.py
- pacing.py
- client_for
- part_paid_zed
- reads.py
- react
- FakeSMTP
- day
- test_trips.py
- briefing.py
- format_inr
- Plan
- test_custom_workflows.py
- go
- test_people_extra.py
- usePurser
- custom.py
- google.py
- purser.md
- Actor
- Diwan: the voice-first back office for Indian SMBs
- test_grounding_and_workflow_memory.py
- make_contract_samples.py
- store.tsx
- gmail.py
- seed_roles
- test_b25_clarify.py
- PurserContext
- tools/charts.py
- Deployment (AWS, us-west-2)
- call
- BaseModel
- eval_run.py
- errors.py
- tools/travel.py
- aws_put_secrets.py
- search
- call
- GEMINI_UI_BRIEF.md
- aws_run_task.sh
- project_end.py
- test_meetings.py
- Purser · the back office you can talk to
- api.ts
- safe_tool
- make_meeting
- PurserContext
- distribution.py
- date
- date
- date
- date
- date
- date
- MunshiContext
- date
- records.py
- date
- PurserSidebar.tsx
- env.py
- services/people.py
- Decimal
- test_perform_each_kind
- .due_on
- FlightCard.tsx
- build
- get_settings
- Production readiness: what happens when things go wrong
- run
- Checklist workflows vs a single agent: evaluation results
- isolate
- _cycle_client
- Ctx
- Any
- mobile-viewport.mjs
- Request
- Demo script: working end to end on fresh input
- test_api_intake.py
- google/__init__.py
- travel/__init__.py
- Request
- Ctx
- Ctx
- Ctx
- Ctx
- Settings
- engine
- Actor
- Actor
- Actor
- Actor
- User
- Actor
- Session
- Actor
- Response
- row
- services/custom_workflows.py
- Reservation
- Mail
- _pick
- Task
- Actor
- Response
- datetime
- xfail
- 1. Accuracy and cost compared with a baseline
- options
- SetCycle
- meetings
- isolate
- events.py
- Purser eval report: combined-check-20261122
- Purser eval report: final-check-20261122
- Purser eval report: run2-20261122
- Purser eval report: run3-20261122
- test_set_month_clears_later_explicit_months_through_march
- Purser eval report: baseline-20261121
- Workflows (`PURSER_WORKFLOWS=1`)
- 📉 Act 5: efficiency. More accurate *and* cheaper
- cal
- pinned
- AddInvoices
- Honest note: built, reused, simulated
- 🛡️ Act 4: the novelty. Why Purser is not "a chatbot on top of Zoho"
- EditInvoice
- scenarios/README.md
- Actor
- RunContextWrapper
- AsyncSession
- StrEnum
- test_workflows_fixes.py
- DomainError
- get
- post
- Purser: the back office you can talk to, and trust with money
- test_cycle_quarterly_combined_advance_books_in_first_month

## God Nodes (most connected - your core abstractions)
1. `make_actor()` - 518 edges
2. `session_scope()` - 469 edges
3. `Actor` - 125 edges
4. `DomainError` - 103 edges
5. `get_settings()` - 98 edges
6. `User` - 97 edges
7. `run()` - 92 edges
8. `propose_and_confirm()` - 89 edges
9. `call()` - 88 edges
10. `Invoice` - 85 edges

## Surprising Connections (you probably didn't know these)
- `gitleaks Secret Scanning` --semantically_similar_to--> `Secrets via Secrets Manager / SSM`  [INFERRED] [semantically similar]
  README.md → CLAUDE.md
- `snap()` --uses--> `ResultSnapshot`  [INFERRED]
  tests/test_trips.py → app/models.py
- `test_search_hotels_date_validation()` --uses--> `ResultSnapshot`  [INFERRED]
  tests/test_trips.py → app/models.py
- `counts()` --uses--> `Conversation`  [INFERRED]
  tests/test_b25_clarify.py → app/models.py
- `test_inspect_document_surfaces_company_payment_and_reservation_routing_data()` --uses--> `Conversation`  [INFERRED]
  tests/test_intake_extra.py → app/models.py

## Import Cycles
- 4-file cycle: `app/agent/purser.py -> app/agent/tools/custom_workflows.py -> app/agent/workflows/custom.py -> app/agent/workflows/registry.py -> app/agent/purser.py`
- 4-file cycle: `app/agent/purser.py -> app/agent/tools/custom_workflows.py -> app/agent/workflows/custom.py -> app/agent/workflows/engine.py -> app/agent/purser.py`
- 4-file cycle: `web/src/FlightCard.tsx -> web/src/components/assistant/PurserVoiceController.tsx -> web/src/state/store.tsx -> web/src/cards.tsx -> web/src/FlightCard.tsx`
- 5-file cycle: `app/agent/purser.py -> app/agent/tools/custom_workflows.py -> app/agent/workflows/custom.py -> app/agent/workflows/engine.py -> app/agent/workflows/registry.py -> app/agent/purser.py`
- 5-file cycle: `app/agent/purser.py -> app/agent/tools/custom_workflows.py -> app/services/custom_workflows.py -> app/agent/workflows/custom.py -> app/agent/workflows/registry.py -> app/agent/purser.py`
- 5-file cycle: `app/agent/purser.py -> app/agent/tools/finance.py -> app/services/briefing.py -> app/agent/workflows/custom.py -> app/agent/workflows/registry.py -> app/agent/purser.py`
- 5-file cycle: `app/agent/purser.py -> app/agent/tools/custom_workflows.py -> app/services/custom_workflows.py -> app/agent/workflows/custom.py -> app/agent/workflows/engine.py -> app/agent/purser.py`
- 5-file cycle: `app/agent/purser.py -> app/agent/tools/finance.py -> app/services/briefing.py -> app/agent/workflows/custom.py -> app/agent/workflows/engine.py -> app/agent/purser.py`
- 5-file cycle: `app/agent/workflows/custom.py -> app/agent/workflows/engine.py -> app/services/proposals.py -> app/services/actions.py -> app/services/custom_workflows.py -> app/agent/workflows/custom.py`

## Hyperedges (group relationships)
- **Candidate AWS Hosting Runtimes** — claude_aws_app_runner, claude_aws_lambda_api_gateway, claude_aws_ecs_fargate, claude_s3_cloudfront [EXTRACTED 1.00]
- **Hackathon Delivery Phases 0-4** — claude_phase_0, claude_phase_1, claude_phase_2, claude_phase_3, claude_phase_4 [EXTRACTED 1.00]
- **Secure CI/CD Pipeline** — claude_github_actions, claude_github_oidc, claude_terraform, claude_least_privilege_iam, readme_ci_hygiene_checks [INFERRED 0.85]

## Communities (237 total, 85 thin omitted)

### Community 0 - "Phase 3: AWS Deployment and CI/CD"
Cohesion: 0.07
Nodes (38): Tiny Agent Evaluation Set, Agent Guardrails (step limits, budgets, timeouts, retries), AWS App Runner, AWS ECS Fargate, AWS Lambda + API Gateway, Change-Scope Rules, CLAUDE.md Hackathon Agent Rules, Cost Awareness (+30 more)

### Community 1 - "hygiene"
Cohesion: 0.08
Nodes (24): concurrency, cancel-in-progress, group, GITLEAKS_VERSION, env, name, runs-on, steps (+16 more)

### Community 2 - "test_ledger_extra.py"
Cohesion: 0.12
Nodes (44): Full settlement only (weekend scope). One per record, enforced by the unique…, Settlement, record_turn(), assert_conservation(), code_of(), count(), line_pos(), _open_approve() (+36 more)

### Community 3 - "session_scope"
Cohesion: 0.07
Nodes (69): One transaction; commits on success, rolls back on any exception., session_scope(), add_doc(), _approved_bill(), code_of(), count(), F(), finance_counts() (+61 more)

### Community 4 - "test_b25_briefing.py"
Cohesion: 0.11
Nodes (21): add_meeting(), add_task(), isolate(), kpi_labels(), fixture, B2 gate: login briefing (role sections, Today from agenda, degradation, rule-…, sec(), test_admin_sections() (+13 more)

### Community 5 - "User"
Cohesion: 0.11
Nodes (30): OnboardingTask, User, _onboard_inputs(), OnboardEmployee, SendMessage, address_plan(), compose(), email_plan() (+22 more)

### Community 6 - "PurserVoiceController.tsx"
Cohesion: 0.10
Nodes (17): setConversation(), PurserComposer(), ACCEPT, ACCEPT_ATTR, Assistant, AssistantContext, CONNECT_RETRIES, handsFreeOn() (+9 more)

### Community 7 - "test_budget_months.py"
Cohesion: 0.10
Nodes (35): allocated(), allocated_in(), cells(), change(), close(), close_oct(), code_of(), count_movements() (+27 more)

### Community 8 - "package.json"
Cohesion: 0.05
Nodes (37): echarts, @fontsource/dm-sans, @fontsource/geist-mono, @fontsource/noto-sans-devanagari, @fontsource/source-serif-4, @types/react, @types/react-dom, @types/three (+29 more)

### Community 9 - "run"
Cohesion: 0.10
Nodes (39): add_usage(), Accumulate token usage per model from SDK raw responses into…, _access(), _brief(), Chip, EngineResult, _kill(), _language_is_hinglish() (+31 more)

### Community 10 - "test_b25_google.py"
Cohesion: 0.07
Nodes (48): dispatch(), Perform queued Google ops once each (SKIP LOCKED; a failure is kept, never…, Prefer text/plain; fall back to text/html with tags removed., _text(), linked(), b64(), ops(), plan() (+40 more)

### Community 11 - "MUNSHI: Voice-only, agent-centric finance and operations copilot"
Cohesion: 0.08
Nodes (25): 0. Planning inputs and research status, 10. Contract liability analysis (re-implemented from the user's guide), 11. Bill and receipt extraction, 12. External integrations, 13. Data model (Postgres; money = BIGINT paise; timestamps UTC, IST display; FY Apr-Mar), 14. Repository layout (this repo, `~/Projects/Builders`), 15. AWS deployment and CI/CD, 16. Security and trust (+17 more)

### Community 12 - "services/charts.py"
Cohesion: 0.08
Nodes (59): _ageing(), _auto_chart(), _bad(), _budget(), _budget_flows(), ChartSpec, ChartType, _claims() (+51 more)

### Community 13 - "app/auth.py"
Cohesion: 0.16
Nodes (19): _actor(), check_write(), current_actor(), current_csrf(), login(), Cookie session auth + CSRF. The Actor is derived from the server session on…, Origin + CSRF header on every state-changing browser request., _serializer() (+11 more)

### Community 14 - "Munshi | Product and delivery plan v2"
Cohesion: 0.12
Nodes (16): 10. Data design and isolation, 11. Secondary workflows and integrations, 12. Implementation and deployment, 13. Build sequence and cut decisions, 14. Acceptance, evaluation and evidence, 15. Four-minute demonstration and handoff, 16. Definition of done, 1. User, problem and submission (+8 more)

### Community 15 - "server.py"
Cohesion: 0.17
Nodes (11): Bridge, create_session(), get_budget_status(), index(), BaseModel, function_tool, get, Request (+3 more)

### Community 16 - "purser.py"
Cohesion: 0.09
Nodes (28): Agent, build_agent(), instructions(), _instructions(), PurserContext, PurserAgent: one conversational agent with typed tools. Same agent for voice…, The Purser agent. `tools` narrows the tool set and `brief` appends context…, Which tools each role is offered. The model never sees a tool its role cannot… (+20 more)

### Community 17 - "compilerOptions"
Cohesion: 0.13
Nodes (14): compilerOptions, isolatedModules, jsx, lib, module, moduleResolution, noEmit, noUnusedLocals (+6 more)

### Community 18 - "make_actor"
Cohesion: 0.08
Nodes (79): make_actor(), run(), sql(), test_auto_chart_selection(), test_bills_totals_match_sql(), test_budget_by_category_matches_movements(), test_date_range_filter_matches_sql(), test_filter_exact_case_insensitive() (+71 more)

### Community 19 - "registry.py"
Cohesion: 0.11
Nodes (22): _allowed(), apply(), enabled(), RunContextWrapper, _escalate(), allowed(), _ctx(), menu() (+14 more)

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
Nodes (50): fn(ss, rv) on a sync session in one committed transaction; return plain data., Kaveri's paid Oct invoice covers Oct-Dec: a monthly cycle from Nov must not…, run(), rv_of(), test_apply_reprices_ticked_and_leaves_paid_and_part_paid(), go(), test_balance_onto_existing_to_raise_month_adds_at_its_rate(), test_carried_months_runs_to_march_not_beyond() (+42 more)

### Community 24 - "5. Financial record lifecycles"
Cohesion: 0.40
Nodes (5): 5. Financial record lifecycles, Budgets, reservations and spend, Employee claims and reimbursements, Revenue, invoicing and collections, Vendor bills and approvals

### Community 25 - "Purser architecture decisions"
Cohesion: 0.50
Nodes (3): Evidence (local spike, `spikes/voice_spike`, synthetic fixture), Purser architecture decisions, Voice transport and confirmation (H0 gate, 2026-11-21) — DECIDED

### Community 38 - "fx.py"
Cohesion: 0.29
Nodes (10): cached(), latest(), _newest(), Exception, Session, Rate, RateUnavailable, Exchange rates from Frankfurter (ECB reference rates, published once a working… (+2 more)

### Community 39 - "_fakes"
Cohesion: 0.13
Nodes (31): seeded(), test_engine_without_routines_picker_gets_old_five_arg_signature(), test_routine_turn_with_open_proposal_and_non_affirmation_creates_no_receipt(), _fakes(), _no_llm(), _open_proposal(), _proposal_statuses(), pick: str or list of str per call. run/esc: async callables or None for a… (+23 more)

### Community 40 - "RevAction"
Cohesion: 0.09
Nodes (20): _write(), EndProject, FxMonthRate, MoveBalance, Actor, AsyncSession, {label: value} the user must have said., Foreign currencies whose live quote the run may need (fetched before the sync… (+12 more)

### Community 41 - "2. Still to do (in priority order)"
Cohesion: 0.07
Nodes (29): 1.10 Commits, 1.1 Voice (hour-0 spike, then productionised), 1.2 Agent (OpenAI Agents SDK), 1.3 Trust boundary: propose → present → confirm → receipt, 1.4 Finance domain, 1.5 People ops (PLAN_v5), 1.6 API and infrastructure (local), 1.7 Web UI (`web/`, React 19 + Vite + TypeScript) (+21 more)

### Community 42 - "DomainError"
Cohesion: 0.07
Nodes (35): Any, DomainError, Any, Action, _apply(), ApplyLeave, Approve, _approve_bill_inputs() (+27 more)

### Community 43 - "contract_actions.py"
Cohesion: 0.26
Nodes (8): CreateContract, _details_inputs(), _fmt(), _iso(), Contract writes as propose -> present -> confirm -> receipt actions (the same…, SetContractDetails, _staged(), _type()

### Community 44 - "ContractCard.tsx"
Cohesion: 0.17
Nodes (11): ContractCard(), ContractClauseCard(), ContractDeadlinesCard(), ContractReviewCard(), Deadlines(), fmtDate(), KIND, LiabilitiesCard() (+3 more)

### Community 45 - "Meeting"
Cohesion: 0.20
Nodes (16): Meeting, A calendar event with a Google Meet link. Queued inside the confirm…, _access_token(), CalendarError, create_event(), event_body(), _google_error(), is_future() (+8 more)

### Community 46 - "services/budget_months.py"
Cohesion: 0.13
Nodes (43): get_budget_recommendations(), Trend recommendations from the last 3 CLOSED months (consistent overrun or…, _rec_plans(), step_id(), alerts(), apply_change(), apply_close(), Cell (+35 more)

### Community 47 - "projection.py"
Cohesion: 0.11
Nodes (20): month_outlook(), Outlook, Where spend is heading (run rate), for the CEO's three bars: allocated, spent,…, budgets / spends: the FY's 12 months in order; current: index of this month (0…, year_outlook(), Change, Month, pace_of() (+12 more)

### Community 48 - "Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST)"
Cohesion: 0.50
Nodes (3): Added capabilities (same agent, same propose → confirm → receipt engine), Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST), Rules

### Community 53 - "main.py"
Cohesion: 0.07
Nodes (58): agent_text(), audit_feed(), budget_line(), budget_line_months(), cancel_button(), confirm_button(), contract_clause_context(), contract_deadlines_view() (+50 more)

### Community 54 - "fx_months.py"
Cohesion: 0.14
Nodes (23): fy_of(), Affected, apply(), carried_months(), Change, effective(), foreign(), history() (+15 more)

### Community 55 - "mk_client"
Cohesion: 0.11
Nodes (33): figures(), mk_client(), mk_inr(), Rs 10,000 Oct with Rs 4,000 in; move Rs 6,000 to Nov: moved_paise 600000, Oct…, send(), test_allocation_without_amount_pays_each_remaining(), go(), test_any_invoice_change_bumps_version() (+25 more)

### Community 56 - "test_revenue_core.py"
Cohesion: 0.12
Nodes (33): pinned(), priya(), propose_confirm(), fixture, parametrize, Revenue core: money maths, invoice lifecycle, allocation, reporting figures,…, Revenue clients are customer Parties in the same workspace table (no separate…, Approver with no conversation: grounding is skipped (the on-screen form path). (+25 more)

### Community 57 - "cycles.py"
Cohesion: 0.08
Nodes (55): ClientCycle, A client's billing cycle from a month on: monthly charge, every N months,…, active(), apply(), ChangePlan, check(), _clashes(), combined() (+47 more)

### Community 58 - "models.py"
Cohesion: 0.11
Nodes (41): list_trips(), AuditEvent, Bill, BudgetLine, BudgetMovement, BudgetPeriod, Claim, CompanyPayment (+33 more)

### Community 59 - "workspace.py"
Cohesion: 0.11
Nodes (30): briefing(), budget_alerts(), claim_review(), draft_message(), DraftIn, _inr(), _line_names(), list_bills() (+22 more)

### Community 60 - "tools/contracts.py"
Cohesion: 0.16
Nodes (20): contract_deadlines(), propose_contract_details(), propose_contract_status(), propose_review_contract_finding(), Ctx, function_tool, Contract tools: review an uploaded agreement, read liabilities / deadlines /…, Dated contract obligations in the next `days` days: expiry, renewal-notice cut-… (+12 more)

### Community 61 - "test_contracts.py"
Cohesion: 0.07
Nodes (58): _attention(), defined_parties(), {defined term (lower) -> party name} from '(hereinafter referred to as "the…, _a_flag(), analyse(), by_type(), contract_by_ref(), deadlines_of() (+50 more)

### Community 62 - "test_roles_rbac.py"
Cohesion: 0.09
Nodes (35): Contract review: read an agreement, find its clauses, identify liabilities (who…, _ctx(), exposed(), margs(), _pin(), fixture, parametrize, B1 RBAC matrix: employee / ceo / finance_approver / admin across tools,… (+27 more)

### Community 63 - "services/intake.py"
Cohesion: 0.09
Nodes (54): ensure_extraction(), prefetch(), Actor, Document reading (vision extraction) shared by the upload path and the…, _read(), close_intake(), correct_extracted_field(), find_reservations() (+46 more)

### Community 64 - "Invoice"
Cohesion: 0.11
Nodes (54): Invoice, A customer invoice (revenue). Ported from the copilot Revenue module. Billing…, _date(), conflict(), due_on(), An invoice is due on the last day of the period it covers., Allocation, BalancePlan (+46 more)

### Community 65 - "cards.tsx"
Cohesion: 0.08
Nodes (32): AuditCard(), BudgetCard(), Deliveries(), fmt(), InboxCard(), LEAVE_NAME, LeaveCard(), LeaveRequestsCard() (+24 more)

### Community 66 - "ChartCard.tsx"
Cohesion: 0.15
Nodes (19): CATS, ChartCard(), compactInr(), DataTable(), fmtAxis(), fmtChange(), fmtFull(), fullInr() (+11 more)

### Community 67 - "Party"
Cohesion: 0.10
Nodes (47): Party, A dated in-app reminder ('remind me Friday to chase Acme'), optionally about a…, Reminder, client(), clients(), create_client(), _currency(), find_clients() (+39 more)

### Community 68 - "extractor.py"
Cohesion: 0.24
Nodes (12): build_agent(), Cite, extract(), ExtractedDocument, LineItem, Agent, BaseModel, ExtractorAgent: reads document page images into a typed schema. It has NO… (+4 more)

### Community 69 - "_propose"
Cohesion: 0.08
Nodes (54): Convert DomainError into a structured result the agent can explain; log name,…, safe_tool(), propose_create_contract(), propose_rescan_contract(), Propose re-reading a saved contract's text with the clause catalogue (keeps…, Propose saving a reviewed contract with its findings and deadlines. Omit…, _propose(), add_reminder() (+46 more)

### Community 70 - "client_by"
Cohesion: 0.11
Nodes (30): client_by(), _end(), invs_of(), go(), test_change_cycle_keeps_raised_and_paid_and_skips_their_months(), go(), go(), test_change_cycle_replaces_later_rules_and_updates_client_currency() (+22 more)

### Community 71 - "tools/proposals.py"
Cohesion: 0.13
Nodes (25): cancel_pending_proposal(), _confirm(), confirm_pending_proposal(), get_pending_proposal(), _proposal_view(), propose_approval(), propose_settlement(), propose_submit_bill() (+17 more)

### Community 72 - "metadata.py"
Cohesion: 0.13
Nodes (30): add_months(), _clean(), _client(), dates(), Detail, Details, _effective(), end_of_term() (+22 more)

### Community 75 - "today_ist"
Cohesion: 0.15
Nodes (28): bm_round(), forecast_budget(), get_budget_alerts(), get_budget_history(), get_budget_month(), get_budget_year(), MonthSplit, propose_apply_recommendations() (+20 more)

### Community 76 - "services/proposals.py"
Cohesion: 0.14
Nodes (37): Proposal, Receipt, cancel(), confirm(), ConfirmOutcome, load(), mark_presented(), _now() (+29 more)

### Community 77 - "test_workflows_engine.py"
Cohesion: 0.12
Nodes (36): check(), Fail loudly if a spec names a tool that does not exist, uses an engine-only…, RegistryError, workflows(), Code check of the checklist outcome from what actually happened (tool log,…, verify(), RuntimeError, test_registry_check_passes_and_covers_routine_manager() (+28 more)

### Community 78 - "revenue_actions.py"
Cohesion: 0.11
Nodes (27): _ccy(), _clean_num(), ClientChange, DeleteDraft, _eff(), _fx_note(), _invoices_by_refs(), money_minor() (+19 more)

### Community 79 - "scan.py"
Cohesion: 0.09
Nodes (35): The shipped clause catalogue: copilot `ctr_0001_contracts.py` CLAUSE_TYPES,…, A clause type as the scan sees it., Rule, rules(), _ask(), _dedup(), _join(), locate() (+27 more)

### Community 80 - "test_revenue_fx_cycles.py"
Cohesion: 0.10
Nodes (49): FxMonth, A conversion rate set by hand for a currency and month; carries forward until…, canonical(), create(), inv_of(), priya(), propose_confirm(), Revenue gate 2: FX pricing and month rates, billing cycles, balance transfers,… (+41 more)

### Community 81 - "code_of"
Cohesion: 0.13
Nodes (12): code_of(), test_balance_delete_requires_unraised_destination(), go(), no_month(), test_end_ignore_needs_a_month_and_pending_must_be_known(), no_month(), unknown(), test_ending_an_ended_client_is_same_state() (+4 more)

### Community 82 - "test_suggest_email_voice.py"
Cohesion: 0.10
Nodes (32): session_config(), test_wake_opener_is_english(), test_location_api_stores_and_returns_nearest(), _call(), _ctx(), _execute(), _items(), _plan() (+24 more)

### Community 83 - "set_quote"
Cohesion: 0.13
Nodes (18): FxQuote, Cached ECB reference quotes (Frankfurter): INR per unit x 10^6, by publication…, AsyncSession, Fetch and cache the latest quote for each foreign ECB currency. Returns…, refresh(), _aug_ecb(), Upsert the cached ECB quote for (ccy, day) with fetched_at = now - age., set_quote() (+10 more)

### Community 84 - "finance.py"
Cohesion: 0.12
Nodes (28): explain_budget_change(), get_attention_items(), get_audit_history(), get_briefing(), get_budget_status(), get_record(), list_budget_categories(), _pos_view() (+20 more)

### Community 85 - "recommend.py"
Cohesion: 0.15
Nodes (18): ClosedMonth, plan(), slots(), PlannedChange, `closed_chrono`: the category's closed months, oldest first (any number)., Trend recommendations: if a category has over- (or under-) run its budget for…, One budget change that acts on the recommendations, for one month (amounts in…, Act on the recommendations for one month, moving money before adding any: each… (+10 more)

### Community 86 - "revenue/money.py"
Cohesion: 0.09
Nodes (30): currencies_in(), digits(), from_minor(), _indian(), numbers_in(), paise_str(), paise_to(), Decimal (+22 more)

### Community 87 - "test_charts.py"
Cohesion: 0.11
Nodes (35): apply_patch(), chart_problem(), ChartSpecPatch, A revision. Anything omitted keeps its current value, so grouping survives…, Why the requested chart type does not fit the spec's shape, or None., build(), client_for(), err() (+27 more)

### Community 88 - "analyse"
Cohesion: 0.29
Nodes (8): analyse(), clean_name(), guess_title(), guess_type(), Northwind Labs Inc, a company incorporated in Delaware' -> 'Northwind Labs Inc'., The whole review of a text: findings with liabilities, details, deadlines. Pure…, test_guess_type_and_title(), test_live_demo_clean_name_has_no_company_tail()

### Community 89 - "classify"
Cohesion: 0.07
Nodes (34): Affirmation, classify(), _contains_affirm(), _normalize(), Deterministic classifier for a confirmation utterance (English, Hindi,…, StrEnum, bridge(), _Conn (+26 more)

### Community 90 - "liability.py"
Cohesion: 0.07
Nodes (45): Deadlines follow the contract's current expiry and its auto-renewal notice…, recompute_deadlines(), as_dict(), assess(), _bearer_term(), _beneficiary(), carve_outs_rules(), Deadline (+37 more)

### Community 91 - "store.py"
Cohesion: 0.14
Nodes (39): get_contract(), list_liabilities(), Liabilities across contracts (risky clauses not rejected), with who bears each,…, One contract by ref (AG3), title or counterparty: liabilities with who bears…, Contract, ContractDeadline, ContractFinding, One agreement. Text is the extracted reading of the original document (kept in… (+31 more)

### Community 92 - "pacing.py"
Cohesion: 0.24
Nodes (9): compute(), days_in_month(), Pacing, date, The pacing / burn-velocity engine and the proactive alert levels (PRD §4). Pure…, `day` is the current day of the month (1..total_days); use total_days for a…, _round2(), test_pacing_approaching_and_limit() (+1 more)

### Community 93 - "client_for"
Cohesion: 0.06
Nodes (57): add_inspected_document(), client_for(), test_button_confirm_and_replay(), test_months_endpoint(), test_http_contract_admin_ok_employee_forbidden(), test_http_deadlines(), test_http_finding_context_marks_span_inside_excerpt(), test_http_injection_in_path_and_params() (+49 more)

### Community 94 - "part_paid_zed"
Cohesion: 0.08
Nodes (32): test_part_payment_summary_is_user_facing(), go(), mk_client(), mk_invoice(), part_paid_zed(), Guide example: Rs 10,000 invoice, Rs 4,000 received, part paid., test_balance_delete_destination_restores_source_to_part_paid(), go() (+24 more)

### Community 95 - "reads.py"
Cohesion: 0.11
Nodes (36): active(), bucket_label(), fy_months(), fy_start(), fy_today(), last_day(), month_label(), period_label() (+28 more)

### Community 96 - "react"
Cohesion: 0.07
Nodes (37): motion, react, react-dom, dur, ease, easeInOut, palette, reveal (+29 more)

### Community 98 - "day"
Cohesion: 0.07
Nodes (52): checkout_link(), google_flights_url(), date, Where the traveller pays for THIS flight: the airline's own checkout via Google…, google_hotels_url(), _norm(), date, Hotel search: SerpAPI Google Hotels (real rates, the hotel's own website for… (+44 more)

### Community 99 - "test_trips.py"
Cohesion: 0.14
Nodes (46): GoogleOp, HotelBooking, Outbox for confirmed Gmail / Google Calendar changes on the linked account.…, A hotel stay approved in Purser. Payment happens on the hotel's own website…, BookTrip, pin(), Replace get_settings everywhere it was imported by name, so one patched…, book_trip() (+38 more)

### Community 100 - "briefing.py"
Cohesion: 0.16
Nodes (27): _admin(), build(), _ceo(), _common(), _employee(), _greeting(), _hm(), _important_mail() (+19 more)

### Community 102 - "format_inr"
Cohesion: 0.19
Nodes (17): format_inr(), INR formatting with Indian digit grouping. Amounts are always integer paise., SubmitClaim, _city(), _execute(), flight_lines(), hotel_lines(), _inputs() (+9 more)

### Community 103 - "Plan"
Cohesion: 0.07
Nodes (31): Execution, Plan, ApplyRecommendations, BudgetChange, _change_plan(), _close_plan(), CloseMonth, _paise() (+23 more)

### Community 104 - "test_custom_workflows.py"
Cohesion: 0.09
Nodes (42): check_unique(), _body(), _ceo_client(), _clear_briefing(), code_of(), _customs(), DomainError, fixture (+34 more)

### Community 105 - "go"
Cohesion: 0.13
Nodes (22): ExceptionInfo, code_of(), test_allocation_across_two_clients_rejected(), go(), test_create_cap_and_duplicate_months(), go(), test_delete_only_when_to_raise(), go() (+14 more)

### Community 106 - "test_people_extra.py"
Cohesion: 0.08
Nodes (69): LeaveRequest, Message, Inbox item and/or email outbox row. Email rows are delivered after the…, dispatch(), Send queued emails. Each row is claimed with SKIP LOCKED so concurrent…, propose_and_confirm(), test_messaging_dispatch_survives_calendar_dispatch_crash(), add_employee() (+61 more)

### Community 107 - "usePurser"
Cohesion: 0.14
Nodes (28): lucide-react, useAssistant(), Briefing, BriefingView(), Item, Section, useBriefing(), AppShell() (+20 more)

### Community 108 - "custom.py"
Cohesion: 0.09
Nodes (36): catalogue(), Checked, _clean(), collisions(), _compile_once(), compile_routine(), _core_words(), _ctx() (+28 more)

### Community 109 - "google.py"
Cohesion: 0.16
Nodes (25): _g(), list_meetings(), _need_google(), propose_cancel_meeting(), propose_email(), propose_mail_action(), propose_reschedule_meeting(), datetime (+17 more)

### Community 110 - "purser.md"
Cohesion: 0.12
Nodes (16): Charts and views, Contracts and liabilities, Facts, Language, Mail and calendar, Monthly budget, alerts, changes and month close, Next step, Other requests (+8 more)

### Community 111 - "Actor"
Cohesion: 0.06
Nodes (41): Actor, The authenticated principal. Always derived from the server session, never from…, Finance approval rights., May SEE budget, revenue, payables, receivables and company-wide records (not…, May not make any change at all (no proposals, no direct writes)., HR/admin rights: onboarding, company-wide announcements, all leave., Base, Conversation (+33 more)

### Community 112 - "Diwan: the voice-first back office for Indian SMBs"
Cohesion: 0.17
Nodes (11): 10. Beyond the weekend, 1. The problem, 2. The solution, 3. Why AI, and what the AI actually does, 4. The trust boundary: propose → present → confirm → receipt, 5. Architecture, 6. What is already built (Saturday, 21 Nov), 7. Plan to the Sunday 14:00 freeze (+3 more)

### Community 113 - "test_grounding_and_workflow_memory.py"
Cohesion: 0.12
Nodes (32): Keep the latest flight / hotel search (its id and options) across turns, so…, _remember_searches(), _normal(), numbers_spoken(), Actor, AsyncSession, A model never supplies a booked amount or rate on its own: the number must…, The user's last few server-observed turns in this conversation, newest last.… (+24 more)

### Community 114 - "make_contract_samples.py"
Cohesion: 0.25
Nodes (9): docx(), main(), _pdf_escape(), Write the synthetic agreements in seed/contract_samples.py as files under…, A real PDF with a text layer: wrapped lines, 50 per page, Helvetica 10pt on A4., Page images only (no text layer), like a scanned agreement., scanned_pdf(), text_pdf() (+1 more)

### Community 115 - "store.tsx"
Cohesion: 0.09
Nodes (18): three, Props, TARGETS, Caption, Choice, Ctx, Decision, OrbState (+10 more)

### Community 116 - "gmail.py"
Cohesion: 0.17
Nodes (17): addresses(), build_raw(), create_draft(), _decode(), get_thread(), _hdr(), Gmail for the linked account. Message bodies are UNTRUSTED data: stripped to…, Recipient, subject and threading headers for a reply to the latest message in a… (+9 more)

### Community 117 - "seed_roles"
Cohesion: 0.14
Nodes (16): date, Monday-Friday count, inclusive. (Holiday calendar is a roadmap item; weekends…, working_days(), BudgetLine, _email(), enrich_core(), AsyncSession, People, leave, budget lines, bills, claims, policies and messages. Runs before… (+8 more)

### Community 118 - "test_b25_clarify.py"
Cohesion: 0.20
Nodes (23): ask(), counts(), opts(), parametrize, B3 gate: ask_choice (2-5 options, chart registry validation, per-topic cap of…, Without a conversation there is nowhere to count: every question is allowed…, An employee's registry has no finance sources, so a finance measure cannot be…, test_build_chart_success_resets_chart_count() (+15 more)

### Community 119 - "PurserContext"
Cohesion: 0.12
Nodes (22): PurserContext, Passed to every tool via RunContextWrapper. Identity comes only from here,…, _mark_presented(), memory(), Actor, One user turn through PurserAgent. Shared by the text channel, push-to-talk and…, PURSER_WORKFLOWS=1: the workflow engine handles the turn…, Any proposal created during this turn has now been presented to the user. (+14 more)

### Community 120 - "tools/charts.py"
Cohesion: 0.11
Nodes (32): build_chart(), _card(), describe_chart_options(), present_view(), function_tool, safe_tool, Chart and view tools. The model composes typed specs; every number comes from a…, What can be charted for this user: sources, measures (with units), dimensions,… (+24 more)

### Community 121 - "Deployment (AWS, us-west-2)"
Cohesion: 0.22
Nodes (9): Architecture, Deployment (AWS, us-west-2), Email and Google Meet, First deploy, Notes, Redeploy (new code), Rollback, Teardown (+1 more)

### Community 122 - "call"
Cohesion: 0.07
Nodes (58): FlightBooking, One stored result feeds chart, table and speech., A SIMULATED flight booking: no ticket is bought. Real fare data from the search…, ResultSnapshot, _km(), nearest(), _norm(), Static airport table (IATA, city, aliases, lat/lon) and a haversine nearest-… (+50 more)

### Community 124 - "eval_run.py"
Cohesion: 0.14
Nodes (21): Path, build_report(), _check(), _cost(), _counts(), _fresh_world(), load_scenarios(), main() (+13 more)

### Community 125 - "errors.py"
Cohesion: 0.12
Nodes (31): add_task(), complete_task(), list_tasks(), list_tickets(), propose_assign_task(), propose_ticket(), propose_ticket_update(), function_tool (+23 more)

### Community 126 - "tools/travel.py"
Cohesion: 0.11
Nodes (28): ask_choice(), bump(), Choice, current(), BaseModel, function_tool, safe_tool, MCQ clarifications: one tappable question at a time, at most three per topic,… (+20 more)

### Community 129 - "search"
Cohesion: 0.11
Nodes (23): FlightSearchError, _hhmm(), _norm_option(), Exception, Flight search: SerpAPI Google Flights (real fares) with a 30-minute cache; on…, Deterministic SAMPLE fares when live search is unavailable. Always labelled…, Returns {source: serpapi|sample, options: [...], note}. Options are sorted…, _sample() (+15 more)

### Community 130 - "call"
Cohesion: 0.13
Nodes (24): _label_id(), perform(), access_token(), call(), error_text(), Response, OAuth refresh-token exchange for the linked Google account, with the access…, create_simple() (+16 more)

### Community 133 - "project_end.py"
Cohesion: 0.21
Nodes (11): Price, INR is 1; a typed rate is manual; then the currency's month rate in force for…, apply(), _close(), EndPlan, _later_or_same(), plan(), Session (+3 more)

### Community 134 - "test_meetings.py"
Cohesion: 0.14
Nodes (28): dispatch(), Create queued meetings at Google. Rows are claimed with SKIP LOCKED so…, args(), code_for(), linked(), meetings(), pin(), queue_meeting() (+20 more)

### Community 135 - "Purser · the back office you can talk to"
Cohesion: 0.11
Nodes (19): 🎬 Act 1: a Tuesday without Purser, 🌅 Act 2: the same Tuesday with Purser, 🧩 Act 3: what's in the box (core features), 🥊 Act 6: the market and where Purser fits, 🧱 Act 7½: built not to break, 🏗️ Act 7: how it is built (AWS), 🎥 Act 8: live demo (about 6 minutes), 🧾 Act 9: honesty and limits (+11 more)

### Community 136 - "api.ts"
Cohesion: 0.12
Nodes (21): api, ApiError, call(), Card, headers(), inr(), Me, setSession() (+13 more)

### Community 138 - "make_meeting"
Cohesion: 0.26
Nodes (11): make_meeting(), route(), wrapped(), test_create_event_409_fetches_existing_event(), test_create_event_http_error_raises_calendar_error(), test_create_event_posts_with_bearer_and_returns_links(), handler(), test_event_body_shape() (+3 more)

### Community 140 - "distribution.py"
Cohesion: 0.20
Nodes (13): by_weights(), even_split(), Divide `total_paise` into `n` parts that sum exactly to it (remainder on the…, Annual -> monthly budget distribution (PRD §3). Integer paise only; no paise is…, Keep the `locked` month indices as given and spread `total_paise - sum(locked)`…, Split `total_paise` in proportion to `weights` (exact fractions, no floats).…, Growing shares: the first month weighs 1 and each next month weighs the one…, The paise each of `months` gets out of `total_paise` (same order, summing to… (+5 more)

### Community 149 - "records.py"
Cohesion: 0.32
Nodes (11): bill_by_ref(), claim_by_ref(), _not_found(), AsyncSession, DomainError, Scoped record lookups. Every read derives scope from the Actor; out-of-scope…, Return scored candidates. Never auto-picks when more than one plausibly matches., record_by_ref() (+3 more)

### Community 151 - "PurserSidebar.tsx"
Cohesion: 0.14
Nodes (16): spring, ACTION_WORDS, ago(), humanize(), NavDef, Note, Notifications(), Profile() (+8 more)

### Community 152 - "env.py"
Cohesion: 0.27
Nodes (9): Connection, do_run_migrations(), include_object(), Run migrations in 'offline' mode. This configures the context with just a URL…, In this scenario we need to create an Engine and associate a connection with…, Run migrations in 'online' mode., run_async_migrations(), run_migrations_offline() (+1 more)

### Community 153 - "services/people.py"
Cohesion: 0.09
Nodes (44): find_people(), get_leave_balance(), get_onboarding_status(), list_leave_requests(), lookup_policy(), _person(), propose_leave(), propose_leave_decision() (+36 more)

### Community 155 - "test_perform_each_kind"
Cohesion: 0.18
Nodes (5): test_perform_each_kind(), create(), modify(), op(), test_perform_label_reuses_existing_or_creates()

### Community 157 - "FlightCard.tsx"
Cohesion: 0.25
Nodes (10): dur(), FlightOptionsCard(), Hotel, HotelOptionsCard(), inr(), openPayment(), Opt, Pay (+2 more)

### Community 158 - "build"
Cohesion: 0.27
Nodes (11): age_bucket(), build(), ClientLine, Due, Exposure, Insights, Kpis, Month (+3 more)

### Community 159 - "get_settings"
Cohesion: 0.08
Nodes (29): The one login whose real Gmail and Google Calendar Purser may use…, get_settings(), configure(), AsyncSession, sessionmaker(), enabled(), LLMUnavailable, BaseModel (+21 more)

### Community 160 - "Production readiness: what happens when things go wrong"
Cohesion: 0.25
Nodes (8): 1. Failure modes and how each one is handled, 2. How we know it holds, 3. Recovery, 4. Known gaps (sized for a hackathon demo, not yet for production), Deployment and infrastructure, External services and slow paths, Money and data integrity, Production readiness: what happens when things go wrong

### Community 162 - "run"
Cohesion: 0.13
Nodes (20): Run fn(ss, rv) on a sync session inside one committed transaction; return what…, run(), rv_of(), sugg(), test_chase_for_overdue_sent_invoice(), go(), test_custom_reminder_survives_pause(), go() (+12 more)

### Community 163 - "Checklist workflows vs a single agent: evaluation results"
Cohesion: 0.12
Nodes (17): 10. Reliability and safety design (why 0 wrong writes is structural, not lucky), 11. Limitations (read before quoting numbers), 12. Conclusion, 1. Summary, 2.1 The three arms, 2.2 The scenario set: 46 conversations, 90 turns, four levels of difficulty, 2.3 What each turn is checked for, 2. What was compared (+9 more)

### Community 165 - "_cycle_client"
Cohesion: 0.29
Nodes (7): _cycle_client(), test_guide_arrears_books_in_december_and_raises_at_period_end(), go(), test_guide_monthly_mode_emits_three_rows_sharing_the_period(), go(), test_guide_quarterly_advance_combined_books_30000_in_october_due_31_dec(), go()

### Community 170 - "mobile-viewport.mjs"
Cohesion: 0.20
Nodes (8): check(), { chromium }, count(), login(), record(), require, results, XFAIL

### Community 172 - "Demo script: working end to end on fresh input"
Cohesion: 0.14
Nodes (14): 0:00 Login and briefing, 0:30 ⭐ Fresh receipt → approved claim, 1:30 ⭐ A chart you talk to, 2:15 ✈️ Spotlight: trip in two sentences, 3:15 📜 Spotlight: contract liability radar, 4:15 🔁 Spotlight: teach Purser a routine, 4-minute cut, 5:00 🛡️ Try to break it (+6 more)

### Community 173 - "test_api_intake.py"
Cohesion: 0.22
Nodes (8): _pdf(), parametrize, HTTP layer + intake gates that need no model: auth, CSRF, upload outcomes,…, test_arithmetic_check(), test_employee_cannot_open_other_users_document(), test_exact_replay_returns_existing_document(), test_upload_explicit_outcomes(), test_write_requires_csrf()

### Community 181 - "Settings"
Cohesion: 0.17
Nodes (4): Settings, BaseSettings, field_validator, test_settings_strip_google_values()

### Community 182 - "engine"
Cohesion: 0.07
Nodes (18): engine(), AsyncEngine, fake_pick(), fake_run(), _row(), test_compile_routine_collision_adds_warning(), test_compile_routine_gives_up_after_one_repair(), test_compile_routine_repairs_once_then_succeeds() (+10 more)

### Community 192 - "row"
Cohesion: 0.29
Nodes (7): row(), go(), go(), go(), test_seeded_northwind_nov_priced_at_carried_oct_rate(), go(), go()

### Community 193 - "services/custom_workflows.py"
Cohesion: 0.13
Nodes (27): delete_routine(), draft_routine(), DraftIn, list_routines(), Actor, BaseModel, get, post (+19 more)

### Community 195 - "Mail"
Cohesion: 0.22
Nodes (6): Mail, fixture, smtp(), test_multiline_default_subject_can_be_emailed(), test_send_smtp_builds_expected_message(), test_send_smtp_never_allows_header_injection()

### Community 196 - "_pick"
Cohesion: 0.33
Nodes (5): _pick(), Rule order decides; the fast model may re-pick among the top candidates and…, A key is present but the model call blows up: fall back to the top rule…, test_next_action_none_when_nothing_to_do(), test_pick_survives_model_failure()

### Community 202 - "1. Accuracy and cost compared with a baseline"
Cohesion: 0.18
Nodes (11): 1. Accuracy and cost compared with a baseline, 2. Engineering checks (automated tests), 3. Outputs on new data, 4. Proof that data persists, Evidence of results, Head-to-head on the same code and scenarios (run 3, `evals/reports/run3-20261122/`), How a judge can verify persistence live (2 minutes), Limitations (please read before quoting) (+3 more)

### Community 203 - "options"
Cohesion: 0.33
Nodes (6): options(), Registry as the model sees it, limited to what this actor may chart., BUG candidate: options() maps every non-paise unit to 'count', so the model is…, test_options_by_role(), test_options_lists_new_chart_types_and_rules(), test_options_reports_pct_unit_distinctly()

### Community 205 - "meetings"
Cohesion: 0.67
Nodes (3): meetings(), datetime, Returns (events, source). Google errors propagate (callers decide whether to…

### Community 207 - "events.py"
Cohesion: 0.40
Nodes (4): In-process event fan-out to the browser (SSE), keyed by conversation. One…, subscribe(), unsubscribe(), Queue

### Community 208 - "Purser eval report: combined-check-20261122"
Cohesion: 0.29
Nodes (6): By tier (task success), Context growth (input tokens per turn, run 1, chained scenarios), Escalations in B (backlog for new specs), Failures (run 1), Headline, Purser eval report: combined-check-20261122

### Community 209 - "Purser eval report: final-check-20261122"
Cohesion: 0.29
Nodes (6): By tier (task success), Context growth (input tokens per turn, run 1, chained scenarios), Escalations in B (backlog for new specs), Failures (run 1), Headline, Purser eval report: final-check-20261122

### Community 210 - "Purser eval report: run2-20261122"
Cohesion: 0.29
Nodes (6): By tier (task success), Context growth (input tokens per turn, run 1, chained scenarios), Escalations in B (backlog for new specs), Failures (run 1), Headline, Purser eval report: run2-20261122

### Community 211 - "Purser eval report: run3-20261122"
Cohesion: 0.29
Nodes (6): By tier (task success), Context growth (input tokens per turn, run 1, chained scenarios), Escalations in B (backlog for new specs), Failures (run 1), Headline, Purser eval report: run3-20261122

### Community 213 - "Purser eval report: baseline-20261121"
Cohesion: 0.33
Nodes (5): By tier (task success), Context growth (input tokens per turn, run 1, chained scenarios), Failures (run 1), Headline, Purser eval report: baseline-20261121

### Community 214 - "Workflows (`PURSER_WORKFLOWS=1`)"
Cohesion: 0.40
Nodes (4): A turn, Add or change a workflow, User routines (custom workflows), Workflows (`PURSER_WORKFLOWS=1`)

### Community 215 - "📉 Act 5: efficiency. More accurate *and* cheaper"
Cohesion: 0.25
Nodes (8): 📉 Act 5: efficiency. More accurate *and* cheaper, Context stays flat in a long conversation, Cost per successful task, Task success, The scoreboard, Tokens per turn, We let the eval drive the engineering, Where the gains came from (by tier)

### Community 216 - "cal"
Cohesion: 0.33
Nodes (3): cal(), fixture, Calendar disabled by default; a test calls pin(monkeypatch, **FAKE) to enable.…

### Community 221 - "Honest note: built, reused, simulated"
Cohesion: 0.33
Nodes (6): Data permissions, Honest note: built, reused, simulated, Known limits, What is simulated, What we built at the event, What we reused

### Community 222 - "🛡️ Act 4: the novelty. Why Purser is not "a chatbot on top of Zoho""
Cohesion: 0.33
Nodes (6): 🛡️ Act 4: the novelty. Why Purser is not "a chatbot on top of Zoho", Novelty 1: propose → present → confirm → receipt, Novelty 2: numbers come from SQL, never from the model, Novelty 3: checklist workflows (our engineering-depth bet), Novelty 4: voice-native and Indian-language-native, Novelty 5: the UI is composed by the agent

### Community 232 - "test_workflows_fixes.py"
Cohesion: 0.18
Nodes (18): _pure_no(), _menu(), parametrize, Gate for the workflow-engine fixes: Hinglish affirmations, _pure_no, bare-yes…, _suggestions(), test_asked_outcome_has_no_chips(), run(), test_ceo_gets_read_workflows_not_writes() (+10 more)

### Community 236 - "Purser: the back office you can talk to, and trust with money"
Cohesion: 0.22
Nodes (9): 1. The real-world problem, 2. What is new here (each item links to code), 3. Requirement → proof, 4. Headline numbers (46 conversations, 90 turns, EN / Hinglish / Hindi), 5. Verify it yourself in 2 minutes, 6. Scale built at the event, Purser: the back office you can talk to, and trust with money, Repository map (+1 more)

### Community 237 - "test_cycle_quarterly_combined_advance_books_in_first_month"
Cohesion: 0.67
Nodes (3): Rs 10,000 a month, 3-month period from Oct, combined/advance: Rs 30,000 in Oct…, test_cycle_quarterly_combined_advance_books_in_first_month(), go()

## Knowledge Gaps
- **377 isolated node(s):** `require`, `{ chromium }`, `XFAIL`, `results`, `Opt` (+372 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1322 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **85 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `session_scope()` connect `session_scope` to `test_ledger_extra.py`, `test_b25_briefing.py`, `User`, `test_meetings.py`, `test_budget_months.py`, `run`, `test_b25_google.py`, `app/auth.py`, `purser.py`, `make_actor`, `registry.py`, `records.py`, `run`, `services/people.py`, `get_settings`, `run`, `_fakes`, `RevAction`, `services/budget_months.py`, `main.py`, `engine`, `test_revenue_core.py`, `models.py`, `workspace.py`, `tools/contracts.py`, `test_contracts.py`, `test_roles_rbac.py`, `services/intake.py`, `services/custom_workflows.py`, `_propose`, `tools/proposals.py`, `today_ist`, `services/proposals.py`, `meetings`, `test_revenue_fx_cycles.py`, `test_suggest_email_voice.py`, `set_quote`, `finance.py`, `test_charts.py`, `liability.py`, `store.py`, `client_for`, `part_paid_zed`, `day`, `test_trips.py`, `briefing.py`, `test_custom_workflows.py`, `go`, `test_people_extra.py`, `custom.py`, `Actor`, `seed_roles`, `test_b25_clarify.py`, `PurserContext`, `tools/charts.py`, `call`, `eval_run.py`, `errors.py`, `tools/travel.py`?**
  _High betweenness centrality (0.100) - this node is a cross-community bridge._
- **Why does `make_actor()` connect `make_actor` to `test_ledger_extra.py`, `session_scope`, `test_b25_briefing.py`, `User`, `test_meetings.py`, `test_budget_months.py`, `run`, `test_b25_google.py`, `registry.py`, `records.py`, `_fakes`, `services/budget_months.py`, `engine`, `test_revenue_core.py`, `test_contracts.py`, `test_roles_rbac.py`, `services/intake.py`, `services/custom_workflows.py`, `options`, `services/proposals.py`, `test_workflows_engine.py`, `test_revenue_fx_cycles.py`, `test_suggest_email_voice.py`, `test_charts.py`, `liability.py`, `store.py`, `client_for`, `day`, `test_trips.py`, `briefing.py`, `test_custom_workflows.py`, `test_workflows_fixes.py`, `test_people_extra.py`, `custom.py`, `Actor`, `test_b25_clarify.py`, `PurserContext`, `tools/charts.py`, `call`, `tools/travel.py`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Why does `get_settings()` connect `get_settings` to `search`, `call`, `session_scope`, `User`, `test_meetings.py`, `run`, `test_b25_google.py`, `app/auth.py`, `purser.py`, `registry.py`, `env.py`, `fx.py`, `_fakes`, `DomainError`, `Meeting`, `test_api_intake.py`, `Settings`, `main.py`, `engine`, `test_revenue_core.py`, `models.py`, `test_roles_rbac.py`, `services/intake.py`, `Mail`, `extractor.py`, `_pick`, `services/proposals.py`, `meetings`, `test_workflows_engine.py`, `test_revenue_fx_cycles.py`, `test_suggest_email_voice.py`, `set_quote`, `day`, `test_trips.py`, `briefing.py`, `format_inr`, `Plan`, `test_people_extra.py`, `custom.py`, `google.py`, `Actor`, `PurserContext`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Are the 90 inferred relationships involving `Actor` (e.g. with `briefing()` and `budget_alerts()`) actually correct?**
  _`Actor` has 90 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `DomainError` (e.g. with `test_beneficiary_cannot_self_approve()` and `test_cross_workspace_object_ids_not_found()`) actually correct?**
  _`DomainError` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `require`, `{ chromium }`, `XFAIL` to the rest of the system?**
  _377 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Phase 3: AWS Deployment and CI/CD` be split into smaller, more focused modules?**
  _Cohesion score 0.06827880512091039 - nodes in this community are weakly interconnected._