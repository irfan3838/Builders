# Purser: the back office you can talk to, and trust with money

A voice-first back office for Indian small businesses: expenses, bills, budgets, revenue, contracts, HR, mail and travel, in **Hindi, Hinglish or English**. The AI only proposes. The server must hear a spoken "haan" itself, and code writes the ledger.

**Judges, start here → [`submission/README.md`](submission/README.md)**

| Submission requirement | Where |
|---|---|
| Setup, logins, journeys (reviewers start here) | [`AGENTS.md`](AGENTS.md) · video: [`VIDEO.md`](VIDEO.md) · slides: [`Purser-shortlist-slides.pdf`](Purser-shortlist-slides.pdf) |
| 1. Working demo, end to end on fresh input | Live on AWS: **https://d342yicbppf96p.cloudfront.net** · script: [`submission/DEMO.md`](submission/DEMO.md) |
| 2. Source code | This repository (FastAPI `app/`, React `web/`, Terraform `infra/terraform/`, tests `tests/`) |
| 3. Evidence of results | [`submission/EVIDENCE.md`](submission/EVIDENCE.md): baseline comparison (100% vs 89% task success, 8.7x cheaper), outputs on new data, proof that data persists |
| 4. Honest note | [`submission/HONEST_NOTE.md`](submission/HONEST_NOTE.md) |
| Story and architecture | [`submission/PRESENTATION.md`](submission/PRESENTATION.md) |
| Production readiness | [`submission/PRODUCTION.md`](submission/PRODUCTION.md) |

## Run it locally
**Setup, logins and end-to-end journeys: [`AGENTS.md`](AGENTS.md).** Short version:
```bash
cp .env.example .env            # add OPENAI_API_KEY (without it the app runs in no-key mode)
docker compose up --build       # Postgres + app, migrated and seeded -> http://localhost:8000
```
Demo video: [`VIDEO.md`](VIDEO.md). Deploying to AWS: [`docs/deployment.md`](docs/deployment.md). All company data in this repository is synthetic.
