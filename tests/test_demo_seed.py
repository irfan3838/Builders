"""Demo seed (seed(demo=True), seed/demo_data.py): base invariants, ledger conservation, leave, contracts, reset."""

import os
from datetime import date

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.pool import NullPool

from app import db
from app.config import get_settings
from app.models import (Base, Bill, BudgetLine, BudgetMovement, BudgetPeriod, Claim, Contract, ContractDeadline,
                        LeaveMovement, Workspace)
from seed.seed_v1 import reset_and_seed, seed


async def _wipe_and_seed(**kw) -> dict:
    url = os.getenv("TEST_DATABASE_URL", get_settings().test_database_url)
    db.configure(url, poolclass=NullPool)
    async with db.engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        tables = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    async with db.session_scope() as s:
        return await seed(s, **kw)


@pytest.fixture
async def demo():
    ids = await _wipe_and_seed(demo=True)
    yield ids
    await db.engine().dispose()


async def _bucket_sums(s, line_id=None, source_type=None, source_id=None) -> dict:
    q = select(BudgetMovement.bucket, func.coalesce(func.sum(BudgetMovement.amount_paise), 0)).group_by(BudgetMovement.bucket)
    if line_id is not None:
        q = q.where(BudgetMovement.line_id == line_id)
    if source_type is not None:
        q = q.where(BudgetMovement.source_type == source_type, BudgetMovement.source_id == source_id)
    return {b: int(v) for b, v in (await s.execute(q)).all()}


async def test_base_line_invariants_hold_with_demo(demo):
    async with db.session_scope() as s:
        travel = await _bucket_sums(s, demo["travel_line_id"])
        assert travel.get("reserved") == 5_000 * 100
        office = (await s.execute(select(BudgetLine).where(BudgetLine.category == "Office Supplies"))).scalar_one()
        o = await _bucket_sums(s, office.id)
        assert o.get("committed") == 18_500 * 100
        assert o.get("spent") == 9_400 * 100


async def test_all_lines_closed_jul_to_sep(demo):
    async with db.session_scope() as s:
        lines = (await s.execute(select(BudgetLine.id))).scalars().all()
        assert len(lines) == 12
        for m in (date(2026, 7, 1), date(2026, 8, 1), date(2026, 9, 1)):
            rows = (await s.execute(select(BudgetPeriod).where(BudgetPeriod.fiscal_month == m))).scalars().all()
            assert {r.line_id for r in rows} == set(lines), f"month {m} not closed for every line"
            assert all(r.closed_at is not None for r in rows), f"month {m} has an open period"


async def test_ledger_conservation_for_bills_and_claims(demo):
    async with db.session_scope() as s:
        records = [("bill", b) for b in (await s.execute(select(Bill))).scalars()] + \
                  [("claim", c) for c in (await s.execute(select(Claim))).scalars()]
        seen = {"settled": 0, "approved": 0, "open": 0}
        for kind, r in records:
            sums = await _bucket_sums(s, source_type=kind, source_id=r.id)
            if r.settlement_state == "settled":
                seen["settled"] += 1
                assert sums.get("committed", 0) == 0, (kind, r.ref, sums)
                assert sums.get("spent", 0) == r.amount_paise, (kind, r.ref, sums)
            elif r.state == "approved":
                seen["approved"] += 1
                assert sums.get("committed", 0) == r.amount_paise, (kind, r.ref, sums)
                assert sums.get("spent", 0) == 0, (kind, r.ref, sums)
            else:
                seen["open"] += 1
                assert r.state in ("submitted", "rejected")
                assert sums == {}, (kind, r.ref, sums)
        assert all(seen.values()), seen  # the demo data exercises every state


async def test_leave_balances_never_negative(demo):
    async with db.session_scope() as s:
        rows = (await s.execute(select(LeaveMovement.user_id, LeaveMovement.leave_type, LeaveMovement.bucket,
                                       func.sum(LeaveMovement.days)).group_by(LeaveMovement.user_id, LeaveMovement.leave_type,
                                                                              LeaveMovement.bucket))).all()
        bal: dict = {}
        for uid, lt, bucket, days in rows:
            bal.setdefault((uid, lt), {})[bucket] = int(days)
        assert len(bal) >= 24 * 3
        for key, b in bal.items():
            avail = b.get("granted", 0) - b.get("reserved", 0) - b.get("used", 0)
            assert avail >= 0, (key, b)


async def test_demo_contracts_and_deadlines(demo):
    async with db.session_scope() as s:
        for n in (5, 6, 7, 8):
            c = (await s.execute(select(Contract).where(Contract.ref == f"AG{n}"))).scalar_one()
            n_dl = (await s.execute(select(func.count()).select_from(ContractDeadline)
                                    .where(ContractDeadline.contract_id == c.id))).scalar_one()
            assert n_dl >= 1, f"AG{n} {c.title} has no deadlines"
        cn_id = demo["contract_saas_cloudnest_ref"]
        cn = (await s.execute(select(Contract).where(Contract.ref == cn_id))).scalar_one()
        due = (await s.execute(select(ContractDeadline.due_on).where(ContractDeadline.contract_id == cn.id,
                                                                    ContractDeadline.kind == "renewal_notice"))).scalars().all()
        assert date(2026, 12, 1) in due, due


async def test_demo_reset_is_idempotent(demo):
    url = os.getenv("TEST_DATABASE_URL", get_settings().test_database_url)
    await db.engine().dispose()
    first = await reset_and_seed(url, demo=True)
    second = await reset_and_seed(url, demo=True)
    assert first["demo_employees"] == second["demo_employees"] == 23  # len(demo_data.PEOPLE)=22 + the invited new joiner
    async with db.session_scope() as s:
        assert (await s.execute(select(func.count()).select_from(Workspace))).scalar_one() == 1
        assert (await s.execute(select(func.count()).select_from(Bill))).scalar_one() >= 22
    await db.engine().dispose()
