# Purser: hackathon submission

**Theme 3 · Build Ambitious (SaaS in a day).** Purser is a voice-first back office for Indian SMBs. It covers finance, budgets, revenue, contracts, HR, mail and travel, all in one AI agent you talk to in Hindi, Hinglish or English. It is safe enough to move money: the AI only proposes, the server verifies a spoken "haan", and code writes the ledger.

| Requirement | Where |
|---|---|
| 🟢 **A working demo that runs end to end on fresh input** | Live on AWS: **https://d342yicbppf96p.cloudfront.net**. Script: [`DEMO.md`](DEMO.md) |
| 📦 **Source code the judges can open** | https://github.com/irfan3838/Builders (branch `build/munshi-mvp`) |
| 📈 **Evidence of results** | [`EVIDENCE.md`](EVIDENCE.md): baseline comparison (100% vs 89% task success, 6x fewer tokens, 8.7x cheaper), outputs on new data, proof of persistence |
| 🧾 **Honest note** | [`HONEST_NOTE.md`](HONEST_NOTE.md) |
| 🎤 **Presentation** | [`PRESENTATION.md`](PRESENTATION.md): the story deck with diagrams and charts |

## Spotlight features
- ✈️ **Voice travel desk:** live flight + hotel search, one whole-trip approval, the itinerary emailed, and a hand-off to the airline/hotel checkout (Purser takes no payment).
- 📜 **Contract liability radar:** who bears each liability, caps in ₹, carve-outs and renewal deadlines. Every phrase is grounded in the contract text; scanned PDFs work too.
- 🔁 **Custom routines:** describe your own workflow by voice. The tools are frozen to your role, injection phrases are screened in code, and every write still needs your yes.

## Headline numbers (46 conversations, 90 turns, EN/Hinglish/Hindi)

| | Single agent (today) | **Purser workflows (shipped)** |
|---|---|---|
| Task success | 89% | **100%** |
| Wrong writes | 0 | **0** |
| Input tokens / turn | 36,195 | **5,993** |
| $ / successful task | $0.0104 | **$0.0012** |
| Confirming "haan" | ~33.6k tokens, 7.9 s | **0 tokens, 118 ms** |

## Repository map
```text
app/                 FastAPI backend
  agent/             Agents SDK agent, tools, workflow engine (workflows/)
  services/          ledger, proposals, confirmation, intake, budgets, revenue, contracts, people, travel
  voice/             GPT-Live bridge + sideband
web/                 React + three.js UI
evals/               scenarios, reports, sample documents (synthetic)
scripts/eval_run.py  eval harness
infra/terraform/     AWS infrastructure
tests/               ~1,350 automated tests
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
