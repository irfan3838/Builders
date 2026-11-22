# Graph Report - Builders  (2026-11-22)

## Corpus Check
- 258 files · ~368,399 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 5, .example 2, .ini 1)

## Summary
- 4411 nodes · 13608 edges · 232 communities (150 shown, 82 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 1265 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3e23c3e4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Phase 3: AWS Deployment and CI/CD
- hygiene
- make_actor
- test_intake_extra.py
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
- test_charts_v2.py
- registry.py
- Munshi | Final weekend build plan
- Munshi | Build plan v3 (scope cut for the weekend)
- 5. Agent architecture
- run
- 5. Financial record lifecycles
- Purser architecture decisions
- PRESENTATION.md
- builders
- datetime
- test_workflows_engine.py
- RevAction
- 2. Still to do (in priority order)
- actions.py
- Plan
- briefing.py
- test_meetings.py
- services/budget_months.py
- projection.py
- Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST)
- fresh-sonnet-per-test-set.sh
- tests-only-in-sonnet.sh
- Agent
- main.py
- fx_months.py
- run
- test_revenue_core.py
- cycles.py
- models.py
- session_scope
- tools/contracts.py
- test_contracts.py
- test_roles_rbac.py
- services/intake.py
- Invoice
- cards.tsx
- ChartCard.tsx
- Party
- agent/reading.py
- _propose
- client_by
- tools/proposals.py
- metadata.py
- budgeting/__init__.py
- _fmt_date
- test_ledger_extra.py
- _log
- DomainError
- scan.py
- test_revenue_fx_cycles.py
- code_of
- test_suggest_email_voice.py
- set_quote
- finance.py
- recommend.py
- revenue/money.py
- test_charts.py
- review.py
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
- live_bridge.py
- booking.py
- google_actions.py
- test_custom_workflows.py
- code_of
- test_people_extra.py
- usePurser
- custom.py
- workflows.py
- purser.md
- get_settings
- Diwan: the voice-first back office for Indian SMBs
- test_grounding_and_workflow_memory.py
- make_contract_samples.py
- store.tsx
- build
- contract_actions.py
- test_b25_clarify.py
- PurserContext
- tools/charts.py
- Deployment (AWS, us-west-2)
- test_b25_travel.py
- BaseModel
- db.py
- Actor
- tools/travel.py
- aws_put_secrets.py
- search
- google.py
- GEMINI_UI_BRIEF.md
- aws_run_task.sh
- Found
- spec
- Purser · the back office you can talk to
- api.ts
- safe_tool
- call
- PurserContext
- Read
- date
- date
- date
- date
- date
- date
- MunshiContext
- date
- runner.py
- date
- PurserSidebar.tsx
- env.py
- services/people.py
- Decimal
- test_perform_each_kind
- .due_on
- FlightCard.tsx
- _text
- post_move
- Production readiness: what happens when things go wrong
- options
- Checklist workflows vs a single agent: evaluation results
- isolate
- _cycle_client
- Ctx
- Any
- AssignTask
- Request
- Demo script: working end to end on fresh input
- gmail.py
- google/__init__.py
- travel/__init__.py
- Request
- Ctx
- Ctx
- Ctx
- Ctx
- Settings
- test_tool_propose_custom_workflow_makes_save_proposal
- Actor
- Actor
- Actor
- Actor
- User
- Actor
- Session
- Actor
- Response
- _pick
- services/custom_workflows.py
- Reservation
- _claim_inputs
- fmt_value
- Task
- Actor
- Response
- datetime
- xfail
- 1. Accuracy and cost compared with a baseline
- test_paused_and_ended_clients_get_no_billing_suggestions
- google_oauth.py
- .__init__
- .as_json
- _frankfurter
- Purser eval report: combined-check-20261122
- Purser eval report: final-check-20261122
- Purser eval report: run2-20261122
- Purser eval report: run3-20261122
- test_set_month_clears_later_explicit_months_through_march
- Purser eval report: baseline-20261121
- Workflows (`PURSER_WORKFLOWS=1`)
- 📉 Act 5: efficiency. More accurate *and* cheaper
- Honest note: built, reused, simulated
- 🛡️ Act 4: the novelty. Why Purser is not "a chatbot on top of Zoho"
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
- `test_apply_leave_reserves_days_and_previews_balance()` --uses--> `LeaveMovement`  [INFERRED]
  tests/test_people_extra.py → app/models.py
- `test_approve_moves_reserved_to_used_and_notifies()` --uses--> `LeaveMovement`  [INFERRED]
  tests/test_people_extra.py → app/models.py
- `test_onboarding_creates_everything_in_one_transaction()` --uses--> `LeaveMovement`  [INFERRED]
  tests/test_people_extra.py → app/models.py
- `test_book_flight_confirm_creates_records()` --uses--> `Message`  [INFERRED]
  tests/test_b25_travel.py → app/models.py

## Import Cycles
- 4-file cycle: `web/src/FlightCard.tsx -> web/src/components/assistant/PurserVoiceController.tsx -> web/src/state/store.tsx -> web/src/cards.tsx -> web/src/FlightCard.tsx`
- 4-file cycle: `app/agent/purser.py -> app/agent/tools/custom_workflows.py -> app/agent/workflows/custom.py -> app/agent/workflows/registry.py -> app/agent/purser.py`
- 4-file cycle: `app/agent/purser.py -> app/agent/tools/custom_workflows.py -> app/agent/workflows/custom.py -> app/agent/workflows/engine.py -> app/agent/purser.py`
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

## Communities (232 total, 82 thin omitted)

### Community 0 - "Phase 3: AWS Deployment and CI/CD"
Cohesion: 0.07
Nodes (38): Tiny Agent Evaluation Set, Agent Guardrails (step limits, budgets, timeouts, retries), AWS App Runner, AWS ECS Fargate, AWS Lambda + API Gateway, Change-Scope Rules, CLAUDE.md Hackathon Agent Rules, Cost Awareness (+30 more)

### Community 1 - "hygiene"
Cohesion: 0.08
Nodes (24): concurrency, cancel-in-progress, group, GITLEAKS_VERSION, env, name, runs-on, steps (+16 more)

### Community 2 - "make_actor"
Cohesion: 0.08
Nodes (47): store(), summarize(), make_actor(), test_booking_non_flight_snapshot_is_not_found(), test_budget_available_after_golden_path(), test_mom_on_gap_filled_month_axis(), test_non_pct_summarize_still_has_largest(), test_pct_summarize_reports_highest_lowest_not_largest_and_public_display() (+39 more)

### Community 3 - "test_intake_extra.py"
Cohesion: 0.07
Nodes (73): close_intake(), correct_extracted_field(), find_reservations(), Ctx, function_tool, Open budget reservations for an employee that this receipt could replace (e.g.…, Finish intake WITHOUT any finance write, with an explicit outcome (contract,…, Show the original document page on screen, highlighting where a field was read… (+65 more)

### Community 4 - "test_b25_briefing.py"
Cohesion: 0.11
Nodes (21): add_meeting(), add_task(), isolate(), kpi_labels(), fixture, B2 gate: login briefing (role sections, Today from agenda, degradation, rule-…, sec(), test_admin_sections() (+13 more)

### Community 5 - "User"
Cohesion: 0.13
Nodes (25): User, _onboard_inputs(), OnboardEmployee, SendMessage, address_plan(), compose(), dispatch_soon(), email_plan() (+17 more)

### Community 6 - "PurserVoiceController.tsx"
Cohesion: 0.09
Nodes (19): api, setConversation(), ACCEPT, ACCEPT_ATTR, Assistant, AssistantContext, CONNECT_RETRIES, handsFreeOn() (+11 more)

### Community 7 - "test_budget_months.py"
Cohesion: 0.10
Nodes (35): allocated(), allocated_in(), cells(), change(), close(), close_oct(), code_of(), count_movements() (+27 more)

### Community 8 - "package.json"
Cohesion: 0.05
Nodes (37): echarts, @fontsource/dm-sans, @fontsource/geist-mono, @fontsource/noto-sans-devanagari, @fontsource/source-serif-4, @types/react, @types/react-dom, @types/three (+29 more)

### Community 9 - "run"
Cohesion: 0.13
Nodes (32): add_usage(), Accumulate token usage per model from SDK raw responses into…, is_custom(), _access(), _brief(), Chip, EngineResult, _escalate() (+24 more)

### Community 10 - "test_b25_google.py"
Cohesion: 0.09
Nodes (39): dispatch(), Perform queued Google ops once each (SKIP LOCKED; a failure is kept, never…, linked(), ops(), plan(), plan_err(), parametrize, queue_two() (+31 more)

### Community 11 - "MUNSHI: Voice-only, agent-centric finance and operations copilot"
Cohesion: 0.08
Nodes (25): 0. Planning inputs and research status, 10. Contract liability analysis (re-implemented from the user's guide), 11. Bill and receipt extraction, 12. External integrations, 13. Data model (Postgres; money = BIGINT paise; timestamps UTC, IST display; FY Apr-Mar), 14. Repository layout (this repo, `~/Projects/Builders`), 15. AWS deployment and CI/CD, 16. Security and trust (+17 more)

### Community 12 - "services/charts.py"
Cohesion: 0.07
Nodes (60): _ageing(), _auto_chart(), _bad(), _budget(), _budget_flows(), ChartSpec, ChartType, _claims() (+52 more)

### Community 13 - "app/auth.py"
Cohesion: 0.13
Nodes (21): _actor(), check_write(), current_actor(), current_csrf(), login(), Cookie session auth + CSRF. The Actor is derived from the server session on…, Origin + CSRF header on every state-changing browser request., _serializer() (+13 more)

### Community 14 - "Munshi | Product and delivery plan v2"
Cohesion: 0.12
Nodes (16): 10. Data design and isolation, 11. Secondary workflows and integrations, 12. Implementation and deployment, 13. Build sequence and cut decisions, 14. Acceptance, evaluation and evidence, 15. Four-minute demonstration and handoff, 16. Definition of done, 1. User, problem and submission (+8 more)

### Community 15 - "server.py"
Cohesion: 0.17
Nodes (11): Bridge, create_session(), get_budget_status(), index(), BaseModel, function_tool, get, Request (+3 more)

### Community 16 - "purser.py"
Cohesion: 0.10
Nodes (24): PurserAgent: one conversational agent with typed tools. Same agent for voice…, apply(), enabled(), Which tools each role is offered. The model never sees a tool its role cannot…, list_custom_workflows(), propose_custom_workflow(), propose_delete_custom_workflow(), User routines (custom workflows) by voice or chat: describe one, hear the… (+16 more)

### Community 17 - "compilerOptions"
Cohesion: 0.13
Nodes (14): compilerOptions, isolatedModules, jsx, lib, module, moduleResolution, noEmit, noUnusedLocals (+6 more)

### Community 18 - "test_charts_v2.py"
Cohesion: 0.07
Nodes (68): run(), sql(), test_bills_totals_match_sql(), test_budget_by_category_matches_movements(), test_date_range_filter_matches_sql(), test_injection_strings_just_fail_to_match(), test_overdue_total_and_filters_match_sql(), test_receivables_totals_and_rows_match_sql() (+60 more)

### Community 19 - "registry.py"
Cohesion: 0.14
Nodes (14): _allowed(), RunContextWrapper, allowed(), _ctx(), menu(), Actor, Loads every workflow spec, checks coverage against the real tool set, and…, A workflow is offered when this role may use at least one of its own tools… (+6 more)

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
Nodes (49): fn(ss, rv) on a sync session in one committed transaction; return plain data., Kaveri's paid Oct invoice covers Oct-Dec: a monthly cycle from Nov must not…, run(), rv_of(), test_apply_reprices_ticked_and_leaves_paid_and_part_paid(), go(), test_carried_months_runs_to_march_not_beyond(), test_change_cycle_midyear_removes_only_to_raise_from_the_change_month() (+41 more)

### Community 24 - "5. Financial record lifecycles"
Cohesion: 0.40
Nodes (5): 5. Financial record lifecycles, Budgets, reservations and spend, Employee claims and reimbursements, Revenue, invoicing and collections, Vendor bills and approvals

### Community 25 - "Purser architecture decisions"
Cohesion: 0.50
Nodes (3): Evidence (local spike, `spikes/voice_spike`, synthetic fixture), Purser architecture decisions, Voice transport and confirmation (H0 gate, 2026-11-21) — DECIDED

### Community 38 - "datetime"
Cohesion: 0.10
Nodes (22): cached(), latest(), _newest(), Exception, Session, Rate, RateUnavailable, Exchange rates from Frankfurter (ECB reference rates, published once a working… (+14 more)

### Community 39 - "test_workflows_engine.py"
Cohesion: 0.11
Nodes (46): _save(), seeded(), test_engine_without_routines_picker_gets_old_five_arg_signature(), test_routine_turn_with_open_proposal_and_non_affirmation_creates_no_receipt(), _ctx_with(), _fakes(), _no_llm(), _open_proposal() (+38 more)

### Community 40 - "RevAction"
Cohesion: 0.09
Nodes (20): EndProject, FxMonthRate, MoveBalance, Actor, AsyncSession, {label: value} the user must have said., Foreign currencies whose live quote the run may need (fetched before the sync…, INR credited against one invoice, or one credit allocated oldest-first across… (+12 more)

### Community 41 - "2. Still to do (in priority order)"
Cohesion: 0.07
Nodes (29): 1.10 Commits, 1.1 Voice (hour-0 spike, then productionised), 1.2 Agent (OpenAI Agents SDK), 1.3 Trust boundary: propose → present → confirm → receipt, 1.4 Finance domain, 1.5 People ops (PLAN_v5), 1.6 API and infrastructure (local), 1.7 Web UI (`web/`, React 19 + Vite + TypeScript) (+21 more)

### Community 42 - "actions.py"
Cohesion: 0.20
Nodes (12): _apply(), _approve_bill_inputs(), _approve_claim_inputs(), ApproveBill, ApproveClaim, _bill_inputs(), _budget_effect(), Business writes, expressed as plan (preview, no side effects) + execute (inside… (+4 more)

### Community 43 - "Plan"
Cohesion: 0.13
Nodes (11): Execution, _message_inputs(), Plan, BudgetChange, CreateContract, _fmt(), Copilot rescan: replaces automated proposed/tagged rows, keeps manual findings…, RescanContract (+3 more)

### Community 44 - "briefing.py"
Cohesion: 0.19
Nodes (23): _admin(), build(), _ceo(), _common(), _employee(), _greeting(), _hm(), _important_mail() (+15 more)

### Community 45 - "test_meetings.py"
Cohesion: 0.07
Nodes (59): Meeting, A calendar event with a Google Meet link. Queued inside the confirm…, _meeting_inputs(), ScheduleMeeting, _access_token(), CalendarError, create_event(), dispatch() (+51 more)

### Community 46 - "services/budget_months.py"
Cohesion: 0.06
Nodes (77): bm_round(), forecast_budget(), get_budget_alerts(), get_budget_history(), get_budget_month(), get_budget_recommendations(), get_budget_year(), MonthSplit (+69 more)

### Community 47 - "projection.py"
Cohesion: 0.07
Nodes (33): by_weights(), even_split(), Divide `total_paise` into `n` parts that sum exactly to it (remainder on the…, Annual -> monthly budget distribution (PRD §3). Integer paise only; no paise is…, Keep the `locked` month indices as given and spread `total_paise - sum(locked)`…, Split `total_paise` in proportion to `weights` (exact fractions, no floats).…, Growing shares: the first month weighs 1 and each next month weighs the one…, The paise each of `months` gets out of `total_paise` (same order, summing to… (+25 more)

### Community 48 - "Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST)"
Cohesion: 0.50
Nodes (3): Added capabilities (same agent, same propose → confirm → receipt engine), Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST), Rules

### Community 53 - "main.py"
Cohesion: 0.08
Nodes (54): agent_text(), audit_feed(), budget_line_months(), cancel_button(), confirm_button(), contract_clause_context(), contract_deadlines_view(), contract_liabilities() (+46 more)

### Community 54 - "fx_months.py"
Cohesion: 0.14
Nodes (23): fy_of(), Affected, apply(), carried_months(), Change, effective(), foreign(), history() (+15 more)

### Community 55 - "run"
Cohesion: 0.08
Nodes (68): figures(), mk_client(), mk_inr(), Rs 10,000 Oct with Rs 4,000 in; move Rs 6,000 to Nov: moved_paise 600000, Oct…, Rs 10,000 a month, 3-month period from Oct, combined/advance: Rs 30,000 in Oct…, Run fn(ss, rv) on a sync session inside one committed transaction; return what…, run(), rv_of() (+60 more)

### Community 56 - "test_revenue_core.py"
Cohesion: 0.10
Nodes (36): pinned(), priya(), propose_confirm(), fixture, Revenue core: money maths, invoice lifecycle, allocation, reporting figures,…, Revenue clients are customer Parties in the same workspace table (no separate…, Approver with no conversation: grounding is skipped (the on-screen form path)., row() (+28 more)

### Community 57 - "cycles.py"
Cohesion: 0.10
Nodes (46): ClientCycle, A client's billing cycle from a month on: monthly charge, every N months,…, active(), apply(), ChangePlan, check(), _clashes(), combined() (+38 more)

### Community 58 - "models.py"
Cohesion: 0.07
Nodes (64): briefing(), budget_alerts(), claim_review(), DraftIn, _inr(), _line_names(), list_bills(), list_budget_lines() (+56 more)

### Community 59 - "session_scope"
Cohesion: 0.05
Nodes (78): draft_message(), mark_read(), prepare_approval(), post, Prepare a send_message proposal from the mail composer. Nothing is sent until…, PREPARE_APPROVAL from the UI: builds the same 'approve' proposal the agent…, One transaction; commits on success, rolls back on any exception., session_scope() (+70 more)

### Community 60 - "tools/contracts.py"
Cohesion: 0.13
Nodes (26): contract_deadlines(), list_liabilities(), propose_contract_details(), propose_contract_status(), propose_create_contract(), propose_rescan_contract(), propose_review_contract_finding(), Ctx (+18 more)

### Community 61 - "test_contracts.py"
Cohesion: 0.07
Nodes (57): _attention(), _a_flag(), analyse(), by_type(), contract_by_ref(), deadlines_of(), dl(), findings_of() (+49 more)

### Community 62 - "test_roles_rbac.py"
Cohesion: 0.09
Nodes (31): Contract review: read an agreement, find its clauses, identify liabilities (who…, _ctx(), exposed(), margs(), _pin(), fixture, parametrize, B1 RBAC matrix: employee / ceo / finance_approver / admin across tools,… (+23 more)

### Community 63 - "services/intake.py"
Cohesion: 0.16
Nodes (25): inspect_document(), Read an uploaded document (runs extraction the first time). Returns type,…, _view(), AsyncSession, record(), accept_upload(), breakdown_sum(), check_arithmetic() (+17 more)

### Community 64 - "Invoice"
Cohesion: 0.11
Nodes (54): Invoice, A customer invoice (revenue). Ported from the copilot Revenue module. Billing…, _date(), due_on(), An invoice is due on the last day of the period it covers., Allocation, BalancePlan, billed_paise() (+46 more)

### Community 65 - "cards.tsx"
Cohesion: 0.06
Nodes (43): AuditCard(), BudgetCard(), Deliveries(), fmt(), InboxCard(), LEAVE_NAME, LeaveCard(), LeaveRequestsCard() (+35 more)

### Community 66 - "ChartCard.tsx"
Cohesion: 0.15
Nodes (19): CATS, ChartCard(), compactInr(), DataTable(), fmtAxis(), fmtChange(), fmtFull(), fullInr() (+11 more)

### Community 67 - "Party"
Cohesion: 0.10
Nodes (55): Party, A dated in-app reminder ('remind me Friday to chase Acme'), optionally about a…, Reminder, normalize_name(), client(), clients(), create_client(), _currency() (+47 more)

### Community 68 - "agent/reading.py"
Cohesion: 0.16
Nodes (19): build_agent(), Cite, extract(), ExtractedDocument, LineItem, Agent, BaseModel, ExtractorAgent: reads document page images into a typed schema. It has NO… (+11 more)

### Community 69 - "_propose"
Cohesion: 0.10
Nodes (48): Convert DomainError into a structured result the agent can explain; log name,…, safe_tool(), _propose(), add_reminder(), complete_reminder(), get_client(), get_fx_rates(), get_invoice() (+40 more)

### Community 70 - "client_by"
Cohesion: 0.11
Nodes (30): client_by(), _end(), invs_of(), test_change_cycle_keeps_raised_and_paid_and_skips_their_months(), go(), go(), test_change_cycle_replaces_later_rules_and_updates_client_currency(), go() (+22 more)

### Community 71 - "tools/proposals.py"
Cohesion: 0.14
Nodes (24): cancel_pending_proposal(), _confirm(), confirm_pending_proposal(), get_pending_proposal(), _proposal_view(), propose_approval(), propose_settlement(), propose_submit_bill() (+16 more)

### Community 72 - "metadata.py"
Cohesion: 0.15
Nodes (29): add_months(), _clean(), _client(), dates(), Detail, Details, _effective(), end_of_term() (+21 more)

### Community 75 - "_fmt_date"
Cohesion: 0.24
Nodes (5): ApplyLeave, DecideLeave, _fmt_date(), _leave_decision_inputs(), date

### Community 76 - "test_ledger_extra.py"
Cohesion: 0.12
Nodes (50): AuditEvent, BudgetMovement, Proposal, Append-only. Balance of each bucket = SUM(amount_paise)., Full settlement only (weekend scope). One per record, enforced by the unique…, Receipt, Settlement, cancel() (+42 more)

### Community 77 - "_log"
Cohesion: 0.14
Nodes (27): check(), Fail loudly if a spec names a tool that does not exist, uses an engine-only…, RegistryError, workflows(), Outcome, Code check of the checklist outcome from what actually happened (tool log,…, verify(), RuntimeError (+19 more)

### Community 78 - "DomainError"
Cohesion: 0.08
Nodes (38): go(), DomainError, AddInvoices, _ccy(), _clean_num(), ClientChange, DeleteDraft, EditInvoice (+30 more)

### Community 79 - "scan.py"
Cohesion: 0.10
Nodes (33): The shipped clause catalogue: copilot `ctr_0001_contracts.py` CLAUSE_TYPES,…, A clause type as the scan sees it., Rule, rules(), _ask(), locate(), ModelFlag, ModelFlags (+25 more)

### Community 80 - "test_revenue_fx_cycles.py"
Cohesion: 0.11
Nodes (42): FxMonth, A conversion rate set by hand for a currency and month; carries forward until…, inv_of(), pinned(), priya(), propose_confirm(), fixture, Revenue gate 2: FX pricing and month rates, billing cycles, balance transfers,… (+34 more)

### Community 81 - "code_of"
Cohesion: 0.12
Nodes (12): code_of(), test_apply_rejects_reprice_ids_not_in_preview(), other_ccy(), paid(), part(), test_balance_delete_requires_unraised_destination(), go(), test_ending_an_ended_client_is_same_state() (+4 more)

### Community 82 - "test_suggest_email_voice.py"
Cohesion: 0.10
Nodes (31): session_config(), test_wake_opener_is_english(), _call(), _ctx(), _execute(), _items(), _plan(), parametrize (+23 more)

### Community 83 - "set_quote"
Cohesion: 0.11
Nodes (19): FxQuote, Cached ECB reference quotes (Frankfurter): INR per unit x 10^6, by publication…, AsyncSession, Fetch and cache the latest quote for each foreign ECB currency. Returns…, refresh(), Upsert the cached ECB quote for (ccy, day) with fetched_at = now - age., set_quote(), test_latest_flags_stale_after_a_day() (+11 more)

### Community 84 - "finance.py"
Cohesion: 0.13
Nodes (28): explain_budget_change(), get_attention_items(), get_audit_history(), get_briefing(), get_budget_status(), list_budget_categories(), _pos_view(), function_tool (+20 more)

### Community 85 - "recommend.py"
Cohesion: 0.15
Nodes (18): ClosedMonth, plan(), slots(), PlannedChange, `closed_chrono`: the category's closed months, oldest first (any number)., Trend recommendations: if a category has over- (or under-) run its budget for…, One budget change that acts on the recommendations, for one month (amounts in…, Act on the recommendations for one month, moving money before adding any: each… (+10 more)

### Community 86 - "revenue/money.py"
Cohesion: 0.08
Nodes (34): currencies_in(), digits(), from_minor(), _indian(), numbers_in(), paise_str(), paise_to(), Decimal (+26 more)

### Community 87 - "test_charts.py"
Cohesion: 0.14
Nodes (23): Look a value up in the stored rows (never a new query), so speech matches what…, read_value(), match(), build(), client_for(), err(), err_sync(), priya_arjun() (+15 more)

### Community 88 - "review.py"
Cohesion: 0.15
Nodes (20): analyse(), can_decide(), can_view(), clean_name(), ensure(), guess_title(), guess_type(), our_names() (+12 more)

### Community 89 - "classify"
Cohesion: 0.07
Nodes (34): Affirmation, classify(), _contains_affirm(), _normalize(), Deterministic classifier for a confirmation utterance (English, Hindi,…, StrEnum, bridge(), _Conn (+26 more)

### Community 90 - "liability.py"
Cohesion: 0.08
Nodes (37): Deadlines follow the contract's current expiry and its auto-renewal notice…, recompute_deadlines(), as_dict(), assess(), _bearer_term(), _beneficiary(), Deadline, deadlines() (+29 more)

### Community 91 - "store.py"
Cohesion: 0.15
Nodes (37): get_contract(), One contract by ref (AG3), title or counterparty: liabilities with who bears…, Contract, ContractDeadline, ContractFinding, One agreement. Text is the extracted reading of the original document (kept in…, A clause found in a contract (copilot ctr_clause) plus Purser's liability…, A dated obligation computed by code from the contract (expiry, renewal notice,… (+29 more)

### Community 92 - "pacing.py"
Cohesion: 0.24
Nodes (9): compute(), days_in_month(), Pacing, date, The pacing / burn-velocity engine and the proactive alert levels (PRD §4). Pure…, `day` is the current day of the month (1..total_days); use total_days for a…, _round2(), test_pacing_approaching_and_limit() (+1 more)

### Community 93 - "client_for"
Cohesion: 0.06
Nodes (53): client_for(), _pdf(), parametrize, HTTP layer + intake gates that need no model: auth, CSRF, upload outcomes,…, test_arithmetic_check(), test_button_confirm_and_replay(), test_employee_cannot_open_other_users_document(), test_exact_replay_returns_existing_document() (+45 more)

### Community 94 - "part_paid_zed"
Cohesion: 0.09
Nodes (30): go(), _aug_ecb(), mk_client(), mk_invoice(), part_paid_zed(), Guide example: Rs 10,000 invoice, Rs 4,000 received, part paid., test_balance_delete_destination_restores_source_to_part_paid(), go() (+22 more)

### Community 95 - "reads.py"
Cohesion: 0.10
Nodes (33): bucket_label(), fy_months(), fy_start(), month_label(), period_label(), period_months(), quarter_of(), Ported from copilot clients_mod/fiscal.py (user's own code), unchanged except… (+25 more)

### Community 96 - "ClaimReview.tsx"
Cohesion: 0.09
Nodes (25): react-dom, dur, ease, easeInOut, palette, cardKey(), CardView(), ArtifactPanel() (+17 more)

### Community 98 - "day"
Cohesion: 0.08
Nodes (49): checkout_link(), Where the traveller pays for THIS flight: the airline's own checkout via Google…, google_hotels_url(), _norm(), date, Hotel search: SerpAPI Google Hotels (real rates, the hotel's own website for…, _safe_link(), _sample() (+41 more)

### Community 99 - "test_trips.py"
Cohesion: 0.16
Nodes (44): GoogleOp, HotelBooking, Outbox for confirmed Gmail / Google Calendar changes on the linked account.…, A hotel stay approved in Purser. Payment happens on the hotel's own website…, pin(), Replace get_settings everywhere it was imported by name, so one patched…, book_trip(), fake_checkout() (+36 more)

### Community 100 - "live_bridge.py"
Cohesion: 0.12
Nodes (14): In-process event fan-out to the browser (SSE), keyed by conversation. One…, subscribe(), unsubscribe(), upload(), bridge_for(), client(), LiveBridge, GPT-Live sideband bridge: server-observed transcripts -> voice_turns;… (+6 more)

### Community 102 - "booking.py"
Cohesion: 0.15
Nodes (20): One stored result feeds chart, table and speech., ResultSnapshot, BookFlight, BookTrip, _city(), _execute(), _flight_args(), flight_lines() (+12 more)

### Community 103 - "google_actions.py"
Cohesion: 0.20
Nodes (11): CancelEvent, _emails(), _local(), MailAction, datetime, _queue(), Confirmed changes on the linked Google account: send/reply email, inbox…, _require_google() (+3 more)

### Community 104 - "test_custom_workflows.py"
Cohesion: 0.06
Nodes (50): fast_match(), run my month-end check' -> that routine, without a model call. Needs a run verb…, The user's saved routines (and shared ones): tapping one runs it. Empty -> one…, _routines(), _body(), _ceo_client(), _clear_briefing(), _customs() (+42 more)

### Community 105 - "code_of"
Cohesion: 0.20
Nodes (10): ExceptionInfo, code_of(), test_create_cap_and_duplicate_months(), go(), test_duplicate_client_name_and_archive_restore(), go(), test_invoice_ref_from_other_workspace_is_not_found(), go() (+2 more)

### Community 106 - "test_people_extra.py"
Cohesion: 0.08
Nodes (72): Conversation, LeaveRequest, Message, Inbox item and/or email outbox row. Email rows are delivered after the…, dispatch(), Send queued emails. Each row is claimed with SKIP LOCKED so concurrent…, actor_by_email(), propose_and_confirm() (+64 more)

### Community 107 - "usePurser"
Cohesion: 0.12
Nodes (28): lucide-react, reveal, useFx(), ToastManager(), useLoad(), usePurser(), FOLDERS, GmailPane() (+20 more)

### Community 108 - "custom.py"
Cohesion: 0.11
Nodes (32): catalogue(), check_unique(), Checked, _clean(), collisions(), _compile_once(), compile_routine(), _core_words() (+24 more)

### Community 109 - "workflows.py"
Cohesion: 0.24
Nodes (12): delete_routine(), draft_routine(), DraftIn, list_routines(), Actor, BaseModel, get, post (+4 more)

### Community 110 - "purser.md"
Cohesion: 0.12
Nodes (16): Charts and views, Contracts and liabilities, Facts, Language, Mail and calendar, Monthly budget, alerts, changes and month close, Next step, Other requests (+8 more)

### Community 111 - "get_settings"
Cohesion: 0.08
Nodes (24): The one login whose real Gmail and Google Calendar Purser may use…, get_settings(), meetings(), datetime, The user's meetings for a time window: real Google Calendar for the linked…, Returns (events, source). Google errors propagate (callers decide whether to…, enabled(), LLMUnavailable (+16 more)

### Community 112 - "Diwan: the voice-first back office for Indian SMBs"
Cohesion: 0.17
Nodes (11): 10. Beyond the weekend, 1. The problem, 2. The solution, 3. Why AI, and what the AI actually does, 4. The trust boundary: propose → present → confirm → receipt, 5. Architecture, 6. What is already built (Saturday, 21 Nov), 7. Plan to the Sunday 14:00 freeze (+3 more)

### Community 113 - "test_grounding_and_workflow_memory.py"
Cohesion: 0.11
Nodes (33): Keep the latest flight / hotel search (its id and options) across turns, so…, _remember_searches(), _normal(), numbers_spoken(), Actor, AsyncSession, A model never supplies a booked amount or rate on its own: the number must…, The user's last few server-observed turns in this conversation, newest last.… (+25 more)

### Community 114 - "make_contract_samples.py"
Cohesion: 0.25
Nodes (9): docx(), main(), _pdf_escape(), Write the synthetic agreements in seed/contract_samples.py as files under…, A real PDF with a text layer: wrapped lines, 50 per page, Helvetica 10pt on A4., Page images only (no text layer), like a scanned agreement., scanned_pdf(), text_pdf() (+1 more)

### Community 115 - "store.tsx"
Cohesion: 0.08
Nodes (33): react, three, Me, setSession(), App(), Login(), PurserComposer(), Props (+25 more)

### Community 116 - "build"
Cohesion: 0.18
Nodes (19): active(), key_ym(), period_end(), period_text(), raise_on(), "Oct'26 to Dec'26" for an invoice of a several-month period, else ''., The last month of the period an invoice belongs to (its own month when it has…, When an unraised invoice should go out: the day set on it (a balance dated… (+11 more)

### Community 117 - "contract_actions.py"
Cohesion: 0.29
Nodes (8): _details_inputs(), _finding_inputs(), _iso(), Contract writes as propose -> present -> confirm -> receipt actions (the same…, ReviewFinding, _staged(), _type(), require_decide()

### Community 118 - "test_b25_clarify.py"
Cohesion: 0.11
Nodes (36): ask_choice(), bump(), Choice, current(), BaseModel, function_tool, safe_tool, MCQ clarifications: one tappable question at a time, at most three per topic,… (+28 more)

### Community 119 - "PurserContext"
Cohesion: 0.22
Nodes (9): PurserContext, Passed to every tool via RunContextWrapper. Identity comes only from here,…, fake_esc(), test_tool_list_custom_workflows_returns_own_and_shared(), test_tool_propose_delete_unknown_routine_is_not_found(), fake_esc(), fake_run(), test_run_turn_dispatches_to_engine_when_flag_on() (+1 more)

### Community 120 - "tools/charts.py"
Cohesion: 0.20
Nodes (17): build_chart(), _card(), describe_chart_options(), present_view(), function_tool, safe_tool, Chart and view tools. The model composes typed specs; every number comes from a…, What can be charted for this user: sources, measures (with units), dimensions,… (+9 more)

### Community 121 - "Deployment (AWS, us-west-2)"
Cohesion: 0.22
Nodes (9): Architecture, Deployment (AWS, us-west-2), Email and Google Meet, First deploy, Notes, Redeploy (new code), Rollback, Teardown (+1 more)

### Community 122 - "test_b25_travel.py"
Cohesion: 0.13
Nodes (33): FlightBooking, A SIMULATED flight booking: no ticket is bought. Real fare data from the search…, day(), do_search(), fake_search(), isolate(), one(), date (+25 more)

### Community 124 - "db.py"
Cohesion: 0.09
Nodes (36): Base, configure(), engine(), AsyncSession, sessionmaker(), async_sessionmaker, AsyncEngine, DeclarativeBase (+28 more)

### Community 125 - "Actor"
Cohesion: 0.06
Nodes (54): Actor, The authenticated principal. Always derived from the server session, never from…, Finance approval rights., May SEE budget, revenue, payables, receivables and company-wide records (not…, May not make any change at all (no proposals, no direct writes)., HR/admin rights: onboarding, company-wide announcements, all leave., get_record(), Details of a claim (C…) or bill (B…): parties, amount, state, settlement,… (+46 more)

### Community 126 - "tools/travel.py"
Cohesion: 0.11
Nodes (29): get_my_location(), _here(), list_my_flights(), propose_flight_booking(), propose_trip_booking(), function_tool, safe_tool, Travel tools: where the user is, live flight search, and a (simulated) booking… (+21 more)

### Community 129 - "search"
Cohesion: 0.11
Nodes (25): FlightSearchError, google_flights_url(), _hhmm(), _norm_option(), date, Exception, Flight search: SerpAPI Google Flights (real fares) with a 30-minute cache; on…, Deterministic SAMPLE fares when live search is unavailable. Always labelled… (+17 more)

### Community 130 - "google.py"
Cohesion: 0.14
Nodes (27): _g(), list_meetings(), _need_google(), propose_cancel_meeting(), propose_email(), propose_mail_action(), propose_reschedule_meeting(), datetime (+19 more)

### Community 133 - "Found"
Cohesion: 0.27
Nodes (10): carve_outs_rules(), Sentences that take matters out of a cap: in the cap's own clause, or a clause…, _sentences(), _dedup(), Found, _join(), One finding per type for overlapping spans (the surer one)., One finding for a clause read as two pieces (split across a page or paragraph). (+2 more)

### Community 134 - "spec"
Cohesion: 0.24
Nodes (16): apply_patch(), chart_problem(), ChartSpecPatch, A revision. Anything omitted keeps its current value, so grouping survives…, Why the requested chart type does not fit the spec's shape, or None., spec(), test_add_filters_replaces_and_clear_filters(), test_month_to_customer_with_line_falls_back_to_auto() (+8 more)

### Community 135 - "Purser · the back office you can talk to"
Cohesion: 0.11
Nodes (19): 🎬 Act 1: a Tuesday without Purser, 🌅 Act 2: the same Tuesday with Purser, 🧩 Act 3: what's in the box (core features), 🥊 Act 6: the market and where Purser fits, 🧱 Act 7½: built not to break, 🏗️ Act 7: how it is built (AWS), 🎥 Act 8: live demo (about 6 minutes), 🧾 Act 9: honesty and limits (+11 more)

### Community 136 - "api.ts"
Cohesion: 0.19
Nodes (10): motion, ApiError, call(), Card, headers(), inr(), uploadWithProgress(), withTimeout() (+2 more)

### Community 138 - "call"
Cohesion: 0.18
Nodes (19): _label_id(), perform(), call(), error_text(), Response, create_simple(), delete_event(), get_event() (+11 more)

### Community 140 - "Read"
Cohesion: 0.29
Nodes (7): docx_text(), _layer(), meaningful(), A contract file -> its plain text. Text layer first (deterministic), the vision…, Paragraphs of a .docx in order (table cells are paragraphs too)., Read, _render()

### Community 149 - "runner.py"
Cohesion: 0.14
Nodes (19): Agent, build_agent(), instructions(), _instructions(), PurserContext, The Purser agent. `tools` narrows the tool set and `brief` appends context…, _mark_presented(), memory() (+11 more)

### Community 151 - "PurserSidebar.tsx"
Cohesion: 0.11
Nodes (21): spring, ACTION_WORDS, ago(), humanize(), NavDef, Note, Notifications(), Profile() (+13 more)

### Community 152 - "env.py"
Cohesion: 0.27
Nodes (9): Connection, do_run_migrations(), include_object(), Run migrations in 'offline' mode. This configures the context with just a URL…, In this scenario we need to create an Engine and associate a connection with…, Run migrations in 'online' mode., run_async_migrations(), run_migrations_offline() (+1 more)

### Community 153 - "services/people.py"
Cohesion: 0.09
Nodes (46): find_people(), get_leave_balance(), get_onboarding_status(), list_leave_requests(), lookup_policy(), _person(), propose_leave(), propose_leave_decision() (+38 more)

### Community 155 - "test_perform_each_kind"
Cohesion: 0.18
Nodes (5): test_perform_each_kind(), create(), modify(), op(), test_perform_label_reuses_existing_or_creates()

### Community 157 - "FlightCard.tsx"
Cohesion: 0.25
Nodes (10): dur(), FlightOptionsCard(), Hotel, HotelOptionsCard(), inr(), openPayment(), Opt, Pay (+2 more)

### Community 158 - "_text"
Cohesion: 0.31
Nodes (9): _decode(), Prefer text/plain; fall back to text/html with tags removed., _text(), walk(), b64(), test_text_nested_parts_and_empty(), test_text_prefers_plain_over_html(), test_text_strips_html_script_style_and_unescapes() (+1 more)

### Community 159 - "post_move"
Cohesion: 0.44
Nodes (9): flows(), lines_by_cat(), post_move(), test_budget_flows_conservation_and_directions(), test_budget_flows_does_not_change_budget_source_and_is_workspace_scoped(), test_budget_flows_empty_on_fresh_seed(), test_budget_flows_multi_month_transfer_pairs_per_month(), test_budget_flows_other_dimensions_and_filters() (+1 more)

### Community 160 - "Production readiness: what happens when things go wrong"
Cohesion: 0.25
Nodes (8): 1. Failure modes and how each one is handled, 2. How we know it holds, 3. Recovery, 4. Known gaps (sized for a hackathon demo, not yet for production), Deployment and infrastructure, External services and slow paths, Money and data integrity, Production readiness: what happens when things go wrong

### Community 162 - "options"
Cohesion: 0.29
Nodes (7): options(), Registry as the model sees it, limited to what this actor may chart., BUG candidate: options() maps every non-paise unit to 'count', so the model is…, test_options_by_role(), test_options_lists_new_chart_types_and_rules(), test_options_reports_pct_unit_distinctly(), test_chart_options_hide_finance_sources_for_employee()

### Community 163 - "Checklist workflows vs a single agent: evaluation results"
Cohesion: 0.12
Nodes (17): 10. Reliability and safety design (why 0 wrong writes is structural, not lucky), 11. Limitations (read before quoting numbers), 12. Conclusion, 1. Summary, 2.1 The three arms, 2.2 The scenario set: 46 conversations, 90 turns, four levels of difficulty, 2.3 What each turn is checked for, 2. What was compared (+9 more)

### Community 165 - "_cycle_client"
Cohesion: 0.29
Nodes (7): _cycle_client(), test_guide_arrears_books_in_december_and_raises_at_period_end(), go(), test_guide_monthly_mode_emits_three_rows_sharing_the_period(), go(), test_guide_quarterly_advance_combined_books_30000_in_october_due_31_dec(), go()

### Community 170 - "AssignTask"
Cohesion: 0.33
Nodes (3): AssignTask, RaiseTicket, _support_team()

### Community 172 - "Demo script: working end to end on fresh input"
Cohesion: 0.14
Nodes (14): 0:00 Login and briefing, 0:30 ⭐ Fresh receipt → approved claim, 1:30 ⭐ A chart you talk to, 2:15 ✈️ Spotlight: trip in two sentences, 3:15 📜 Spotlight: contract liability radar, 4:15 🔁 Spotlight: teach Purser a routine, 4-minute cut, 5:00 🛡️ Try to break it (+6 more)

### Community 173 - "gmail.py"
Cohesion: 0.20
Nodes (15): addresses(), build_raw(), create_draft(), get_thread(), _hdr(), Gmail for the linked account. Message bodies are UNTRUSTED data: stripped to…, Recipient, subject and threading headers for a reply to the latest message in a…, reply_context() (+7 more)

### Community 181 - "Settings"
Cohesion: 0.17
Nodes (4): Settings, BaseSettings, field_validator, test_settings_strip_google_values()

### Community 182 - "test_tool_propose_custom_workflow_makes_save_proposal"
Cohesion: 0.12
Nodes (10): fake_pick(), test_compile_routine_collision_adds_warning(), test_compile_routine_gives_up_after_one_repair(), test_compile_routine_repairs_once_then_succeeds(), test_rest_draft_returns_draft_and_saves_nothing(), fake_compile(), test_tool_propose_custom_workflow_makes_save_proposal(), Uses the real _escalate logging path with only the model call faked. (+2 more)

### Community 192 - "_pick"
Cohesion: 0.33
Nodes (5): _pick(), Rule order decides; the fast model may re-pick among the top candidates and…, A key is present but the model call blows up: fall back to the top rule…, test_next_action_none_when_nothing_to_do(), test_pick_survives_model_failure()

### Community 193 - "services/custom_workflows.py"
Cohesion: 0.19
Nodes (15): CustomWorkflow, A routine a user described in their own words, compiled into the same shape as…, forget(), _check(), _custom(), delete(), DeleteCustomWorkflow, _forget() (+7 more)

### Community 195 - "_claim_inputs"
Cohesion: 0.17
Nodes (9): Any, Action, Approve, _claim_inputs(), Actor, Dispatch approval by record ref prefix (C = claim, B = bill)., SubmitClaim, AsyncSession (+1 more)

### Community 196 - "fmt_value"
Cohesion: 0.50
Nodes (4): fmt_value(), public(), The card payload: numbers as integers plus display strings computed here, not…, test_fmt_value_pct()

### Community 202 - "1. Accuracy and cost compared with a baseline"
Cohesion: 0.18
Nodes (11): 1. Accuracy and cost compared with a baseline, 2. Engineering checks (automated tests), 3. Outputs on new data, 4. Proof that data persists, Evidence of results, Head-to-head on the same code and scenarios (run 3, `evals/reports/run3-20261122/`), How a judge can verify persistence live (2 minutes), Limitations (please read before quoting) (+3 more)

### Community 203 - "test_paused_and_ended_clients_get_no_billing_suggestions"
Cohesion: 0.60
Nodes (5): test_paused_and_ended_clients_get_no_billing_suggestions(), end(), kinds(), nw_before(), resume()

### Community 204 - "google_oauth.py"
Cohesion: 0.33
Nodes (7): Path, _client(), _env(), main(), One-time Google login for the linked account (Gmail + Calendar): gets a refresh…, _set_env(), _wait_for_code()

### Community 207 - "_frankfurter"
Cohesion: 0.67
Nodes (3): _frankfurter(), Decimal, AsyncClient

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

### Community 221 - "Honest note: built, reused, simulated"
Cohesion: 0.33
Nodes (6): Data permissions, Honest note: built, reused, simulated, Known limits, What is simulated, What we built at the event, What we reused

### Community 222 - "🛡️ Act 4: the novelty. Why Purser is not "a chatbot on top of Zoho""
Cohesion: 0.33
Nodes (6): 🛡️ Act 4: the novelty. Why Purser is not "a chatbot on top of Zoho", Novelty 1: propose → present → confirm → receipt, Novelty 2: numbers come from SQL, never from the model, Novelty 3: checklist workflows (our engineering-depth bet), Novelty 4: voice-native and Indian-language-native, Novelty 5: the UI is composed by the agent

### Community 232 - "test_workflows_fixes.py"
Cohesion: 0.16
Nodes (19): _pure_no(), _menu(), parametrize, Gate for the workflow-engine fixes: Hinglish affirmations, _pure_no, bare-yes…, _suggestions(), test_asked_outcome_has_no_chips(), run(), test_ceo_gets_read_workflows_not_writes() (+11 more)

### Community 236 - "Purser: the back office you can talk to, and trust with money"
Cohesion: 0.22
Nodes (9): 1. The real-world problem, 2. What is new here (each item links to code), 3. Requirement → proof, 4. Headline numbers (46 conversations, 90 turns, EN / Hinglish / Hindi), 5. Verify it yourself in 2 minutes, 6. Scale built at the event, Purser: the back office you can talk to, and trust with money, Repository map (+1 more)

## Knowledge Gaps
- **373 isolated node(s):** `Pre-flight (2 minutes before going on stage)`, `0:00 Login and briefing`, `0:30 ⭐ Fresh receipt → approved claim`, `1:30 ⭐ A chart you talk to`, `2:15 ✈️ Spotlight: trip in two sentences` (+368 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1315 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **82 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `session_scope()` connect `session_scope` to `make_actor`, `test_intake_extra.py`, `test_b25_briefing.py`, `User`, `spec`, `test_budget_months.py`, `run`, `test_b25_google.py`, `app/auth.py`, `purser.py`, `test_charts_v2.py`, `runner.py`, `run`, `services/people.py`, `post_move`, `test_workflows_engine.py`, `briefing.py`, `test_meetings.py`, `services/budget_months.py`, `main.py`, `test_tool_propose_custom_workflow_makes_save_proposal`, `run`, `test_revenue_core.py`, `models.py`, `tools/contracts.py`, `test_contracts.py`, `test_roles_rbac.py`, `services/intake.py`, `agent/reading.py`, `_propose`, `tools/proposals.py`, `test_ledger_extra.py`, `test_revenue_fx_cycles.py`, `test_suggest_email_voice.py`, `set_quote`, `finance.py`, `test_charts.py`, `review.py`, `store.py`, `client_for`, `day`, `test_trips.py`, `live_bridge.py`, `booking.py`, `test_custom_workflows.py`, `code_of`, `test_people_extra.py`, `custom.py`, `workflows.py`, `get_settings`, `test_grounding_and_workflow_memory.py`, `test_b25_clarify.py`, `tools/charts.py`, `test_b25_travel.py`, `db.py`, `Actor`, `tools/travel.py`?**
  _High betweenness centrality (0.102) - this node is a cross-community bridge._
- **Why does `make_actor()` connect `make_actor` to `test_intake_extra.py`, `test_b25_briefing.py`, `User`, `spec`, `test_budget_months.py`, `run`, `test_b25_google.py`, `services/charts.py`, `test_charts_v2.py`, `registry.py`, `runner.py`, `post_move`, `options`, `test_workflows_engine.py`, `briefing.py`, `test_meetings.py`, `test_tool_propose_custom_workflow_makes_save_proposal`, `test_revenue_core.py`, `session_scope`, `test_contracts.py`, `test_roles_rbac.py`, `test_ledger_extra.py`, `test_revenue_fx_cycles.py`, `test_suggest_email_voice.py`, `test_charts.py`, `store.py`, `client_for`, `day`, `test_trips.py`, `booking.py`, `test_custom_workflows.py`, `test_workflows_fixes.py`, `test_people_extra.py`, `custom.py`, `test_b25_clarify.py`, `PurserContext`, `test_b25_travel.py`, `Actor`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Why does `Actor` connect `Actor` to `make_actor`, `test_intake_extra.py`, `User`, `test_b25_google.py`, `services/charts.py`, `app/auth.py`, `services/people.py`, `options`, `AssignTask`, `services/budget_months.py`, `models.py`, `session_scope`, `test_roles_rbac.py`, `services/intake.py`, `tools/proposals.py`, `test_ledger_extra.py`, `review.py`, `store.py`, `live_bridge.py`, `test_people_extra.py`, `get_settings`, `contract_actions.py`, `tools/charts.py`, `db.py`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Are the 90 inferred relationships involving `Actor` (e.g. with `briefing()` and `budget_alerts()`) actually correct?**
  _`Actor` has 90 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `DomainError` (e.g. with `test_beneficiary_cannot_self_approve()` and `test_cross_workspace_object_ids_not_found()`) actually correct?**
  _`DomainError` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Pre-flight (2 minutes before going on stage)`, `0:00 Login and briefing`, `0:30 ⭐ Fresh receipt → approved claim` to the rest of the system?**
  _373 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Phase 3: AWS Deployment and CI/CD` be split into smaller, more focused modules?**
  _Cohesion score 0.06827880512091039 - nodes in this community are weakly interconnected._