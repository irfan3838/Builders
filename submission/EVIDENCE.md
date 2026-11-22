# Evidence of results

There are three kinds of evidence:
1. **Accuracy against a baseline**: an agent eval with three arms.
2. **Outputs on new data**: fresh inputs at demo time.
3. **Proof that data persists**: ledgers and an audit trail in RDS.

Raw data is in the repo. Every number below links to its source file.

---

## 1. Accuracy and cost compared with a baseline

**Question:** does our checklist-workflow engine (B) beat a conventional single agent with all tools (A0 today; A1 on the same cheap model)?

**Method** (`scripts/eval_run.py`, scenarios in `evals/scenarios/*.yaml`):
- **46 conversations, 90 turns**, written the way people talk: English, romanized Hinglish and Devanagari Hindi, with corrections, short answers ("haan", "Tradelinks wala") and topic switches.
- **Four tiers:** 17 single actions, 12 chained tasks (2–5 turns), 10 edge cases (ambiguity, corrections, documents, out of scope) and 7 safety cases (prompt injection, wrong role, "yes" with nothing pending, approving your own leave).
- **Machine-checked on every turn:** required and forbidden tools, UI cards, reply content and language, and the **exact database effect**. 22 business tables are diffed before and after each turn. Any unexpected change is a *wrong write*, which is a hard fail.
- **Isolation:** each arm gets a throwaway database, re-seeded for every scenario. Real email, calendar, flight search and FX are switched off.
- Prices come from `evals/prices.json` (OpenAI Standard tier, checked 21 Nov 2026).

### Head-to-head on the same code and scenarios (run 3, `evals/reports/run3-20261122/`)

Run 3 used 45 scenarios (6 safety cases). The 46th, "employees can't see budgets", was added after it, so only the shipped run below has 46.

| Arm | Task success | Wrong writes | $ / successful task | Input tokens / turn | 0-LLM turns | p50 / p95 |
|---|---|---|---|---|---|---|
| A0 · single agent, 99 tools, `gpt-5.4-mini` | 40/45 (89%) | 0 | $0.0104 | 36,195 | 0% | 7.7 / 14.4 s |
| A1 · single agent, `gpt-6-luna` | 42/45 (93%) | 0 | $0.0025 | 39,709 | 0% | 9.5 / 15.1 s |
| **B · checklist workflows** | **44/45 (98%)** | **0** | **$0.0017** | **6,875** | **20%** | 8.7 / 19.8 s |

### Shipped workflow engine (`evals/reports/combined-check-20261122/`)

| Arm | Task success | Wrong writes | $ / successful task | Input tokens / turn | 0-LLM turns | Escalated | p50 / p95 |
|---|---|---|---|---|---|---|---|
| **B** | **46/46 (100%)** | **0** | **$0.0012** | **5,993** | 20% | 1% | 8.0 / 15.5 s |

**By tier (shipped):** Tier 1 17/17 · Tier 2 12/12 · Tier 3 10/10 · Tier 4 7/7. **By tier (run 3, B):** 16/17 · 12/12 · 10/10 · 6/6.

### What it means

- **More accurate:** 98% vs 93% vs 89% on identical code (44 vs 42 vs 40 of 45, one run each), and 100% on the shipped build. The gains are on chained and edge tasks, where a single agent skips steps. This is our own scenario set, and the engine was iterated against it.
- **5–6x fewer tokens per turn** (6,875 vs 36,195 and 39,709 in the same run). Finished workflows are "killed" and leave only a one-line summary, so context usually stays at **5k–10k tokens** (up to ~17k on chart refinements in the shipped run) instead of growing to 50k+.
- **Cheaper per successful task:** 1.5x less than a single agent on the same model (A1 $0.0025 vs B $0.0017), and 6x less than today's agent (A0 $0.0104), most of which comes from the cheaper model. The shipped build is $0.0012. These are text-agent costs; real-time voice audio is billed separately.
- **Confirmations are free and instant:** 18 of 90 turns ("haan", "mat karo") were handled in code with **0 tokens in ~118 ms**. The same turns cost the single agent ~33,600 tokens and ~7.9 s.
- **Zero wrong writes in every arm and every run.** For B this is structural: no workflow has a confirm tool.

Full analysis, including the iteration log, failure analysis and cost breakdown: [`docs/workflow-eval-results.md`](../docs/workflow-eval-results.md).

**Reproduce:**
```bash
uv run python -m scripts.eval_run --arm A0,A1,B --parallel --runs 1
```

### Limitations (please read before quoting)
- Single run per arm. LLM behaviour varies between runs. The 3-run consistency gate and the strong-model ceiling arm (A2) were stopped early.
- The eval used the **text path only**. Voice uses the same `run_turn`, but it was not evaluated end to end.
- Synthetic seeded workspace, 90 turns (the target was 150+).
- B is slower at p95 because of retries and escalations: 19.8 s vs 14.4 s for A0 in run 3, and 15.5 s on the shipped build.
- Per-task costs cover the text agent only. Real-time voice audio (GPT-Live) is billed separately and is not included.

---

## 2. Engineering checks (automated tests)

- **~1,030 test functions** (pytest, against a real Postgres), written and run by **independent Sonnet tester agents**. A project hook stops the main coding agent from running tests itself.
- The latest full run in the workflow round: **1,347 passed, 2 failed.** Both failures are wording assertions that already failed on the previous commit and are unrelated to the workflow engine (source: `docs/workflow-eval-results.md` §10).
- The independent testers found **real bugs** throughout the build (11 in the first rounds, more in later ones). They were marked as strict xfail with evidence, then fixed. Examples: seed leave counted Fri–Sat as working days; a multi-line email subject broke `EmailMessage`; "nahi nahi 2,01,000" cancelled instead of correcting; employees could see the `budget_change` workflow.
- `ruff check` is clean on `app/`, `seed/` and `tests/`.

---

## 3. Outputs on new data

Purser is not a replay of canned answers. At demo time the judges can:

| Fresh input | What to observe |
|---|---|
| **Any receipt or bill image/PDF** you bring (we also have a fresh demo receipt that is **not** in the eval set) | Purser extracts the vendor, amount and date with vision, **re-checks the arithmetic in Python**, flags duplicates (SHA-256 + party/amount/date), and proposes a claim or bill |
| A **receipt with a wrong total** (`evals/dev/dev_wrong_total_synthetic.png`) | Purser flags the mismatch instead of trusting the printed total |
| A **contract** (PDF, DOCX or scanned) | Clause scan, who bears each liability, caps in ₹, notice periods and renewal deadlines. Every phrase is grounded in the document text |
| **Any question in Hindi / Hinglish / English** about budgets, receivables, leave or meetings | A chart or answer built from SQL. Ask a follow-up ("sirf overdue") and the chart revises |
| A **flight/hotel search** for any city pair | Live fares from SerpAPI, or a clearly labelled "Estimated" fallback |
| **The same receipt again** | Replay detected; no second claim |

Agent traces for every turn (tools called, tokens, latency) are captured in **LangSmith** in production.

---

## 4. Proof that data persists

- **Storage:** Amazon RDS PostgreSQL 16 (private subnet), not container memory. Uploaded files go to a private S3 bucket.
- **Append-only ledgers:** `budget_movements` and the leave ledger are never updated in place. Balances are always the sum of their movements.
- **Audit trail:** every confirmed change writes an `audit_events` row (actor, action, before/after, linked proposal and receipt) in the **same transaction** as the change.
- **Receipts are idempotent:** saying "haan" twice returns the same receipt ID, and the ledger moves once.
- **Across deployments:** the demo workspace was seeded on 21 Nov. Since then the ECS service has been redeployed through several task definitions (up to `munshi:15`, image `7bb2f04`) **without reseeding**. Logins, ledgers and history carried over (round 6 added role logins with `seed-roles`, which adds data without a reset).

### How a judge can verify persistence live (2 minutes)
1. Log in and say: *"Travel budget mein kitna bacha hai?"* Note the figure.
2. Approve a pending claim with *"approve kar do"* → *"haan"*. Note the receipt ID.
3. **Log out, close the tab, log back in** (or come back hours later).
4. Ask: *"Is claim ki history batao"* or *"Travel mein kitna bacha hai?"* The new balance and the audit entry (who, what, when, source document) are still there.
5. Say *"haan"* again with nothing pending. Purser writes nothing.

### Live deployment status (checked 22 Nov 2026)
- `https://d342yicbppf96p.cloudfront.net/health` → `{"ok":true}`
- ECS service `munshi` (us-west-2): 1/1 running task, task definition `munshi:15`, image `munshi:7bb2f04`, rollout `COMPLETED`, `PURSER_WORKFLOWS=1`, 1 vCPU / 2 GB.
- The eval reports were produced on the workflow engine from `8c39078`. `2dcc7dc` adds Devanagari spoken-amount grounding, invoice lookup for payments and travel-search memory. Those fixes are covered by 25 extra Sonnet tests (`a7d3afb`), but the 90-turn eval was **not** re-run on them. The live build `7bb2f04` adds only visual UI fixes (ribbons, phone-width layout) and the deploy pipeline on top; no backend or agent code.

How it stays up when things fail (timeouts, fallbacks, rollback, known gaps): [`PRODUCTION.md`](PRODUCTION.md).
