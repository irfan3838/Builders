"""Agent-composed charts and views.

The model fills a typed ChartSpec (enum-limited names only). This module checks it against a registry of
vetted measures and dimensions, compiles a parameterised SQLAlchemy Core query scoped to the actor's
workspace and role, and stores the result as a ResultSnapshot. The chart, the table and the spoken
answer all read that one snapshot. No model text ever reaches SQL: names are looked up in the registry
and filter values are matched against values that already exist in the actor's scope.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Date, and_, case, func, literal, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement

from app.actor import Actor
from app.errors import AMBIGUOUS, FORBIDDEN, NOT_FOUND, VALIDATION, DomainError
from app.models import Bill, BudgetLine, BudgetMovement, Claim, Conversation, Invoice, Party, ResultSnapshot
from app.money import format_inr
from app.services.records import normalize_name, today_ist

MAX_GROUPS = 500
MAX_SERIES = 3  # validated categorical slots; the rest fold into "Other"
STATEMENT_TIMEOUT_MS = 3000
AGEING_ORDER = ["not yet due", "1-30 days overdue", "31-60 days overdue", "61-90 days overdue", "90+ days overdue", "paid"]


# ------------------------------------------------------------------ public spec (what the model may say)

class MeasureName(StrEnum):
    receivables_outstanding = "receivables_outstanding"
    invoiced_amount = "invoiced_amount"
    received_amount = "received_amount"
    invoice_count = "invoice_count"
    to_raise_amount = "to_raise_amount"
    overdue_amount = "overdue_amount"
    fx_gain = "fx_gain"
    payables_outstanding = "payables_outstanding"
    bill_amount = "bill_amount"
    bill_count = "bill_count"
    claims_amount = "claims_amount"
    claims_count = "claims_count"
    budget_allocated = "budget_allocated"
    budget_reserved = "budget_reserved"
    budget_committed = "budget_committed"
    budget_spent = "budget_spent"
    budget_available = "budget_available"
    budget_actual = "budget_actual"
    budget_remaining = "budget_remaining"


class DimensionName(StrEnum):
    customer = "customer"
    invoice = "invoice"
    vendor = "vendor"
    employee = "employee"
    category = "category"
    department = "department"
    status = "status"
    ageing_bucket = "ageing_bucket"
    issue_month = "issue_month"
    due_month = "due_month"
    bill_month = "bill_month"
    claim_month = "claim_month"
    budget_month = "budget_month"
    billing_month = "billing_month"
    currency = "currency"
    client_state = "client_state"


class ChartType(StrEnum):
    auto = "auto"
    bar = "bar"
    horizontal_bar = "horizontal_bar"
    grouped_bar = "grouped_bar"
    stacked_bar = "stacked_bar"
    line = "line"
    area = "area"
    donut = "donut"
    table = "table"
    kpi = "kpi"


class SortOrder(StrEnum):
    value_desc = "value_desc"
    value_asc = "value_asc"
    label = "label"


class FilterSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dimension: DimensionName
    values: list[str] = Field(min_length=1, max_length=10, description="Spoken values, e.g. ['Acme']; matched against real records")
    exclude: bool | None = Field(None, description="true = everything except these values")


class ChartSpec(BaseModel):
    """What to chart. Names only; the server owns the SQL."""

    model_config = ConfigDict(extra="forbid")
    measures: list[MeasureName] = Field(min_length=1, max_length=3, description="1-3 measures from the same source and unit")
    dimension: DimensionName | None = Field(None, description="Group by (x axis). Omit for a single headline number.")
    series_by: DimensionName | None = Field(None, description="Optional second grouping (stacked/grouped). Only with one measure.")
    filters: list[FilterSpec] | None = Field(None, max_length=5)
    overdue_only: bool | None = Field(None, description="Receivables/payables past their due date and still unpaid")
    date_from: date | None = Field(None, description="Inclusive, on the source's business date (invoice issue / bill / claim date)")
    date_to: date | None = None
    chart: ChartType | None = Field(None, description="Omit or 'auto' to let the server choose")
    sort: SortOrder | None = None
    top_n: int | None = Field(None, ge=1, le=20, description="Keep the largest N groups; the rest fold into 'Other'")
    title: str | None = Field(None, max_length=80, description="Optional display title; generated when omitted")


class ChartSpecPatch(BaseModel):
    """A revision. Anything omitted keeps its current value, so grouping survives 'only overdue'."""

    model_config = ConfigDict(extra="forbid")
    measures: list[MeasureName] | None = Field(None, min_length=1, max_length=3)
    dimension: DimensionName | None = None
    clear_dimension: bool | None = Field(None, description="Collapse to a single total")
    series_by: DimensionName | None = None
    clear_series_by: bool | None = None
    add_filters: list[FilterSpec] | None = Field(None, max_length=5)
    remove_filters: list[DimensionName] | None = Field(None, description="Drop filters on these dimensions")
    clear_filters: bool | None = Field(None, description="Drop all dimension filters and overdue_only and dates")
    overdue_only: bool | None = None
    date_from: date | None = None
    date_to: date | None = None
    clear_dates: bool | None = None
    chart: ChartType | None = None
    sort: SortOrder | None = None
    top_n: int | None = Field(None, ge=1, le=20)
    clear_top_n: bool | None = None
    title: str | None = Field(None, max_length=80)


class ViewItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    snapshot_id: str = Field(max_length=40)
    display: Literal["chart", "table", "kpi"] | None = Field(None, description="chart (default, the snapshot's own type), table or kpi")


class ViewSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=80)
    items: list[ViewItem] = Field(min_length=1, max_length=4)


# ------------------------------------------------------------------ registry (what the server knows)

@dataclass(frozen=True)
class Measure:
    label: str
    unit: str  # paise | count
    source: str
    description: str


@dataclass(frozen=True)
class Dim:
    label: str
    kind: str  # category | time | bucket
    description: str


MEASURES: dict[str, Measure] = {
    "receivables_outstanding": Measure("Outstanding", "paise", "receivables", "Sent / part-paid customer invoices not yet paid (total − received − moved on)"),
    "invoiced_amount": Measure("Projected", "paise", "receivables", "Billed to customers (projection): total less balances moved on; merged rows 0; written off = what came in"),
    "received_amount": Measure("Received", "paise", "receivables", "INR credited against customer invoices (counted in the invoice's billing month)"),
    "invoice_count": Measure("Invoices", "count", "receivables", "Number of customer invoices"),
    "to_raise_amount": Measure("To raise", "paise", "receivables", "Planned customer invoices not raised (sent) yet"),
    "overdue_amount": Measure("Overdue", "paise", "receivables", "Outstanding past its due date"),
    "fx_gain": Measure("FX gain/loss", "paise", "receivables", "On paid invoices: received + moved − booked INR total (negative = loss / short pay)"),
    "payables_outstanding": Measure("Unpaid", "paise", "payables", "Vendor bills not yet settled (awaiting approval or approved)"),
    "bill_amount": Measure("Billed", "paise", "payables", "Vendor bill amounts (rejected bills excluded)"),
    "bill_count": Measure("Bills", "count", "payables", "Number of vendor bills (rejected excluded)"),
    "claims_amount": Measure("Claimed", "paise", "claims", "Employee expense claim amounts"),
    "claims_count": Measure("Claims", "count", "claims", "Number of expense claims"),
    "budget_allocated": Measure("Allocated", "paise", "budget", "Budget allocation (sum of allocation movements)"),
    "budget_reserved": Measure("Reserved", "paise", "budget", "Held for open reservations (e.g. booked trips)"),
    "budget_committed": Measure("Committed", "paise", "budget", "Approved but not yet paid"),
    "budget_spent": Measure("Spent", "paise", "budget", "Paid / settled"),
    "budget_available": Measure("Available", "paise", "budget", "allocated − reserved − committed − spent"),
    "budget_actual": Measure("Actual", "paise", "budget", "Approved spend (committed + spent), as the monthly budget counts it"),
    "budget_remaining": Measure("Remaining", "paise", "budget", "Budget minus actual (approved spend); excludes reservations"),
}

DIMS: dict[str, Dim] = {
    "customer": Dim("Customer", "category", "Customer name"),
    "invoice": Dim("Invoice", "category", "Individual invoice number"),
    "vendor": Dim("Vendor", "category", "Vendor name"),
    "employee": Dim("Employee", "category", "Claim beneficiary"),
    "category": Dim("Category", "category", "Budget category (Travel, IT & Cloud, ...)"),
    "department": Dim("Department", "category", "Owning department"),
    "status": Dim("Status", "category", "Lifecycle status (overdue / awaiting approval / paid ...)"),
    "ageing_bucket": Dim("Ageing", "bucket", "Days past due: not yet due, 1-30, 31-60, 61-90, 90+"),
    "issue_month": Dim("Invoice month", "time", "Month the invoice was issued"),
    "due_month": Dim("Due month", "time", "Month the payment is due"),
    "bill_month": Dim("Bill month", "time", "Month of the bill date"),
    "claim_month": Dim("Claim month", "time", "Month of the expense"),
    "budget_month": Dim("Budget month", "time", "Budget month (April-March financial year)"),
    "billing_month": Dim("Billing month", "time", "Month a customer invoice bills for (what revenue reports by)"),
    "currency": Dim("Currency", "category", "Invoice currency (INR, USD, ...)"),
    "client_state": Dim("Client state", "category", "Customer active / paused / project over"),
}


@dataclass
class Compiled:
    """One source compiled for one actor and day: FROM, scope WHERE, and named column expressions."""

    frm: object
    where: list[ColumnElement]
    dims: dict[str, ColumnElement]
    measures: dict[str, ColumnElement]
    ref: ColumnElement
    open_where: ColumnElement | None = None  # applied when an "open balance" measure is charted
    open_measures: frozenset[str] = frozenset()
    overdue: ColumnElement | None = None
    date_col: ColumnElement | None = None
    scope_note: str | None = None


@dataclass(frozen=True)
class Source:
    label: str
    record_label: str
    approver_only: bool
    compile: Callable[[Actor, date], Compiled] = field(repr=False)


def _ageing(due: ColumnElement, is_open: ColumnElement, today: date) -> ColumnElement:
    days = literal(today, Date) - due
    return case(
        (~is_open, "paid"),
        (days <= 0, "not yet due"),
        (days <= 30, "1-30 days overdue"),
        (days <= 60, "31-60 days overdue"),
        (days <= 90, "61-90 days overdue"),
        else_="90+ days overdue",
    )


def _month(col: ColumnElement) -> ColumnElement:
    return func.to_char(func.date_trunc("month", col), "YYYY-MM")


def _receivables(a: Actor, today: date) -> Compiled:
    """Customer invoices with the revenue module's figures (ported from copilot): projection, received, outstanding
    (sent / part paid only), overdue, to raise, FX gain. Reported by billing month."""
    cust = aliased(Party)
    st = Invoice.status
    left = func.greatest(Invoice.amount_paise - Invoice.paid_paise - Invoice.moved_paise, 0)
    out = case((st.in_(("sent", "part_paid")), left), else_=0)
    is_open = out > 0
    overdue = and_(Invoice.due_date < today, is_open)
    billed = case((st == "merged", 0), (st == "written_off", Invoice.paid_paise), else_=Invoice.amount_paise - Invoice.moved_paise)
    bill_date = func.make_date(Invoice.year, Invoice.month, 1)
    number = func.coalesce(Invoice.number, Invoice.ref)
    return Compiled(
        frm=Invoice.__table__.join(cust, cust.id == Invoice.customer_party_id),
        where=[Invoice.workspace_id == a.workspace_id, cust.workspace_id == a.workspace_id, cust.archived_at.is_(None)],
        dims={
            "customer": cust.name, "invoice": number,
            "status": case((st == "to_raise", "to raise"), (st.in_(("written_off", "merged")), "closed"), (st == "paid", "paid"),
                           (~is_open, "paid"), (Invoice.due_date < today, "overdue"), else_="not yet due"),
            "ageing_bucket": case((st == "to_raise", "not yet due"), else_=_ageing(Invoice.due_date, is_open, today)),
            "issue_month": _month(func.coalesce(Invoice.issue_date, bill_date)), "due_month": _month(Invoice.due_date),
            "billing_month": _month(bill_date), "currency": Invoice.currency, "client_state": cust.state,
        },
        measures={
            "receivables_outstanding": func.sum(out), "invoiced_amount": func.sum(billed),
            "received_amount": func.sum(Invoice.paid_paise), "invoice_count": func.count(Invoice.id),
            "to_raise_amount": func.sum(case((st == "to_raise", Invoice.amount_paise), else_=0)),
            "overdue_amount": func.sum(case((overdue, out), else_=0)),
            "fx_gain": func.sum(case((st == "paid", Invoice.paid_paise + Invoice.moved_paise - Invoice.amount_paise), else_=0)),
        },
        ref=number,
        open_where=is_open, open_measures=frozenset({"receivables_outstanding", "overdue_amount"}),
        overdue=overdue,
        date_col=bill_date,
    )


def _payables(a: Actor, today: date) -> Compiled:
    ven = aliased(Party)
    is_open = Bill.settlement_state == "unpaid"
    return Compiled(
        frm=Bill.__table__.join(ven, ven.id == Bill.vendor_party_id).join(BudgetLine, BudgetLine.id == Bill.line_id),
        where=[Bill.workspace_id == a.workspace_id, Bill.state != "rejected", BudgetLine.workspace_id == a.workspace_id],
        dims={
            "vendor": ven.name, "category": BudgetLine.category, "department": BudgetLine.department,
            "status": case((~is_open, "paid"), (Bill.state == "submitted", "awaiting approval"), else_="approved, unpaid"),
            "ageing_bucket": _ageing(func.coalesce(Bill.due_date, Bill.business_date), is_open, today),
            "bill_month": _month(Bill.business_date), "due_month": _month(func.coalesce(Bill.due_date, Bill.business_date)),
        },
        measures={"payables_outstanding": func.sum(Bill.amount_paise), "bill_amount": func.sum(Bill.amount_paise),
                  "bill_count": func.count(Bill.id)},
        ref=Bill.ref,
        open_where=is_open, open_measures=frozenset({"payables_outstanding"}),
        overdue=and_(func.coalesce(Bill.due_date, Bill.business_date) < today, is_open),
        date_col=Bill.business_date,
    )


def _claims(a: Actor, today: date) -> Compiled:
    emp = aliased(Party)
    where = [Claim.workspace_id == a.workspace_id, BudgetLine.workspace_id == a.workspace_id]
    note = None
    if not a.is_approver:  # same rule as records.claim_by_ref
        where.append(or_(Claim.beneficiary_party_id == a.party_id, Claim.submitter_id == a.user_id))
        note = "your own claims only"
    return Compiled(
        frm=Claim.__table__.join(emp, emp.id == Claim.beneficiary_party_id).join(BudgetLine, BudgetLine.id == Claim.line_id),
        where=where,
        dims={
            "employee": emp.name, "category": BudgetLine.category, "department": BudgetLine.department,
            "status": case((Claim.settlement_state == "settled", "reimbursed"), (Claim.state == "approved", "approved, unpaid"),
                           else_=Claim.state),
            "claim_month": _month(Claim.business_date),
        },
        measures={"claims_amount": func.sum(Claim.amount_paise), "claims_count": func.count(Claim.id)},
        ref=Claim.ref, date_col=Claim.business_date, scope_note=note,
    )


def _budget(a: Actor, today: date) -> Compiled:
    def bucket(name: str) -> ColumnElement:
        return func.coalesce(func.sum(case((BudgetMovement.bucket == name, BudgetMovement.amount_paise), else_=0)), 0)

    alloc, res, com, spent = (bucket(b) for b in ("allocation", "reserved", "committed", "spent"))
    return Compiled(
        frm=BudgetMovement.__table__.join(BudgetLine, BudgetLine.id == BudgetMovement.line_id),
        where=[BudgetMovement.workspace_id == a.workspace_id, BudgetLine.workspace_id == a.workspace_id],
        dims={"category": BudgetLine.category, "department": BudgetLine.department,
              "budget_month": _month(BudgetMovement.fiscal_month)},
        measures={"budget_allocated": alloc, "budget_reserved": res, "budget_committed": com, "budget_spent": spent,
                  "budget_available": alloc - res - com - spent, "budget_actual": com + spent,
                  "budget_remaining": alloc - com - spent},
        ref=BudgetLine.category,
    )


SOURCES: dict[str, Source] = {
    "receivables": Source("Receivables (customer invoices)", "invoices", True, _receivables),
    "payables": Source("Payables (vendor bills)", "bills", True, _payables),
    "claims": Source("Expense claims", "claims", False, _claims),
    "budget": Source("Budget ledger", "budget lines", False, _budget),
}


def options(actor: Actor) -> dict:
    """Registry as the model sees it, limited to what this actor may chart."""
    today = today_ist()
    out = []
    for key, src in SOURCES.items():
        if src.approver_only and not actor.is_approver:
            continue
        c = src.compile(actor, today)
        out.append({
            "source": key, "label": src.label,
            "measures": [{"name": n, "label": m.label, "unit": "INR" if m.unit == "paise" else "count", "description": m.description}
                         for n, m in MEASURES.items() if m.source == key],
            "dimensions": [{"name": d, "label": DIMS[d].label, "kind": DIMS[d].kind, "description": DIMS[d].description} for d in c.dims],
            "supports_overdue_only": c.overdue is not None, "supports_date_range": c.date_col is not None,
            "scope": c.scope_note or "whole workspace",
        })
    return {
        "sources": out,
        "chart_types": [t.value for t in ChartType],
        "rules": [
            "All measures in one chart come from the same source and share a unit (no dual axis).",
            "line/area need a month dimension; kpi has no dimension; donut is one measure by one non-time dimension.",
            "series_by needs a dimension and exactly one measure; at most 3 series are drawn, the rest fold into 'Other'.",
            "Filter values are matched against real records; ambiguous or unknown values come back with candidates.",
        ],
    }


# ------------------------------------------------------------------ validation

def _bad(msg: str, **details) -> DomainError:
    return DomainError(VALIDATION, msg, **details)


def _source_for(spec: ChartSpec) -> str:
    srcs = {MEASURES[m.value].source for m in spec.measures}
    if len(srcs) > 1:
        raise _bad("Measures come from different sources; make one chart per source.",
                   measure_sources={m.value: MEASURES[m.value].source for m in spec.measures})
    units = {MEASURES[m.value].unit for m in spec.measures}
    if len(units) > 1:
        raise _bad("Amounts and counts cannot share one axis; make two charts.")
    if len({m.value for m in spec.measures}) != len(spec.measures):
        raise _bad("A measure is listed twice.")
    return srcs.pop()


def chart_problem(spec: ChartSpec) -> str | None:
    """Why the requested chart type does not fit the spec's shape, or None."""
    ct = spec.chart or ChartType.auto
    d = DIMS[spec.dimension.value] if spec.dimension else None
    multi = len(spec.measures) > 1 or spec.series_by is not None
    if ct in (ChartType.line, ChartType.area) and (d is None or d.kind != "time"):
        return f"A {ct.value} chart needs a month dimension (billing_month, issue_month, due_month, bill_month, claim_month or budget_month)."
    if ct == ChartType.kpi and d is not None:
        return "A kpi shows a single number; remove the dimension or pick another chart type."
    if ct == ChartType.donut and (d is None or d.kind == "time" or multi):
        return "A donut shows one measure split by one non-time dimension."
    if ct in (ChartType.bar, ChartType.horizontal_bar, ChartType.grouped_bar, ChartType.stacked_bar) and d is None:
        return f"A {ct.value} chart needs a dimension."
    if ct in (ChartType.grouped_bar, ChartType.stacked_bar) and not multi:
        return f"A {ct.value} chart needs series_by or more than one measure."
    return None


def validate(spec: ChartSpec, actor: Actor, today: date) -> tuple[str, Compiled]:
    key = _source_for(spec)
    src = SOURCES[key]
    if src.approver_only and not actor.is_approver:
        raise DomainError(FORBIDDEN, f"{src.label} are visible to finance approvers only.")
    c = src.compile(actor, today)
    allowed = sorted(c.dims)
    for name, dim in (("dimension", spec.dimension), ("series_by", spec.series_by)):
        if dim is not None and dim.value not in c.dims:
            raise _bad(f"{src.label} cannot be grouped by '{dim.value}'.", field=name, available_dimensions=allowed)
    for f in spec.filters or []:
        if f.dimension.value not in c.dims:
            raise _bad(f"{src.label} cannot be filtered by '{f.dimension.value}'.", available_dimensions=allowed)
    if len({f.dimension for f in spec.filters or []}) != len(spec.filters or []):
        raise _bad("Use one filter per dimension (list several values in it).")
    if spec.series_by is not None:
        if spec.dimension is None:
            raise _bad("series_by needs a dimension.")
        if spec.series_by == spec.dimension:
            raise _bad("series_by must differ from the dimension.")
        if len(spec.measures) > 1:
            raise _bad("series_by works with exactly one measure.")
    if spec.overdue_only and c.overdue is None:
        raise _bad(f"{src.label} have no due dates; overdue_only does not apply.")
    if (spec.date_from or spec.date_to) and c.date_col is None:
        raise _bad(f"{src.label} have no business date to filter on.")
    if spec.date_from and spec.date_to and spec.date_from > spec.date_to:
        raise _bad("date_from is after date_to.")
    if spec.top_n and spec.dimension and DIMS[spec.dimension.value].kind == "time":
        raise _bad("top_n applies to non-time dimensions.")
    if (p := chart_problem(spec)) is not None:
        raise _bad(p)
    return key, c


async def _resolve_filter_values(s: AsyncSession, c: Compiled, f: FilterSpec) -> list[str]:
    """Map spoken values onto values that exist in scope. Exact (case-insensitive) beats fuzzy; ambiguity is an error."""
    col = c.dims[f.dimension.value]
    existing = [v for v in (await s.execute(select(col).select_from(c.frm).where(*c.where).distinct().limit(200))).scalars() if v]
    out: list[str] = []
    for raw in f.values:
        want = normalize_name(raw)
        if not want:
            raise _bad("Empty filter value.")
        exact = [v for v in existing if normalize_name(v) == want]
        hits = exact or [v for v in existing if normalize_name(v).startswith(want) or want in normalize_name(v)]
        if not hits:
            raise _bad(f"No {DIMS[f.dimension.value].label.lower()} matches '{raw}'.", available=sorted(existing)[:15])
        if len(hits) > 1:
            raise DomainError(AMBIGUOUS, f"'{raw}' matches more than one {DIMS[f.dimension.value].label.lower()}. Ask which one.",
                              candidates=sorted(hits))
        out.append(hits[0])
    return out


# ------------------------------------------------------------------ execution

def _month_range(first: str, last: str) -> list[str]:
    y, m = map(int, first.split("-"))
    ly, lm = map(int, last.split("-"))
    out = []
    while (y, m) <= (ly, lm) and len(out) < 120:
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _month_label(key: str) -> str:
    return date(int(key[:4]), int(key[5:7]), 1).strftime("%b %Y")


def _auto_chart(spec: ChartSpec, n_keys: int, longest_label: int = 0) -> str:
    if spec.dimension is None:
        return "kpi"
    kind = DIMS[spec.dimension.value].kind
    if kind == "time":
        return "line"
    if spec.series_by is not None or len(spec.measures) > 1:
        return "grouped_bar"
    # Names are read sideways badly in a narrow panel; long category labels go horizontal.
    return "horizontal_bar" if n_keys > 6 or (n_keys > 3 and longest_label > 10) else "bar"


def _title(spec: ChartSpec, applied: list[str]) -> str:
    if spec.title:
        return spec.title.strip()
    t = " vs ".join(MEASURES[m.value].label for m in spec.measures)
    src = MEASURES[spec.measures[0].value].source
    t = {"receivables": f"Receivables: {t.lower()}", "payables": f"Payables: {t.lower()}", "claims": f"Claims: {t.lower()}",
         "budget": f"Budget: {t.lower()}"}[src]
    if spec.dimension:
        t += f" by {DIMS[spec.dimension.value].label.lower()}"
    if spec.series_by:
        t += f" and {DIMS[spec.series_by.value].label.lower()}"
    if any(a.startswith("overdue") for a in applied):
        t = t.replace(": outstanding", ": overdue").replace(": unpaid", ": overdue")
    return t  # every applied filter is listed under the chart and returned with the spoken summary


async def run_spec(s: AsyncSession, actor: Actor, spec: ChartSpec, *, today: date | None = None) -> dict:
    """Validate and run a spec. Returns the snapshot payload (spec, rows, totals, meta) without storing it."""
    today = today or today_ist()
    key, c = validate(spec, actor, today)
    measures = [m.value for m in spec.measures]
    where = list(c.where)
    applied: list[str] = []
    if c.open_where is not None and set(measures) & c.open_measures:
        where.append(c.open_where)
        applied.append(f"open {SOURCES[key].record_label} only")
    if spec.overdue_only:
        where.append(c.overdue)
        applied.append(f"overdue as of {today:%d %b %Y}")
    if spec.date_from:
        where.append(c.date_col >= spec.date_from)
    if spec.date_to:
        where.append(c.date_col <= spec.date_to)
    if spec.date_from or spec.date_to:
        applied.append(f"{spec.date_from or '…'} to {spec.date_to or '…'}")
    resolved_filters = []
    for f in spec.filters or []:
        vals = await _resolve_filter_values(s, c, f)
        col = c.dims[f.dimension.value]
        where.append(col.notin_(vals) if f.exclude else col.in_(vals))
        applied.append(f"{DIMS[f.dimension.value].label.lower()} {'not ' if f.exclude else ''}{', '.join(vals)}")
        resolved_filters.append({"dimension": f.dimension.value, "values": vals, "exclude": bool(f.exclude)})

    group = [c.dims[d.value] for d in (spec.dimension, spec.series_by) if d is not None]
    cols = [g.label(f"g{i}") for i, g in enumerate(group)] + [c.measures[m].label(m) for m in measures]
    cols.append(func.array_agg(c.ref.distinct()).label("refs"))
    q = select(*cols).select_from(c.frm).where(*where)
    if group:
        q = q.group_by(*group)
    await s.execute(text(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}"))
    raw = (await s.execute(q.limit(MAX_GROUPS + 1))).mappings().all()
    if len(raw) > MAX_GROUPS:
        raise _bad("Too many groups to chart; add a filter or top_n.")

    rows = []
    for r in raw:
        refs = sorted(x for x in (r["refs"] or []) if x is not None)
        if not group and not refs:
            continue  # aggregate over zero rows
        rows.append({"key": r.get("g0") if group else "Total", "series": r.get("g1") if spec.series_by else None,
                     "values": {m: int(r[m] or 0) for m in measures}, "refs": refs})

    folded = _fold(rows, spec, measures)
    _order(rows, spec, measures)
    kind = DIMS[spec.dimension.value].kind if spec.dimension else None
    if kind == "time" and rows and spec.series_by is None:  # gap-fill months so the line is honest
        have = {r["key"] for r in rows}
        for k in _month_range(min(have), max(have)):
            if k not in have:
                rows.append({"key": k, "series": None, "values": {m: 0 for m in measures}, "refs": []})
        rows.sort(key=lambda r: r["key"])
    for r in rows:
        r["label"] = _month_label(r["key"]) if kind == "time" else r["key"]

    totals = {m: sum(r["values"][m] for r in rows) for m in measures}
    n_keys = len({r["key"] for r in rows})
    chart = (spec.chart or ChartType.auto).value
    meta = {
        "source": key, "source_label": SOURCES[key].label, "record_label": SOURCES[key].record_label,
        "measures": [{"name": m, "label": MEASURES[m].label, "unit": MEASURES[m].unit} for m in measures],
        "dimension": {"name": spec.dimension.value, "label": DIMS[spec.dimension.value].label, "kind": kind} if spec.dimension else None,
        "series_by": {"name": spec.series_by.value, "label": DIMS[spec.series_by.value].label} if spec.series_by else None,
        "filters_applied": applied, "filters_resolved": resolved_filters, "as_of": today.isoformat(),
        "currency": "INR", "chart": _auto_chart(spec, n_keys, max((len(str(r["label"])) for r in rows), default=0)) if chart == "auto" else chart, "chart_requested": chart,
        "title": _title(spec, applied), "row_count": len(rows), "group_count": n_keys, "folded": folded,
        "scope": c.scope_note or "whole workspace",
        "source_record_count": len({x for r in rows for x in r["refs"]}),
    }
    return {"spec": spec.model_dump(mode="json"), "rows": rows, "totals": totals, "meta": meta}


def _fold(rows: list[dict], spec: ChartSpec, measures: list[str]) -> dict | None:
    """top_n on keys and the series cap; the remainder becomes 'Other' so totals stay whole."""
    folded = None
    first = measures[0]

    def fold_by(attr: str, keep: int) -> dict | None:
        sums: dict = {}
        for r in rows:
            sums[r[attr]] = sums.get(r[attr], 0) + r["values"][first]
        if len(sums) <= keep:
            return None
        ranked = sorted(sums, key=lambda k: (-sums[k], str(k)))
        drop = set(ranked[keep:])
        merged: dict = {}
        for r in [r for r in rows if r[attr] in drop]:
            rows.remove(r)
            other_key = r["series"] if attr == "key" else r["key"]
            m = merged.setdefault(other_key, {"key": "Other" if attr == "key" else r["key"],
                                              "series": r["series"] if attr == "key" else "Other",
                                              "values": {x: 0 for x in measures}, "refs": []})
            for x in measures:
                m["values"][x] += r["values"][x]
            m["refs"] = sorted(set(m["refs"]) | set(r["refs"]))
        rows.extend(merged.values())
        return {"by": attr, "kept": keep, "folded_groups": sorted(map(str, drop))}

    if spec.top_n and spec.dimension:
        folded = fold_by("key", spec.top_n)
    if spec.series_by:
        sf = fold_by("series", MAX_SERIES)
        folded = {**(folded or {}), "series": sf} if sf else folded
    return folded


def _order(rows: list[dict], spec: ChartSpec, measures: list[str]) -> None:
    if not spec.dimension:
        return
    kind = DIMS[spec.dimension.value].kind
    first = measures[0]
    if kind == "time":
        rows.sort(key=lambda r: (r["key"], r["series"] == "Other", str(r["series"])))
        return
    if kind == "bucket":
        rows.sort(key=lambda r: (AGEING_ORDER.index(r["key"]) if r["key"] in AGEING_ORDER else 99, r["series"] == "Other", str(r["series"])))
        return
    totals: dict = {}
    for r in rows:
        totals[r["key"]] = totals.get(r["key"], 0) + r["values"][first]
    order = spec.sort or SortOrder.value_desc

    def k(r):
        other = r["key"] == "Other"  # the folded remainder always sits last
        if order == SortOrder.label:
            return (other, str(r["key"]).lower(), r["series"] == "Other", str(r["series"]))
        sign = -1 if order == SortOrder.value_desc else 1
        return (other, sign * totals[r["key"]], str(r["key"]).lower(), r["series"] == "Other", str(r["series"]))

    rows.sort(key=k)


# ------------------------------------------------------------------ snapshots

async def store(s: AsyncSession, actor: Actor, payload: dict, *, parent: ResultSnapshot | None = None) -> ResultSnapshot:
    snap = ResultSnapshot(workspace_id=actor.workspace_id, conversation_id=actor.conversation_id, actor_id=actor.user_id,
                          parent_id=parent.id if parent else None, spec=payload["spec"], rows=payload["rows"],
                          totals=payload["totals"], meta=dict(payload["meta"]))
    s.add(snap)
    await s.flush()
    snap.meta = {**snap.meta, "lineage": (parent.meta.get("lineage") if parent else None) or (parent.id if parent else snap.id)}
    if actor.conversation_id:
        conv = await s.get(Conversation, actor.conversation_id)
        if conv is not None and conv.workspace_id == actor.workspace_id and conv.user_id == actor.user_id:
            conv.last_snapshot_id = snap.id
    await s.flush()
    return snap


async def load(s: AsyncSession, actor: Actor, snapshot_id: str | None) -> ResultSnapshot:
    """A snapshot is readable only by the actor who made it (its rows were scoped to that actor's role)."""
    if not snapshot_id:
        conv = await s.get(Conversation, actor.conversation_id) if actor.conversation_id else None
        snapshot_id = conv.last_snapshot_id if conv and conv.user_id == actor.user_id else None
        if not snapshot_id:
            raise DomainError(NOT_FOUND, "There is no chart in this conversation yet. Build one first.")
    snap = await s.get(ResultSnapshot, snapshot_id)
    if snap is None or snap.workspace_id != actor.workspace_id or snap.actor_id != actor.user_id:
        raise DomainError(NOT_FOUND, f"Chart {snapshot_id} not found")
    return snap


def apply_patch(spec: ChartSpec, patch: ChartSpecPatch) -> ChartSpec:
    d = spec.model_dump()
    p = patch.model_dump(exclude_none=True)
    for k in ("measures", "dimension", "series_by", "overdue_only", "date_from", "date_to", "chart", "sort", "top_n", "title"):
        if k in p:
            d[k] = p[k]
    if p.get("clear_dimension"):
        d["dimension"] = d["series_by"] = None
        d["top_n"] = None
    if p.get("clear_series_by"):
        d["series_by"] = None
    if p.get("clear_top_n"):
        d["top_n"] = None
    if p.get("clear_dates"):
        d["date_from"] = d["date_to"] = None
    filters = list(d.get("filters") or [])
    if p.get("clear_filters"):
        filters, d["overdue_only"], d["date_from"], d["date_to"] = [], None, None, None
        if "overdue_only" in p:
            d["overdue_only"] = p["overdue_only"]
    drop = set(p.get("remove_filters") or [])
    filters = [f for f in filters if f["dimension"] not in drop]
    for nf in p.get("add_filters") or []:  # a new filter on a dimension replaces the old one
        filters = [f for f in filters if f["dimension"] != nf["dimension"]] + [nf]
    d["filters"] = filters or None
    new = ChartSpec.model_validate(d)
    if "title" not in p and spec.title and p:
        new = new.model_copy(update={"title": None})  # an explicit title described the old chart
    if patch.chart is None and chart_problem(new):  # the old type no longer fits the new shape
        new = new.model_copy(update={"chart": ChartType.auto})
    return new


# ------------------------------------------------------------------ speech: read from the snapshot only

def fmt_value(paise_or_count: int, unit: str) -> str:
    return format_inr(paise_or_count) if unit == "paise" else str(paise_or_count)


def summarize(snap: ResultSnapshot, *, max_rows: int = 8) -> dict:
    meta, rows = snap.meta, snap.rows
    ms = meta["measures"]
    first = ms[0]
    total = snap.totals.get(first["name"], 0)
    shown = []
    for r in rows[:max_rows]:
        item = {"label": r["label"], **({"series": r["series"]} if r.get("series") else {})}
        for m in ms:
            item[m["label"].lower()] = fmt_value(r["values"][m["name"]], m["unit"])
        item[meta["record_label"]] = len(r["refs"])
        shown.append(item)
    insights = []
    keyed: dict = {}
    for r in rows:
        if r["key"] != "Other":
            keyed[r["label"]] = keyed.get(r["label"], 0) + r["values"][first["name"]]
    if len(keyed) > 1 and total:
        top = max(keyed, key=lambda k: keyed[k])
        insights.append(f"Largest: {top}, {fmt_value(keyed[top], first['unit'])} ({round(100 * keyed[top] / total)}% of the total)")
        if meta.get("dimension") and meta["dimension"]["kind"] == "time":
            nz = [k for k in keyed if keyed[k]]
            if len(nz) >= 2:
                insights.append(f"From {nz[0]} to {nz[-1]}: {fmt_value(keyed[nz[0]], first['unit'])} → {fmt_value(keyed[nz[-1]], first['unit'])}")
    return {
        "snapshot_id": snap.id, "title": meta["title"], "chart": meta["chart"], "as_of": meta["as_of"],
        "filters_applied": meta["filters_applied"], "scope": meta["scope"],
        "totals": {m["label"].lower(): fmt_value(snap.totals.get(m["name"], 0), m["unit"]) for m in ms},
        "groups": meta["group_count"], "rows": shown, "more_rows": max(0, len(rows) - max_rows),
        "insights": insights, "source_records": meta["source_record_count"],
        "folded": meta.get("folded"),
    }


def read_value(snap: ResultSnapshot, label: str, *, series: str | None = None) -> dict:
    """Look a value up in the stored rows (never a new query), so speech matches what is on screen."""
    want = normalize_name(label)
    if not want:
        raise _bad("Say which bar or row to read.")

    def match(rows: list[dict], attr: str, w: str) -> list[dict]:
        exact = [r for r in rows if normalize_name(str(r[attr] or "")) == w]
        return exact or [r for r in rows if w in normalize_name(str(r[attr] or ""))]

    hits = match(snap.rows, "label", want) or match(snap.rows, "key", want)
    if series:
        hits = match(hits, "series", normalize_name(series))
    labels = sorted({r["label"] for r in hits})
    if not hits:
        raise DomainError(NOT_FOUND, f"'{label}' is not in this chart.", available=sorted({r["label"] for r in snap.rows})[:15],
                          filters_applied=snap.meta["filters_applied"])
    if len(labels) > 1:
        raise DomainError(AMBIGUOUS, f"'{label}' matches more than one row. Ask which one.", candidates=labels)
    ms = snap.meta["measures"]
    first = ms[0]["name"]
    vals = {m["name"]: sum(r["values"][m["name"]] for r in hits) for m in ms}
    total = snap.totals.get(first, 0)
    return {
        "snapshot_id": snap.id, "label": labels[0],
        "series": sorted({r["series"] for r in hits if r.get("series")}) or None,
        "values": {m["label"].lower(): fmt_value(vals[m["name"]], m["unit"]) for m in ms},
        "share_of_total_pct": round(100 * vals[first] / total, 1) if total else None,
        "source_records": sorted({x for r in hits for x in r["refs"]}),
        "filters_applied": snap.meta["filters_applied"], "as_of": snap.meta["as_of"],
    }


def public(snap: ResultSnapshot) -> dict:
    """The card payload: numbers as integers plus display strings computed here, not in the browser."""
    return {"id": snap.id, "parent_id": snap.parent_id, "created_at": snap.created_at.isoformat() if snap.created_at else None,
            "spec": snap.spec, "rows": snap.rows, "meta": snap.meta,
            "totals": {k: {"value": v, "display": fmt_value(v, MEASURES[k].unit)} for k, v in snap.totals.items()}}
