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
    budget_utilisation_pct = "budget_utilisation_pct"
    budget_moved = "budget_moved"
    liability_count = "liability_count"
    capped_liability_amount = "capped_liability_amount"
    contract_count = "contract_count"


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
    day = "day"
    week = "week"
    quarter = "quarter"
    fy = "fy"
    from_category = "from_category"
    to_category = "to_category"
    risk = "risk"
    bearer = "bearer"
    counterparty = "counterparty"
    clause_type = "clause_type"
    contract_type = "contract_type"
    expiry_month = "expiry_month"
    review_state = "review_state"


class ChartType(StrEnum):
    auto = "auto"
    bar = "bar"
    horizontal_bar = "horizontal_bar"
    grouped_bar = "grouped_bar"
    stacked_bar = "stacked_bar"
    line = "line"
    area = "area"
    donut = "donut"
    pie = "pie"
    treemap = "treemap"
    heatmap = "heatmap"
    calendar_heatmap = "calendar_heatmap"
    sankey = "sankey"
    table = "table"
    kpi = "kpi"


class CompareMode(StrEnum):
    none = "none"
    prev_period = "prev_period"
    yoy = "yoy"
    mom = "mom"


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
    compare: CompareMode | None = Field(None, description="prev_period / yoy: the date_from..date_to window against the one before / "
                                                          "a year earlier (two series). mom: month-over-month % change on a month axis.")
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
    compare: CompareMode | None = None
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
    unit: str  # paise | count | pct (basis points: 8534 = 85.34%)
    source: str
    description: str


@dataclass(frozen=True)
class Dim:
    label: str
    kind: str  # category | time | bucket
    description: str
    grain: str | None = None  # time dims: month | day | week | quarter | fy


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
    "budget_utilisation_pct": Measure("Utilisation", "pct", "budget", "Actual (approved spend) as a % of the budget allocated"),
    "budget_moved": Measure("Moved", "paise", "budget_flows", "Budget moved between categories, added (top-ups) or taken back"),
    "liability_count": Measure("Liabilities", "count", "contracts", "Risky contract clauses not rejected by Legal (proposed, accepted, modified)"),
    "capped_liability_amount": Measure("Stated cap", "paise", "contracts", "Liability caps written as an amount in the contracts (not a loss estimate)"),
    "contract_count": Measure("Contracts", "count", "contracts", "Number of contracts"),
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
    "issue_month": Dim("Invoice month", "time", "Month the invoice was issued", grain="month"),
    "due_month": Dim("Due month", "time", "Month the payment is due", grain="month"),
    "bill_month": Dim("Bill month", "time", "Month of the bill date", grain="month"),
    "claim_month": Dim("Claim month", "time", "Month of the expense", grain="month"),
    "budget_month": Dim("Budget month", "time", "Budget month (April-March financial year)", grain="month"),
    "billing_month": Dim("Billing month", "time", "Month a customer invoice bills for (what revenue reports by)", grain="month"),
    "currency": Dim("Currency", "category", "Invoice currency (INR, USD, ...)"),
    "client_state": Dim("Client state", "category", "Customer active / paused / project over"),
    "day": Dim("Day", "time", "Calendar day of the business date", grain="day"),
    "week": Dim("Week", "time", "Week (starting Monday) of the business date", grain="week"),
    "quarter": Dim("Quarter", "time", "Financial-year quarter (Q1 = Apr-Jun)", grain="quarter"),
    "fy": Dim("Financial year", "time", "April-March financial year", grain="fy"),
    "from_category": Dim("From", "category", "Where budget came from (a category, or New budget for a top-up)"),
    "to_category": Dim("To", "category", "Where budget went (a category, or Returned for a reduction)"),
    "risk": Dim("Risk", "category", "Clause risk: high / medium / low / standard"),
    "bearer": Dim("Who bears it", "category", "us / counterparty / mutual / unclear"),
    "counterparty": Dim("Counterparty", "category", "The other party to the contract"),
    "clause_type": Dim("Clause", "category", "Clause type (unlimited liability, indemnity, ...)"),
    "contract_type": Dim("Contract type", "category", "NDA / MSA / SoW / vendor / other"),
    "expiry_month": Dim("Expiry month", "time", "Month the contract ends", grain="month"),
    "review_state": Dim("Review state", "category", "proposed (to review) / accepted / modified / rejected / tagged"),
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
    # pct measures: (numerator, denominator) summed per group, divided in Python so totals stay a true ratio
    ratios: dict[str, tuple[ColumnElement, ColumnElement]] = field(default_factory=dict)


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


def _grains(col: ColumnElement, *, fine: bool = True) -> dict[str, ColumnElement]:
    """Day / week / FY quarter / FY keys for a business date. Keys sort in time order ('FY2026-27 Q3')."""
    from sqlalchemy import Integer, String, cast

    mo = cast(func.extract("month", col), Integer)
    start = cast(func.extract("year", col), Integer) - case((mo < 4, 1), else_=0)
    fy = func.concat("FY", cast(start, String), "-", func.right(cast(start + 1, String), 2))
    q = case((mo.in_((4, 5, 6)), "Q1"), (mo.in_((7, 8, 9)), "Q2"), (mo.in_((10, 11, 12)), "Q3"), else_="Q4")
    out = {"quarter": func.concat(fy, " ", q), "fy": fy}
    if fine:
        out |= {"day": func.to_char(col, "YYYY-MM-DD"), "week": func.to_char(func.date_trunc("week", col), "YYYY-MM-DD")}
    return out


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
            **_grains(bill_date, fine=False),  # invoices report by billing month: quarter / FY only
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
            **_grains(Bill.business_date),
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
            **_grains(Claim.business_date),
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
              "budget_month": _month(BudgetMovement.fiscal_month), **_grains(BudgetMovement.fiscal_month, fine=False)},
        measures={"budget_allocated": alloc, "budget_reserved": res, "budget_committed": com, "budget_spent": spent,
                  "budget_available": alloc - res - com - spent, "budget_actual": com + spent,
                  "budget_remaining": alloc - com - spent, "budget_utilisation_pct": com + spent},
        ref=BudgetLine.category,
        ratios={"budget_utilisation_pct": (com + spent, alloc)},
    )


def _budget_flows(a: Actor, today: date) -> Compiled:
    """Budget changes as flows: transfers (paired out/in legs of one change), top-ups (New budget -> category) and
    reductions (category -> Returned). Legs pair on the confirming receipt, or the seed's event id."""
    from sqlalchemy import String, cast, literal_column, union_all

    o, i = aliased(BudgetMovement), aliased(BudgetMovement)
    lo, li = aliased(BudgetLine), aliased(BudgetLine)
    pair = lambda m: func.coalesce(cast(m.receipt_id, String), m.economic_event_id)  # noqa: E731
    transfers = (select(lo.category.label("src"), li.category.label("dst"), i.amount_paise.label("amt"),
                        o.fiscal_month.label("month"), pair(o).label("ref"))
                 .select_from(o).join(lo, lo.id == o.line_id)
                 .join(i, and_(pair(i) == pair(o), i.fiscal_month == o.fiscal_month, i.kind == "budget_transfer_in",
                               i.workspace_id == a.workspace_id))
                 .join(li, li.id == i.line_id)
                 .where(o.workspace_id == a.workspace_id, o.kind == "budget_transfer_out"))
    ml = aliased(BudgetLine)
    m = aliased(BudgetMovement)
    topups = (select(literal_column("'New budget'").label("src"), ml.category.label("dst"), m.amount_paise.label("amt"),
                     m.fiscal_month.label("month"), pair(m).label("ref"))
              .select_from(m).join(ml, ml.id == m.line_id)
              .where(m.workspace_id == a.workspace_id, m.kind == "budget_top_up"))
    m2, ml2 = aliased(BudgetMovement), aliased(BudgetLine)
    cuts = (select(ml2.category.label("src"), literal_column("'Returned'").label("dst"), (-m2.amount_paise).label("amt"),
                   m2.fiscal_month.label("month"), pair(m2).label("ref"))
            .select_from(m2).join(ml2, ml2.id == m2.line_id)
            .where(m2.workspace_id == a.workspace_id, m2.kind == "budget_reduction"))
    fl = union_all(transfers, topups, cuts).subquery("flows")
    return Compiled(
        frm=fl, where=[],
        dims={"from_category": fl.c.src, "to_category": fl.c.dst, "budget_month": _month(fl.c.month),
              **_grains(fl.c.month, fine=False)},
        measures={"budget_moved": func.sum(fl.c.amt)},
        ref=fl.c.ref, date_col=fl.c.month,
    )


def _contracts(a: Actor, today: date) -> Compiled:
    """Contracts and their findings (the contracts module): liabilities, stated caps, counts."""
    from app.models import Contract, ContractFinding
    from app.services.contracts.catalogue import CONTRACT_TYPES, NAMES

    f = ContractFinding
    risky = and_(f.risk.in_(("high", "medium", "low")), f.state.in_(("proposed", "accepted", "modified")))
    capped = and_(f.clause_type.in_(("limitation_of_liability",)), f.state != "rejected")
    return Compiled(
        frm=Contract.__table__.outerjoin(f, and_(f.contract_id == Contract.id, f.workspace_id == Contract.workspace_id)),
        where=[Contract.workspace_id == a.workspace_id],
        dims={
            "risk": func.coalesce(f.risk, "none"), "bearer": func.coalesce(f.bearer, "unclear"),
            "counterparty": func.coalesce(Contract.counterparty_name, "Unknown"),
            "clause_type": case(*[(f.clause_type == k, v) for k, v in NAMES.items()], else_=func.coalesce(f.clause_type, "none")),
            "contract_type": case(*[(Contract.contract_type == k, v) for k, v in CONTRACT_TYPES.items()], else_=Contract.contract_type),
            "expiry_month": _month(Contract.expiry_on), "review_state": func.coalesce(f.state, "none"), "status": Contract.status,
        },
        measures={"liability_count": func.count(case((risky, f.id))),
                  "capped_liability_amount": func.coalesce(func.sum(case((capped, f.cap_paise), else_=0)), 0),
                  "contract_count": func.count(Contract.id.distinct())},
        ref=Contract.ref, date_col=Contract.expiry_on,
    )


SOURCES: dict[str, Source] = {
    "receivables": Source("Receivables (customer invoices)", "invoices", True, _receivables),
    "payables": Source("Payables (vendor bills)", "bills", True, _payables),
    "claims": Source("Expense claims", "claims", False, _claims),
    "budget": Source("Budget ledger", "budget lines", False, _budget),
    "budget_flows": Source("Budget changes (transfers, top-ups, reductions)", "changes", True, _budget_flows),
    "contracts": Source("Contracts and liabilities", "contracts", True, _contracts),
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
            "measures": [{"name": n, "label": m.label, "unit": {"paise": "INR", "pct": "percent"}.get(m.unit, "count"), "description": m.description}
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
            "line/area need a time dimension (a month dimension, day, week, quarter or fy); kpi has no dimension; donut/pie is one measure by one non-time dimension.",
            "treemap: one measure by a non-time dimension (series_by nests inside it). heatmap: dimension x series_by, one measure (e.g. category x budget_month with budget_utilisation_pct). calendar_heatmap: the day dimension. sankey: from-dimension -> series_by to-dimension (budget_flows: from_category -> to_category; or category -> vendor).",
            "compare prev_period / yoy needs date_from and date_to for the current window (e.g. this quarter); mom needs a month dimension.",
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
    if ct in (ChartType.donut, ChartType.pie) and (d is None or d.kind == "time" or multi):
        return f"A {ct.value} shows one measure split by one non-time dimension."
    one = len(spec.measures) == 1
    if ct == ChartType.treemap and (d is None or d.kind == "time" or not one):
        return "A treemap shows one measure by a non-time dimension (series_by optional, nested inside it)."
    if ct == ChartType.heatmap and (d is None or spec.series_by is None or not one):
        return "A heatmap needs a dimension, a series_by (the rows) and one measure, e.g. category x budget_month."
    if ct == ChartType.calendar_heatmap and (d is None or d.grain != "day" or not one or spec.series_by is not None):
        return "A calendar heatmap needs the 'day' dimension and one measure."
    if ct == ChartType.sankey and (d is None or spec.series_by is None or not one or d.kind == "time"):
        return "A sankey needs a from-dimension, a series_by to-dimension and one measure (e.g. from_category -> to_category)."
    if ct in (ChartType.bar, ChartType.horizontal_bar, ChartType.grouped_bar, ChartType.stacked_bar) and d is None:
        return f"A {ct.value} chart needs a dimension."
    compared = (spec.compare or CompareMode.none) in (CompareMode.prev_period, CompareMode.yoy)
    if ct in (ChartType.grouped_bar, ChartType.stacked_bar) and not (multi or compared):
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
    pct = any(MEASURES[m.value].unit == "pct" for m in spec.measures)
    if pct and spec.top_n:
        raise _bad("top_n cannot fold percentages into 'Other'; filter instead.")
    cmp = spec.compare or CompareMode.none
    if cmp in (CompareMode.prev_period, CompareMode.yoy):
        if not (spec.date_from and spec.date_to):
            raise _bad("A comparison needs date_from and date_to for the current period (e.g. this quarter).")
        if c.date_col is None:
            raise _bad(f"{src.label} have no business date to compare periods on.")
        if spec.series_by is not None or len(spec.measures) > 1:
            raise _bad("A comparison works with one measure and no series_by (the two periods are the series).")
        d = DIMS[spec.dimension.value] if spec.dimension else None
        if d is not None and d.kind == "time" and (d.grain != "month" or not _whole_months(spec.date_from, spec.date_to)):
            raise _bad("Compare over time only on a month axis with whole months (1st to month end).")
    if cmp == CompareMode.mom:
        d = DIMS[spec.dimension.value] if spec.dimension else None
        if d is None or d.grain != "month" or spec.series_by is not None or len(spec.measures) > 1:
            raise _bad("Month-over-month needs one measure on a month dimension and no series_by.")
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
         "budget": f"Budget: {t.lower()}", "budget_flows": "Budget moved", "contracts": f"Contracts: {t.lower()}"}[src]
    if spec.dimension:
        t += f" by {DIMS[spec.dimension.value].label.lower()}"
    if spec.series_by:
        t += f" and {DIMS[spec.series_by.value].label.lower()}"
    if any(a.startswith("overdue") for a in applied):
        t = t.replace(": outstanding", ": overdue").replace(": unpaid", ": overdue")
    return t  # every applied filter is listed under the chart and returned with the spoken summary


def _whole_months(d1: date, d2: date) -> bool:
    from calendar import monthrange

    return d1.day == 1 and d2.day == monthrange(d2.year, d2.month)[1]


def _months_between(d1: date, d2: date) -> int:
    return (d2.year - d1.year) * 12 + d2.month - d1.month + 1


def _shift_months(d: date, n: int) -> date:
    from calendar import monthrange

    y, m = divmod(d.month - 1 + n, 12)
    yy, mm = d.year + y, m + 1
    return date(yy, mm, min(d.day, monthrange(yy, mm)[1]))


def _previous_window(spec: ChartSpec) -> tuple[date, date, int]:
    """(from, to, month shift) of the comparison window."""
    from datetime import timedelta

    d1, d2 = spec.date_from, spec.date_to
    if spec.compare == CompareMode.yoy:
        return _shift_months(d1, -12), _shift_months(d2, -12), 12
    if _whole_months(d1, d2):
        n = _months_between(d1, d2)
        p1 = _shift_months(d1, -n)
        return p1, d1 - timedelta(days=1), n
    days = (d2 - d1).days + 1
    return d1 - timedelta(days=days), d1 - timedelta(days=1), 0


def _window_label(d1: date, d2: date) -> str:
    if _whole_months(d1, d2):
        return d1.strftime("%b %Y") if (d1.year, d1.month) == (d2.year, d2.month) else f"{d1:%b %Y}–{d2:%b %Y}"
    return f"{d1:%d %b %Y}–{d2:%d %b %Y}"


def key_label(key: str, grain: str | None) -> str:
    if key == "Other" or key is None:
        return key
    try:
        if grain == "month":
            return _month_label(key)
        if grain == "day":
            return date.fromisoformat(key).strftime("%d %b %Y")
        if grain == "week":
            return "Week of " + date.fromisoformat(key).strftime("%d %b")
        if grain == "quarter":  # 'FY2026-27 Q3' -> 'Q3 FY26-27'
            fy, q = key.split(" ")
            return f"{q} FY{fy[4:6]}-{fy[-2:]}"
        if grain == "fy":
            return f"FY {key[2:]}"
    except (ValueError, IndexError):
        pass
    return key


NO_SERIES_CAP = ("heatmap", "sankey", "treemap")


async def _fetch(s: AsyncSession, c: Compiled, spec: ChartSpec, measures: list[str], where: list) -> list[dict]:
    group = [c.dims[d.value] for d in (spec.dimension, spec.series_by) if d is not None]
    cols = [g.label(f"g{i}") for i, g in enumerate(group)]
    for m in measures:
        if m in c.ratios:
            n, d = c.ratios[m]
            cols += [n.label(f"{m}__n"), d.label(f"{m}__d")]
        else:
            cols.append(c.measures[m].label(m))
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
        refs = sorted(str(x) for x in (r["refs"] or []) if x is not None)
        if not group and not refs:
            continue  # aggregate over zero rows
        values, parts = {}, {}
        for m in measures:
            if m in c.ratios:
                n, d = int(r[f"{m}__n"] or 0), int(r[f"{m}__d"] or 0)
                parts[m] = [n, d]
                values[m] = round(n * 10000 / d) if d else 0
            else:
                values[m] = int(r[m] or 0)
        row = {"key": r.get("g0") if group else "Total", "series": r.get("g1") if spec.series_by else None,
               "values": values, "refs": refs}
        if parts:
            row["parts"] = parts
        rows.append(row)
    return rows


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
    resolved_filters = []
    for f in spec.filters or []:
        vals = await _resolve_filter_values(s, c, f)
        col = c.dims[f.dimension.value]
        where.append(col.notin_(vals) if f.exclude else col.in_(vals))
        applied.append(f"{DIMS[f.dimension.value].label.lower()} {'not ' if f.exclude else ''}{', '.join(vals)}")
        resolved_filters.append({"dimension": f.dimension.value, "values": vals, "exclude": bool(f.exclude)})

    def dated(d1: date | None, d2: date | None) -> list:
        w = list(where)
        if d1:
            w.append(c.date_col >= d1)
        if d2:
            w.append(c.date_col <= d2)
        return w

    cmp = (spec.compare or CompareMode.none).value
    rows = await _fetch(s, c, spec, measures, dated(spec.date_from, spec.date_to))
    compare_meta = None
    if cmp in ("prev_period", "yoy"):
        p1, p2, shift = _previous_window(spec)
        cur_label, prev_label = _window_label(spec.date_from, spec.date_to), _window_label(p1, p2)
        prev = await _fetch(s, c, spec, measures, dated(p1, p2))
        timed = spec.dimension is not None and DIMS[spec.dimension.value].kind == "time"
        for r in rows:
            r["series"] = cur_label
        for r in prev:
            if timed:  # align the earlier month onto the current axis
                y, mo = map(int, r["key"].split("-"))
                r["key"] = _shift_months(date(y, mo, 1), shift).strftime("%Y-%m")
            r["series"] = prev_label
        m0 = measures[0]
        cur_t, prev_t = _total(rows, m0, c), _total(prev, m0, c)
        compare_meta = {"mode": cmp, "current": cur_label, "previous": prev_label, "current_total": cur_t, "previous_total": prev_t,
                        "change_pct": round(100 * (cur_t - prev_t) / abs(prev_t), 1) if prev_t else None}
        rows = rows + prev
        applied.append(f"{cur_label} vs {prev_label}")
    elif spec.date_from or spec.date_to:
        applied.append(f"{spec.date_from or '…'} to {spec.date_to or '…'}")

    chart = (spec.chart or ChartType.auto).value
    folded = _fold(rows, spec, measures, cap_series=chart not in NO_SERIES_CAP and compare_meta is None)
    _order(rows, spec, measures)
    dim = DIMS[spec.dimension.value] if spec.dimension else None
    kind, grain = (dim.kind, dim.grain) if dim else (None, None)
    if grain == "month" and rows and spec.series_by is None and compare_meta is None:  # gap-fill months so the line is honest
        have = {r["key"] for r in rows if r["key"]}
        for k in _month_range(min(have), max(have)) if have else []:
            if k not in have:
                rows.append({"key": k, "series": None, "values": {m: 0 for m in measures}, "refs": []})
        rows.sort(key=lambda r: r["key"] or "")
    for r in rows:
        r["label"] = key_label(r["key"], grain) if kind == "time" else r["key"]
        if r.get("series") and spec.series_by is not None:
            sd = DIMS[spec.series_by.value]
            r["series"] = key_label(r["series"], sd.grain) if sd.kind == "time" else r["series"]

    changes = None
    if cmp == "mom":
        m0, prev_v, changes = measures[0], None, []
        for r in rows:
            v = r["values"][m0]
            changes.append({"label": r["label"], "change_pct": round(100 * (v - prev_v) / abs(prev_v), 1) if prev_v else None})
            prev_v = v

    totals = {m: (_total([r for r in rows if compare_meta is None or r["series"] == compare_meta["current"]], m, c)) for m in measures}
    n_keys = len({r["key"] for r in rows})
    series_meta = ({"name": spec.series_by.value, "label": DIMS[spec.series_by.value].label} if spec.series_by
                   else {"name": "period", "label": "Period"} if compare_meta else None)
    if chart == "auto":
        chart = ("line" if kind == "time" else "grouped_bar") if compare_meta else \
            _auto_chart(spec, n_keys, max((len(str(r["label"])) for r in rows), default=0))
    meta = {
        "source": key, "source_label": SOURCES[key].label, "record_label": SOURCES[key].record_label,
        "measures": [{"name": m, "label": MEASURES[m].label, "unit": MEASURES[m].unit} for m in measures],
        "dimension": {"name": spec.dimension.value, "label": dim.label, "kind": kind, "grain": grain} if dim else None,
        "series_by": series_meta,
        "filters_applied": applied, "filters_resolved": resolved_filters, "as_of": today.isoformat(),
        "currency": "INR", "chart": chart, "chart_requested": (spec.chart or ChartType.auto).value,
        "title": _title(spec, applied), "row_count": len(rows), "group_count": n_keys, "folded": folded,
        "scope": c.scope_note or "whole workspace", "compare": compare_meta, "changes": changes,
        "source_record_count": len({x for r in rows for x in r["refs"]}),
    }
    return {"spec": spec.model_dump(mode="json"), "rows": rows, "totals": totals, "meta": meta}


def _total(rows: list[dict], m: str, c: Compiled) -> int:
    if m in c.ratios:  # a ratio of the summed parts, never a sum of percentages
        n = sum(r.get("parts", {}).get(m, [0, 0])[0] for r in rows)
        d = sum(r.get("parts", {}).get(m, [0, 0])[1] for r in rows)
        return round(n * 10000 / d) if d else 0
    return sum(r["values"][m] for r in rows)


def _fold(rows: list[dict], spec: ChartSpec, measures: list[str], *, cap_series: bool = True) -> dict | None:
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
    if spec.series_by and cap_series and not any(MEASURES[m].unit == "pct" for m in measures):
        sf = fold_by("series", MAX_SERIES)
        folded = {**(folded or {}), "series": sf} if sf else folded
    return folded


def _order(rows: list[dict], spec: ChartSpec, measures: list[str]) -> None:
    if not spec.dimension:
        return
    kind = DIMS[spec.dimension.value].kind
    first = measures[0]
    if kind == "time":
        rows.sort(key=lambda r: (r["key"] or "", r["series"] == "Other", str(r["series"])))
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
    for k in ("measures", "dimension", "series_by", "overdue_only", "date_from", "date_to", "chart", "sort", "top_n", "compare", "title"):
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
    if unit == "pct":
        return f"{paise_or_count / 100:.1f}%"
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
    if first["unit"] == "pct":  # percentages never add up: name the highest and lowest single cells instead
        cells = [r for r in rows if r["key"] != "Other" and (r.get("parts", {}).get(first["name"], [0, 0])[1] or not r.get("parts"))]
        if cells:
            hi = max(cells, key=lambda r: r["values"][first["name"]])
            lo = min(cells, key=lambda r: r["values"][first["name"]])
            name = lambda r: r["label"] + (f" · {r['series']}" if r.get("series") else "")  # noqa: E731
            insights.append(f"Highest: {name(hi)}, {fmt_value(hi['values'][first['name']], 'pct')}")
            if lo is not hi:
                insights.append(f"Lowest: {name(lo)}, {fmt_value(lo['values'][first['name']], 'pct')}")
        rows_for_sum: list = []
    else:
        rows_for_sum = rows
    for r in rows_for_sum:
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
        **({"comparison": {**meta["compare"], "current_total": fmt_value(meta["compare"]["current_total"], first["unit"]),
                           "previous_total": fmt_value(meta["compare"]["previous_total"], first["unit"])}} if meta.get("compare") else {}),
        **({"month_over_month": [c for c in meta["changes"] if c["change_pct"] is not None][-6:]} if meta.get("changes") else {}),
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
