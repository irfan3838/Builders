# Purser: the back office you can talk to, and trust with money

A voice-first back office for Indian small businesses: expenses, bills, budgets, revenue, contracts, HR, mail and travel, in **Hindi, Hinglish or English**. The AI only proposes. The server must hear a spoken "haan" itself, and code writes the ledger.

**Judges, start here → [`submission/README.md`](submission/README.md)**

| Submission requirement | Where |
|---|---|
| 1. Working demo, end to end on fresh input | Live on AWS: **https://d342yicbppf96p.cloudfront.net** · script: [`submission/DEMO.md`](submission/DEMO.md) |
| 2. Source code | This repository (FastAPI `app/`, React `web/`, Terraform `infra/terraform/`, tests `tests/`) |
| 3. Evidence of results | [`submission/EVIDENCE.md`](submission/EVIDENCE.md): baseline comparison (100% vs 89% task success, 8.7x cheaper), outputs on new data, proof that data persists |
| 4. Honest note | [`submission/HONEST_NOTE.md`](submission/HONEST_NOTE.md) |
| Story and architecture | [`submission/PRESENTATION.md`](submission/PRESENTATION.md) |
| Production readiness | [`submission/PRODUCTION.md`](submission/PRODUCTION.md) |

## Run it locally
```bash
cp .env.example .env            # add OPENAI_API_KEY (other integrations are optional)
docker compose up -d            # Postgres 16 on :5433
uv sync && uv run alembic upgrade head
uv run python -m seed.seed_v1 --reset --demo && uv run python -m seed.role_users
uv run uvicorn app.main:app --reload
cd web && npm install && npm run dev
```
Deploying to AWS: [`docs/deployment.md`](docs/deployment.md). All company data in this repository is synthetic.
