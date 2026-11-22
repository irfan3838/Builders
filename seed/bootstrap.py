"""First-boot seed for a fresh database (used by `docker compose up`). Safe to run on every start.

  python -m seed.bootstrap
Empty database (no workspace) -> synthetic demo workspace (seed_v1 --demo) + the role logins (role_users).
Already seeded -> does nothing, so restarts never wipe data. To start over: `docker compose down -v`.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import func, select

from app import db
from app.models import Workspace


async def bootstrap(url: str | None = None) -> dict:
    sm = db.configure(url)
    async with sm() as s:
        n = (await s.execute(select(func.count()).select_from(Workspace))).scalar_one()
    if n:
        return {"seeded": False, "reason": f"already seeded ({n} workspace)"}
    from seed import role_users
    from seed.seed_v1 import reset_and_seed

    ids = await reset_and_seed(url, demo=True)
    roles = await role_users.main()
    return {"seeded": True, "workspace": ids.get("workspace_id"), "roles": roles.get("users")}


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    print(asyncio.run(bootstrap()))
