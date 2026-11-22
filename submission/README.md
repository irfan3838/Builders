# Purser: the back office you can talk to, and trust with money

**Theme 3 · Build Ambitious (SaaS in a day).** Purser is a voice-first back office for Indian small businesses. One AI agent handles expenses, bills, budgets, revenue, contracts, HR, mail and travel, and you talk to it in **Hindi, Hinglish or English**.

What makes it different: **the AI can only propose.** The server must hear a spoken "haan" itself, every amount must come from the user's own words, and plain code writes the ledger.

🌐 **Live on AWS:** https://d342yicbppf96p.cloudfront.net  ·  📦 **Code:** https://github.com/irfan3838/Builders

---

## 1. The real-world problem

| Fact | Source |
|---|---|
| India has **~6.3 crore MSMEs** (NSS 73rd round, 2015-16), and **~7.3 crore** by the 2023-24 ASUSE estimate. Most are micro firms with no finance team | [PIB / Ministry of MSME](https://pib.gov.in/PressReleasePage.aspx?PRID=2087361), [Factly on ASUSE 2023-24](https://factly.in/data-msmes-estimated-at-7-3-crores-as-of-2023-24-wide-variation-in-state-sectoral-distribution) |
| Only **~10.6%** of Indians speak English at all (mostly as a 2nd/3rd language), while **~57%** speak Hindi | Census 2011 language tables ([summary](https://en.wikipedia.org/wiki/List_of_languages_by_number_of_native_speakers_in_India)) |
| Back-office software (accounting, expenses, HR) is **form-based and English-first**, and usually split across separate products | Zoho Books/Expense, Tally, Keka, greytHR (product scope as we understand it) |

**The result** is that a typical small company routes every receipt, approval, leave request and "who owes us money?" through **one admin person**. That person works across WhatsApp, Excel, an accounting tool and email, and overspending shows up only at month end. Generic AI chatbots speak Hindi, but they can't be trusted to post to the books: there's no proof of what changed, why, or who agreed.

> Our persona "Priya" (finance + admin at a 40-person Pune company) is illustrative. The pain points come from the reference products' own workflows.

## 2. What is new here (each item links to code)

| # | Novel mechanism | Why it matters | Code |
|---|---|---|---|
| 1 | **Server-heard confirmation.** A write commits only when the *server's own transcript* contains a pure "haan / yes / ठीक है", classified by deterministic code. A model or browser claiming "the user said yes" is ignored | Voice becomes safe enough to move money | `app/services/affirmation.py`, `app/services/confirmation.py` |
| 2 | **Amount grounding.** Every rupee amount in a write must appear in the user's recent speech ("38 hazaar", "1.5L", Devanagari numbers) | The model can't hallucinate a payment | `app/services/revenue/grounding.py`, `app/services/revenue_actions.py` |
| 3 | **Checklist workflows with "kill".** Instead of one agent juggling 102 tools, a cheap picker chooses 1 of **67 workflows**. Each runs with only 1–8 tools and a checklist that code verifies, then it is *killed* to a one-line summary | **6x fewer tokens, 8.7x cheaper, 100% task success** vs 89% for a single agent | `app/agent/workflows/` |
| 4 | **Numbers come from SQL, never from the model.** The agent picks a typed ChartSpec; vetted SQL computes it; the chart, the table and the spoken number all read **one snapshot** | Speech and screen can't disagree | `app/services/charts.py` |
| 5 | **Grounded contract liability radar.** The model only *points* at phrases. Code checks each phrase is in the text, then resolves who bears it, the cap in ₹, and the real calendar deadlines | "What do we owe, how much, by when", not a summary | `app/services/contracts/` |
| 6 | **Teach-by-voice routines** with tools frozen to your role and an injection deny-list **in code** | Purser learns *your* workflow and still can't skip the yes | `app/agent/workflows/custom.py` |

## 3. Requirement → proof

| Hackathon requirement | Proof | Status |
|---|---|---|
| Working end-to-end demo on **fresh input** | Live URL above. Script with expected results: [`DEMO.md`](DEMO.md). Bring your own receipt or contract | ✅ Deployed & healthy (checked 22 Nov) |
| **Evidence of results**: baseline comparison | 3-arm eval with an exact DB diff: [`EVIDENCE.md`](EVIDENCE.md) §1 | ✅ |
| **Evidence**: outputs on new data | [`EVIDENCE.md`](EVIDENCE.md) §3 | ✅ |
| **Evidence**: data persists | RDS, append-only ledgers, audit trail; survived redeploys: [`EVIDENCE.md`](EVIDENCE.md) §4 | ✅ |
| Won't break in production | Failure-mode table, recovery, known gaps: [`PRODUCTION.md`](PRODUCTION.md) | ✅ (gaps listed) |
| **Honest note**: built / reused / simulated | [`HONEST_NOTE.md`](HONEST_NOTE.md) | ✅ |
| Voice-first, multilingual, AI-centric | GPT-Live voice; EN / Hinglish / Devanagari Hindi in the eval | ✅ |
| Story + architecture | [`PRESENTATION.md`](PRESENTATION.md) | ✅ |

## 4. Headline numbers (46 conversations, 90 turns, EN / Hinglish / Hindi)

| | Single agent (A0) | **Purser workflows (shipped)** |
|---|---|---|
| Task success | 89% | **100%** |
| Wrong database writes | 0 | **0** |
| Input tokens per turn | 36,195 | **5,993** (6x fewer) |
| US$ per successful task | $0.0104 | **$0.0012** (8.7x cheaper) |
| Confirming "haan" | ~33.6k tokens, 7.9 s | **0 tokens, 118 ms** |

Single run per arm, text path only. Limits are in [`EVIDENCE.md`](EVIDENCE.md).

## 5. Verify it yourself in 2 minutes

1. `curl https://d342yicbppf96p.cloudfront.net/health` → `{"ok":true}`
2. Log in as **admin**. Say or type *"Travel mein kitna bacha hai?"* and note the figure.
3. Drop any receipt → *"Arjun ne pay kiya tha"* → *"approve kar do"* → *"haan"*. You get a receipt with an ID.
4. Say *"haan"* again: the **same** receipt comes back and nothing posts twice.
5. Log out and back in → *"Is claim ki history batao"*: who approved it, when, and the source document, read from RDS.
6. Log in as **employee** → *"Company ka budget batao"*: refused.

Logins are in the submission form, not in the repo.

## 6. Scale built at the event

~19,900 lines of Python · ~4,600 lines of TypeScript · **102 typed agent tools** · **67 workflows** · ~990 test functions (~1,350 collected cases) · Terraform for the whole AWS stack.

## Repository map
```text
app/                 FastAPI backend
  agent/             Agents SDK agent, tools, workflow engine (workflows/)
  services/          ledger, proposals, confirmation, intake, budgets, revenue, contracts, people, travel
  voice/             GPT-Live bridge + sideband
web/                 React + three.js UI
evals/               scenarios, reports, sample documents (synthetic)
scripts/eval_run.py  eval harness
infra/terraform/     AWS infrastructure (CloudFront → ALB → ECS Fargate → RDS, S3, Secrets Manager)
tests/               automated tests (pytest, real Postgres)
docs/                plans, architecture, deployment, eval results, authorship log
```

## Run it yourself
```bash
cp .env.example .env            # add OPENAI_API_KEY (other integrations are optional)
docker compose up -d            # Postgres 16 on :5433
uv sync && uv run alembic upgrade head
uv run python -m seed.seed_v1 --reset --demo && uv run python -m seed.role_users   # synthetic demo workspace + role logins
uv run uvicorn app.main:app --reload
cd web && npm install && npm run dev   # set APP_ORIGIN=http://localhost:5173 for the API
```
Deploying to AWS: [`docs/deployment.md`](../docs/deployment.md).
