# Munshi | Build plan v3 (scope cut for the weekend)

**Status:** working plan as of Sat 2026-11-21, 11:20 IST. Code freeze Sun 14:00 IST.
**Supersedes for scheduling and scope:** [Plan_v2.md](Plan_v2.md). v2 is still the product spec for everything after the hackathon. Where this file says nothing, v2's rules still apply (money in paise, IST, April–March financial year, the confirmation rules, honesty labels).

## 0. Why a v3

v2 is a good product specification, but it isn't a plan that one person can finish this weekend.

- **Time.** From 11:20 Saturday to 14:00 Sunday is about 26.5 hours on the clock. Take out about 6 hours of sleep, meals and setup, and there are about **18–19 working hours**. v2's schedule needs 26 working hours with no slack.
- **Judging.** We are entering **Build Ambitious: "A SaaS product, in a day."** The card says: *"Show us the product you chose, working end to end. Completeness is the core of it. What stands out: speed and engineering depth."* Judges reward one reference product that clearly works. They don't reward ten features that each half work.
- **The screen says "Pick one."** v2 also claims the Build Creative track as a differentiator. We drop that claim (see §3).

The rule for every cut below: **if it doesn't make the chosen product more complete or the engineering visibly deeper in a four-minute demo, it goes.**

## 1. Product in one sentence

**Zoho Books expenses and payables, operated entirely by voice in Hindi, English and Hinglish.** Drop a receipt or vendor bill, answer one question, approve aloud, and see the exact budget and balance change, backed by records.

- **Reference product:** Zoho Books (Expenses + Bills + Budgets, plus the Receivables report). Expensify is the comparison for employee reimbursements.
- **What we add to it:** you speak the job instead of filling forms. The agent asks only the questions that change the outcome. Every number it speaks comes from SQL, and every write goes through a preview and an explicit confirmation.

## 2. P0: what must work, deployed on AWS

| # | Capability | Done when |
|---|---|---|
| 1 | **Voice session** in the browser: mic, live captions, spoken replies, push-to-talk fallback, reconnect button | A spoken request runs a server tool and the result is spoken back, on the deployed HTTPS URL |
| 2 | **"What needs my attention?"** (light briefing): pending approvals, bills due within 7 days, overdue receivables, top 3 spoken | Same items on screen and in speech, ranked by due date |
| 3 | **Receipt/bill intake** (PDF, JPEG, PNG): extract fields with a vision model and structured output, check the arithmetic in code, show the source page | A fresh receipt produces a correct draft. Wrong totals are flagged, not hidden |
| 4 | **"Who paid?" routing:** employee paid → expense claim; company/vendor → vendor bill. Links to Arjun's seeded Pune trip when dates match | The same receipt becomes a claim or a bill depending on the answer, and the amount isn't asked twice |
| 5 | **Approval with confirmation:** preview → "Haan / yes" → commit once → read-back receipt. Server enforces approval limits and no self-approval | Saying yes twice creates one decision. Self-approval and over-limit approval are rejected with a spoken reason |
| 6 | **Budget effect:** append-only ledger (allocate, reserve, release, commit, spend); "how much travel budget is left?" | v2's worked example passes: ₹50,000 / ₹5,000 reserved → **₹45,200** after approval and again after reimbursement |
| 7 | **Settle:** "mark Arjun reimbursed, reference UTR…" and "mark the AWS bill paid" | Settlement row with reference; the claim or bill shows as settled; committed moves to spent |
| 8 | **Receivables chart:** "who owes us money?" → bar chart; "only overdue" → revised chart; "read Acme's amount" | Spoken total = chart total = SQL total |
| 9 | **Decision history:** actor, action, amount, timestamp and source document for every write | Opened at the end of the demo |

**Data:** a seeded demo company (synthetic, labelled as such) with Priya (finance manager, approver) and Arjun (employee), 6 vendors, 5 customers with open and overdue invoices, a Travel budget, and one Pune trip with a ₹5,000 hotel reservation. Fresh receipts and bills are the live input.

## 3. What we cut, and why

### Cut from P0 (stretch only if P0 is green on AWS)

| Cut | Where it goes | Why |
|---|---|---|
| **Contract liability review (MSA scan, cited findings)** | Roadmap slide | (a) It's a **different reference product** (Ironclad, not Zoho Books), so it weakens "the product you chose, end to end". (b) It needs its own pipeline: page-anchored segmentation, party-role resolution, cross-clause linking and quote verification. That's 3 hours or more on its own. (c) Its demo minute would come out of the core loop. (d) A wrong legal finding on stage does more harm than leaving the feature out. |
| **Spreadsheet import with column mapping** | P1 as a *fixed-mapping CSV* import | Header detection, typed transforms, row-level outcomes, templates and retries make up a large surface where messy real data fails unpredictably. The receipt drop already proves "fresh input → useful outcome". Seeding uses a plain script, not this feature. |
| **Sending payment reminders (SES), outbox, delivery reconciliation** | P1: preview plus send to one verified inbox | SES needs identity verification and sandbox approval, and the outbox/reconciliation design is a production reliability problem. A preview card shows the same agent ability at a fraction of the risk. |
| **Budget transfer, rollover, freeze, forecast** | Transfer is P1; the rest is roadmap | The ledger design supports them (they're just more movement types), so the engineering depth is already visible. Each one adds a confirmation flow and edge cases without strengthening the main story. |
| **Multi-role auth, invitations, real identity provider** | Two seeded logins (Priya, Arjun) | Judges can't see auth quality in four minutes. The actor is still fixed on the server for each session, so the separation-of-duties checks remain real. |
| **Two-tenant isolation tests, composite cross-workspace foreign keys** | Keep a `workspace_id` column on every table; skip the rest | The column costs nothing and keeps the door open. Enforcing and testing multi-tenancy is production work with no demo value this weekend. |
| **Background job leases, resumable jobs, task suspend/resume** | Roadmap | They're only needed for long scans and big imports, both of which are cut. A single receipt extracts synchronously in a few seconds. |
| **Morning briefing as a ranking and notification engine** | Replaced by the light "what needs my attention" query (P0 #2) | The light version gives the same demo moment with one SQL query instead of a notification system. |
| **Partial reimbursements by voice, bulk approvals, batch undo** | Roadmap | The data model stores amounts, so partial settlement works for seeded rows. The voice flows for these add edge cases, not story. |
| **Calendar, travel booking, bank reconciliation, inbox/Drive sync** | Roadmap (already P1/P2 in v2) | Stated here so there's no doubt: none of them get started. |
| **Extra formats: DOCX, HEIC, XLS, ZIP** | Roadmap | PDF, JPEG and PNG cover receipts and bills. Every extra format needs safety limits and fixture testing. |
| **Claiming the Build Creative track** | Dropped | The card says "Pick one". v2's "same question before and after an approval gives a different answer" is just data freshness, which any database has. Judges may see the claim as stretching. Munshi's real story is stronger without it. |

### Smaller simplifications (still the same behaviour)

- **Tool-call path.** The browser opens the voice session with a short-lived key minted by the backend. When the model calls a tool, the browser forwards the call to `POST /api/tools/{name}`, the server checks the session actor and executes it, and the browser returns the result to the session. The v1 server "sideband" design stays optional: use it only if the hour-0 spike shows it's just as quick. **Why:** this works on any host and is the fewest moving parts.
- **Confirmation contract, kept but slimmed.** A proposal row stores the actor, tool, frozen arguments, their hash, the target record's version, a 10-minute expiry and an idempotency key. Confirmation re-checks authorization and the version inside one transaction. **Why:** this is the main engineering-depth claim, so it stays. The outbox and provider reconciliation go because email sending is cut.
- **Evaluation sized to fit** (§6). v2's 40 + 30 + 25 + workbooks + agreements becomes about 45 items that we will actually run.

## 4. Four-minute demo (golden path)

| Time | What the judge sees | What it proves |
|---|---|---|
| 0:00–0:30 | Priya, in Hindi: "आज क्या pending है?" → top 3 spoken and shown. "Travel budget kitna bacha hai?" → ₹45,000, with the basis stated | Voice in Hindi; numbers from records; labelled demo company |
| 0:30–1:55 | She drops a **fresh** hotel receipt → "This matches Arjun's Pune trip. Did Arjun pay or the company?" → "Arjun ne" → claim preview → "submit" → "approve" → "Haan" → read-back → "travel budget?" → **₹45,200**, with the release and commit rows shown | Extraction, one clarifying question, confirmation, exact budget change |
| 1:55–2:40 | She drops a vendor bill → "company paid" → bill → approve → "mark it paid, UTR 4471…" → settled | Same intake, other branch; settlement with a reference |
| 2:40–3:25 | "Who owes us money?" → chart → "only overdue" → revised → "read Acme's amount" | Spoken number = chart = SQL |
| 3:25–4:00 | Decision history → evaluation numbers → one architecture slide | Traceability; measured results; AWS |

Backup: a screen recording of the same path on the deployed URL, labelled as a recording.

## 5. Architecture (minimum that ships)

```
Browser (React + TS, ECharts)
  ├─ WebRTC mic/speaker ⇄ OpenAI voice session (short-lived key from backend)
  └─ tool calls ⇄ FastAPI /api/tools/* (session cookie → fixed actor)
FastAPI (Python, Pydantic tools, SQLAlchemy + Alembic)
  ├─ services: intake, claims, bills, budget ledger, receivables, proposals, audit
  ├─ OpenAI: vision extraction (structured output); models from env vars
  └─ Postgres (RDS) · S3 (uploads, private) · Secrets Manager (OpenAI key)
AWS: one container (API + built SPA) on ECS Fargate behind an ALB · CloudWatch logs
```

- **Voice model.** Use whatever the hour-0 spike confirms on our account. PLAN.md lists the candidates checked on 2026-11-21: GPT-Live, or the Realtime fallback. Model names live in env vars, as CLAUDE.md requires.
- **Networking.** Fargate tasks run in public subnets with a public IP, which gives outbound access to OpenAI with **no NAT gateway**. RDS sits in private subnets, reachable only from the task's security group.
- **HTTPS is mandatory.** Browsers only allow the microphone on secure origins. Use an ALB with an ACM certificate if we have a domain. Otherwise put CloudFront in front of the ALB and use the default `*.cloudfront.net` certificate (verify this works for our request types during the deploy step).
- **Infrastructure:** one small Terraform root (VPC, ECR, ECS service, ALB, RDS, S3, secret, log group). **CI:** lint + tests + frontend build on push. **CD:** a GitHub Actions deploy via OIDC *after* the first manual deploy works. Don't let the pipeline block the first live URL.
- **Spend:** needs your explicit go-ahead before `terraform apply`. Price-check the region first, then set a budget alert and a teardown date.

## 6. Evidence for the submission

The submission asks for baseline comparisons and proof on new data. We will run:

1. **Golden-path task suite (text harness, same tools):** 15 scripted tasks, covering 8 happy paths, 4 tricky ones (two Arjuns, an ambiguous date, a wrong total, an over-limit approval) and 3 that must be refused (self-approval, a repeated yes, a stale preview). Metric: **correct final database state** and **zero unexpected writes**.
2. **Indian-voice baseline vs Munshi:** about 20 recorded Hindi, Hinglish and English commands containing amounts ("साढ़े चार हज़ार", "4.8k", "₹18,400"), Indian names and dates. **Baseline:** raw transcript plus one plain LLM extraction call. **Munshi:** the same audio through our session, workspace entity resolution and code-side normalization. Metric: exact match on amount, party and date, reported per language.
3. **Extraction on fresh documents:** about 10 receipts and bills that were *not* used during development. Field exact-match before and after the arithmetic check.

Only measured numbers go on the slide, with sample sizes. Anything not run is labelled "not measured".

## 7. Build order (clock times, IST)

| When | Deliverable | Exit test | If it slips |
|---|---|---|---|
| Sat 11:30–12:45 | **Voice spike:** session, one dummy tool round trip, Hindi smoke test | Speak → server tool → spoken answer | By 13:00 switch to the Realtime fallback; by 14:00 switch to push-to-talk (transcribe → Responses → TTS) |
| 12:45–15:30 | Schema, seed data, budget ledger, claim/bill state machines, proposal/confirm service, audit; tests for the ₹45,200 example, idempotency and self-approval | Tests pass | Drop the vendor bill state machine (claims only) |
| 15:30–18:30 | Intake: upload → extraction → arithmetic check → who paid? → claim or bill → approve → budget, all via the text harness | Golden steps 0:30–1:55 pass as text | Support one document type (receipts only) |
| 18:30–19:15 | Break | | |
| 19:15–22:00 | Voice UI: mic, captions, cards (evidence, preview, receipt, budget), confirm/cancel buttons | Golden path spoken locally | Captions and cards only, minimal styling |
| 22:00–01:00 | **First AWS deploy** (needs spend approval): Terraform, image push, migrate, seed, HTTPS smoke test | Golden path on the deployed URL | If blocked by 01:00, stop, mark it BLOCKED, sleep, and give it a 2-hour cap in the morning |
| 01:00–07:00 | Sleep | | |
| Sun 07:00–09:30 | Settlement, receivables chart and revision, light briefing, decision history | Demo 1:55–4:00 works locally | Drop the briefing (start the demo at the receipt) |
| 09:30–11:00 | Run the evaluation (§6), fix failures, CI workflow, redeploy | Numbers recorded; deployed smoke test passes | Report partial sample sizes honestly |
| 11:00–12:15 | **One** P1 item only if everything above is green: transfer, reminder preview or CSV import | Works on the deployed URL | Skip it |
| 12:15–13:30 | Rehearse ×3, record the backup, README and run steps, honest note, slides | Demo under 4:00 from a fresh seed | |
| 13:30–14:00 | Buffer → **freeze** | | |

## 8. Top risks

| Risk | Mitigation |
|---|---|
| Voice model access or tool-call quirks | Hour-0 spike, with two fallbacks decided ahead of time (§7) |
| Hindi number and name errors | Normalize amounts and dates in code; read back the amount and name before any confirmation |
| Extraction errors on real receipts | Arithmetic check in code; show the source page; Priya corrects by voice before anything is submitted |
| AWS setup eats the night | Hard stop at 01:00; the local build stays demoable; the backup recording is made in the morning |
| Scope creep from v2 | Nothing from §3 starts until P0 is green on the deployed URL |
