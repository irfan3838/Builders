import os
from datetime import date

import pytest
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.pool import NullPool

load_dotenv()

from app import db  # noqa: E402
from app.actor import Actor  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.models import Base, Conversation, Document, Extraction  # noqa: E402
from seed.seed_v1 import seed  # noqa: E402

_schema_ready = False


@pytest.fixture
async def seeded():
    global _schema_ready
    url = os.getenv("TEST_DATABASE_URL", get_settings().test_database_url)
    db.configure(url, poolclass=NullPool)
    async with db.engine().begin() as conn:
        if not _schema_ready:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
            _schema_ready = True
        tables = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    async with db.session_scope() as s:
        ids = await seed(s)
    yield ids
    await db.engine().dispose()


async def make_actor(ids: dict, who: str = "priya", *, conversation: bool = True, channel: str = "text") -> Actor:
    from app.models import User

    async with db.session_scope() as s:
        u = await s.get(User, ids[f"{who}_id"])
        conv_id = None
        if conversation:
            c = Conversation(workspace_id=u.workspace_id, user_id=u.id, channel=channel)
            s.add(c)
            await s.flush()
            conv_id = c.id
        return Actor(u.id, u.workspace_id, u.role, u.party_id, u.display_name, conv_id)


async def add_inspected_document(actor: Actor, *, vendor="Sunrise Residency Pune", total_rupees=4800,
                                 bdate=date(2026, 11, 19), arithmetic="ok", doc_type="receipt", sha="a" * 64) -> int:
    async with db.session_scope() as s:
        d = Document(workspace_id=actor.workspace_id, uploader_id=actor.user_id, storage_key="test/key", filename="receipt.pdf",
                     sha256=sha, media_type="application/pdf", pages=1, size_bytes=1000, status="inspected")
        s.add(d)
        await s.flush()
        s.add(Extraction(workspace_id=actor.workspace_id, document_id=d.id, doc_type=doc_type, arithmetic=arithmetic,
                         fields={"vendor": vendor, "date": bdate.isoformat(), "total_paise": total_rupees * 100, "currency": "INR"}))
        return d.id
