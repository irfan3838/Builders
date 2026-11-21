# Munshi | Product and delivery plan v2

**BUILDERS ’26 · Design specification · Solo build · 26-hour planning envelope · Sunday 2 PM code freeze**

Munshi is a voice-operated finance workspace for Indian small businesses. Priya, the finance manager, can drop the spreadsheet she already uses, ask what needs her attention, correct a record aloud, approve an expense and see whose balance changed. Each answer about money should lead back to a record. Each action should end with a receipt that tells her exactly what happened.

This document specifies the intended product, the smaller release to demonstrate, and the tests that distinguish a working feature from a slide. Model access, deployment, integrations and measured results are implementation gates. The original design is preserved in [PLAN.md](PLAN.md).

## 1. User, problem and submission

Priya starts her day with three different questions. Which customers owe us money? Which employees are waiting for me? Can we afford the bills waiting for approval? Answering them means switching between an invoice register, expense receipts, department budgets and email. A spreadsheet can give her a total, but getting from that total to the one employee she needs to reimburse takes another search.

**Theme 3 is the proposed submission track.** Use Zoho Books as the named reference. Pick one familiar job from that product, accounts payable, and show how Priya completes it through conversation. Expensify supplies the reimbursement comparison. Ironclad, Navan and Mixpanel are secondary references for contract review, travel and ad hoc analytics. A four-minute pitch needs only the references relevant to the live walkthrough.

**Theme 1 supplies the differentiator.** Priya’s role, department budgets, recent uploads, outstanding approvals, language and prior corrections determine what she hears. Demonstrate this by asking the same question immediately before and after a fresh receipt is approved. Show the exact row responsible for the changed answer.

**User evidence to gather.** Ask one finance or operations practitioner to walk through their most recent expense approval. Capture which document arrived, what they had to look up, who authorized it and how they knew the employee was paid. With permission, use a redacted example or recreate its structure. Time their existing workflow and the equivalent Munshi task under comparable conditions. Until that happens, label Priya and the seeded company as demo personas and the time saving as a hypothesis.

## 2. Release boundaries and ownership

| Delivery level | Capability and completion evidence |
|---|---|
| P0 · submission path | Signed-in demo workspace on AWS, multilingual voice and captions, spoken briefing, fresh bill/receipt and spreadsheet ingestion, vendor and employee approval queues, confirmed writes, reimbursement and settlement records, receivables and reminder preview/send, budget status and transfer, charts with one spoken revision, PDF contract scan with cited findings. Each demonstrated action has a persisted result or a visible delivery state. |
| P1 · extended finance product | Partial receipts and settlement entry through voice, recurring and milestone invoice generation, budget rollover and forecast, bank reconciliation, bulk approvals, batch undo, contract amendments and portfolio review, calendar operations. Keep the P0 data model compatible with these operations. |
| P2 · extensions | Travel search and labelled sandbox booking, inbox or Drive ingestion with scoped consent, remembered preferences across sessions, arbitrary file questions, deeper multilingual coverage, chart export and comparisons, multi-workspace onboarding and subscription billing. |
| Production release | Tenant provisioning, real identity provider, invitations, retention and deletion controls, restore drills, support and usage controls. Design tenant isolation from the first migration. Validate operational readiness separately before admitting customer finance data. |

Priya can manage finance within her workspace. Arjun can submit a claim and see his own status. A department approver can decide eligible items within assigned limits. A legal reviewer can disposition contract findings. An administrator manages memberships and policy. Keep the authenticated actor fixed throughout the session. Demo different roles using separate signed-in sessions. A spoken “I’m Priya” is conversational content.

## 3. What Priya experiences

One browser screen contains the microphone state, live captions in the spoken script, current question or proposal, activity timeline and an output canvas. A drop area accepts documents. The canvas can show a source page, validation errors, approval preview, chart, or execution receipt. Keep the most recent task visible while a background job runs. Each actionable card has a short spoken name such as “Arjun’s hotel claim.”

After sign-in, microphone permission and any external account consent, speech covers every business command in the release. Uploading a local file requires a drop or file picker. Support push-to-talk, keyboard-accessible confirm/cancel, readable status text, a table equivalent for charts and a visible audio-reconnect control. Voice commands include “repeat that,” “read the errors,” “open the source,” “cancel,” “what is pending?” and “continue with the invoice.”

**Example interaction with a deliberately ambiguous receipt**

1. Priya drops a hotel receipt. Munshi extracts ₹4,800 and finds Arjun’s trip for the same dates. “I found a hotel receipt matching Arjun’s Pune trip. Did Arjun pay, or did the company pay?”
2. “Arjun did. How much travel budget would be left?” Munshi checks the current travel line and linked booking. It shows the incremental impact and states whether the amount already has a reservation.
3. “Submit it.” Munshi previews an employee claim with employee, amount, category and evidence. Priya confirms. The server records a pending claim and returns its identifier.
4. “Approve that claim.” Munshi checks her approval authority and policy, reads the proposed decision, then waits. “Haan.” The receipt says “Approved, awaiting reimbursement.” Arjun appears in the unpaid employee queue.
5. “Show me the breakdown by department.” The canvas uses the same period and expense measure. “Read the travel amount” retrieves the same numbers as the chart. Priya has used one file picker and zero finance forms.

## 4. Conversation, information gathering and memory

| Stage | Agent behavior | What the server remembers |
|---|---|---|
| Understand | Detect language, intent, period, named party, referenced card and desired operation. Normalize rupee amounts, dates and entity identifiers. Echo ambiguous dates as weekday and calendar date. | Current user, workspace, timezone, task identifier, turn and active references. |
| Investigate | Read authorized records, upload evidence, policy, applicable budget, pending proposals and linked trips. Search internal sources before asking Priya for information the workspace already contains. | Evidence IDs, versions, query period and unresolved fields. |
| Clarify | Ask one question that changes the result. With two “Rahuls,” give a distinguishing vendor or department. For “revenue,” offer billed, collected or expected when context does not settle it. | Candidate IDs, missing field and the task to resume. |
| Present | Choose a spoken total, list, chart or source excerpt. State period, basis and currency. For an action, preview affected records, recipients, amounts and exceptions. | Chart or proposal ID, scope, revision and expiry. |
| Confirm | Bind affirmative speech to the foreground proposal and the speaker’s authorized session. When two proposals are plausible ask which one. Corrections replace the proposal and require a fresh confirmation. | Frozen arguments, actor, expiry, record versions and idempotency key. |
| Execute and report | Commit once, reread the affected records and report the actual result. When an external operation is pending, report its status and allow a later status query. | Audit event, affected IDs, delivery/job status and resulting balances. |

A user can interrupt a read-only explanation, ask a side question and return to the unfinished task. Suspend the task with its missing fields or proposal ID. A notification that arrives mid-confirmation cannot take focus. Reconnection reloads open tasks and asks Priya to reconfirm an expired or materially changed preview. Ambiguous audio around a name, amount or decision triggers a short readback. Silence expires the preview. “Cancel” stops an uncommitted action. After completion, Munshi explains the available reversal and its effects.

Day-one sources are the scoped database, uploaded documents, import history and explicitly connected services. Email sending grants no inbox-reading capability. A future inbox/Drive connector needs separate consent, source labels, sync status and deletion behavior. Save a lasting preference only when requested and confirmed. Keep language preference, recent entity references and accounting facts separate so a stale conversation summary cannot override a live balance.

## 5. Financial record lifecycles

Store money as integer paise, display INR with Indian grouping, store timestamps in UTC and interpret business dates in the workspace timezone. Default to IST and an April–March financial year for the demo. Display period boundaries for “last quarter.” Preserve both document date and transaction/settlement date. Keep source currency on every record. Route unsupported currencies for clarification until conversion policy is implemented.

### Vendor bills and approvals

A bill moves from draft to submitted, then approved or rejected. Submission checks vendor identity, invoice number, amount, due date, department and supporting evidence. Approval records the decision maker, policy version, amount and reason for exceptions. An authorized edit to material fields invalidates a pending approval. If a rejected bill is corrected, retain the original decision and submit a new revision.

“Which bills need me today?” returns only bills Priya can decide, ranked by due date, with disputed or incomplete items called out. “Approve the AWS bill” produces a preview. “Approve all under ₹10,000” freezes the exact eligible IDs, count, total and skipped items. A newly submitted bill cannot join that batch after preview. Enforce approval limits and separation of duties on the server. Route exceptions to an authorized reviewer.

Track settlement independently as unpaid, partially settled or settled, with date, amount and reference. Scheduling records an intention. Marking paid records evidence of settlement. The demo makes no bank transfer. Correct an erroneous posted settlement through a linked reversal entry that preserves history.

### Employee claims and reimbursements

Create from speech, a receipt or a trip. Capture employee, merchant, expense date, business purpose, amount, payer, category, department, receipt and optional trip. Compare against policy and possible duplicates. Distinguish an absent receipt from a rejected claim. An employee may supply missing evidence and resubmit.

Track submitted, needs information, approved and rejected decisions. Track approved balance and reimbursement separately. “Who is waiting for me?” means pending decisions in Priya’s queue. “Who is waiting for money?” means approved employee balances less recorded reimbursements. When Priya records a reimbursement, require a settlement reference, positive amount and sufficient outstanding balance. Preserve partial balances and show them explicitly even if partial-entry voice support ships later.

### Revenue, invoicing and collections

Keep three views distinct. **Billed** sums issued invoice amounts by issue date. **Collected** sums posted receipts by receipt date. **Expected inflows** combine open invoice balances by expected collection date with unbilled recurring or contractual milestones by projected collection date. Label projections and disclose assumptions. Once a milestone becomes an invoice, its projection is replaced by the invoice’s open balance. Overdue is a subset of outstanding.

“Who owes us money?” returns customer, outstanding amount, due date and ageing bucket. “Remind Acme” resolves the invoice, confirms the recipient and language, drafts a message, shows amount and due date, then requests confirmation to send. Persist message and provider IDs. Distinguish queued, accepted by provider, delivered when evidenced, and failed. A second request mentions the last reminder.

For issuance, prepare customer, lines, taxes, due date and invoice number. A confirmed issuance creates a unique invoice. Sending it is a distinct external effect. For receipts, allocate to identified open invoices, preserve unapplied credit, and reject over-allocation. Never call expected collections recognized accounting revenue. Formal accrual revenue recognition requires its own accounting policy and ledger work.

### Budgets, reservations and spend

Each line belongs to one workspace, department, category and period. Effective allocation equals opening allocation plus signed transfers, adjustments and rollovers. Use an append-only movement ledger. A transfer debits one line and credits the other in the same transaction. Enforce source availability, active periods and freeze rules.

Use a **cash-based operational budget** for the demo. Committed means reserved and unpaid, including an approved bill, approved claim or booked trip. Spent means settled. Available equals effective allocation less open commitments less spent. Show pending approvals and their projected impact separately. Display the basis on every budget comparison.

**Worked acceptance fixture.** Travel starts with ₹50,000 allocated and a ₹5,000 reservation for Arjun’s hotel. Available is ₹45,000. If the ₹4,800 final claim fully replaces the reservation, release ₹5,000 and commit ₹4,800 atomically. Available becomes ₹45,200. Recording the ₹4,800 reimbursement moves it from committed to spent and leaves available at ₹45,200. Link both entries to the same expense. Ask about a partial stay or a second receipt before releasing a reservation in full.

Support allocate, transfer, freeze, status, history and later rollover. For “carry forward at most 20%,” establish the denominator. Example policy: carry the lesser of positive unspent availability and 20% of effective allocation. Preview each source and destination period with the exact amounts. Exclude open commitments. Threshold watchers create one notification per crossing with a link to the underlying line. Forecasts show known commitments and an explicitly labelled extrapolation period.

## 6. Upload intake and routing

An upload authorizes intake and analysis. Creating a business record, committing an import, approving a finding or sending anything outside the workspace goes through a proposal. Record upload owner, workspace, checksum, detected type, processing state and evidence locations. Return a batch ID immediately. “What happened to my files?” reads per-file outcomes.

| Input | Initial processing | Voice outcome and next action |
|---|---|---|
| Vendor invoice PDF or photo | Extract vendor, GSTIN where present, invoice number, dates, totals, taxes and line items. Validate arithmetic and match vendor and duplicate candidates. | “One new bill for ₹18,400, due Friday.” Show evidence and offer to submit for approval. |
| Employee or ambiguous receipt | Check payer, employee, trip, existing company-card expense and duplicates. | Ask who paid when ambiguous. Link to the existing booking or draft the correct bill/claim. |
| Excel/CSV register or budget sheet | Detect header and sheets, sample columns, propose a typed mapping, apply deterministic transforms, flag totals rows, missing fields, duplicates and unknown parties. | Speak counts and total. Accept “read row 41,” “use invoice date for column C,” “skip invalid rows,” or “cancel.” |
| Contract, amendment or SoW | Identify parties and role, link version or parent when supported, extract text with page/section anchors, start review job. | Announce processing and allow other work. Return cited findings and review questions. |
| Bank statement | Identify account, period, debit/credit convention and balances. Find candidate invoice receipts or bill settlements by reference, amount and date. | Preview proposed matches with ambiguity reasons. Confirm postings individually or as an exact batch. |
| ZIP or mixed batch | Inspect archive safely, apply per-file limits and route each supported item independently. | Report counts by outcome, pending questions and failures. One corrupt attachment should not conceal successful analyses. |
| Unknown, encrypted, unreadable or low confidence | Record the reason and any readable pages. Offer reclassification or a clearer/unlocked copy. | Speak the smallest useful next step. Keep uncertain data out of committed business records. |

Start with PDF/JPEG/PNG, XLSX and CSV. Add DOCX for contracts, then HEIC, legacy XLS and ZIP after fixture verification. Initial limits from v1 are 25 MB per upload and 200 ZIP members. Also bound expanded bytes, page count, nesting, processing time and parallelism. Reject unsafe paths and macros. MIME sniffing, storage isolation and authorization apply to every retrieval.

For OCR, retain source page and crop or text location. Validate invoice subtotal, tax components and final total separately. Preserve unclear characters in names and identifiers for review. A match in a model-generated transcription alone cannot establish legibility. Show the original page when a high-impact value is uncertain.

Map spreadsheet columns to typed fields using a whitelist of transforms for dates, INR shorthand, Indian number formats, party/category lookup and constants. Apply transforms in code. A confirmation preview might read “540 input rows: 528 ready, nine duplicates, three need correction.” Keep row-level outcomes and ensure counts reconcile. Store confirmed mapping templates per workspace and header fingerprint. Revalidate a template when column types drift.

Tag committed records with a batch ID. Retrying an interrupted batch resumes from recorded outcomes. Undo previews downstream effects. Reverse eligible rows and identify records that now carry approvals, settlements or external messages requiring their own correction. Never silently unwind later work.

## 7. Contract liability review

The question is “What could our company have to pay, do, give up or lose under this agreement?” Establish company identity and whether it is supplier, customer, employer or another party before attributing an obligation. When two interpretations remain possible, ask Priya. A finding is a review aid, and a qualified reviewer owns the final interpretation.

1. **Identify the instrument.** Store immutable file version, parties, effective date, term, notice window, governing law, signatures, referenced schedules and any parent agreement. An identical file hash is a duplicate. A similar title is a candidate for a new version and needs identity verification.
2. **Preserve evidence.** Segment by headings and clauses with original page references. Preserve definitions and exhibits. Mark uncertain OCR and missing schedules. For DOCX use a stable section/paragraph reference or a versioned PDF rendering.
3. **Find candidate obligations.** Combine rule patterns and structured model extraction for indemnity, liability caps, carve-outs, confidentiality, data incidents, IP ownership, SLA credits, penalties, set-off, termination, insurance, audit, renewal and notice. Record obligated party, beneficiary, trigger, consequence, duration, cap, exclusions and reviewer question.
4. **Check related provisions.** For example, a ₹50 lakh general cap may exclude indemnities. Retrieve both clauses, verify each excerpt against the source and explain which obligations the exception appears to affect. Record unresolved precedence between an amendment and its parent. Keep “amount unspecified” distinct from “expressly uncapped.”
5. **Present and review.** “Two findings need attention. The first concerns indemnity in §9.2. Read the clause or its cap exception?” The findings card opens each quotation at its location, lists unanswered questions and identifies assumptions. Accept, edit, dismiss or request evidence by voice with a confirmed review decision.
6. **Version and close.** Open findings or unresolved required evidence block final approval under the demo policy. A new version triggers a new scan and review of changed clauses. A prior approval stays attached to its version. Portfolio views count findings and deadlines. Show monetary exposure only where source text and currency support aggregation.

A scanned MSA fixture should include a cap, an indemnity carve-out and a missing exhibit. Success requires both citations, correct assignment of the obligation, an explicit missing-evidence warning and a human decision tied to the reviewed version.

## 8. Adaptive charts and spoken analysis

The answer format follows the question. For “how much,” speak one number and its basis. For “which ones,” list the few relevant records and offer the full table. Use a chart for ranking, trend, comparison or budget movement. Always expose period, filters, units, source freshness and access scope. A user can request a table or a spoken summary at any point.

| Request | Default output | Follow-up that must work |
|---|---|---|
| “Who owes the most?” | Ranked horizontal bars of open balance by customer, alongside total outstanding. | “Only overdue” retains customer grouping and changes the predicate. |
| “How has collection changed?” | Monthly line of posted receipts with period and currency. | “Quarterly, last financial year” changes grain and range together. |
| “Can Marketing afford this?” | Current vs proposed allocated, committed, spent and available amounts. | “Show the underlying bills” lists record IDs contributing to the same calculation. |
| “Where did our allocation go?” | Waterfall of opening amount, transfers, adjustments and closing allocation. | “Read the largest transfer” retrieves a ledger movement. |
| “What risks are in the MSA?” | Findings table ordered by review priority with source links. | “Read the exception to the cap” opens the related clause. |

The model fills a typed chart specification with metric, allowed dimension, grain, period, filters, series, comparison and optional top-N. The registry owns units, aggregation, allowed joins, date basis and default view. A parameterized query compiler enforces tenant, role, result cap and timeout. Compute chart data, narrative totals and drill-downs from the same query definition. Persist chart ID, spec revision, result timestamp and data hash. A chart revision inherits all unspecified fields. If the data has changed since the prior answer, disclose the refresh.

Register billed, collected, expected, open and overdue receivables, bills due, approvals pending, reimbursement balances, spent, committed, allocated, available, utilization, cash flow, renewal counts and reviewed exposure counts. Denominator zero means utilization undefined. An empty period with known coverage can show zero. Missing coverage must show “data unavailable.” Label forecasts, assumptions and the boundary between observed and projected values.

## 9. Agent, interfaces and trust boundaries

Use one conversational agent with typed server-side tools. Give AI responsibility for intent, language, clarification, draft mappings, extraction and explanation. Give application code responsibility for authorization, validation, calculations, transitions and delivery receipts. The same registry serves a browser voice session and a text evaluation harness.

**Request path.** Browser microphone → authenticated voice session → scoped tool request → FastAPI registry → domain service → Postgres or integration → structured result → spoken response and canvas update. Use private object storage for uploads and server events for cards and job progress. The browser holds a short-lived session credential. Keep provider keys on the backend.

During the first hour, verify actual account access, SDK methods, voice transport, interruption handling and one server-side function round trip. Prefer a supported low-latency voice session. If server-side delegation is available, exercise it with a real tool before adopting it. A fallback uses speech transcription, a Responses tool loop and speech synthesis over the same registry. Benchmark the fallback separately and show its actual turn-taking behavior. Model names in v1 are candidates requiring access checks.

| Service surface | Representative operations |
|---|---|
| Session and context | Start/reconnect, get briefing, resolve party, list pending work, request clarification, recall current references. |
| Intake and jobs | Inspect, classify, preview mapping, correct row, submit import, get status, retry eligible items, preview undo. |
| Payables and claims | Draft/submit bill or claim, policy check, list eligible approvals, propose approve/reject, record settlement or reimbursement. |
| Revenue and budget | Invoice balances and ageing, draft invoice, propose reminder/receipt, budget status/transfer/rollover, explain movement. |
| Analytics and contracts | Create/revise/drill chart, scan version, list findings, open evidence, explain related clauses, propose review decision. |
| Shared writes | Preview effect, confirm exact proposal, cancel, fetch execution receipt. Connector tools use the same permission and confirmation rules. |

Each tool specifies input schema, output schema, allowed roles, read/write classification, timeout, entity versions and explainable failure codes. Typical results include data, evidence references, warnings, proposal or job ID, affected records and a short user-facing status. Bound delegations initially to ten calls and sixty seconds. Move scans and large imports into resumable jobs. On budget exhaustion report completed steps and the next unresolved decision.

**Confirmation contract.** Store tenant, actor, tool, canonical frozen arguments, hash, revision, exact IDs, expected record versions, rendered preview and ten-minute expiry. Confirm under transaction with current authorization and version checks. An idempotency key maps repeat submissions to the original receipt. If balances, policy, recipient or eligible records changed, generate a new preview. For external sends, transactionally enqueue an outbox entry. Retry safely when the provider supports idempotency. If acceptance is unknown, reconcile provider status before resending.

**API outline.** Authenticated endpoints create voice sessions, authorize file upload, finalize intake, stream session events, fetch job status and serve scoped source previews. Expose the same confirmation service for spoken and accessible on-screen approval. Use event IDs and a resume cursor so a refreshed browser can reconstruct pending cards. A health endpoint reports readiness without exposing customer data.

## 10. Data design and isolation

| Group | Key entities and invariants |
|---|---|
| Identity and policy | Workspaces, users, memberships, departments, role grants, approval policies with effective dates. Every business key and query carries workspace scope. |
| Parties and documents | Vendors/customers/employees, upload objects, versions, extracted fields, evidence spans, import jobs and rows. Signed download links are short-lived and checked against membership. |
| Finance | Bills and lines, claims, invoices and lines, receipts, settlement allocations, reimbursement entries, trips, milestones and decision history. Preserve record versions and source links. |
| Budget | Plans, period lines, signed movements, reservations and settlement events. Linked business documents share one economic expense identifier for budget calculations. |
| Legal | Contracts, versions, party roles, segments, evidence spans, clause findings, cross-references, reviewer dispositions and notice reminders. |
| Agent operations | Sessions, task state, entity references, proposals, audit entries, charts, jobs, notification deduplication and delivery outbox. Each job or proposal carries its initiating actor and scope. |

Use composite foreign keys or equivalent constraints to prevent cross-workspace links. Unique constraints cover external event IDs, confirmation keys and imported row identities within scope. Scope search, chart dimensions, candidate matches, background jobs and downloads as rigorously as the main queries. Test using two demo tenants with overlapping vendor names and invoice numbers. Restrict employees’ queries to their own claims and approved visibility. Record access to sensitive source files.

Treat document contents as evidence. Ignore embedded instructions. Limit type, size, archive expansion and extraction resources. Encrypt traffic and private storage. Keep raw audio off by default. Avoid logging full prompts, documents, email bodies and financial identifiers. Define retention by data class before customer onboarding, including uploaded originals, extracted text, transcripts, backups and audit history. Track deletion requests and identify records subject to an agreed retention policy.

## 11. Secondary workflows and integrations

- **Morning briefing.** Gather overdue receivables, due bills, approval requests, budget threshold crossings, contract notices and calendar items actually available to this actor. Rank by due date, amount and required decision. Speak the top three, then offer more. “Start with the second one” must select the same item even if fresh notifications arrive.
- **Calendar.** Read connected calendars within granted scopes. Resolve attendee, date, timezone and duration; show conflicts. Confirm create/reschedule/cancel and store provider ID. If only an internal calendar or an ICS invitation is available, state exactly which artifact was produced.
- **Travel.** Search test offers, check policy, read airline/route/time/price, refresh stale fares and confirm the selected offer. Label test bookings in speech and on screen. Link trip reservation to subsequent receipt or claim. Handle expired offers and price changes with a new proposal.
- **Reconciliation.** Stage bank rows, rank possible matches and present supporting date/reference/amount evidence. Multiple plausible matches require a human choice. Imported statements and reimbursement records describe past movements. Union linked entries by settlement identity to avoid duplicate cash reporting.
- **Background updates.** A durable worker leases import, scan and send jobs. Record progress and checkpoints. Release stale leases, bound retries and retain per-item errors. Announce completion at a pause. Allow “read me the result,” “retry failed pages” and “stop processing the remaining files.”

## 12. Implementation and deployment

Use a Python/FastAPI backend, typed Pydantic tools, SQLAlchemy and migrations over Postgres. React/TypeScript supplies voice controls, captions and cards; ECharts renders typed chart results. Keep domain logic under services, tool wrappers under agent/tools, source adapters under integrations and job handlers separate. Store replay fixtures, anonymized evaluation inputs and hand-computed expected outputs outside application code.

For the demo, package the SPA and API into one image. The proposed AWS target is ECS Fargate behind HTTPS, private RDS Postgres, private S3 uploads, Secrets Manager and CloudWatch. A worker can share the initial deployment using database leases. Measure memory during OCR and spreadsheet parsing before fixing task size. Set a concurrency limit; increase workers independently only when observed queue time justifies it.

Before applying Terraform, identify approved account, region, domain/certificate, private database connectivity, outbound provider access, state storage, SES identities and email sandbox restrictions. Estimate cost in that region for compute hours, load balancer, database, logs, storage, network egress and voice/model usage. Set an event budget, daily usage alert and authorized teardown date. Use v1 cost figures only as historical planning assumptions. Infrastructure provisioning and real spend require explicit authorization.

CI should run Python lint/service tests, TypeScript checks, frontend build, one seeded end-to-end smoke and Terraform validation where applicable. Use GitHub OIDC and least-privilege roles. Deploy a commit-tagged image, run a one-off migration, verify readiness, then exercise the browser voice path via HTTPS. Keep the prior image and use backward-compatible migrations. Verify restoration separately on disposable data. Local replay, deployed smoke and live-provider results each get their own label.

## 13. Build sequence and cut decisions

| Elapsed hours | Deliverable | Exit test |
|---|---|---|
| 0–1 | Voice spike, account capability inventory and fallback selection. | A spoken request executes a server tool and returns its result aloud. Interrupt once and resume. |
| 1–4 | Workspace, seed, membership checks, budget arithmetic, approval state machines and proposal service. | Repeat confirmation produces one decision. A second tenant cannot see it. |
| 4–7 | Receipt intake → payer clarification → claim → approval → budget view. | Fresh input changes the pending and approved balances by the expected deltas. |
| 7–10 | Workspace cards, captions, reconnect and first approved AWS deployment. | Run the above path on the deployed URL. Retain the local path and record actual deployment status. |
| 10–13 | Vendor approval, settlement, revenue views and confirmed reminder. | Show an unpaid vendor bill, approve it, preview reminder for a separate receivable and verify the recipient inbox where available. |
| 13–16 | Spreadsheet mapping, error correction, adaptive chart revision and budget transfer. | Import a messy file once, then reconcile a spoken total, chart total and database total. |
| 16–19 | Contract PDF extraction, party-role resolution, cross-clause evidence and voice review. | Fresh contract produces a sourced finding; incomplete evidence is surfaced. |
| 19–21 | Integrate briefing and background progress. Resolve the weakest P0 path. | One session handles a scan while Priya reviews expenses without losing confirmation context. |
| 21–24 | Run evaluation, fix failures, redeploy and rehearse. | Final report has measured denominators, known failures and a deployed smoke result. |
| 24–26 | Record backup, finalize slides and freeze. | Demonstrator can run from a fresh tenant, finish within four minutes and identify every simulated operation. |

This schedule is a target, not evidence of feasibility. If the receipt loop misses hour 7, keep one receipt type and one chart and fix that loop. If infrastructure access is blocked, retain a reproducible local build, record the dependency and continue independent product work. Cut travel, inbox sync, arbitrary file Q&A, calendar mutations, bulk operations and forecast polish before sacrificing the three demonstrated journeys. If a core path is incomplete at freeze, explicitly list its missing step.

## 14. Acceptance, evaluation and evidence

Run tests with a fresh database, fixed business date, versioned inputs and independently calculated expected totals. Record model/config version, language, transport, completion status and latency. The numbers below are proposed test sizes or acceptance conditions, never reported results.

| Scenario | Pass condition |
|---|---|
| Payer ambiguity | The same receipt yields an employee claim or vendor bill according to the answer. The agent resumes without asking for the amount twice. |
| Approvals and access | Self-approval, out-of-limit decisions and cross-tenant access are rejected. A repeated yes creates one decision. Two pending previews cause disambiguation. |
| Budget consistency | The ₹50,000 worked fixture gives ₹45,200 available after approval and after reimbursement. Two concurrent transfers cannot overspend the same source. |
| Revenue and reminders | Partial collection reduces outstanding by the posted amount. A billed milestone is counted once. Provider timeout cannot cause an automatic duplicate reminder. |
| Import quality | Count every source row once. Confirmed duplicate skips survive a retry. Bad dates are shown with row references. A new file changes a subsequent query by the hand-computed amount. |
| Chart fidelity | Spoken total, table and chart agree. “Last quarter, only Engineering” preserves the underlying measure and applies both filters. |
| Contract evidence | Correct party, quoted clause, cap exception and page references. Missing schedule is flagged. New version reopens review. |
| Conversation continuity | Barge-in, language switch, session reconnect, expired preview and background completion preserve identity and task scope. |
| Failure recovery | Lost microphone, OCR timeout, unreadable file, stale approval, failed email and interrupted import each produce an accurate user-visible status and recovery path. |

Begin with 40 scripted text tasks, 30 recorded voice requests, 25 chart requests, three messy workbooks, 15 receipts/bills and three to five independently labelled agreements as targets. Report completed sample sizes. Evaluate English, Hindi and Hinglish first, then add available Tamil, Telugu, Kannada, Marathi and Bengali recordings. Report each language separately, including incorrect names, dates and amounts. Demo languages must pass the golden flow.

Measure end-to-end task completion, correct final database state, clarification success, unexpected writes, field exact match, duplicate detection, source citation correctness, clause precision/recall and p50/p95 time to first useful speech. Compare extraction before/after validation and clause detection by patterns alone, model alone and combined. Count abstentions and unsupported files. For user value, measure time and manual interactions from raw receipt to verified decision. Any unauthorized or duplicate financial write blocks release of that path.

## 15. Four-minute demonstration and handoff

| Time | What the judge sees | Proof |
|---|---|---|
| 0:00–0:35 | Priya asks in Hindi what needs attention and how much travel budget is available. | Dated starting balance, labelled demo tenant and ranked briefing. |
| 0:35–1:55 | Drop a fresh receipt. Clarify payer, submit, approve and ask for the budget impact. | Source evidence, separate submission and approval, current reimbursement status, exact budget delta. |
| 1:55–2:45 | Ask who owes money, narrow to overdue customers, revise the visualization and confirm one reminder. | Same figures in voice and chart; message receipt and inbox arrival when available. |
| 2:45–3:45 | Drop an MSA. Ask which obligation could exceed the general cap and which party bears it. | Source page, linked exception and explicit missing exhibit. If scan latency exceeds the slot, show job progress and open a clearly labelled previously scanned version. |
| 3:45–4:00 | Return to the decision history and measured results. | Actor, action, timestamp, source and verification status. |

Prepare fresh anonymized inputs, a disposable seeded workspace, a tested microphone and a recorded backup. Label sandbox travel, recorded replay, synthetic company records and the absence of money movement. Slides cover user evidence, the live workflow, architecture and confirmation boundary, measured results, and the production roadmap. Credit earlier design inspiration and AI assistance accurately. Record which code and fixtures were created during the event.

## 16. Definition of done

For each P0 workflow, capture the user utterance, source input, expected state, actual result and recovery behavior. A reviewer must be able to trace a spoken number to the records behind it and a spoken “yes” to the exact proposal executed. Ship a clean-checkout run procedure, seed/reset instructions for disposable demo data, configuration placeholders, migration steps, evaluation results, deployment status and demo script. Mark every feature as deployed and verified, local only, simulated, blocked or planned according to observed evidence.

The release is ready to present when Priya can finish the receipt, receivables and contract journeys in a fresh session, using speech after file selection, and another person can independently verify the resulting balances, delivery state and clause citations.
