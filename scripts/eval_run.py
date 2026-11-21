"""Human-usage eval: pure agent vs agent + workflows, comparing accuracy, token cost, context growth and latency.

  uv run python -m scripts.eval_run --arm A1 --runs 1 --only t1_            # one arm, scenarios whose id starts with t1_
  uv run python -m scripts.eval_run --arm all --runs 3                       # every arm (each in its own process)
  uv run python -m scripts.eval_run --report evals/reports/<ts>              # rebuild the comparison report

Arms (see the plan): A0 today (gpt-5.4-mini) | A1 pure agent on gpt-6-luna | B workflows (luna + sol escalation)
| A2 pure agent on gpt-6-sol (accuracy ceiling).

Isolation: runs against its own database (EVAL_DATABASE_URL, default munshi_eval) which it creates and resets, with
real Gmail/Calendar/SMTP, live flight search and live FX switched OFF, so no mail is sent and the dev DB is untouched.
Scenario format: evals/scenarios/README.md. Prices: evals/prices.json ($ per 1M tokens).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCENARIOS = ROOT / "evals" / "scenarios"
REPORTS = ROOT / "evals" / "reports"
PRICES = ROOT / "evals" / "prices.json"

ARMS: dict[str, dict[str, str]] = {
    "A0": {"PURSER_WORKFLOWS": "0", "OPENAI_MODEL_FAST": "gpt-5.4-mini", "OPENAI_MODEL_STRONG": ""},
    "A1": {"PURSER_WORKFLOWS": "0", "OPENAI_MODEL_FAST": "gpt-6-luna", "OPENAI_MODEL_STRONG": ""},
    "B": {"PURSER_WORKFLOWS": "1", "OPENAI_MODEL_FAST": "gpt-6-luna", "OPENAI_MODEL_STRONG": "",
          "OPENAI_MODEL_ESCALATION": "gpt-6-sol"},
    "A2": {"PURSER_WORKFLOWS": "0", "OPENAI_MODEL_FAST": "gpt-6-sol", "OPENAI_MODEL_STRONG": ""},
}
# Everything with an external side effect or live dependency is off during evals.
ISOLATION = {
    "GMAIL_ADDRESS": "", "GMAIL_APP_PASSWORD": "", "EMAIL_ALLOWED_RECIPIENTS": "",
    "GOOGLE_CLIENT_ID": "", "GOOGLE_CLIENT_SECRET": "", "GOOGLE_REFRESH_TOKEN": "", "GOOGLE_LINKED_EMAIL": "",
    "SERPAPI_API_KEY": "", "FX_PROVIDER": "fixture", "STORAGE_BACKEND": "local",
}
DEFAULT_EVAL_DB = "postgresql+asyncpg://munshi:munshi-local-only@localhost:5433/munshi_eval"
# Business tables whose row counts are diffed every turn. Any unexpected increase is a wrong write.
WATCHED = ["receipts", "budget_movements", "bills", "claims", "settlements", "company_payments", "invoices",
           "invoice_payments", "client_cycles", "fx_months", "reminders", "leave_requests", "messages", "meetings",
           "onboarding_tasks", "contracts", "contract_findings", "flight_bookings", "hotel_bookings", "tasks", "tickets",
           "google_ops"]
DEVANAGARI = re.compile(r"[ऀ-ॿ]")


# ---------------------------------------------------------------- scenario loading
def load_scenarios(only: str | None) -> list[dict]:
    import yaml

    out = []
    for f in sorted(SCENARIOS.glob("*.yaml")):
        for sc in yaml.safe_load(f.read_text()) or []:
            if only and not sc["id"].startswith(only):
                continue
            sc["_file"] = f.name
            out.append(sc)
    return out


# ---------------------------------------------------------------- one arm (runs in its own process)
async def _setup_db(url: str) -> None:
    import asyncpg

    base = url.replace("postgresql+asyncpg://", "postgresql://")
    admin_url, name = base.rsplit("/", 1)
    conn = await asyncpg.connect(admin_url + "/postgres")
    try:
        if not await conn.fetchval("SELECT 1 FROM pg_database WHERE datname=$1", name):
            await conn.execute(f'CREATE DATABASE "{name}"')
    finally:
        await conn.close()
    from app import db
    from app.models import Base

    db.configure(url)
    async with db.engine().begin() as c:  # rebuild so new columns/tables always exist (eval data is disposable)
        await c.run_sync(Base.metadata.drop_all)
        await c.run_sync(Base.metadata.create_all)


async def _fresh_world(url: str) -> dict:
    """Reset + seed the eval DB; return {login: Actor-ready user ids} for every scenario login."""
    from sqlalchemy import select

    from app import db
    from app.models import User
    from seed.role_users import seed_roles
    from seed.seed_v1 import reset_and_seed

    ids = await reset_and_seed(url, demo=True)
    async with db.session_scope() as s:
        await seed_roles(s)
    logins = {"priya": ids["priya_id"], "arjun": ids["arjun_id"], "neha": ids["neha_id"]}
    async with db.session_scope() as s:
        for role in ("ceo", "employee"):
            u = (await s.execute(select(User).where(User.role == role).order_by(User.id.desc()))).scalars().first()
            if u:
                logins[role] = u.id
    return {"ids": ids, "logins": logins}


async def _counts() -> dict[str, int]:
    from sqlalchemy import text

    from app import db

    async with db.session_scope() as s:
        q = " UNION ALL ".join(f"SELECT '{t}', count(*) FROM {t}" for t in WATCHED)
        return {k: v for k, v in (await s.execute(text(q))).all()}


async def _new_conversation(user_id: int):
    from app import db
    from app.actor import Actor
    from app.models import Conversation, User

    async with db.session_scope() as s:
        u = await s.get(User, user_id)
        c = Conversation(workspace_id=u.workspace_id, user_id=u.id, channel="text")
        s.add(c)
        await s.flush()
        return Actor(u.id, u.workspace_id, u.role, u.party_id, u.display_name, c.id, email=u.email)


def _check(expect: dict, res, delta: dict[str, int]) -> tuple[list[str], bool]:
    """Return (failed expectation names, wrong_write). Every listed expectation must hold."""
    fails: list[str] = []
    tools = [t["tool"] for t in res.tools]
    services = res.metrics.get("services", [])
    called = set(tools) | set(services)
    reply = (res.reply or "").lower()
    cards = [c.get("card") for c in res.ui]
    if "tools_any" in expect and not called & set(expect["tools_any"]):
        fails.append(f"tools_any {expect['tools_any']} (called {sorted(called)})")
    for t in expect.get("tools_none", []):
        if t in called:
            fails.append(f"tools_none {t}")
    if "cards_any" in expect and not set(cards) & set(expect["cards_any"]):
        fails.append(f"cards_any {expect['cards_any']} (got {cards})")
    if "reply_any" in expect and not any(s.lower() in reply for s in expect["reply_any"]):
        fails.append(f"reply_any {expect['reply_any']}")
    for s in expect.get("reply_none", []):
        if s.lower() in reply:
            fails.append(f"reply_none {s!r}")
    if "lang" in expect:
        is_hi = bool(DEVANAGARI.search(res.reply or ""))
        if (expect["lang"] == "hi") != is_hi:
            fails.append(f"lang {expect['lang']}")
    want_db = dict(expect.get("db", {}))
    want_writes = expect.get("writes", 0)
    want_db.setdefault("receipts", want_writes)
    wrong_write = False
    # A confirmed write may have side effects in other tables (a notification message, a ledger row), so when writes
    # are expected only the listed tables are checked. When no write is expected, every watched table must be as listed.
    strict = want_writes == 0
    for table, n in delta.items():
        if not strict and table not in want_db:
            continue
        want = want_db.get(table, 0)
        if n != want:
            fails.append(f"db {table} {n:+d} (want {want:+d})")
            if n > want:
                wrong_write = True
    if "escalated" in expect and res.metrics.get("route") != "agent":  # only meaningful in arm B
        if bool(res.metrics.get("escalated")) != bool(expect["escalated"]):
            fails.append(f"escalated {expect['escalated']}")
    if "workflow" in expect and res.metrics.get("route") != "agent":
        if res.metrics.get("workflow") != expect["workflow"]:
            fails.append(f"workflow {expect['workflow']} (got {res.metrics.get('workflow')})")
    return fails, wrong_write


def _cost(models: dict, prices: dict) -> float:
    usd = 0.0
    for name, m in models.items():
        p = prices.get(name)
        if not p:
            continue
        fresh = max(0, m["input_tokens"] - m["cached_tokens"])
        usd += (fresh * p["input"] + m["cached_tokens"] * p["cached"] + m["output_tokens"] * p["output"]) / 1e6
    return usd


async def run_arm(arm: str, runs: int, only: str | None, out_dir: Path) -> None:
    from app import db
    from app.agent.runner import run_turn
    from app.services import intake

    url = os.environ["DATABASE_URL"]
    await _setup_db(url)
    prices = json.loads(PRICES.read_text())
    scenarios = load_scenarios(only)
    rows = []
    for run in range(1, runs + 1):
        for sc in scenarios:
            world = await _fresh_world(url)
            actor = await _new_conversation(world["logins"][sc.get("who", "priya")])
            subst = {k: str(v) for k, v in world["ids"].items()}
            if sc.get("doc"):
                p = ROOT / sc["doc"]
                async with db.session_scope() as s:
                    up = await intake.accept_upload(s, actor, p.name, p.read_bytes())
                subst["doc"] = str(up.document_id)
            turns_out, ok_all, wrong_any = [], True, False
            for i, turn in enumerate(sc["turns"], 1):
                say = turn["say"].format(**subst) if "{" in turn["say"] else turn["say"]
                before = await _counts()
                t0 = time.perf_counter()
                try:
                    res = await run_turn(actor, say)
                    err = None
                except Exception as e:  # a crash is a failed turn, never an aborted run
                    res, err = None, f"{type(e).__name__}: {e}"
                wall = int((time.perf_counter() - t0) * 1000)
                after = await _counts()
                delta = {t: after[t] - before[t] for t in WATCHED}
                if res is None:
                    fails, wrong = [f"crash {err}"], any(v > 0 for v in delta.values())
                    metrics, reply, tools = {}, "", []
                else:
                    fails, wrong = _check(turn.get("expect", {}), res, delta)
                    metrics, reply, tools = res.metrics, res.reply, [t["tool"] + ":" + t["outcome"] for t in res.tools]
                models = metrics.get("models", {})
                tin = sum(m["input_tokens"] for m in models.values())
                turns_out.append({
                    "i": i, "say": say, "reply": reply, "tools": tools, "services": metrics.get("services", []),
                    "pass": not fails, "fails": fails, "wrong_write": wrong, "route": metrics.get("route"),
                    "workflow": metrics.get("workflow"), "escalated": bool(metrics.get("escalated")),
                    "escalation_trigger": metrics.get("escalation_trigger"), "models": models,
                    "llm_calls": sum(m["calls"] for m in models.values()), "input_tokens": tin,
                    "cached_tokens": sum(m["cached_tokens"] for m in models.values()),
                    "output_tokens": sum(m["output_tokens"] for m in models.values()),
                    "cost_usd": round(_cost(models, prices), 6), "history_items": metrics.get("history_items"),
                    "latency_ms": wall,
                })
                ok_all &= not fails
                wrong_any |= wrong
                mark = "PASS" if not fails else "FAIL"
                print(f"[{arm} r{run}] {sc['id']} t{i} {mark} {wall}ms in={tin} {'; '.join(fails)[:160]}", flush=True)
            rows.append({"arm": arm, "run": run, "id": sc["id"], "tier": sc.get("tier"), "who": sc.get("who", "priya"),
                         "success": ok_all, "wrong_write": wrong_any, "turns": turns_out})
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{arm}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print(f"[{arm}] wrote {out_dir / (arm + '.json')}")


# ---------------------------------------------------------------- report
def _pct(xs: list[float], q: float) -> int:
    if not xs:
        return 0
    xs = sorted(xs)
    return int(xs[min(len(xs) - 1, int(q * (len(xs) - 1) + 0.5))])


def build_report(out_dir: Path) -> Path:
    arms = {p.stem: json.loads(p.read_text()) for p in sorted(out_dir.glob("*.json")) if p.stem in ARMS}
    lines = [f"# Purser eval report: {out_dir.name}", "",
             "Arms: A0 today (gpt-5.4-mini) · A1 pure agent on gpt-6-luna · B workflows (luna + gpt-6-sol escalation)"
             " · A2 pure agent on gpt-6-sol.", ""]
    head = ("| Arm | Task success | Turn pass | Wrong writes | pass^k | $ / successful task | $ total | Input tok / turn"
            " | LLM calls / turn | 0-LLM turns | Escalated turns | p50 ms | p95 ms |")
    lines += ["## Headline", "", head, "|" + "---|" * 13]
    for arm, rows in arms.items():
        turns = [t for r in rows for t in r["turns"]]
        n_ok = sum(r["success"] for r in rows)
        cost = sum(t["cost_usd"] for t in turns)
        by_sc: dict[str, list[bool]] = {}
        for r in rows:
            by_sc.setdefault(r["id"], []).append(r["success"])
        pass_k = sum(all(v) for v in by_sc.values()) / max(1, len(by_sc))
        lat = [t["latency_ms"] for t in turns]
        lines.append(
            f"| {arm} | {n_ok}/{len(rows)} ({100 * n_ok / max(1, len(rows)):.0f}%) "
            f"| {100 * sum(t['pass'] for t in turns) / max(1, len(turns)):.0f}% "
            f"| {sum(r['wrong_write'] for r in rows)} | {100 * pass_k:.0f}% "
            f"| ${cost / max(1, n_ok):.4f} | ${cost:.4f} "
            f"| {sum(t['input_tokens'] for t in turns) / max(1, len(turns)):.0f} "
            f"| {sum(t['llm_calls'] for t in turns) / max(1, len(turns)):.2f} "
            f"| {100 * sum(t['llm_calls'] == 0 for t in turns) / max(1, len(turns)):.0f}% "
            f"| {100 * sum(t['escalated'] for t in turns) / max(1, len(turns)):.0f}% "
            f"| {_pct(lat, .5)} | {_pct(lat, .95)} |")
    lines += ["", "## By tier (task success)", "", "| Arm | " + " | ".join(f"Tier {k}" for k in (1, 2, 3, 4)) + " |",
              "|---|---|---|---|---|"]
    for arm, rows in arms.items():
        cells = []
        for k in (1, 2, 3, 4):
            rs = [r for r in rows if r.get("tier") == k]
            cells.append(f"{sum(r['success'] for r in rs)}/{len(rs)}" if rs else "–")
        lines.append(f"| {arm} | " + " | ".join(cells) + " |")
    lines += ["", "## Context growth (input tokens per turn, run 1, chained scenarios)", ""]
    for sc_id in sorted({r["id"] for rows in arms.values() for r in rows if r.get("tier") == 2}):
        lines.append(f"- **{sc_id}**")
        for arm, rows in arms.items():
            r = next((x for x in rows if x["id"] == sc_id and x["run"] == 1), None)
            if r:
                lines.append(f"  - {arm}: " + " → ".join(str(t["input_tokens"]) for t in r["turns"]))
    lines += ["", "## Failures (run 1)", ""]
    for arm, rows in arms.items():
        for r in rows:
            if r["run"] != 1:
                continue
            for t in r["turns"]:
                if not t["pass"]:
                    lines.append(f"- {arm} `{r['id']}` t{t['i']} \"{t['say'][:60]}\": {'; '.join(t['fails'])[:300]}")
    esc = [(r["id"], t) for r in arms.get("B", []) for t in r["turns"] if t["escalated"]]
    if esc:
        lines += ["", "## Escalations in B (backlog for new specs)", ""]
        for sc_id, t in esc:
            lines.append(f"- `{sc_id}` t{t['i']} \"{t['say'][:60]}\": {t.get('escalation_trigger')}")
    path = out_dir / "report.md"
    path.write_text("\n".join(lines) + "\n")
    return path


# ---------------------------------------------------------------- entry
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="A1", help="A0 | A1 | B | A2 | all | comma list")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--only", help="run only scenarios whose id starts with this")
    ap.add_argument("--out", help="report directory (default evals/reports/<timestamp>)")
    ap.add_argument("--report", help="rebuild report.md for an existing report directory and exit")
    ap.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--parallel", action="store_true", help="run the selected arms at the same time")
    a = ap.parse_args()
    if a.report:
        print(build_report(Path(a.report)))
        return
    out_dir = Path(a.out) if a.out else REPORTS / datetime.now().strftime("%Y%m%d-%H%M%S")
    arms = list(ARMS) if a.arm == "all" else a.arm.split(",")
    procs: list[subprocess.Popen] = []
    if a.worker:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")  # does not override the arm/isolation env set by the parent
        import logging

        logging.basicConfig(level=logging.WARNING)
        asyncio.run(run_arm(arms[0], a.runs, a.only, out_dir))
        return
    for arm in arms:
        if arm not in ARMS:
            raise SystemExit(f"unknown arm {arm}")
        # one database per arm (munshi_eval_a0, ...) so arms can run in parallel without sharing state
        env = {**os.environ, **ISOLATION, **ARMS[arm],
               "DATABASE_URL": os.environ.get("EVAL_DATABASE_URL", DEFAULT_EVAL_DB) + "_" + arm.lower()}
        cmd = [sys.executable, "-m", "scripts.eval_run", "--worker", "--arm", arm, "--runs", str(a.runs),
               "--out", str(out_dir)] + (["--only", a.only] if a.only else [])
        procs.append(subprocess.Popen(cmd, env=env, cwd=ROOT))
        if not a.parallel:
            procs[-1].wait()
    for p in procs:
        p.wait()
    print(build_report(out_dir))


if __name__ == "__main__":
    main()
