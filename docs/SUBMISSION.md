# Diwan: the voice-first back office for Indian SMBs

> **Diwan:** in a princely state, the official who ran both the treasury and the administration. Codename in the repo: `Purser`.

**Theme:** 3, SaaS in a day (reference product: Zoho Books expenses and payables, extended into HR)
**One-liner:** Speak to your back office in Hindi, English or Hinglish. Diwan reads bills, routes claims, moves budgets, approves leave and onboards people. It always shows you the exact effect first and never writes money without your confirmation.

---

## 1. The problem

Most Indian SMBs, from about 10 to 200 people, run finance and HR on a mix of WhatsApp photos of receipts, Excel sheets, Tally entries and one overloaded finance/admin person.

- **The admin person is the bottleneck.** One person chases receipts, works out who paid, checks budgets, approves leave and answers "how much do customers owe us?" All of it goes through screens built for accountants.
- **Tools assume English and a desk.** Owners and managers think and talk in Hindi or Hinglish, often on the move. Form-heavy SaaS (Zoho, Tally, Keka) has low adoption outside the finance team.
- **Budgets are tracked after the fact.** Teams find out a budget line is blown at month-end close, not when the expense arrives.
- **Chatbots are not safe for money.** A generic AI assistant that "just does it" cannot be trusted with approvals, payments or employee records. Nothing proves what it changed, why, or who agreed.

## 2. The solution

Diwan is a single AI agent that you talk to. It is backed by a real accounting ledger and an HR system.

| You say | Diwan does |
|---|---|
| *"Diwan, aaj kya pending hai?"* | Reads the top items from pending approvals, bills due this week, overdue invoices and budget alerts. The same list appears on screen. |
| *(drop a hotel receipt)* "Arjun ne pay kiya tha" | Reads the document, checks the arithmetic and duplicates, and matches it to Arjun's Pune trip reservation. It drafts a reimbursement claim and shows the budget impact. |
| *"Approve kar do"* → *"haan"* | Approves the claim. It releases the ₹5,000 reservation and commits ₹4,800 in one transaction, then speaks the receipt: Travel available goes from ₹45,000 to ₹45,200. |
| *"Kaun paisa dena baaki hai?"* → *"sirf overdue"* → *"Acme ka amount padho"* | Builds a receivables chart, narrows it to overdue invoices and reads out Acme's ₹1,25,000 with the bar highlighted. Speech, chart and table come from the same snapshot. |
| *"October close karo"* | Closes the month with spoken variance reasons and carries over unspent budget. It then recommends reallocations, for example "Events -66.7%, IT & Cloud +68.4%", and applies them only after you say yes. |
| *"Neha ko 1 Dec se Sales executive add karo, Priya ko report karegi"* | Previews the login, manager, leave balances and onboarding checklist. On confirmation it creates everything and sends a welcome message (inbox plus email). |
| *"Kal aur parson casual leave chahiye"* | Counts working days, shows the balance after the leave and submits it. The manager approves by voice. |

The interface is deliberately minimal: a voice orb and a panel of cards. The agent decides which artifacts to show (charts, previews, receipts, source documents), based on what you asked.

## 3. Why AI, and what the AI actually does

The AI handles what is ambiguous. Everything else is deterministic.

| AI does (OpenAI) | Deterministic code does |
|---|---|
| Understands speech in Hindi, English and Hinglish | All money arithmetic, in integer paise |
| Reads unstructured receipts and bills (vision extraction) | Ledger postings, budget buckets, leave balances |
| Decides which of 44 tools to call over a multi-turn conversation, and remembers context ("only overdue", "read Acme") | Database queries; the model never writes SQL |
| Resolves ambiguity: "Did Arjun pay, or is the vendor still owed?" | Duplicate detection (file hash plus party, amount and date) |
| Composes charts and views from a typed spec | Authorization, idempotency and audit trail |
| Explains changes and drafts messages and variance reasons | Budget pacing, forecasts and recommendations |

**Every number Diwan speaks comes from a database query, never from the model's memory.**

## 4. The trust boundary: propose → present → confirm → receipt

This makes a voice agent safe for finance.

1. **Propose.** Every write tool (`propose_settlement`, `propose_leave`, ...) only creates a proposal. The proposal stores the exact arguments, the affected records and their versions, a preview generated on the server and a 10-minute expiry.
2. **Present.** Diwan speaks the exact effect and shows it on screen: "Record ₹4,800 to Arjun against claim C12, reference 4471?"
3. **Confirm.** A spoken "yes/haan" counts only if **the server itself heard it** on its own audio transcript, after the preview was shown, and a deterministic multilingual classifier accepts it. A browser or model claiming "the user said yes" is ignored. A Confirm button (cookie plus CSRF) is always available as well.
4. **Receipt.** The change runs in one database transaction: re-authorize, lock rows, check versions, post to the ledger, write the audit row, issue the receipt. Saying "yes" twice returns the same receipt, so nothing is paid twice. If the data changed in the meantime, Diwan shows a fresh preview.

Policy is enforced in code: a beneficiary cannot approve their own claim, an employee cannot see another employee's claim, and a second settlement of the same bill is rejected.

## 5. Architecture

```
Browser (React + Vite, voice orb + cards)
   │  WebRTC audio                         ▲ SSE: cards, captions
   ▼                                       │
OpenAI GPT-Live (speech in/out)  ──delegation──►  FastAPI backend
                                    sideband       ├─ Agents SDK: Diwan agent (44 typed tools)
                                    (server hears  ├─ Vision extractor agent (structured output)
                                     the "yes")    ├─ Proposal / confirmation / receipt engine
                                                   ├─ Ledger, budgets, leave, outbox (email)
                                                   └─ PostgreSQL (append-only ledgers, audit)
```

- **Voice:** OpenAI GPT-Live over browser WebRTC with client delegation. The API key never reaches the browser. A Python sideband connection receives the server-side transcript and runs the agent.
- **Agent:** OpenAI Agents SDK, a single agent with 44 typed tools. The actor and workspace come from the server session, never from model arguments. Conversation memory is stored in Postgres.
- **Data:** PostgreSQL with Alembic migrations, append-only budget and leave ledgers, and a transactional email outbox that sends only after commit.
- **AWS target:** one container on ECS Fargate behind HTTPS (ALB), private RDS PostgreSQL, a private S3 bucket for uploads, Secrets Manager for keys, CloudWatch logs. Terraform and a GitHub Actions deploy with OIDC (no long-lived AWS keys).

## 6. What is already built (Saturday, 21 Nov)

| Area | Status |
|---|---|
| Voice loop: speech → agent → tool → spoken answer, with server-observed confirmation | Working locally. Spike evidence: "Travel budget mein kitna bacha hai" → `get_budget_status` → "₹45,000 bacha hai" |
| Expense and bill intake: PDF/JPG/PNG, extraction, arithmetic check, duplicate and replay detection, reservation matching | Working locally |
| Claims and vendor bills: submit → approve → settle, with the ₹45,000 → ₹45,200 budget golden path | Working locally |
| Agent-built receivables and budget charts, with voice revision ("sirf overdue") | Verified through the real agent and in the browser |
| Monthly budget brain: pacing, alerts, month close, carry-over, recommendations, forecasts, what-if | Verified through the real agent (Hinglish) |
| People ops: onboarding, leave with approvals, announcements and inbox, real email to an allow-list, policy Q&A | Working locally. A real email was delivered in a check |
| Automated tests | **353 passing, 0 failing** in the latest full run. An independent tester agent wrote them and found 11 real bugs, all fixed |
| AWS deployment | **Not yet deployed.** Planned for the next build block |

## 7. Plan to the Sunday 14:00 freeze

1. Deploy to AWS (Fargate, RDS, S3, HTTPS) and run the spoken golden path on the live URL.
2. Bring upload → spoken answer latency down to about 5 seconds.
3. Run a frozen evaluation set, about 15 text workflows, 20 recorded voice commands in Hindi, Hinglish and English, and 10 held-out documents. Report accuracy for amount, party and date per language, plus zero unauthorized or duplicate writes.
4. Set up CI/CD (GitHub Actions with OIDC), the demo script, a labelled backup recording and a timed rehearsal.

## 8. How we will prove value

- **Accuracy:** per-language accuracy of amount, party and date (with denominators). This compares plain transcription plus extraction against Diwan's full context-assisted workflow on the same recordings.
- **Safety:** zero unauthorized writes, zero duplicate payments, ledger totals conserved across the whole eval run.
- **Effort:** a receipt goes from upload to approved and posted to the budget in one spoken conversation, with a target of under 2 minutes. The time will be measured in the demo run.
- **Traceability:** for every change, the user can say what changed, who approved it and which source document supports the amount.

## 9. Honest note

- **Built at the event:** the application code (backend, agent, tools, voice bridge, UI, tests), written with Claude Code under the builder's direction. A full authorship log is in `docs/AUTHORSHIP.md`.
- **Reused:** budget maths (pacing, status bands, forecast, recommendations) from the builder's own earlier project, disclosed file by file. Open-source libraries: FastAPI, SQLAlchemy, OpenAI SDKs, React and ECharts.
- **Simulated:** all company, employee, vendor and customer data is synthetic and labelled. July to September budget actuals are a synthetic "imported snapshot". Real email goes only to allow-listed demo addresses.
- **Not yet done:** AWS deployment and the formal evaluation run. Claims above are limited to what has been verified locally.

## 10. Beyond the weekend

Contract approval chains, amendments and redlining, bank statement reconciliation, bulk and spreadsheet imports, payroll and attendance, WhatsApp as a voice channel, multi-tenant onboarding.
