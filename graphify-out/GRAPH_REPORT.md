# Graph Report - Builders  (2026-11-21)

## Corpus Check
- 203 files · ~231,212 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 5, .example 2, .ini 1)

## Summary
- 3858 nodes · 12168 edges · 202 communities (126 shown, 76 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 1220 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3e57879b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Phase 3: AWS Deployment and CI/CD
- hygiene
- document
- test_intake_extra.py
- today_ist
- actions.py
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
- purser.py
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
- build
- models.py
- Meeting
- 2. Still to do (in priority order)
- finance.py
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
- tools/budget_months.py
- test_charts.py
- test_contracts.py
- test_roles_rbac.py
- services/intake.py
- Invoice
- cards.tsx
- ChartCard.tsx
- Party
- Extraction
- _propose
- client_by
- create_event
- metadata.py
- budgeting/__init__.py
- Settings
- propose_and_confirm
- confirmation.py
- revenue_actions.py
- scan.py
- inv_of
- Ctx
- test_suggest_email_voice.py
- test_revenue_fx_cycles.py
- services/people.py
- recommendations
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
- test_trips.py
- Message
- get_settings
- DomainError
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
- ._target
- safe_tool
- test_b25_clarify.py
- sugg
- User
- Deployment (AWS, us-west-2)
- call
- Conversation
- google_oauth.py
- errors.py
- travel.py
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
- contract_actions.py
- bills
- row
- date
- date
- date
- date
- date
- date
- MunshiContext
- dispatch
- db.py
- date
- PurserSidebar.tsx
- env.py
- tool_access.py
- test_paused_and_ended_clients_get_no_billing_suggestions
- test_perform_each_kind
- _cycle_client
- FlightCard.tsx
- post_move
- make_actor
- review.py
- options
- cal
- build_raw
- status.py
- Ctx
- Any
- isolate
- Request
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
- Response
- datetime
- xfail

## God Nodes (most connected - your core abstractions)
1. `make_actor()` - 436 edges
2. `session_scope()` - 431 edges
3. `Actor` - 182 edges
4. `DomainError` - 98 edges
5. `User` - 92 edges
6. `run()` - 92 edges
7. `Invoice` - 90 edges
8. `get_settings()` - 89 edges
9. `propose_and_confirm()` - 89 edges
10. `call()` - 88 edges

## Surprising Connections (you probably didn't know these)
- `gitleaks Secret Scanning` --semantically_similar_to--> `Secrets via Secrets Manager / SSM`  [INFERRED] [semantically similar]
  README.md → CLAUDE.md
- `test_demo_reset_is_idempotent()` --uses--> `Workspace`  [INFERRED]
  tests/test_demo_seed.py → app/models.py
- `_party_id()` --uses--> `Party`  [INFERRED]
  tests/test_intake_extra.py → app/models.py
- `test_bill_needs_a_vendor_and_prefers_existing_id()` --uses--> `Party`  [INFERRED]
  tests/test_intake_extra.py → app/models.py
- `test_new_vendor_bill_creates_vendor_only_on_confirm()` --uses--> `Party`  [INFERRED]
  tests/test_intake_extra.py → app/models.py

## Import Cycles
- 4-file cycle: `web/src/FlightCard.tsx -> web/src/components/assistant/PurserVoiceController.tsx -> web/src/state/store.tsx -> web/src/cards.tsx -> web/src/FlightCard.tsx`

## Hyperedges (group relationships)
- **Candidate AWS Hosting Runtimes** — claude_aws_app_runner, claude_aws_lambda_api_gateway, claude_aws_ecs_fargate, claude_s3_cloudfront [EXTRACTED 1.00]
- **Hackathon Delivery Phases 0-4** — claude_phase_0, claude_phase_1, claude_phase_2, claude_phase_3, claude_phase_4 [EXTRACTED 1.00]
- **Secure CI/CD Pipeline** — claude_github_actions, claude_github_oidc, claude_terraform, claude_least_privilege_iam, readme_ci_hygiene_checks [INFERRED 0.85]

## Communities (202 total, 76 thin omitted)

### Community 0 - "Phase 3: AWS Deployment and CI/CD"
Cohesion: 0.07
Nodes (38): Tiny Agent Evaluation Set, Agent Guardrails (step limits, budgets, timeouts, retries), AWS App Runner, AWS ECS Fargate, AWS Lambda + API Gateway, Change-Scope Rules, CLAUDE.md Hackathon Agent Rules, Cost Awareness (+30 more)

### Community 1 - "hygiene"
Cohesion: 0.08
Nodes (24): concurrency, cancel-in-progress, group, GITLEAKS_VERSION, env, name, runs-on, steps (+16 more)

### Community 2 - "document"
Cohesion: 0.13
Nodes (30): close_intake(), correct_extracted_field(), find_reservations(), inspect_document(), Ctx, function_tool, Intake tools: inspect an uploaded document, correct fields by voice, match…, Open budget reservations for an employee that this receipt could replace (e.g.… (+22 more)

### Community 3 - "test_intake_extra.py"
Cohesion: 0.09
Nodes (42): add_doc(), _approved_bill(), count(), F(), finance_counts(), _http_proposal(), _party_id(), _pdf() (+34 more)

### Community 4 - "today_ist"
Cohesion: 0.07
Nodes (53): _attention(), meetings(), datetime, The user's meetings for a time window: real Google Calendar for the linked…, Returns (events, source). Google errors propagate (callers decide whether to…, _admin(), build(), _ceo() (+45 more)

### Community 5 - "actions.py"
Cohesion: 0.07
Nodes (59): get_record(), Details of a claim (C…) or bill (B…): parties, amount, state, settlement,…, claim_review(), draft_message(), DraftIn, _inr(), _line_names(), list_bills() (+51 more)

### Community 6 - "PurserVoiceController.tsx"
Cohesion: 0.10
Nodes (18): setConversation(), ACCEPT, ACCEPT_ATTR, Assistant, AssistantContext, CONNECT_RETRIES, handsFreeOn(), PurserVoiceController() (+10 more)

### Community 7 - "test_budget_months.py"
Cohesion: 0.10
Nodes (35): allocated(), allocated_in(), cells(), change(), close(), close_oct(), code_of(), count_movements() (+27 more)

### Community 8 - "package.json"
Cohesion: 0.05
Nodes (37): echarts, @fontsource/dm-sans, @fontsource/geist-mono, @fontsource/noto-sans-devanagari, @fontsource/source-serif-4, @types/react, @types/react-dom, @types/three (+29 more)

### Community 9 - "events.py"
Cohesion: 0.40
Nodes (4): In-process event fan-out to the browser (SSE), keyed by conversation. One…, subscribe(), unsubscribe(), Queue

### Community 10 - "test_b25_google.py"
Cohesion: 0.10
Nodes (34): linked(), ops(), plan(), plan_err(), parametrize, B2 gate: Gmail/Calendar helpers, google_actions (queue/dispatch/perform),…, Token refresh failure surfaces as GoogleError, never leaks the secret., test_auth_call_maps_errors() (+26 more)

### Community 11 - "MUNSHI: Voice-only, agent-centric finance and operations copilot"
Cohesion: 0.08
Nodes (25): 0. Planning inputs and research status, 10. Contract liability analysis (re-implemented from the user's guide), 11. Bill and receipt extraction, 12. External integrations, 13. Data model (Postgres; money = BIGINT paise; timestamps UTC, IST display; FY Apr-Mar), 14. Repository layout (this repo, `~/Projects/Builders`), 15. AWS deployment and CI/CD, 16. Security and trust (+17 more)

### Community 12 - "services/charts.py"
Cohesion: 0.09
Nodes (45): BudgetLine, _ageing(), _bad(), _budget(), _budget_flows(), ChartType, _claims(), CompareMode (+37 more)

### Community 14 - "Munshi | Product and delivery plan v2"
Cohesion: 0.12
Nodes (16): 10. Data design and isolation, 11. Secondary workflows and integrations, 12. Implementation and deployment, 13. Build sequence and cut decisions, 14. Acceptance, evaluation and evidence, 15. Four-minute demonstration and handoff, 16. Definition of done, 1. User, problem and submission (+8 more)

### Community 15 - "server.py"
Cohesion: 0.17
Nodes (11): Bridge, create_session(), get_budget_status(), index(), BaseModel, function_tool, get, Request (+3 more)

### Community 16 - "purser.py"
Cohesion: 0.11
Nodes (22): Agent, PurserContext, Passed to every tool via RunContextWrapper. Identity comes only from here,…, build_agent(), _instructions(), RunContextWrapper, PurserAgent: one conversational agent with typed tools. Same agent for voice…, memory() (+14 more)

### Community 17 - "compilerOptions"
Cohesion: 0.13
Nodes (14): compilerOptions, isolatedModules, jsx, lib, module, moduleResolution, noEmit, noUnusedLocals (+6 more)

### Community 18 - "test_charts_v2.py"
Cohesion: 0.08
Nodes (56): run(), sql(), test_bills_totals_match_sql(), test_budget_by_category_matches_movements(), test_date_range_filter_matches_sql(), test_injection_strings_just_fail_to_match(), test_overdue_total_and_filters_match_sql(), test_receivables_totals_and_rows_match_sql() (+48 more)

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
Cohesion: 0.07
Nodes (31): Guide: changing a month clears later explicit settings in the affected span…, fn(ss, rv) on a sync session in one committed transaction; return plain data., run(), rv_of(), test_carried_months_runs_to_march_not_beyond(), test_cycle_active_and_current_rules(), go(), test_fx_cached_returns_micro_or_none() (+23 more)

### Community 24 - "5. Financial record lifecycles"
Cohesion: 0.40
Nodes (5): 5. Financial record lifecycles, Budgets, reservations and spend, Employee claims and reimbursements, Revenue, invoicing and collections, Vendor bills and approvals

### Community 25 - "Purser architecture decisions"
Cohesion: 0.50
Nodes (3): Evidence (local spike, `spikes/voice_spike`, synthetic fixture), Purser architecture decisions, Voice transport and confirmation (H0 gate, 2026-11-21) — DECIDED

### Community 38 - "build"
Cohesion: 0.16
Nodes (20): active(), cached(), _frankfurter(), latest(), _newest(), Decimal, Exception, Session (+12 more)

### Community 39 - "models.py"
Cohesion: 0.11
Nodes (31): CompanyPayment, InvoicePayment, OnboardingTask, Policy, SQLAlchemy models. Money is integer paise; timestamps are UTC; business dates…, INR actually credited against a customer invoice (copilot `cli_receipt`)., Server-observed user utterances. The only evidence a spoken confirmation can…, Helpdesk request (IT / admin / facilities) raised by an employee; resolved by… (+23 more)

### Community 40 - "Meeting"
Cohesion: 0.12
Nodes (19): Meeting, A calendar event with a Google Meet link. Queued inside the confirm…, ScheduleMeeting, _access_token(), CalendarError, _google_error(), is_future(), _meet_url() (+11 more)

### Community 41 - "2. Still to do (in priority order)"
Cohesion: 0.07
Nodes (29): 1.10 Commits, 1.1 Voice (hour-0 spike, then productionised), 1.2 Agent (OpenAI Agents SDK), 1.3 Trust boundary: propose → present → confirm → receipt, 1.4 Finance domain, 1.5 People ops (PLAN_v5), 1.6 API and infrastructure (local), 1.7 Web UI (`web/`, React 19 + Vite + TypeScript) (+21 more)

### Community 42 - "finance.py"
Cohesion: 0.13
Nodes (26): explain_budget_change(), get_attention_items(), get_audit_history(), get_briefing(), get_budget_status(), list_budget_categories(), _pos_view(), function_tool (+18 more)

### Community 43 - "Plan"
Cohesion: 0.09
Nodes (21): ApplyLeave, Execution, Plan, ApplyRecommendations, BudgetChange, _change_plan(), _close_plan(), CloseMonth (+13 more)

### Community 45 - "test_meetings.py"
Cohesion: 0.15
Nodes (26): dispatch(), Create queued meetings at Google. Rows are claimed with SKIP LOCKED so…, args(), code_for(), linked(), meetings(), queue_meeting(), Schedule-meeting coverage: validation, plan text, execute, calendar dispatch,… (+18 more)

### Community 46 - "services/budget_months.py"
Cohesion: 0.16
Nodes (34): BudgetPeriod, One category-month. Open months read the ledger; a closed month keeps its…, _rec_plans(), step_id(), alerts(), apply_change(), apply_close(), Cell (+26 more)

### Community 47 - "projection.py"
Cohesion: 0.11
Nodes (20): month_outlook(), Outlook, Where spend is heading (run rate), for the CEO's three bars: allocated, spent,…, budgets / spends: the FY's 12 months in order; current: index of this month (0…, year_outlook(), Change, Month, pace_of() (+12 more)

### Community 48 - "Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST)"
Cohesion: 0.50
Nodes (3): Added capabilities (same agent, same propose → confirm → receipt engine), Munshi — scope addendum v5: people operations (2026-11-21, ~13:00 IST), Rules

### Community 53 - "Actor"
Cohesion: 0.05
Nodes (77): Actor, The authenticated principal. Always derived from the server session, never from…, Finance approval rights., May SEE budget, revenue, payables, receivables and company-wide records (not…, May not make any change at all (no proposals, no direct writes)., HR/admin rights: onboarding, company-wide announcements, all leave., briefing(), budget_alerts() (+69 more)

### Community 55 - "go"
Cohesion: 0.10
Nodes (45): figures(), mk_client(), mk_inr(), Rs 10,000 Oct with Rs 4,000 in; move Rs 6,000 to Nov: moved_paise 600000, Oct…, send(), test_allocation_across_two_clients_rejected(), go(), test_allocation_without_amount_pays_each_remaining() (+37 more)

### Community 56 - "test_revenue_core.py"
Cohesion: 0.12
Nodes (32): pinned(), priya(), propose_confirm(), fixture, parametrize, Revenue core: money maths, invoice lifecycle, allocation, reporting figures,…, Revenue clients are customer Parties in the same workspace table (no separate…, Approver with no conversation: grounding is skipped (the on-screen form path). (+24 more)

### Community 57 - "cycles.py"
Cohesion: 0.08
Nodes (55): ClientCycle, A client's billing cycle from a month on: monthly charge, every N months,…, active(), apply(), ChangePlan, check(), _clashes(), combined() (+47 more)

### Community 58 - "run_spec"
Cohesion: 0.12
Nodes (22): _auto_chart(), ChartSpec, _fetch(), FilterSpec, _fold(), fold_by(), key_label(), _month_label() (+14 more)

### Community 59 - "tools/budget_months.py"
Cohesion: 0.13
Nodes (29): bm_round(), forecast_budget(), get_budget_alerts(), get_budget_history(), get_budget_month(), get_budget_recommendations(), get_budget_year(), MonthSplit (+21 more)

### Community 60 - "test_charts.py"
Cohesion: 0.11
Nodes (35): apply_patch(), chart_problem(), ChartSpecPatch, A revision. Anything omitted keeps its current value, so grouping survives…, Why the requested chart type does not fit the spec's shape, or None., build(), client_for(), err() (+27 more)

### Community 61 - "test_contracts.py"
Cohesion: 0.11
Nodes (37): parse_cap(), (cap in paise, basis text). A non-INR or non-numeric cap keeps paise None and…, _a_flag(), analyse(), by_type(), contract_by_ref(), deadlines_of(), dl() (+29 more)

### Community 62 - "test_roles_rbac.py"
Cohesion: 0.10
Nodes (31): Contract review: read an agreement, find its clauses, identify liabilities (who…, _ctx(), exposed(), margs(), _pin(), fixture, parametrize, B1 RBAC matrix: employee / ceo / finance_approver / admin across tools,… (+23 more)

### Community 63 - "services/intake.py"
Cohesion: 0.20
Nodes (21): Document, AsyncSession, record(), accept_upload(), check_arithmetic(), close(), company_payment_matches(), correct_field() (+13 more)

### Community 64 - "Invoice"
Cohesion: 0.09
Nodes (57): Invoice, date, A customer invoice (revenue). Ported from the copilot Revenue module. Billing…, _date(), due_on(), An invoice is due on the last day of the period it covers., Allocation, BalancePlan (+49 more)

### Community 65 - "cards.tsx"
Cohesion: 0.08
Nodes (32): AuditCard(), BudgetCard(), Deliveries(), fmt(), InboxCard(), LEAVE_NAME, LeaveCard(), LeaveRequestsCard() (+24 more)

### Community 66 - "ChartCard.tsx"
Cohesion: 0.15
Nodes (19): CATS, ChartCard(), compactInr(), DataTable(), fmtAxis(), fmtChange(), fmtFull(), fullInr() (+11 more)

### Community 67 - "Party"
Cohesion: 0.08
Nodes (63): go(), Party, A dated in-app reminder ('remind me Friday to chase Acme'), optionally about a…, Reminder, client(), clients(), create_client(), _currency() (+55 more)

### Community 68 - "Extraction"
Cohesion: 0.16
Nodes (20): build_agent(), Cite, extract(), ExtractedDocument, LineItem, Agent, BaseModel, ExtractorAgent: reads document page images into a typed schema. It has NO… (+12 more)

### Community 69 - "_propose"
Cohesion: 0.07
Nodes (69): Convert DomainError into a structured result the agent can explain; log name,…, safe_tool(), cancel_pending_proposal(), _confirm(), confirm_pending_proposal(), get_pending_proposal(), _proposal_view(), _propose() (+61 more)

### Community 70 - "client_by"
Cohesion: 0.09
Nodes (32): client_by(), _end(), invs_of(), Kaveri's paid Oct invoice covers Oct-Dec: a monthly cycle from Nov must not…, test_apply_reprices_ticked_and_leaves_paid_and_part_paid(), go(), test_change_cycle_midyear_removes_only_to_raise_from_the_change_month(), go() (+24 more)

### Community 71 - "create_event"
Cohesion: 0.28
Nodes (14): create_event(), event_body(), Create (or fetch, if it already exists) the Google event. Returns (meet_url,…, make_meeting(), pin(), route(), wrapped(), test_create_event_409_fetches_existing_event() (+6 more)

### Community 72 - "metadata.py"
Cohesion: 0.13
Nodes (30): add_months(), _clean(), _client(), dates(), Detail, Details, _effective(), end_of_term() (+22 more)

### Community 75 - "Settings"
Cohesion: 0.18
Nodes (4): Settings, BaseSettings, field_validator, test_settings_strip_google_values()

### Community 76 - "propose_and_confirm"
Cohesion: 0.08
Nodes (76): AuditEvent, BudgetMovement, Proposal, Append-only. Balance of each bucket = SUM(amount_paise)., Full settlement only (weekend scope). One per record, enforced by the unique…, Receipt, Settlement, cancel() (+68 more)

### Community 77 - "confirmation.py"
Cohesion: 0.27
Nodes (14): AsyncSession, Spoken confirmation is valid only from a server-observed user turn that started…, Return evidence for confirming `p`, or raise CONFIRMATION_REQUIRED with the…, record_turn(), spoken_confirmation(), _open_approve(), _present_then_turn(), _spoken() (+6 more)

### Community 78 - "revenue_actions.py"
Cohesion: 0.06
Nodes (48): go(), AddInvoices, _ccy(), _clean_num(), ClientChange, DeleteDraft, EditInvoice, _eff() (+40 more)

### Community 79 - "scan.py"
Cohesion: 0.09
Nodes (35): The shipped clause catalogue: copilot `ctr_0001_contracts.py` CLAUSE_TYPES,…, A clause type as the scan sees it., Rule, rules(), _ask(), _dedup(), _join(), locate() (+27 more)

### Community 80 - "inv_of"
Cohesion: 0.06
Nodes (53): inv_of(), priya(), propose_confirm(), Approver with no conversation: grounding skipped (the on-screen form path)., Northwind Oct: $1,500 at 83.90 = Rs 125,850; Rs 60,000 in; Rs 65,850 left =…, test_amount_edit_with_rate_is_a_manual_rate_not_month_rate(), go(), test_apply_rejects_reprice_ids_not_in_preview() (+45 more)

### Community 82 - "test_suggest_email_voice.py"
Cohesion: 0.10
Nodes (31): session_config(), test_wake_opener_is_english(), _call(), _ctx(), _execute(), _items(), _plan(), parametrize (+23 more)

### Community 83 - "test_revenue_fx_cycles.py"
Cohesion: 0.12
Nodes (24): FxQuote, Cached ECB reference quotes (Frankfurter): INR per unit x 10^6, by publication…, AsyncSession, Fetch and cache the latest quote for each foreign ECB currency. Returns…, refresh(), _aug_ecb(), pinned(), fixture (+16 more)

### Community 84 - "services/people.py"
Cohesion: 0.09
Nodes (47): find_people(), get_leave_balance(), get_onboarding_status(), list_leave_requests(), lookup_policy(), _person(), propose_leave(), propose_leave_decision() (+39 more)

### Community 85 - "recommendations"
Cohesion: 0.14
Nodes (21): The plan for `target`, without steps already applied for that month (same kind,…, recommendations(), short(), still_to_do(), ClosedMonth, plan(), slots(), PlannedChange (+13 more)

### Community 86 - "revenue/money.py"
Cohesion: 0.09
Nodes (30): currencies_in(), digits(), from_minor(), _indian(), numbers_in(), paise_str(), paise_to(), Decimal (+22 more)

### Community 87 - "tools/charts.py"
Cohesion: 0.14
Nodes (25): build_chart(), _card(), describe_chart_options(), present_view(), function_tool, safe_tool, Chart and view tools. The model composes typed specs; every number comes from a…, What can be charted for this user: sources, measures (with units), dimensions,… (+17 more)

### Community 88 - "distribution.py"
Cohesion: 0.20
Nodes (13): by_weights(), even_split(), Divide `total_paise` into `n` parts that sum exactly to it (remainder on the…, Annual -> monthly budget distribution (PRD §3). Integer paise only; no paise is…, Keep the `locked` month indices as given and spread `total_paise - sum(locked)`…, Split `total_paise` in proportion to `weights` (exact fractions, no floats).…, Growing shares: the first month weighs 1 and each next month weighs the one…, The paise each of `months` gets out of `total_paise` (same order, summing to… (+5 more)

### Community 89 - "classify"
Cohesion: 0.07
Nodes (32): Affirmation, classify(), _contains_affirm(), _normalize(), StrEnum, Deterministic classifier for a confirmation utterance (English, Hindi,…, bridge(), _Conn (+24 more)

### Community 90 - "liability.py"
Cohesion: 0.10
Nodes (36): Deadlines follow the contract's current expiry and its auto-renewal notice…, recompute_deadlines(), as_dict(), assess(), _bearer_term(), _beneficiary(), carve_outs_rules(), Deadline (+28 more)

### Community 91 - "store.py"
Cohesion: 0.08
Nodes (64): contract_deadlines(), get_contract(), list_liabilities(), propose_contract_details(), propose_contract_status(), propose_create_contract(), propose_rescan_contract(), propose_review_contract_finding() (+56 more)

### Community 92 - "pacing.py"
Cohesion: 0.24
Nodes (9): compute(), days_in_month(), Pacing, date, The pacing / burn-velocity engine and the proactive alert levels (PRD §4). Pure…, `day` is the current day of the month (1..total_days); use total_days for a…, _round2(), test_pacing_approaching_and_limit() (+1 more)

### Community 93 - "client_for"
Cohesion: 0.05
Nodes (68): add_inspected_document(), client_for(), test_employee_cannot_open_other_users_document(), test_exact_replay_returns_existing_document(), test_write_requires_csrf(), test_location_api_requires_login_and_csrf(), test_location_api_stores_and_returns_nearest(), test_months_endpoint() (+60 more)

### Community 94 - "part_paid_zed"
Cohesion: 0.08
Nodes (30): mk_client(), mk_invoice(), part_paid_zed(), Guide example: Rs 10,000 invoice, Rs 4,000 received, part paid., test_balance_delete_destination_restores_source_to_part_paid(), go(), test_balance_into_other_currency_month_makes_its_own_balance_invoice(), go() (+22 more)

### Community 95 - "reads.py"
Cohesion: 0.10
Nodes (29): bucket_label(), fy_months(), fy_start(), fy_today(), last_day(), month_label(), month_number(), period_label() (+21 more)

### Community 96 - "ClaimReview.tsx"
Cohesion: 0.07
Nodes (33): motion, react-dom, ease, easeInOut, palette, reveal, api, inr() (+25 more)

### Community 98 - "test_trips.py"
Cohesion: 0.08
Nodes (56): checkout_link(), google_flights_url(), date, Where the traveller pays for THIS flight: the airline's own checkout via Google…, google_hotels_url(), _norm(), date, Hotel search: SerpAPI Google Hotels (real rates, the hotel's own website for… (+48 more)

### Community 99 - "Message"
Cohesion: 0.15
Nodes (42): GoogleOp, HotelBooking, Message, Inbox item and/or email outbox row. Email rows are delivered after the…, Outbox for confirmed Gmail / Google Calendar changes on the linked account.…, A hotel stay approved in Purser. Payment happens on the hotel's own website…, BookTrip, pin() (+34 more)

### Community 100 - "get_settings"
Cohesion: 0.08
Nodes (28): The one login whose real Gmail and Google Calendar Purser may use…, _actor(), check_write(), current_actor(), current_csrf(), login(), Cookie session auth + CSRF. The Actor is derived from the server session on…, Origin + CSRF header on every state-changing browser request. (+20 more)

### Community 102 - "DomainError"
Cohesion: 0.13
Nodes (21): DomainError, Any, can_decide(), require_decide(), BookFlight, _city(), _execute(), _flight_args() (+13 more)

### Community 103 - "fx_months.py"
Cohesion: 0.12
Nodes (28): FxMonth, A conversion rate set by hand for a currency and month; carries forward until…, fy_of(), Affected, apply(), carried_months(), Change, effective() (+20 more)

### Community 105 - "run"
Cohesion: 0.12
Nodes (21): ExceptionInfo, code_of(), Run fn(ss, rv) on a sync session inside one committed transaction; return what…, run(), rv_of(), test_create_cap_and_duplicate_months(), go(), test_cycle_monthly_mode_emits_one_row_per_month() (+13 more)

### Community 106 - "test_people_extra.py"
Cohesion: 0.07
Nodes (69): LeaveMovement, LeaveRequest, Append-only leave ledger per user and type. available = granted - reserved -…, dispatch(), Send queued emails. Each row is claimed with SKIP LOCKED so concurrent…, test_messaging_dispatch_survives_calendar_dispatch_crash(), add_employee(), apply() (+61 more)

### Community 107 - "usePurser"
Cohesion: 0.12
Nodes (32): lucide-react, PurserComposer(), useAssistant(), Briefing, BriefingView(), Item, Section, useBriefing() (+24 more)

### Community 109 - "code_of"
Cohesion: 0.14
Nodes (11): code_of(), test_balance_delete_requires_unraised_destination(), go(), test_end_ignore_needs_a_month_and_pending_must_be_known(), no_month(), unknown(), test_ending_an_ended_client_is_same_state(), test_foreign_and_inr_month_inputs_validated() (+3 more)

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

### Community 116 - "._target"
Cohesion: 0.16
Nodes (8): Any, Action, Approve, DecideLeave, _leave_decision_inputs(), AsyncSession, Dispatch approval by record ref prefix (C = claim, B = bill)., Protocol

### Community 118 - "test_b25_clarify.py"
Cohesion: 0.21
Nodes (22): ask(), counts(), opts(), parametrize, B3 gate: ask_choice (2-5 options, chart registry validation, per-topic cap of…, Without a conversation there is nowhere to count: every question is allowed…, An employee's registry has no finance sources, so a finance measure cannot be…, test_build_chart_success_resets_chart_count() (+14 more)

### Community 119 - "sugg"
Cohesion: 0.25
Nodes (9): sugg(), test_custom_reminder_survives_pause(), go(), test_paused_client_gets_no_billing_suggestions(), go(), test_raise_when_raise_date_arrived_not_before(), go(), test_reminder_due_today_appears_future_does_not() (+1 more)

### Community 120 - "User"
Cohesion: 0.12
Nodes (26): User, _message_inputs(), _onboard_inputs(), OnboardEmployee, SendMessage, address_plan(), compose(), dispatch_soon() (+18 more)

### Community 121 - "Deployment (AWS, us-west-2)"
Cohesion: 0.22
Nodes (8): Architecture, Deployment (AWS, us-west-2), Email and Google Meet, First deploy, Notes, Redeploy (new code), Rollback, Teardown

### Community 122 - "call"
Cohesion: 0.11
Nodes (40): FlightBooking, A SIMULATED flight booking: no ticket is bought. Real fare data from the search…, day(), do_search(), fake_search(), _s(), isolate(), one() (+32 more)

### Community 123 - "Conversation"
Cohesion: 0.10
Nodes (23): ask_choice(), bump(), Choice, current(), BaseModel, function_tool, safe_tool, MCQ clarifications: one tappable question at a time, at most three per topic,… (+15 more)

### Community 124 - "google_oauth.py"
Cohesion: 0.33
Nodes (7): Path, _client(), _env(), main(), One-time Google login for the linked account (Gmail + Calendar): gets a refresh…, _set_env(), _wait_for_code()

### Community 125 - "errors.py"
Cohesion: 0.11
Nodes (32): add_task(), complete_task(), list_tasks(), list_tickets(), propose_assign_task(), propose_ticket(), propose_ticket_update(), function_tool (+24 more)

### Community 126 - "travel.py"
Cohesion: 0.10
Nodes (31): get_my_location(), _here(), list_my_flights(), propose_flight_booking(), propose_trip_booking(), function_tool, safe_tool, Travel tools: where the user is, live flight search, and a (simulated) booking… (+23 more)

### Community 129 - "search"
Cohesion: 0.11
Nodes (23): FlightSearchError, _hhmm(), _norm_option(), Exception, Flight search: SerpAPI Google Flights (real fares) with a 30-minute cache; on…, Deterministic SAMPLE fares when live search is unavailable. Always labelled…, Returns {source: serpapi|sample, options: [...], note}. Options are sorted…, _sample() (+15 more)

### Community 130 - "google.py"
Cohesion: 0.17
Nodes (24): _g(), list_meetings(), _need_google(), propose_cancel_meeting(), propose_email(), propose_mail_action(), propose_reschedule_meeting(), datetime (+16 more)

### Community 133 - "call"
Cohesion: 0.16
Nodes (22): _label_id(), perform(), access_token(), call(), error_text(), GoogleError, Exception, Response (+14 more)

### Community 134 - "gmail.py"
Cohesion: 0.17
Nodes (18): addresses(), _decode(), get_thread(), _hdr(), Gmail for the linked account. Message bodies are UNTRUSTED data: stripped to…, Prefer text/plain; fall back to text/html with tags removed., Recipient, subject and threading headers for a reply to the latest message in a…, reply_context() (+10 more)

### Community 135 - "google_actions.py"
Cohesion: 0.20
Nodes (11): CancelEvent, _emails(), _local(), MailAction, datetime, _queue(), Confirmed changes on the linked Google account: send/reply email, inbox…, _require_google() (+3 more)

### Community 136 - "react"
Cohesion: 0.18
Nodes (12): react, three, ApiError, call(), Card, headers(), Me, setSession() (+4 more)

### Community 138 - "contract_actions.py"
Cohesion: 0.33
Nodes (7): _details_inputs(), _iso(), Contract writes as propose -> present -> confirm -> receipt actions (the same…, SetContractDetails, _staged(), _type(), _has()

### Community 139 - "bills"
Cohesion: 0.31
Nodes (9): bills(), fy(), fyq(), monday(), date, (business_date, amount, vendor, category) of non-rejected bills., test_bills_by_day_and_week(), test_bills_by_quarter_and_fy_match_independent_sums() (+1 more)

### Community 140 - "row"
Cohesion: 0.22
Nodes (8): row(), go(), go(), go(), test_seeded_northwind_nov_priced_at_carried_oct_rate(), go(), go(), test_version_persists_across_sessions()

### Community 148 - "dispatch"
Cohesion: 0.32
Nodes (6): dispatch(), Perform queued Google ops once each (SKIP LOCKED; a failure is kept, never…, queue_two(), test_dispatch_marks_done_and_failed(), test_dispatch_noop_when_google_not_configured(), test_dispatch_respects_limit()

### Community 149 - "db.py"
Cohesion: 0.12
Nodes (23): Base, configure(), engine(), AsyncSession, sessionmaker(), async_sessionmaker, AsyncEngine, DeclarativeBase (+15 more)

### Community 151 - "PurserSidebar.tsx"
Cohesion: 0.17
Nodes (12): spring, ACTION_WORDS, ago(), humanize(), NavDef, Note, Notifications(), Profile() (+4 more)

### Community 152 - "env.py"
Cohesion: 0.27
Nodes (9): Connection, do_run_migrations(), include_object(), Run migrations in 'offline' mode. This configures the context with just a URL…, In this scenario we need to create an Engine and associate a connection with…, Run migrations in 'online' mode., run_async_migrations(), run_migrations_offline() (+1 more)

### Community 153 - "tool_access.py"
Cohesion: 0.33
Nodes (6): _allowed(), apply(), enabled(), RunContextWrapper, Which tools each role is offered. The model never sees a tool its role cannot…, FunctionTool

### Community 154 - "test_paused_and_ended_clients_get_no_billing_suggestions"
Cohesion: 0.60
Nodes (5): test_paused_and_ended_clients_get_no_billing_suggestions(), end(), kinds(), nw_before(), resume()

### Community 155 - "test_perform_each_kind"
Cohesion: 0.15
Nodes (6): test_perform_each_kind(), create(), modify(), op(), test_perform_label_reuses_existing_or_creates(), test_save_mail_draft_new_requires_to_and_subject()

### Community 156 - "_cycle_client"
Cohesion: 0.29
Nodes (7): _cycle_client(), test_guide_arrears_books_in_december_and_raises_at_period_end(), go(), test_guide_monthly_mode_emits_three_rows_sharing_the_period(), go(), test_guide_quarterly_advance_combined_books_30000_in_october_due_31_dec(), go()

### Community 157 - "FlightCard.tsx"
Cohesion: 0.25
Nodes (10): dur(), FlightOptionsCard(), Hotel, HotelOptionsCard(), inr(), openPayment(), Opt, Pay (+2 more)

### Community 158 - "post_move"
Cohesion: 0.44
Nodes (9): flows(), lines_by_cat(), post_move(), test_budget_flows_conservation_and_directions(), test_budget_flows_does_not_change_budget_source_and_is_workspace_scoped(), test_budget_flows_empty_on_fresh_seed(), test_budget_flows_multi_month_transfer_pairs_per_month(), test_budget_flows_other_dimensions_and_filters() (+1 more)

### Community 159 - "make_actor"
Cohesion: 0.06
Nodes (75): One transaction; commits on success, rolls back on any exception., session_scope(), create(), AsyncSession, Revenue demo rows (ALL SYNTHETIC), written through the revenue services so…, seed(), bill(), _seed_revenue() (+67 more)

### Community 160 - "review.py"
Cohesion: 0.15
Nodes (19): analyse(), can_view(), clean_name(), ensure(), guess_title(), guess_type(), our_names(), prefetch() (+11 more)

### Community 162 - "options"
Cohesion: 0.33
Nodes (6): options(), Registry as the model sees it, limited to what this actor may chart., BUG candidate: options() maps every non-paise unit to 'count', so the model is…, test_options_by_role(), test_options_lists_new_chart_types_and_rules(), test_options_reports_pct_unit_distinctly()

### Community 163 - "cal"
Cohesion: 0.33
Nodes (3): cal(), fixture, Calendar disabled by default; a test calls pin(monkeypatch, **FAKE) to enable.…

### Community 164 - "build_raw"
Cohesion: 0.25
Nodes (7): build_raw(), isolate(), parse(), fixture, test_build_raw_plain_message(), test_build_raw_reply_headers(), test_build_raw_subject_is_single_line_and_capped()

### Community 165 - "status.py"
Cohesion: 0.50
Nodes (3): compute_status(), Month-end utilisation status: OPEN (no positive budget), UNDERUSED (< 85%),…, test_compute_status_boundaries()

### Community 172 - "test_cycle_quarterly_combined_advance_books_in_first_month"
Cohesion: 0.67
Nodes (3): Rs 10,000 a month, 3-month period from Oct, combined/advance: Rs 30,000 in Oct…, test_cycle_quarterly_combined_advance_books_in_first_month(), go()

## Knowledge Gaps
- **261 isolated node(s):** `Briefing`, `Item`, `Section`, `Props`, `Caption` (+256 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1120 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **76 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `session_scope()` connect `make_actor` to `document`, `test_intake_extra.py`, `today_ist`, `actions.py`, `test_budget_months.py`, `test_b25_google.py`, `purser.py`, `test_charts_v2.py`, `dispatch`, `db.py`, `run`, `post_move`, `review.py`, `Meeting`, `finance.py`, `test_meetings.py`, `Actor`, `test_revenue_core.py`, `tools/budget_months.py`, `test_charts.py`, `test_contracts.py`, `test_roles_rbac.py`, `Extraction`, `_propose`, `propose_and_confirm`, `confirmation.py`, `inv_of`, `test_suggest_email_voice.py`, `test_revenue_fx_cycles.py`, `services/people.py`, `tools/charts.py`, `store.py`, `client_for`, `part_paid_zed`, `test_trips.py`, `Message`, `get_settings`, `run`, `test_people_extra.py`, `test_b25_clarify.py`, `User`, `call`, `Conversation`, `errors.py`, `travel.py`?**
  _High betweenness centrality (0.117) - this node is a cross-community bridge._
- **Why does `make_actor()` connect `make_actor` to `document`, `test_intake_extra.py`, `today_ist`, `test_budget_months.py`, `test_b25_google.py`, `bills`, `test_charts_v2.py`, `dispatch`, `db.py`, `test_perform_each_kind`, `post_move`, `options`, `Meeting`, `test_meetings.py`, `Actor`, `test_revenue_core.py`, `run_spec`, `test_charts.py`, `test_contracts.py`, `test_roles_rbac.py`, `propose_and_confirm`, `confirmation.py`, `inv_of`, `test_suggest_email_voice.py`, `tools/charts.py`, `store.py`, `client_for`, `test_trips.py`, `Message`, `get_settings`, `test_people_extra.py`, `test_b25_clarify.py`, `User`, `call`, `Conversation`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Why does `Actor` connect `Actor` to `document`, `test_intake_extra.py`, `today_ist`, `actions.py`, `test_b25_google.py`, `services/charts.py`, `db.py`, `make_actor`, `review.py`, `options`, `Plan`, `services/budget_months.py`, `run_spec`, `tools/budget_months.py`, `test_roles_rbac.py`, `services/intake.py`, `_propose`, `propose_and_confirm`, `confirmation.py`, `revenue_actions.py`, `services/people.py`, `recommendations`, `tools/charts.py`, `store.py`, `client_for`, `get_settings`, `DomainError`, `._target`, `User`, `call`, `Conversation`, `errors.py`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Are the 138 inferred relationships involving `Actor` (e.g. with `briefing()` and `budget_alerts()`) actually correct?**
  _`Actor` has 138 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `DomainError` (e.g. with `test_beneficiary_cannot_self_approve()` and `test_cross_workspace_object_ids_not_found()`) actually correct?**
  _`DomainError` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 62 inferred relationships involving `User` (e.g. with `_here()` and `people_directory()`) actually correct?**
  _`User` has 62 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Briefing`, `Item`, `Section` to the rest of the system?**
  _261 weakly-connected nodes found - possible documentation gaps or missing edges._