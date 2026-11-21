"""Budget ledger. Every balance is computed from the append-only budget_movements table.

available = allocation - reserved - committed - spent. A rupee sits in exactly one of the
reserved / committed / spent buckets at a time, so approval and settlement only move money
between buckets.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NOT_FOUND, DomainError
from app.models import BudgetLine, BudgetMovement, Claim

BUCKETS = ("allocation", "reserved", "committed", "spent")


async def get_line(s: AsyncSession, workspace_id: int, *, line_id: int | None = None, category: str | None = None) -> BudgetLine:
    q = select(BudgetLine).where(BudgetLine.workspace_id == workspace_id)
    if line_id is not None:
        q = q.where(BudgetLine.id == line_id)
    elif category is not None:
        q = q.where(func.lower(BudgetLine.category) == category.strip().lower())
    else:
        raise ValueError("line_id or category required")
    line = (await s.execute(q)).scalars().first()
    if line is None:
        known = (await s.execute(select(BudgetLine.category).where(BudgetLine.workspace_id == workspace_id))).scalars().all()
        raise DomainError(NOT_FOUND, f"No budget line for {category or line_id}", known_categories=sorted(known))
    return line


async def position(s: AsyncSession, workspace_id: int, line_id: int) -> dict:
    rows = (
        await s.execute(
            select(BudgetMovement.bucket, func.coalesce(func.sum(BudgetMovement.amount_paise), 0))
            .where(BudgetMovement.workspace_id == workspace_id, BudgetMovement.line_id == line_id)
            .group_by(BudgetMovement.bucket)
        )
    ).all()
    b = {k: 0 for k in BUCKETS}
    b.update({k: int(v) for k, v in rows})
    pending = (
        await s.execute(
            select(func.coalesce(func.sum(Claim.amount_paise), 0)).where(
                Claim.workspace_id == workspace_id, Claim.line_id == line_id, Claim.state == "submitted"
            )
        )
    ).scalar_one()
    return {
        "allocated_paise": b["allocation"],
        "reserved_paise": b["reserved"],
        "committed_paise": b["committed"],
        "spent_paise": b["spent"],
        "available_paise": b["allocation"] - b["reserved"] - b["committed"] - b["spent"],
        "pending_claims_paise": int(pending),
    }


async def post(
    s: AsyncSession,
    workspace_id: int,
    line_id: int,
    bucket: str,
    amount_paise: int,
    kind: str,
    *,
    source_type: str | None = None,
    source_id: int | None = None,
    economic_event_id: str | None = None,
    receipt_id: int | None = None,
    memo: str | None = None,
) -> BudgetMovement:
    assert bucket in BUCKETS, bucket
    m = BudgetMovement(
        workspace_id=workspace_id,
        line_id=line_id,
        bucket=bucket,
        amount_paise=amount_paise,
        kind=kind,
        source_type=source_type,
        source_id=source_id,
        economic_event_id=economic_event_id,
        receipt_id=receipt_id,
        memo=memo,
    )
    s.add(m)
    await s.flush()
    return m


async def movements(s: AsyncSession, workspace_id: int, line_id: int, *, limit: int = 20) -> list[BudgetMovement]:
    q = (
        select(BudgetMovement)
        .where(BudgetMovement.workspace_id == workspace_id, BudgetMovement.line_id == line_id)
        .order_by(BudgetMovement.id.desc())
        .limit(limit)
    )
    return list((await s.execute(q)).scalars().all())
