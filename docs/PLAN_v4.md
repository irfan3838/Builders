# Munshi | Final weekend build plan

**Decision:** Use this plan for weekend scope, implementation order and release acceptance. [Plan v2](Plan_v2.md) remains the full SaaS specification. [Plan v3](PLAN_v3.md) records the original scope cut. “Final” applies to the plan. All implementation and deployment milestones below require evidence.

**Status:** Finalized Sat 2026-11-21 11:30 IST. Kickoff reading: about 26.5 clock hours to the Sun 14:00 IST freeze, which fits the 18-hour active budget in §5 plus sleep and rehearsal.

## 1. Product promise and scope

Enter Theme 3 with Zoho Books expenses and payables as the reference. Priya can drop a fresh document, answer a question in Hindi, English or Hinglish, approve a legitimate expense, inspect the resulting budget and record settlement. Her role, the employee’s trip and the live balances provide the personal context behind the answer. Sign-in, microphone permission and selecting a local file precede the voice workflow.

| User need | Weekend acceptance | Full-product follow-through |
|---|---|---|
| Ask what needs attention | Read up to three authorized items from pending approvals, bills due within seven days and overdue invoices. Use a stable order with dated items first and a deterministic tie-breaker. Speech and screen reference the same list. | Proactive notifications and individualized briefing preferences. |
| Process a fresh file | PDF/JPEG/PNG receipt or bill, evidence preview, correction by voice, duplicate check and payer routing. Every other upload receives an explicit outcome. | Messy spreadsheets, batched imports, bank statements and more formats. |
| Approve and settle | Employee and vendor workflows with separate submission, approval and recorded settlement. Each confirmed action yields an audit receipt. | Partial and bulk operations, reconciliation and exception routing. |
| Manage budgets | Read allocation, reserved, committed, spent and available. Approval replaces a linked reservation; settlement moves committed to spent. | First discretionary extension is a confirmed transfer between two budget lines. Rollover and forecast follow. |
| Understand revenue | Read open invoice balances, revise chart to overdue only and drill into a customer. Speech and chart use the same snapshot. Call this receivables reporting. | Invoice issuance, collections entry, expected revenue and reminder delivery. |
| Find contractual liabilities | Recognize an apparent contract or ask the document type when uncertain. Tell Priya that contract review is outside the weekend release. Close intake without a finance write. | First post-event document workflow: identify our party and role, extract obligations, cite clause and exception, flag missing exhibits and route findings for human review. Acceptance uses a fresh MSA with both a general cap and a carve-out. |

Only call a capability shipped after it passes on the deployed build. If either approval workflow drops out, narrow the demo title and feature list to the workflow actually verified.

## 2. Intake and accounting decisions

1. Accept an authenticated upload scoped to a single demo workspace. Start with a proposed 10 MB and five-page limit. Check size, detected media type and readability. Report encrypted PDFs, unsupported documents, ambiguous document type and extraction failures aloud. A contract is never an invoice simply because it contains a rupee figure.
2. Extract vendor, date, amount, currency, invoice number when present, and visible breakdown with page references. Show the source. Check arithmetic only when the components exist. Speak “could not verify the breakdown” for a total-only receipt. A mismatch pauses submission for a correction and an updated preview.
3. Compare the file hash and likely business duplicates across bills, claims and settled expenses. For the weekend, a likely duplicate means the same party, the same amount and a business date within three days. An exact replay returns the existing record and its status. A probable duplicate requires resolution before submission. Trip dates alone are insufficient to identify an employee or a booking. Compare employee, merchant, dates and reservation, and ask when ambiguous.
4. Resolve the **economic event**. “Did Arjun pay, did the company already pay, or is the vendor still owed?” An unpaid vendor invoice enters payables. An employee-paid business expense enters claims. A company-paid receipt is matched to existing payment evidence. If unmatched, show it for reconciliation and finish intake without creating an open payable or a reimbursement. Recording a new historical company-card expense is a later release.
5. Use a fixed signed-in actor. Priya may submit on behalf of Arjun because her role allows it. Persist submitter, beneficiary and approver separately. **Decision:** the demo policy bars the beneficiary from approving their own reimbursement. It does not bar a submitter from approving. This keeps the demo to a single login. Disclose it as a policy choice; a configurable submitter-approval bar is a production follow-up. Arjun’s login exists for the access-control tests. An employee cannot view another employee’s claim or approve a vendor bill.
6. Full settlement is the weekend write. Read back outstanding amount, payee, business date and reference. Recheck approved state and outstanding balance when confirming. Return the existing receipt for a retry. Reject a different attempt against an already settled balance. Distinguish recording a past payment from initiating a transfer.

### Budget fixture and acceptance

Use integer paise, INR, IST and an April–March fiscal year. Available = effective allocation − open reservations − approved unpaid commitments − settled spend. Each rupee belongs to one of the latter three buckets at a time; pending claims can be shown separately.

| Travel line | Allocated | Reserved | Committed | Spent | Available |
|---|---:|---:|---:|---:|---:|
| Before upload | ₹50,000 | ₹5,000 | ₹0 | ₹0 | ₹45,000 |
| ₹4,800 claim submitted | ₹50,000 | ₹5,000 | ₹0 | ₹0 | ₹45,000 |
| Approved as final charge for that reservation | ₹50,000 | ₹0 | ₹4,800 | ₹0 | ₹45,200 |
| Full reimbursement recorded | ₹50,000 | ₹0 | ₹0 | ₹4,800 | ₹45,200 |

Release the reservation and post the commitment atomically. A partial stay, ambiguous match or different reservation requires clarification. With a fresh receipt of another amount, compute and narrate its actual delta. Never hardcode the demo total. Use a separate category for the vendor bill walkthrough so it cannot obscure the travel example.

### Seed fixture

All seed data is synthetic and labelled as such. It covers one workspace and two logins:

- **Priya:** finance approver.
- **Arjun:** employee, with the Pune trip and a ₹5,000 hotel reservation against Travel.

It also includes the following:

- Six vendors, including one approved, unpaid bill in a non-travel category for the settlement walkthrough.
- Five customers with open invoices. Some are overdue, including Acme.
- Two similarly named parties for the ambiguity case.

Pin a seed version so the demo and evaluation reset to the same state.

## 3. Conversation and confirmation

Support “show the source,” “correct the amount,” “repeat,” “cancel,” “what’s pending?” and “read Acme’s amount.” Keep one foreground proposal per actor/session. A read-only follow-up can inspect its effect. A material correction supersedes it. Reconnect restores the pending preview and asks again. Bind an affirmative utterance to the preview already presented. No ambiguous or interrupted utterance commits a write.

For every business write, separate asking for the action, presenting its exact effect, and receiving a subsequent confirmation. Example: “Mark Arjun reimbursed, reference 4471” → “Record ₹4,800 to Arjun against claim C12, reference 4471?” → “Yes” → execution receipt. Apply this to submission and settlement as well as approval. Internal extraction and audit events do not require a separate user decision.

On the server store actor, workspace, proposal ID, canonical arguments, expiry, affected versions and unique idempotency key. During one transaction, authorize, verify versions of all affected records (including linked reservation), apply ledger and state transitions, create audit row and persist receipt. A repeated confirmation returns that receipt. A stale preview returns a new preview for confirmation. Speak success only from the execution receipt.

## 4. Architecture and deployment gates

React/TypeScript renders captions, proposals, source pages, receipts and ECharts. FastAPI owns typed Pydantic tools, deterministic services and PostgreSQL transactions. S3 holds private uploads. Resolve receivables and budgets through fixed parameterized queries. Never allow generated SQL. Use a shared result object for chart, table and speech, including period, units, filters and source record IDs. “Only overdue” retains customer grouping. “Read Acme” uses the filtered snapshot.

Spike an account-supported voice model using the official SDK and env-configured IDs. The proof is one spoken question, one authenticated server tool invocation and a spoken result. Browser-relayed arguments are untrusted. Keep raw mutation services off the public tool surface. Require the authenticated actor, session-bound proposal, explicit confirmation and origin/CSRF protection for browser writes. A client claiming that a model heard “yes” cannot establish user intent. For hands-free financial confirmation, use a server-observed voice turn bound to the preview, or server-side push-to-talk transcription of the confirm utterance. If neither works, require a user-operated confirmation button and disclose the limitation in the demo.

Serve one synthetic demo tenant behind authenticated access. Derive workspace and actor from the server session on every query, file request and confirmation. Include one negative test for another actor’s restricted record and one mismatched-workspace object ID. Use private objects and short-lived authorized previews. Bound upload and provider usage. Keep audio and document bodies out of logs. This release demonstrates a single workspace; customer onboarding belongs to the production roadmap.

Target one container on ECS Fargate, HTTPS ingress, private RDS, private S3, managed secrets and structured logs. Check account, region, certificate/domain or alternative HTTPS endpoint, outbound access, cost estimate and spend authorization early. Isolate signed-in pages and API routes from shared caching. Test microphone and session cookies on the actual origin. Prefer a manual first deploy through repeatable infrastructure and image steps, then GitHub Actions OIDC. Save the deployed commit, migration, seed version and smoke result. A local recording is an acceptable labelled backup when cloud access is blocked.

## 5. Delivery budget and cut line

Use **18 working hours** as the ceiling. Take a fresh time-to-freeze reading at kickoff; preserve sleep and the final rehearsal. Elapsed hours below are active build time. Start cloud prerequisites in block one. Paid provisioning remains subject to authorization.

| Active hours | Build | Gate |
|---|---|---|
| 0–1 | Voice/tool spike. In parallel, read-only cloud preflight (account, region, HTTPS endpoint option, cost estimate); no provisioning | Record working transport and confirmation mechanism; select push-to-talk if needed. |
| 1–4 | Seeded actors, bill/claim states, proposal/receipt service, ledger fixture | Replay, stale proposal, self-approval and ₹45,200 tests pass. |
| 4–7 | Upload, extraction, spoken clarification, duplicate resolution and claim path | Fresh receipt through approval locally; incompatible file exits safely. |
| 7–10 | Compact UI, evidence, voice confirmation and first HTTPS deployment | Spoken core loop on deployed origin, or a documented cloud blocker. |
| 10–13 | Vendor approval, both settlement paths, receivables chart and revision | Verify both balances, chart totals and retried settlement. |
| 13–15 | Light briefing, audit view, role and failure-path checks | One session completes the advertised workflows; failures preserve balances. |
| 15–17 | Held-out evaluation, fixes, CI and redeploy | Re-run affected cases on final revision; save counts and failures. |
| 17–18 | Rehearsal, backup recording, README and submission | Timed run under four minutes; each slide claim ties to a receipt or measurement. |

When late, cut the optional transfer, slide polish and briefing before reducing intake/approval correctness. If voice delivery slips, use the server-side push-to-talk path. If deployment slips, use remaining discretionary time for deployment recovery and rehearse locally. If the vendor branch fails, remove it from the live claim, expose a clear unsupported outcome and mark that P0 gate missed. Attempt one optional transfer only when all gates and rehearsal are green and real time remains.

## 6. Demo and evaluation

- **0:00–0:30** Ask in Hindi for attention items and the travel balance. Show ₹45,000 and the open reservation.
- **0:30–1:55** Drop the fresh hotel receipt. Resolve payer and reservation; submit, confirm, approve and confirm. Ask what changed. Open the two ledger entries that explain the ₹200 increase in the worked fixture.
- **1:55–2:40** Open a seeded approved, unpaid vendor bill. Record its settlement with reference, preview, confirm and show the receipt. Demonstrate fresh vendor intake in the acceptance suite. This keeps time for authentic spoken confirmations.
- **2:40–3:25** Ask who owes money, then “only overdue,” then “read Acme’s amount.” Show the outstanding invoice rows behind the filtered chart.
- **3:25–4:00** Show decision history, measured outcomes and deployment status. Retain a labelled recording and reproducible demo seed.

Run about 15 text workflows, 20 recorded commands spanning Hindi, Hinglish and English, and 10 held-out documents as time permits. Freeze expected outcomes before running. Cover payer ambiguity, already-paid evidence, wrong total, duplicate upload, unrelated contract PDF, two matching names, stale proposal, repeated yes, over-limit and self-approval, cross-actor access, double settlement and chart revision. Verify final records, ledger conservation and zero unauthorized or duplicate writes. A repeated yes is a successful replay of the original receipt.

For voice, use the same recordings and expected entities in both arms. Compare plain transcription plus structured extraction against the full context-assisted workflow; label this as a system comparison. Report exact amount, party and date accuracy by language with denominators. For document extraction, measure raw field correctness, error-detection rate and coverage of fields accepted after validation. Report user-corrected accuracy separately. An arithmetic flag detects an inconsistency; it cannot establish which field is right.

Record commit, fixtures, actual sample sizes, timing, failures and environment. Show a deployed result, local result, recording, blocked dependency or roadmap item according to its evidence. The finish condition is a finance user who can explain what changed, who approved it and which source supports the amount after one uninterrupted voice workflow.
