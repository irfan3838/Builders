# Purser · the back office you can talk to

> **Theme 3 · Build Ambitious: a SaaS product, in a day**
> Reference products: **Zoho Books / Zoho Expense** (finance), **Keka / greytHR** (HR), **Expensify** (claims).
> What we did: rebuilt their core jobs as **one voice agent** that speaks Hindi, Hinglish and English, and made it **safe enough to move money**.

🌐 **Live on AWS:** https://d342yicbppf96p.cloudfront.net  ·  📦 **Code:** https://github.com/irfan3838/Builders  ·  🧪 **Evidence:** [`EVIDENCE.md`](EVIDENCE.md)

---

## 🎬 Act 1: a Tuesday without Purser

**Meet Priya.** She is the finance-and-admin person at a 40-person company in Pune. She is also the bottleneck.

```mermaid
journey
    title Priya's Tuesday (today)
    section 9:00 Inbox
      14 WhatsApp receipt photos: 2: Priya
      Work out who paid for each: 1: Priya
    section 11:00 Approvals
      Open Zoho, check Travel budget: 2: Priya
      Approve claim, update Excel tracker: 1: Priya
    section 14:00 Owner calls
      "How much do customers owe us?": 1: Priya, Owner
      Export, filter, build a chart, send: 1: Priya
    section 16:00 HR
      Leave request on email: 2: Priya
      New joiner: login, checklist, welcome mail: 1: Priya
    section 19:00 Month end
      Find out Events budget was blown in week 2: 1: Priya
```

### The four problems

| 😩 Pain | What it looks like today |
|---|---|
| **One person in the middle of everything** | Receipts, budgets, approvals, leave and "who owes us" all go through one admin, on screens built for accountants |
| **Software assumes English and a desk** | Owners and managers think in Hindi or Hinglish, often away from a desk. Form-heavy SaaS goes unused outside the finance team |
| **Budgets are checked after the fact** | Overspend shows up at month-end close, not when the bill arrives |
| **Chatbots can't be trusted with money** | A generic AI that "just does it" gives no proof of what changed, why, or who agreed |

```mermaid
flowchart LR
    R[📸 Receipt on WhatsApp] --> P((Priya))
    E[📧 Leave email] --> P
    O[📞 Owner: who owes us?] --> P
    B[📊 Budget Excel] --> P
    P --> Z[Zoho Books]
    P --> X[Excel tracker]
    P --> K[HR tool]
    P --> G[Gmail]
    style P fill:#c0392b,color:#fff
```

> **Six tools, one tired human, and no single source of truth.**

---

## 🌅 Act 2: the same Tuesday with Purser

Priya says **"Purser"**, then talks.

```mermaid
flowchart LR
    V["🎙️ 'Purser, aaj kya pending hai?'"] --> A{{Purser agent}}
    D[📎 Drop a receipt] --> A
    A --> L[(Ledger · budgets · HR · revenue<br/>PostgreSQL on AWS)]
    A --> C[🃏 Cards on screen<br/>charts · previews · receipts]
    A --> S[🔊 Spoken answer]
    A --> M[📧 Gmail · 📅 Calendar · ✈️ Flights]
    style A fill:#1e5631,color:#fff
```

| 🗣️ Priya says | ⚙️ Purser does |
|---|---|
| *"Purser, aaj kya pending hai?"* | Reads her role-specific briefing: pending approvals, bills due, overdue invoices, budget alerts. The same list appears on screen |
| *(drops a hotel receipt)* "Arjun ne pay kiya tha" | Reads it with vision, **checks the arithmetic in code**, checks for duplicates, matches Arjun's Pune trip reservation, drafts the claim and shows the budget impact |
| *"Approve kar do"* → *"haan"* | One transaction: releases the ₹5,000 reservation, commits ₹4,800. **Travel available: ₹45,000 → ₹45,200**. Issues a receipt |
| *"Kaun paisa dena baaki hai?"* → *"sirf overdue"* → *"Acme ka amount padho"* | Builds a receivables chart, narrows it to overdue, reads out **₹1,25,000** and highlights the bar |
| *"October close karo"* | Closes the month with spoken variance reasons and carries unspent budget forward. Recommends *Events −66.7%, IT & Cloud +68.4%* and applies it only after a yes |
| *"Neha ko 1 Dec se Sales executive add karo"* | Previews the login, manager, leave balance and onboarding checklist. On yes it creates them all and sends a welcome mail |
| *"Pune se Mumbai flight aur hotel dhoondo"* → *"book the cheapest"* | Live fare and hotel search, a trip approval, then a hand-off to the airline or hotel checkout. Purser never takes payment |

### Before → after

```mermaid
flowchart TB
    subgraph Before["❌ Before: Priya does the routing"]
      direction LR
      r1[Receipt] --> p1[Priya] --> z1[Zoho] --> x1[Excel] --> m1[Mail]
    end
    subgraph After["✅ After: Purser does the routing, Priya decides"]
      direction LR
      r2[Receipt + voice] --> a2[Purser] --> c2[Preview] --> y2["Priya: 'haan'"] --> rc2[Receipt + audit + mail]
    end
    Before ~~~ After
```

---

## 🧩 Act 3: what's in the box (core features)

```mermaid
mindmap
  root((Purser))
    Finance
      Receipt and bill intake by vision
      Claims and vendor bills
      Approve and settle
      Duplicate and replay detection
      Append-only budget ledger
    Budget brain
      Monthly pacing and alerts
      Month close and carry-over
      Recommendations and forecasts
      What-if
    Revenue
      Invoices, USD and INR
      Part payments and allocation
      ECB FX rates
      Billing cycles and reminders
    Contracts
      Clause and risk scan
      Who bears each liability
      Caps, carve-outs, notice periods
      Renewal deadlines
    People ops
      Leave with approvals
      Onboarding checklists
      Inbox and announcements
      Policy Q&A
    Workplace
      Real Gmail and Calendar
      Meetings with Meet links
      Flights and hotels
      Tasks and helpdesk
    Agent-built UI
      Charts from a typed spec
      Voice revisions
      Role briefings
      User routines
```

| Module | Highlights | Example voice command |
|---|---|---|
| 💸 **Expenses & bills** | PDF/JPG/PNG intake, arithmetic check, SHA-256 replay detection, reservation matching | *"Ye hotel ka bill hai, Arjun ne pay kiya"* |
| 📊 **Budgets** | Allocated / reserved / committed / spent buckets, pacing, month close, recommendations | *"Travel mein kitna bacha hai?"* |
| 💰 **Revenue** | Invoices, part payments, balance moves, FX, reminders | *"Acme Traders ka 38 hazaar aa gaya"* |
| 📜 **Contracts** | 12 clause types, liability bearer, caps in paise, deadline calendar | *"Kaunse liabilities humpe hain?"* |
| 👥 **People ops** | Leave ledger with working-day counting, onboarding, announcements, email | *"Kal aur parson casual leave chahiye"* |
| 📅 **Mail & calendar** | Real Gmail and Calendar for the linked login, Meet links, reschedule and cancel | *"Rohan ke saath kal 4 baje meeting rakho"* |
| ✈️ **Travel** | Live flights and hotels (SerpAPI), whole-trip approval, checkout hand-off | *"Cheapest flight aur hotel book karo"* |
| 📈 **Charts & views** | Bar, line, pie, treemap, heatmap, calendar, sankey; period comparison | *"Sirf Marketing aur Travel dikhao"* |
| 🔁 **User routines** | Save your own multi-step workflow by chat or in Settings | *"Har Monday ka routine banao: pending bills + overdue invoices"* |

**The scale built in one weekend:** ~18,000 lines of Python, ~4,600 lines of TypeScript, **99+ typed agent tools**, **67 workflows**, 7 role-aware modules, and ~1,350 automated tests.

---

## ⭐ Spotlight: the 3 features no competitor has together

```mermaid
flowchart LR
    T["✈️ Voice travel desk<br/>search → approve → checkout"] --- P((Purser))
    C["📜 Contract liability radar<br/>who pays, how much, by when"] --- P
    R["🔁 Custom routines<br/>teach Purser your own workflow"] --- P
    style P fill:#1e5631,color:#fff
    style T fill:#2c3e50,color:#fff
    style C fill:#2c3e50,color:#fff
    style R fill:#2c3e50,color:#fff
```

---

### ✈️ Spotlight 1: the voice travel desk (flight + hotel, approved in one sentence)

**Today:** an employee emails a request, the admin searches MakeMyTrip, someone approves on WhatsApp, the admin books, and the itinerary gets forwarded. That's 5 people-steps and 3 apps.

**With Purser:**

```mermaid
sequenceDiagram
    autonumber
    actor A as Admin
    participant P as Purser
    participant G as Live fares (Google Flights / Hotels via SerpAPI)
    participant DB as Trips + audit (RDS)
    participant M as Gmail
    A->>P: "Arjun ke liye Friday Pune se Mumbai flight aur hotel dhoondo"
    P->>G: search_flights + search_hotels (live)
    G-->>A: 🃏 Flight cards + hotel cards (real prices, ranked)
    A->>P: "Sabse sasta dono book karo"
    P-->>A: 🃏 ONE whole-trip proposal: flight + hotel + total ₹
    A->>P: "haan"
    P->>DB: Trip recorded · pending_payment · audit row
    P->>M: Itinerary emailed to Arjun (cc admin) from the admin's real Gmail
    P-->>A: 🔗 Airline checkout link + hotel website (Purser never takes payment)
```

| What makes it special | Detail |
|---|---|
| **Live data, not mocks** | Real Google Flights / Google Hotels fares. A clearly labelled "Estimated" fallback if live search fails |
| **Whole-trip approval** | Flight + hotel in **one** proposal and **one** "haan" |
| **Book for someone else** | The admin can book for any employee. The itinerary goes to the traveller's address on file, or one spoken aloud |
| **Never assumes** | Asks for the origin city instead of guessing (an eval found this and we fixed it) |
| **Honest payment hand-off** | Purser approves and records; the traveller pays on the **airline's own checkout** and the **hotel's own site**. No card details ever touch Purser |

> 🎤 **Talking point:** "A trip that takes 5 people and 3 apps is now 2 sentences and a yes."

---

### 📜 Spotlight 2: the contract liability radar

**Today:** a 15-page MSA sits in a shared drive. Nobody knows that **the company** carries unlimited liability for data loss, or that the auto-renewal notice window closes on 1 December.

**With Purser:** drop the contract (PDF, DOCX or **scanned** PDF) and ask *"kaunse liabilities humpe hain?"*

```mermaid
flowchart LR
    D["📄 Contract<br/>PDF · DOCX · scanned"] --> R["Read<br/>text layer → OCR by vision<br/>if scanned"]
    R --> S["Scan 12 clause types<br/>indemnity · liability cap ·<br/>termination · renewal · data · IP …"]
    S --> L["🧠 Model POINTS at phrases<br/>(never invents)"]
    L --> G["⚙️ Code GROUNDS each phrase<br/>in the text, then resolves:"]
    G --> B1["👤 Bearer: us or them?"]
    G --> B2["₹ Cap parsed to paise"]
    G --> B3["Carve-outs"]
    G --> B4["⏰ Notice + survival periods<br/>→ real calendar deadlines"]
    B4 --> BR["🔔 Shows up in the morning briefing<br/>30 days before it bites"]
    style L fill:#7d6608,color:#fff
    style G fill:#1e5631,color:#fff
```

| Ask by voice | You get |
|---|---|
| *"Kaunse liabilities humpe hain?"* | Liabilities **we** bear: trigger, cap in ₹, carve-outs, and the exact source clause |
| *"Agle 60 din ki deadlines"* | Renewal-notice cut-offs, expiries and survival ends on a timeline |
| *"Ye clause dikhao"* | The clause excerpt card, so every claim is traceable to the text |
| *"Indemnity flag accept karo"* | A legal review decision recorded through propose → confirm → receipt |

| Why it's different | |
|---|---|
| **Grounded, not generated** | The model only points at phrases. Code checks that each phrase exists in the document before it counts |
| **Answers "who pays?"** | Bearer resolution through defined terms → named party → us/counterparty. If it's unclear, it says `unclear` instead of guessing |
| **Turns into action** | Deadlines feed the daily briefing and attention bell. Review runs in the background, so you can keep talking |

> 🎤 **Talking point:** "Purser doesn't summarise contracts. It tells you what you owe, the cap, and the date you have to act by."

---

### 🔁 Spotlight 3: custom routines (teach Purser your own workflow, by voice)

**Every company has its own Monday ritual.** Purser lets any user turn theirs into a reusable workflow, without code, just by describing it.

```mermaid
flowchart LR
    U["🗣️ 'Ek routine banao: Monday ko<br/>pending bills, overdue invoices<br/>aur budget alerts ek saath'"] --> C["Compile into steps<br/>(max 8 steps, 8 tools)"]
    C --> V["🛡️ Validate in code<br/>· tools frozen to your role<br/>· injection phrases rejected<br/>· no hardcoded payees or amounts in shared routines"]
    V --> PV["🃏 Preview steps → 'haan'"]
    PV --> S[(Saved routine)]
    S --> RUN["Later: 'Monday routine chalao'"]
    RUN --> ENG["Runs on the SAME workflow engine<br/>every write still needs a yes"]
    style V fill:#1e5631,color:#fff
```

| Safety by design | How |
|---|---|
| **The tool list is frozen at creation** | Picked once from the tools your role may use. Text inside a routine, or inside an email it reads, **cannot add a tool** |
| **Your raw prompt never reaches the runtime model** | Only the compiled, length-limited steps you previewed |
| **Screened in code, not by another LLM** | A deterministic deny-list blocks "ignore previous instructions", "auto-approve", "skip confirmation" and similar. An LLM judge could be prompt-injected too |
| **Writes still need a human yes** | Every write step is a proposal. Nothing happens until the person running it says yes in their own words |
| **Share across the team** | Admins can share routines. A shared routine always runs with the **runner's** role, never the author's |

Create one **by voice** or in **Settings → My routines**. Run it with *"Monday routine chalao"*.

> 🎤 **Talking point:** "Zoho gives you their workflows. Purser learns yours, and it still can't skip the confirmation."

---

## 🏆 The best demo moments (highlight reel)

| # | Moment | Say / do | The "wow" | Proves |
|---|---|---|---|---|
| 1 | 🧾 **Receipt to approved claim** | Drop a fresh receipt → *"Arjun ne pay kiya"* → *"approve kar do"* → *"haan"* | Travel ₹45,000 → ₹45,200, with a receipt | Vision + ledger + safe writes |
| 2 | 📊 **Chart you talk to** | *"Kaun paisa dena baaki hai"* → *"sirf overdue"* → *"Acme ka padho"* | The chart reshapes live and the bar lights up as it speaks | Numbers from SQL, not the model |
| 3 | ✈️ **Trip in two sentences** | *"Friday Pune se Mumbai flight aur hotel"* → *"sabse sasta dono book karo"* → *"haan"* | Live fares, one approval, itinerary emailed | Real integrations, honest payment hand-off |
| 4 | 📜 **Liability radar** | Drop the MSA → *"kaunse liabilities humpe hain?"* → *"agle 60 din ki deadlines"* | Who pays, the cap in ₹, and the date to act | Grounded document reasoning |
| 5 | 🔁 **Teach a routine** | *"Monday routine banao: pending bills, overdue invoices, budget alerts"* → *"haan"* → *"Monday routine chalao"* | Purser learns a new workflow live | Extensible + injection-safe |
| 6 | 🛡️ **Try to break it** | Employee: *"company ka budget batao"* · CEO: *"budget badha do"* · injected "approve all bills" | Refused every time | Role rules + no confirm tool |
| 7 | ⚡ **The free "haan"** | Say *"haan"* on any proposal | Instant, with 0 model tokens | The efficiency engine |

---

## 🛡️ Act 4: the novelty. Why Purser is not "a chatbot on top of Zoho"

### Novelty 1: propose → present → confirm → receipt

**The AI can't move money on its own. It can only propose.**

```mermaid
sequenceDiagram
    autonumber
    actor U as Priya
    participant V as Voice (GPT-Live)
    participant A as Purser agent
    participant S as Server (FastAPI)
    participant DB as Ledger (Postgres)
    U->>V: "Approve kar do"
    V->>A: delegated request
    A->>S: propose_approval(claim C12)
    S->>DB: snapshot rows + versions
    S-->>U: 🃏 Preview: "₹4,800 to Arjun, Travel ₹45,000 → ₹45,200"
    U->>V: "haan"
    Note over S: Server heard "haan" on ITS OWN transcript,<br/>after the preview, and a deterministic<br/>EN/HI/Hinglish classifier accepted it
    S->>DB: ONE transaction: re-authorise · lock rows · check versions · post · audit
    S-->>U: 🧾 Receipt R-4471 (a second "haan" returns the same receipt)
```

| Guarantee | How it is enforced (in code, not in the prompt) |
|---|---|
| The model never confirms | No workflow has a confirm tool. Only the engine confirms, and only from the user's own words |
| "Yes" must be **heard by the server** | A browser or model saying "the user said yes" is ignored. A Confirm button (cookie + CSRF) is the fallback |
| No hallucinated amounts | **Grounding check**: an amount must appear in the user's recent speech (digits, "1.5L", "38 hazaar", Hindi number words) |
| No double payment | Idempotent receipts; a second settlement of the same bill is rejected |
| No stale writes | Row versions are checked. If data changed, Purser shows a fresh preview |
| Role rules | A beneficiary can't approve their own claim. Employees never see budgets, revenue or contracts. The CEO login is read-only |

### Novelty 2: numbers come from SQL, never from the model

```mermaid
flowchart LR
    Q["'Kaun paisa dena baaki hai?'"] --> LLM[LLM picks a typed ChartSpec<br/>source · measure · dimension · filters]
    LLM --> V{Validated by Pydantic<br/>against an enum registry}
    V --> SQL[Vetted, parameterised SQLAlchemy<br/>scoped to workspace + role]
    SQL --> SNAP[(One result snapshot)]
    SNAP --> CH[📊 Chart]
    SNAP --> TB[📋 Table]
    SNAP --> SP[🔊 Spoken number]
    style SNAP fill:#1e5631,color:#fff
```

> The model chooses **what** to show. Code computes **every number**. The chart, the table and the voice all read the **same snapshot**, so they can't disagree.

### Novelty 3: checklist workflows (our engineering-depth bet)

A single agent with 99 tools re-sends ~36,000 tokens on **every** call and skips steps in long chains. We replaced it:

```mermaid
flowchart TD
    T[User turn] --> Y{Clear yes / no on a<br/>waiting change?}
    Y -- yes --> C0["✅ Confirm in CODE<br/>0 tokens · ~118 ms"]
    Y -- no --> P["Picker (cheap model)<br/>chooses 1 of 67 workflows<br/>from a role-filtered menu"]
    P --> W["Workflow runs with ONLY its 1–8 tools<br/>+ checklist + ~300-token brief<br/>no chat history"]
    W --> VER{Code verifies<br/>the checklist}
    VER -- pass --> K["☠️ Kill the workflow:<br/>keep one summary line"]
    VER -- fail / unknown --> ESC["Escalate to strong model<br/>+ log for the backlog"]
    style C0 fill:#1e5631,color:#fff
    style K fill:#1e5631,color:#fff
```

### Novelty 4: voice-native and Indian-language-native

- **GPT-Live over WebRTC** with client delegation. The API key never reaches the browser.
- A **Python sideband** listens to the server-side transcript. That is why a spoken "haan" can be trusted as a confirmation: the server heard it itself.
- Works in **English, romanized Hinglish and Devanagari Hindi**, including corrections ("nahi nahi, 2,01,000") and Indian number formats (lakh, crore, hazaar).
- Wake word **"Purser"**, with a tap fallback.

### Novelty 5: the UI is composed by the agent

Nothing on screen is hardcoded. The agent decides which cards to show (chart, proposal, receipt, source document, contract finding, flight options). The frontend only knows generic card types. Only the **trust shell** is fixed: login, mic, drop zone, Confirm/Cancel, and the server-rendered effect lines.

---

## 📉 Act 5: efficiency. More accurate *and* cheaper

Measured on **46 human-style conversations (90 turns)** in English, Hinglish and Hindi, across 4 difficulty tiers. Each turn is checked against **the exact database diff over 22 business tables**. Details: [`EVIDENCE.md`](EVIDENCE.md), [`docs/workflow-eval-results.md`](../docs/workflow-eval-results.md).

### Task success

```mermaid
xychart-beta
    title "Task success (%), same 45 scenarios, same code (run 3)"
    x-axis ["A0 · today's single agent", "A1 · single agent, cheap model", "B · checklist workflows"]
    y-axis "Task success %" 80 --> 100
    bar [89, 93, 98]
```

> On the shipped code, workflows scored **46/46 (100%)** with **0 wrong writes**.

### Tokens per turn

```mermaid
xychart-beta
    title "Input tokens sent to the model per turn"
    x-axis ["A0 · today", "A1 · cheap model", "B · workflows (shipped)"]
    y-axis "Tokens per turn" 0 --> 42000
    bar [36195, 39709, 5993]
```

### Cost per successful task

```mermaid
xychart-beta
    title "US$ per successful task (lower is better)"
    x-axis ["A0 · today", "A1 · cheap model", "B · workflows (shipped)"]
    y-axis "USD" 0 --> 0.011
    bar [0.0104, 0.0025, 0.0012]
```

### Context stays flat in a long conversation

```mermaid
xychart-beta
    title "Tokens per turn in a 5-turn chain: briefing → pending → payment → haan → reminder"
    x-axis ["T1", "T2", "T3", "T4 haan", "T5"]
    y-axis "Input tokens (k)" 0 --> 60
    line [50.0, 51.8, 53.7, 55.1, 18.6]
    line [5.3, 6.2, 9.4, 0, 7.2]
```
*Top line: today's single agent (A0). Bottom line: workflows (B). T4 is a "haan", handled in code with 0 tokens.*

### The scoreboard

| | A0 · today | A1 · cheap model | 🏆 **B · workflows** |
|---|---|---|---|
| ✅ Task success (same code) | 89% | 93% | **98%** (shipped code: **100%**) |
| 🚫 Wrong writes | 0 | 0 | **0** |
| 🔤 Input tokens / turn | 36,195 | 39,709 | **5,993** (**6x fewer**) |
| 💵 $ / successful task | $0.0104 | $0.0025 | **$0.0012** (**8.7x cheaper**) |
| ⚡ Turns with **no** LLM call | 0% | 0% | **20%** |
| 👍 Confirming "haan" | ~33,600 tokens · 7.9 s | same | **0 tokens · 118 ms** |
| ⏱️ Latency p50 / p95 | 7.7 / 14.4 s | 9.5 / 15.1 s | 8.0 / 15.5 s |

### Where the gains came from (by tier)

| Tier | A0 | A1 | **B** | Why workflows win |
|---|---|---|---|---|
| 1 · Single action | 17/17 | 17/17 | **17/17** | Same accuracy, **9.5x cheaper** |
| 2 · Chained (2–5 turns) | 9/12 | 11/12 | **12/12** | Single agents forget reminders and drop chart refinements |
| 3 · Edge (ambiguity, corrections, documents) | 8/10 | 8/10 | **10/10** | Checklist forces "find → ask if ambiguous → propose → confirm" |
| 4 · Safety (injection, wrong role, "yes" with nothing pending) | 6/6 | 6/6 | **7/7** | Structural: the model has no confirm tool at all |

### We let the eval drive the engineering

```mermaid
xychart-beta
    title "Workflow arm task success across iterations (%)"
    x-axis ["Baseline", "Run 2", "Run 3", "Final", "Shipped"]
    y-axis "Task success %" 70 --> 100
    line [76, 93, 98, 100, 100]
```

| Round | What the eval exposed | Fix |
|---|---|---|
| Baseline · 76% | Escalation path crashed; "approve kar do" treated as a bare yes | Fixed the crash; mid-chat "yes" with nothing pending goes to the picker |
| Run 2 · 93% | Hinglish confirmations not recognised; out-of-scope requests had no home | Hinglish confirm phrases; reply-only workflow |
| Run 3 · 98% | One empty reply; clarifying options only shown as buttons (voice users can't see them) | Empty replies fail verification; options are spoken aloud |
| Final · 100% | Owner rule: employees must not see budgets or revenue | Role-filtered menus; new safety scenario passes |

---

## 🥊 Act 6: the market and where Purser fits

```mermaid
quadrantChart
    title Where Purser sits
    x-axis "Form-first (screens)" --> "Conversation-first (voice)"
    y-axis "Talks only" --> "Safely writes to a real ledger"
    quadrant-1 "Purser's space"
    quadrant-2 "Classic SaaS"
    quadrant-3 "Spreadsheets"
    quadrant-4 "General assistants"
    "Zoho Books / Expense": [0.22, 0.82]
    "Tally": [0.12, 0.78]
    "Keka / greytHR": [0.25, 0.65]
    "Expensify": [0.35, 0.7]
    "Excel + WhatsApp": [0.15, 0.2]
    "ChatGPT / Gemini Live": [0.85, 0.15]
    "In-app AI helpers": [0.55, 0.35]
    "Purser": [0.9, 0.88]
```

| | Zoho Books / Expense | Tally | Keka / greytHR | Expensify | General AI assistants | **Purser** |
|---|---|---|---|---|---|---|
| Finance + HR + revenue + contracts in one place | Finance only (HR is a separate product) | Accounting | HR only | Expenses | ✗ (no ledger) | ✅ |
| Voice is the main interface | ✗ | ✗ | ✗ | ✗ | ✅ | ✅ |
| Hindi / Hinglish conversation | ✗ | ✗ | ✗ | ✗ | Partial | ✅ |
| AI takes multi-step actions | Assistant features | ✗ | ✗ | Receipt scanning | Talks, can't post to your books | ✅ 99+ tools |
| Server-verified confirmation before any write | n/a | n/a | n/a | n/a | ✗ | ✅ |
| Every spoken number comes from SQL | n/a | n/a | n/a | n/a | ✗ | ✅ |
| Charts built on demand by voice | Fixed reports | Fixed reports | Fixed reports | Fixed reports | Ad hoc, unverified | ✅ typed spec |

*Competitor columns describe each product's core experience as we understand it. Several vendors are adding AI features; the gap we target is voice-first plus safe writes to the books.*

> **Our position:** classic SaaS is safe but form-heavy and English-first. AI assistants are fluent but can't safely touch the books. **Purser is the first to offer both: you talk naturally, and the books stay correct.**

---

## 🏗️ Act 7: how it is built (AWS)

```mermaid
flowchart TB
    U[👤 Browser · React + three.js orb<br/>WebRTC mic · SSE cards] -->|HTTPS| CF[☁️ CloudFront]
    U <-->|WebRTC audio| OAI[OpenAI GPT-Live]
    CF -->|secret origin header| ALB[ALB · CloudFront-only]
    ALB --> ECS[ECS Fargate · FastAPI<br/>Agents SDK · workflow engine<br/>proposal / receipt engine]
    OAI <-->|sideband transcript + delegation| ECS
    ECS --> RDS[(RDS Postgres 16 · private<br/>append-only ledgers · audit)]
    ECS --> S3[(S3 · private uploads<br/>30-day expiry)]
    ECS --> SM[🔐 Secrets Manager]
    ECS --> CW[CloudWatch logs]
    ECS --> EXT[OpenAI API · Gmail · Calendar<br/>SerpAPI · ECB FX]
    ECS -.traces.-> LS[LangSmith]
```

| Layer | Choice | Why |
|---|---|---|
| Voice | OpenAI GPT-Live, WebRTC + sideband | Low-latency speech; the server hears the confirmation itself |
| Agent | OpenAI Agents SDK + our checklist workflow engine | Typed tools; a cheap model by default, a strong one only when needed |
| Models | `gpt-6-luna` (workflows), `gpt-6-sol` (escalation), `gpt-5.4-mini` (fast paths) | All configurable via environment variables |
| Data | PostgreSQL + Alembic, append-only ledgers | Auditable money; data persists across deploys |
| Infra | Terraform: CloudFront → ALB → Fargate, private RDS, S3, Secrets Manager | 1 vCPU / 2 GB, about **$0.12/hour**. No GPU, no Bedrock (organiser rule) |
| Observability | CloudWatch logs, `/health`, LangSmith agent traces | See every tool call and its cost |

---

## 🎥 Act 8: live demo (about 6 minutes)

Full script with expected results: [`DEMO.md`](DEMO.md)

```mermaid
timeline
    title Golden path + spotlights (all on the live AWS URL)
    0:00 : Log in as admin : Spoken role briefing
    0:30 : Drop a FRESH receipt : "Arjun ne pay kiya tha" : "approve kar do" → "haan" : Travel ₹45,000 → ₹45,200
    1:30 : "Kaun paisa dena baaki hai?" : "sirf overdue" : "Acme ka amount padho"
    2:15 : ✈️ Flight + hotel search : "sabse sasta dono book karo" → "haan" : itinerary emailed + checkout links
    3:15 : 📜 Drop the MSA : "kaunse liabilities humpe hain?" : "agle 60 din ki deadlines"
    4:15 : 🔁 "Monday routine banao…" → "haan" : "Monday routine chalao"
    5:00 : 🛡️ Employee asks for budget → refused : CEO tries a change → read-only
    5:30 : Proof: "Is claim ki history batao" : log out/in → data persisted
```

---

## 🧾 Act 9: honesty and limits

| ✅ Real | ⚠️ Simulated / limited |
|---|---|
| Live AWS deployment, real OpenAI voice and agent calls | Company, people, vendors and clients are **synthetic** |
| Real Gmail + Calendar for one linked login | Flight/hotel **booking** hands off to the vendor; Purser takes no payment |
| Live flight/hotel fares (SerpAPI) and ECB FX rates | The eval is **text-path, single runs, 90 turns**; voice was not evaluated end to end |
| Persisted ledgers, audit trail, receipts in RDS | Jul–Sep budget actuals are a synthetic "imported snapshot" |

Built with Claude Code under the builder's direction. Budget, revenue and contract logic were reused from the builder's own earlier project and are disclosed file by file. Full details: [`HONEST_NOTE.md`](HONEST_NOTE.md).

---

## 🚀 Closing

```mermaid
flowchart LR
    A["🗣️ Speak naturally<br/>Hindi · Hinglish · English"] --> B["🤖 Purser does the routing<br/>67 workflows · 99+ tools"]
    B --> C["🛡️ Server-verified yes<br/>numbers from SQL"]
    C --> D["🧾 Receipt + audit trail<br/>on AWS"]
```

### Purser in three lines
1. **The whole back office in one voice agent:** finance, budgets, revenue, contracts, HR, mail, travel.
2. **Safe by construction:** the AI proposes, the server verifies a spoken "haan", and code writes the ledger.
3. **Engineered to be efficient:** 100% task success at **6x fewer tokens** and **8.7x lower cost** than a single agent.

> **"Priya doesn't need another dashboard. She needs a Purser."**
