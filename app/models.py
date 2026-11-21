"""SQLAlchemy models. Money is integer paise; timestamps are UTC; business dates are IST dates.

Every business row carries workspace_id. Child -> parent links use composite foreign keys
(workspace_id, parent_id) so a row can never point at another workspace's record.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def ws_fk(local: str, parent: str) -> ForeignKeyConstraint:
    return ForeignKeyConstraint(["workspace_id", local], [f"{parent}.workspace_id", f"{parent}.id"])


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Workspace(Base, TimestampMixin):
    __tablename__ = "workspaces"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    tz: Mapped[str] = mapped_column(String(40), default="Asia/Kolkata")
    fy_start_month: Mapped[int] = mapped_column(Integer, default=4)
    seed_version: Mapped[str | None] = mapped_column(String(40))
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)


class Party(Base, TimestampMixin):
    __tablename__ = "parties"
    __table_args__ = (UniqueConstraint("workspace_id", "id"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # vendor | customer | employee
    name: Mapped[str] = mapped_column(String(200))
    normalized_name: Mapped[str] = mapped_column(String(200), index=True)
    aliases: Mapped[list] = mapped_column(JSONB, default=list)
    # Revenue client profile (kind=customer only): billing currency, lifecycle, soft delete.
    currency: Mapped[str | None] = mapped_column(String(3))
    state: Mapped[str] = mapped_column(String(10), default="active", server_default="active")  # active | paused | ended
    state_on: Mapped[date | None] = mapped_column(Date)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("workspace_id", "id"), ws_fk("party_id", "parties"))
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    email: Mapped[str] = mapped_column(String(200), unique=True)
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(30))  # finance_approver | employee
    password_hash: Mapped[str] = mapped_column(String(300))
    party_id: Mapped[int | None] = mapped_column(BigInteger)
    preferred_language: Mapped[str] = mapped_column(String(20), default="hinglish")
    # people ops
    department: Mapped[str | None] = mapped_column(String(60))
    designation: Mapped[str | None] = mapped_column(String(80))
    reports_to_id: Mapped[int | None] = mapped_column(BigInteger)
    start_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | invited
    notify_email: Mapped[str | None] = mapped_column(String(200))  # real inbox for demo email (allow-listed)


class Trip(Base, TimestampMixin):
    __tablename__ = "trips"
    __table_args__ = (UniqueConstraint("workspace_id", "id"), ws_fk("employee_party_id", "parties"))
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    employee_party_id: Mapped[int] = mapped_column(BigInteger)
    city: Mapped[str] = mapped_column(String(80))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    purpose: Mapped[str] = mapped_column(String(200))


class BudgetLine(Base, TimestampMixin):
    __tablename__ = "budget_lines"
    __table_args__ = (UniqueConstraint("workspace_id", "id"), UniqueConstraint("workspace_id", "category", "fy"))
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    category: Mapped[str] = mapped_column(String(60))
    department: Mapped[str] = mapped_column(String(60))
    fy: Mapped[str] = mapped_column(String(12))  # e.g. FY2026-27


class Reservation(Base, TimestampMixin):
    __tablename__ = "reservations"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
        ws_fk("line_id", "budget_lines"),
        ws_fk("trip_id", "trips"),
        ws_fk("employee_party_id", "parties"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    ref: Mapped[str] = mapped_column(String(20))
    line_id: Mapped[int] = mapped_column(BigInteger)
    trip_id: Mapped[int | None] = mapped_column(BigInteger)
    employee_party_id: Mapped[int | None] = mapped_column(BigInteger)
    description: Mapped[str] = mapped_column(String(200))
    merchant_hint: Mapped[str | None] = mapped_column(String(200))
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | released
    version: Mapped[int] = mapped_column(Integer, default=1)


class BudgetMovement(Base, TimestampMixin):
    """Append-only. Balance of each bucket = SUM(amount_paise)."""

    __tablename__ = "budget_movements"
    __table_args__ = (ws_fk("line_id", "budget_lines"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    line_id: Mapped[int] = mapped_column(BigInteger, index=True)
    bucket: Mapped[str] = mapped_column(String(20))  # allocation | reserved | committed | spent
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    kind: Mapped[str] = mapped_column(String(40))
    source_type: Mapped[str | None] = mapped_column(String(30))
    source_id: Mapped[int | None] = mapped_column(BigInteger)
    economic_event_id: Mapped[str | None] = mapped_column(String(40))
    receipt_id: Mapped[int | None] = mapped_column(BigInteger)
    memo: Mapped[str | None] = mapped_column(String(300))
    # First day of the budget month this movement belongs to (the record's business month for actuals,
    # the planned month for allocations). Null only for legacy annual rows.
    fiscal_month: Mapped[date | None] = mapped_column(Date, index=True)


class BudgetPeriod(Base, TimestampMixin):
    """One category-month. Open months read the ledger; a closed month keeps its frozen actual and status."""

    __tablename__ = "budget_periods"
    __table_args__ = (UniqueConstraint("line_id", "fiscal_month", name="uq_budget_period_line_month"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    line_id: Mapped[int] = mapped_column(BigInteger, index=True)
    fiscal_month: Mapped[date] = mapped_column(Date)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by: Mapped[int | None] = mapped_column(BigInteger)
    adjusted_paise: Mapped[int | None] = mapped_column(BigInteger)  # frozen at close
    actual_paise: Mapped[int | None] = mapped_column(BigInteger)  # frozen at close
    status: Mapped[str | None] = mapped_column(String(20))  # OPEN | UNDERUSED | ON_TRACK | OVERRUN
    source: Mapped[str] = mapped_column(String(30), default="ledger")  # ledger | imported_snapshot
    variance_reason: Mapped[str | None] = mapped_column(String(60))
    variance_note: Mapped[str | None] = mapped_column(String(300))
    surplus_action: Mapped[str | None] = mapped_column(String(20))  # carried | absorbed
    receipt_id: Mapped[int | None] = mapped_column(BigInteger)


class Document(Base, TimestampMixin):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("workspace_id", "id"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    uploader_id: Mapped[int] = mapped_column(BigInteger)
    storage_key: Mapped[str] = mapped_column(String(300))
    filename: Mapped[str] = mapped_column(String(300))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    media_type: Mapped[str] = mapped_column(String(80))
    pages: Mapped[int] = mapped_column(Integer, default=1)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(30), default="uploaded")  # uploaded|inspected|closed
    outcome: Mapped[str | None] = mapped_column(String(40))
    outcome_reason: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)


class Extraction(Base, TimestampMixin):
    __tablename__ = "extractions"
    __table_args__ = (ws_fk("document_id", "documents"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    document_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    doc_type: Mapped[str] = mapped_column(String(30))
    fields: Mapped[dict] = mapped_column(JSONB, default=dict)
    evidence: Mapped[dict] = mapped_column(JSONB, default=dict)
    arithmetic: Mapped[str] = mapped_column(String(20), default="unverifiable")
    corrections: Mapped[list] = mapped_column(JSONB, default=list)
    model: Mapped[str | None] = mapped_column(String(60))
    latency_ms: Mapped[int | None] = mapped_column(Integer)


class Bill(Base, TimestampMixin):
    __tablename__ = "bills"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
        ws_fk("vendor_party_id", "parties"),
        ws_fk("line_id", "budget_lines"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    ref: Mapped[str] = mapped_column(String(20), index=True)
    vendor_party_id: Mapped[int] = mapped_column(BigInteger)
    document_id: Mapped[int | None] = mapped_column(BigInteger)
    invoice_no: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(String(300))
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    business_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    line_id: Mapped[int] = mapped_column(BigInteger)
    state: Mapped[str] = mapped_column(String(20), default="submitted")  # submitted|approved|rejected
    settlement_state: Mapped[str] = mapped_column(String(20), default="unpaid")  # unpaid|settled
    submitter_id: Mapped[int | None] = mapped_column(BigInteger)
    approver_id: Mapped[int | None] = mapped_column(BigInteger)
    economic_event_id: Mapped[str] = mapped_column(String(40), default=_uuid)
    version: Mapped[int] = mapped_column(Integer, default=1)


class Claim(Base, TimestampMixin):
    __tablename__ = "claims"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id"),
        ws_fk("beneficiary_party_id", "parties"),
        ws_fk("line_id", "budget_lines"),
        ws_fk("reservation_id", "reservations"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    ref: Mapped[str] = mapped_column(String(20), index=True)
    beneficiary_party_id: Mapped[int] = mapped_column(BigInteger)
    submitter_id: Mapped[int] = mapped_column(BigInteger)
    approver_id: Mapped[int | None] = mapped_column(BigInteger)
    document_id: Mapped[int | None] = mapped_column(BigInteger)
    merchant: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(300))
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    business_date: Mapped[date] = mapped_column(Date)
    line_id: Mapped[int] = mapped_column(BigInteger)
    reservation_id: Mapped[int | None] = mapped_column(BigInteger)
    reservation_treatment: Mapped[str | None] = mapped_column(String(20))  # final | none
    state: Mapped[str] = mapped_column(String(20), default="submitted")
    settlement_state: Mapped[str] = mapped_column(String(20), default="unpaid")
    economic_event_id: Mapped[str] = mapped_column(String(40), default=_uuid)
    version: Mapped[int] = mapped_column(Integer, default=1)


class Settlement(Base, TimestampMixin):
    """Full settlement only (weekend scope). One per record, enforced by the unique constraint."""

    __tablename__ = "settlements"
    __table_args__ = (UniqueConstraint("workspace_id", "record_type", "record_id"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    record_type: Mapped[str] = mapped_column(String(10))  # claim | bill
    record_id: Mapped[int] = mapped_column(BigInteger)
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    business_date: Mapped[date] = mapped_column(Date)
    reference: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(30), default="recorded_past_payment")
    recorded_by: Mapped[int] = mapped_column(BigInteger)
    receipt_id: Mapped[int | None] = mapped_column(BigInteger)


class CompanyPayment(Base, TimestampMixin):
    __tablename__ = "company_payments"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    payee_name: Mapped[str] = mapped_column(String(200))
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    paid_on: Mapped[date] = mapped_column(Date)
    reference: Mapped[str] = mapped_column(String(80))
    method: Mapped[str] = mapped_column(String(30), default="company_card")
    matched_document_id: Mapped[int | None] = mapped_column(BigInteger)


class Invoice(Base, TimestampMixin):
    """A customer invoice (revenue). Ported from the copilot Revenue module.

    Billing month (year, month) is what reporting uses. `amount_minor` is in `currency`; `fx_rate_micro` is
    INR per unit x 10^6; `amount_paise` is the booked INR total, computed only by the revenue service.
    `paid_paise` caches the sum of `payments` (kept in step by the service). Status: to_raise | sent |
    part_paid | paid | written_off | merged. Kind: regular | balance | combined.
    """

    __tablename__ = "invoices"
    __table_args__ = (
        ws_fk("customer_party_id", "parties"),
        Index("uq_invoice_regular_month", "workspace_id", "customer_party_id", "year", "month", unique=True,
              postgresql_where="kind = 'regular'"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    ref: Mapped[str | None] = mapped_column(String(20), index=True)  # S{id}: what a user says
    number: Mapped[str | None] = mapped_column(String(40))  # assigned on first send
    customer_party_id: Mapped[int] = mapped_column(BigInteger, index=True)
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3), default="INR", server_default="INR")
    fx_rate_micro: Mapped[int] = mapped_column(BigInteger, default=1_000_000, server_default="1000000")
    fx_source: Mapped[str] = mapped_column(String(10), default="inr", server_default="inr")  # inr | manual | month | ecb
    fx_date: Mapped[date | None] = mapped_column(Date)
    issue_date: Mapped[date | None] = mapped_column(Date)  # the send day
    due_date: Mapped[date | None] = mapped_column(Date)
    amount_paise: Mapped[int] = mapped_column(BigInteger)  # booked INR total
    paid_paise: Mapped[int] = mapped_column(BigInteger, default=0)  # cache: sum of payments
    status: Mapped[str] = mapped_column(String(12), default="to_raise", server_default="to_raise")
    checked_on: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str] = mapped_column(String(200), default="", server_default="")
    period_from: Mapped[int | None] = mapped_column(Integer)  # yyyymm
    period_months: Mapped[int | None] = mapped_column(Integer)
    cycle_id: Mapped[int | None] = mapped_column(ForeignKey("client_cycles.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(10), default="regular", server_default="regular")
    moved_paise: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    moved_to_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id", ondelete="SET NULL"))
    raise_on: Mapped[date | None] = mapped_column(Date)
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    updated_by: Mapped[int | None] = mapped_column(BigInteger)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")

    client: Mapped[Party] = relationship(Party, primaryjoin="Invoice.customer_party_id == Party.id",
                                         foreign_keys="Invoice.customer_party_id")
    cycle: Mapped[ClientCycle | None] = relationship("ClientCycle", foreign_keys="Invoice.cycle_id")
    payments: Mapped[list[InvoicePayment]] = relationship(
        "InvoicePayment", order_by="InvoicePayment.id", cascade="all, delete-orphan", passive_deletes=True)

    # copilot names, so the ported service reads the same
    @property
    def total_paise(self) -> int:
        return self.amount_paise

    @total_paise.setter
    def total_paise(self, v: int) -> None:
        self.amount_paise = v

    @property
    def sent_on(self) -> date | None:
        return self.issue_date

    @sent_on.setter
    def sent_on(self, v: date | None) -> None:
        self.issue_date = v

    @property
    def due_on(self) -> date | None:
        return self.due_date

    @due_on.setter
    def due_on(self, v: date | None) -> None:
        self.due_date = v


class InvoicePayment(Base, TimestampMixin):
    """INR actually credited against a customer invoice (copilot `cli_receipt`)."""

    __tablename__ = "invoice_payments"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), index=True)
    received_on: Mapped[date | None] = mapped_column(Date)
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    receipt_id: Mapped[int | None] = mapped_column(BigInteger)


class ClientCycle(Base, TimestampMixin):
    """A client's billing cycle from a month on: monthly charge, every N months, advance/arrears, combined/monthly."""

    __tablename__ = "client_cycles"
    __table_args__ = (ws_fk("client_id", "parties"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    client_id: Mapped[int] = mapped_column(BigInteger, index=True)
    from_year: Mapped[int] = mapped_column(Integer)
    from_month: Mapped[int] = mapped_column(Integer)
    monthly_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3))
    period_months: Mapped[int] = mapped_column(Integer, default=1)
    timing: Mapped[str] = mapped_column(String(10), default="advance")  # advance | arrears
    mode: Mapped[str] = mapped_column(String(10), default="combined")  # combined | monthly
    created_by: Mapped[int | None] = mapped_column(BigInteger)


class FxQuote(Base):
    """Cached ECB reference quotes (Frankfurter): INR per unit x 10^6, by publication date. Not business data."""

    __tablename__ = "fx_quotes"
    __table_args__ = (UniqueConstraint("currency", "rate_date"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    currency: Mapped[str] = mapped_column(String(3))
    rate_date: Mapped[date] = mapped_column(Date)
    rate_micro: Mapped[int] = mapped_column(BigInteger)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FxMonth(Base):
    """A conversion rate set by hand for a currency and month; carries forward until the next one."""

    __tablename__ = "fx_months"
    __table_args__ = (UniqueConstraint("workspace_id", "currency", "year", "month"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    currency: Mapped[str] = mapped_column(String(3))
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    rate_micro: Mapped[int] = mapped_column(BigInteger)
    set_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    set_by: Mapped[int | None] = mapped_column(BigInteger)


class Reminder(Base, TimestampMixin):
    """A dated in-app reminder ('remind me Friday to chase Acme'), optionally about a client or invoice."""

    __tablename__ = "reminders"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    client_id: Mapped[int | None] = mapped_column(BigInteger)
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id", ondelete="SET NULL"))
    due_on: Mapped[date] = mapped_column(Date)
    text: Mapped[str] = mapped_column(String(200))
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    client: Mapped[Party | None] = relationship(Party, primaryjoin="Reminder.client_id == Party.id",
                                                foreign_keys="Reminder.client_id")


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=_uuid)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    channel: Mapped[str] = mapped_column(String(20))  # live | realtime | ptt | text
    live_session_id: Mapped[str | None] = mapped_column(String(120))
    foreground_proposal_id: Mapped[str | None] = mapped_column(String(40))
    current_document_id: Mapped[int | None] = mapped_column(BigInteger)
    last_snapshot_id: Mapped[str | None] = mapped_column(String(40))


class VoiceTurn(Base, TimestampMixin):
    """Server-observed user utterances. The only evidence a spoken confirmation can rely on."""

    __tablename__ = "voice_turns"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    source: Mapped[str] = mapped_column(String(30))  # live_sideband | realtime_sideband | ptt_server | text
    transcript: Mapped[str] = mapped_column(Text)
    start_ms: Mapped[int | None] = mapped_column(BigInteger)
    end_ms: Mapped[int | None] = mapped_column(BigInteger)
    completed: Mapped[bool] = mapped_column(Boolean, default=True)
    interrupted: Mapped[bool] = mapped_column(Boolean, default=False)


class Proposal(Base, TimestampMixin):
    __tablename__ = "proposals"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=_uuid)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(40), index=True)
    actor_id: Mapped[int] = mapped_column(BigInteger)
    kind: Mapped[str] = mapped_column(String(40))
    args: Mapped[dict] = mapped_column(JSONB)
    args_hash: Mapped[str] = mapped_column(String(64))
    affected: Mapped[list] = mapped_column(JSONB)  # [{table, id, version}]
    preview: Mapped[dict] = mapped_column(JSONB)  # {title, lines[], effects[]}
    status: Mapped[str] = mapped_column(String(20), default="open")
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, default=_uuid)
    presented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    presented_offset_ms: Mapped[int | None] = mapped_column(BigInteger)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    receipt_id: Mapped[int | None] = mapped_column(BigInteger)
    superseded_by: Mapped[str | None] = mapped_column(String(40))


class Receipt(Base, TimestampMixin):
    __tablename__ = "receipts"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    ref: Mapped[str] = mapped_column(String(20))
    proposal_id: Mapped[str] = mapped_column(String(40), unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True)
    actor_id: Mapped[int] = mapped_column(BigInteger)
    confirmed_via: Mapped[str] = mapped_column(String(30))
    confirmation_evidence: Mapped[dict] = mapped_column(JSONB, default=dict)
    summary: Mapped[str] = mapped_column(Text)
    effects: Mapped[list] = mapped_column(JSONB, default=list)


class AuditEvent(Base, TimestampMixin):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    actor_id: Mapped[int | None] = mapped_column(BigInteger)
    action: Mapped[str] = mapped_column(String(60))
    record_type: Mapped[str | None] = mapped_column(String(30))
    record_id: Mapped[int | None] = mapped_column(BigInteger)
    record_ref: Mapped[str | None] = mapped_column(String(30))
    before: Mapped[dict | None] = mapped_column(JSONB)
    after: Mapped[dict | None] = mapped_column(JSONB)
    proposal_id: Mapped[str | None] = mapped_column(String(40))
    receipt_id: Mapped[int | None] = mapped_column(BigInteger)


class ResultSnapshot(Base, TimestampMixin):
    """One stored result feeds chart, table and speech."""

    __tablename__ = "result_snapshots"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=_uuid)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(40))
    actor_id: Mapped[int] = mapped_column(BigInteger)
    parent_id: Mapped[str | None] = mapped_column(String(40))
    spec: Mapped[dict] = mapped_column(JSONB)
    rows: Mapped[list] = mapped_column(JSONB)
    totals: Mapped[dict] = mapped_column(JSONB)
    meta: Mapped[dict] = mapped_column(JSONB)


# ------------------------------------------------------------------ people operations


class LeaveMovement(Base, TimestampMixin):
    """Append-only leave ledger per user and type. available = granted - reserved - used (whole days)."""

    __tablename__ = "leave_movements"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    leave_type: Mapped[str] = mapped_column(String(10))  # CL | SL | EL
    bucket: Mapped[str] = mapped_column(String(10))  # granted | reserved | used
    days: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[int | None] = mapped_column(BigInteger)
    receipt_id: Mapped[int | None] = mapped_column(BigInteger)
    memo: Mapped[str | None] = mapped_column(String(300))


class LeaveRequest(Base, TimestampMixin):
    __tablename__ = "leave_requests"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    ref: Mapped[str] = mapped_column(String(20), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    submitted_by: Mapped[int] = mapped_column(BigInteger)
    leave_type: Mapped[str] = mapped_column(String(10))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    days: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(String(300))
    state: Mapped[str] = mapped_column(String(20), default="submitted")  # submitted | approved | rejected | cancelled
    approver_id: Mapped[int | None] = mapped_column(BigInteger)
    decision_note: Mapped[str | None] = mapped_column(String(300))
    version: Mapped[int] = mapped_column(Integer, default=1)


class Message(Base, TimestampMixin):
    """Inbox item and/or email outbox row. Email rows are delivered after the confirming transaction commits."""

    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    ref: Mapped[str] = mapped_column(String(20), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # announcement | message | welcome | leave_decision
    channel: Mapped[str] = mapped_column(String(10))  # inbox | email
    sender_id: Mapped[int | None] = mapped_column(BigInteger)
    recipient_user_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    email_to: Mapped[str | None] = mapped_column(String(200))
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20))  # delivered | read | queued | sent | skipped | failed
    status_detail: Mapped[str | None] = mapped_column(String(300))
    provider_id: Mapped[str | None] = mapped_column(String(200))
    batch_id: Mapped[str | None] = mapped_column(String(40), index=True)
    receipt_id: Mapped[int | None] = mapped_column(BigInteger)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OnboardingTask(Base, TimestampMixin):
    __tablename__ = "onboarding_tasks"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    title: Mapped[str] = mapped_column(String(200))
    owner: Mapped[str] = mapped_column(String(20))  # hr | it | manager | employee
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | done
    done_by: Mapped[int | None] = mapped_column(BigInteger)


class Policy(Base, TimestampMixin):
    __tablename__ = "policies"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    code: Mapped[str] = mapped_column(String(20))  # e.g. HR-4.2
    topic: Mapped[str] = mapped_column(String(60), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
