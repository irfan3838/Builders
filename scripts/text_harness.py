"""Scripted text conversation through the real MunshiAgent against the dev DB (reset to seed-v1).

  uv run python -m scripts.text_harness --doc evals/dev/dev_hotel_receipt_synthetic.png "turn 1" "turn 2" ...
Prints each reply, tools called, latency, and the Travel budget position after the run.
"""

import argparse
import asyncio
import json
import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from app import db  # noqa: E402
from app.actor import Actor  # noqa: E402
from app.agent.runner import run_turn  # noqa: E402
from app.models import Conversation, User  # noqa: E402
from app.services import budget, intake  # noqa: E402
from seed.seed_v1 import reset_and_seed  # noqa: E402


async def main(turns: list[str], doc: str | None, who: str) -> None:
    ids = await reset_and_seed()
    async with db.session_scope() as s:
        u = await s.get(User, ids[f"{who}_id"])
        c = Conversation(workspace_id=u.workspace_id, user_id=u.id, channel="text")
        s.add(c)
        await s.flush()
        actor = Actor(u.id, u.workspace_id, u.role, u.party_id, u.display_name, c.id)
    if doc:
        async with db.session_scope() as s:
            up = await intake.accept_upload(s, actor, Path(doc).name, Path(doc).read_bytes())
        print(f"[upload] {up.outcome} document_id={up.document_id} {up.message}")
        turns = [t.replace("{doc}", str(up.document_id)) for t in turns]
    for t in turns:
        r = await run_turn(actor, t)
        print(f"\nUSER: {t}\nMUNSHI ({r.latency_ms} ms): {r.reply}\n  tools: {[x['tool'] + ':' + x['outcome'] for x in r.tools]}")
    async with db.session_scope() as s:
        p = await budget.position(s, ids["workspace_id"], ids["travel_line_id"])
    print("\nTravel:", json.dumps({k: v // 100 for k, v in p.items()}))


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc")
    ap.add_argument("--who", default="priya")
    ap.add_argument("turns", nargs="+")
    a = ap.parse_args()
    asyncio.run(main(a.turns, a.doc, a.who))
