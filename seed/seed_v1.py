"""Seed v1 — ALL DATA IS SYNTHETIC. One workspace, two logins (Priya: finance approver, Arjun: employee).

Usage:  uv run python -m seed.seed_v1 --reset
"""

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import date

from argon2 import PasswordHasher
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import db
from app.models import (
    Base,
    Bill,
    BudgetLine,
    Claim,
    CompanyPayment,
    Invoice,
    Party,
    Reservation,
    Settlement,
    Trip,
    User,
    Workspace,
)
from app.services import budget
from app.services.records import normalize_name

SEED_VERSION = "seed-v1"
FY = "FY2026-27"
L = 100  # paise per rupee


def _party(ws: int, kind: str, name: str, *aliases: str) -> Party:
    return Party(workspace_id=ws, kind=kind, name=name, normalized_name=normalize_name(name), aliases=list(aliases))


async def seed(s: AsyncSession, *, workspace_name: str = "Munshi Demo Traders Pvt Ltd (SYNTHETIC)", email_domain: str = "munshi.demo") -> dict:
    ph = PasswordHasher()
    password = os.getenv("SEED_PASSWORD", "munshi-demo")
    ws = Workspace(name=workspace_name, seed_version=SEED_VERSION, is_synthetic=True)
    s.add(ws)
    await s.flush()
    W = ws.id

    priya_p, arjun_p, neha_p = (_party(W, "employee", n) for n in ("Priya Sharma", "Arjun Mehta", "Neha Iyer"))
    vendors = {
        "ganesh": _party(W, "vendor", "Shree Ganesh Printers"),
        "aws": _party(W, "vendor", "Amazon Web Services India Pvt Ltd", "AWS", "Amazon Web Services"),
        "kaveri": _party(W, "vendor", "Kaveri Caterers"),
        "bluedart": _party(W, "vendor", "BlueDart Couriers", "Blue Dart"),
        "sunrise": _party(W, "vendor", "Sunrise Residency Pune", "Sunrise Residency"),
        "indigo": _party(W, "vendor", "IndiGo Airlines", "Indigo"),
    }
    customers = {
        "acme": _party(W, "customer", "Acme Traders"),
        "acmetl": _party(W, "customer", "Acme Tradelinks"),
        "nimbus": _party(W, "customer", "Nimbus Retail"),
        "patel": _party(W, "customer", "Patel Agro Exports"),
        "lotus": _party(W, "customer", "Lotus Hospitality"),
    }
    s.add_all([priya_p, arjun_p, neha_p, *vendors.values(), *customers.values()])
    await s.flush()

    priya = User(workspace_id=W, email=f"priya@{email_domain}", display_name="Priya Sharma", role="finance_approver",
                 password_hash=ph.hash(password), party_id=priya_p.id, preferred_language="hinglish")
    arjun = User(workspace_id=W, email=f"arjun@{email_domain}", display_name="Arjun Mehta", role="employee",
                 password_hash=ph.hash(password), party_id=arjun_p.id, preferred_language="english")
    s.add_all([priya, arjun])

    alloc = {"Travel": 50_000, "Office Supplies": 40_000, "IT & Cloud": 2_00_000, "Events": 30_000, "Logistics": 25_000, "Conveyance": 15_000}
    dept = {"Travel": "Sales", "Office Supplies": "Admin", "IT & Cloud": "Engineering", "Events": "Marketing", "Logistics": "Operations", "Conveyance": "Sales"}
    lines = {}
    for cat in alloc:
        lines[cat] = BudgetLine(workspace_id=W, category=cat, department=dept[cat], fy=FY)
    s.add_all(lines.values())
    await s.flush()
    for cat, amt in alloc.items():
        await budget.post(s, W, lines[cat].id, "allocation", amt * L, "opening_allocation", memo=f"{FY} opening allocation")

    trip = Trip(workspace_id=W, employee_party_id=arjun_p.id, city="Pune", start_date=date(2026, 11, 16),
                end_date=date(2026, 11, 19), purpose="Client visits, Pune (synthetic)")
    s.add(trip)
    await s.flush()
    rs = Reservation(workspace_id=W, ref="RS1", line_id=lines["Travel"].id, trip_id=trip.id, employee_party_id=arjun_p.id,
                     description="Hotel stay, Pune trip 16-19 Nov", merchant_hint="hotel", amount_paise=5_000 * L)
    s.add(rs)
    await s.flush()
    await budget.post(s, W, lines["Travel"].id, "reserved", rs.amount_paise, "reservation_opened",
                      source_type="reservation", source_id=rs.id, memo="RS1 hotel reservation for Arjun's Pune trip")

    async def bill(vkey, cat, rupees, bdate, due, state, settled_ref=None, inv=None, desc=None):
        b = Bill(workspace_id=W, ref="pending", vendor_party_id=vendors[vkey].id, invoice_no=inv, description=desc,
                 amount_paise=rupees * L, business_date=bdate, due_date=due, line_id=lines[cat].id, state=state,
                 settlement_state="settled" if settled_ref else "unpaid", submitter_id=priya.id,
                 approver_id=priya.id if state == "approved" else None)
        s.add(b)
        await s.flush()
        b.ref = f"B{b.id}"
        if state == "approved":
            await budget.post(s, W, b.line_id, "committed", b.amount_paise, "bill_approved", source_type="bill", source_id=b.id,
                              economic_event_id=b.economic_event_id, memo=f"{b.ref} approved (seed)")
        if settled_ref:
            s.add(Settlement(workspace_id=W, record_type="bill", record_id=b.id, amount_paise=b.amount_paise,
                             business_date=due or bdate, reference=settled_ref, recorded_by=priya.id))
            await budget.post(s, W, b.line_id, "committed", -b.amount_paise, "bill_settled", source_type="bill", source_id=b.id,
                              economic_event_id=b.economic_event_id)
            await budget.post(s, W, b.line_id, "spent", b.amount_paise, "bill_settled", source_type="bill", source_id=b.id,
                              economic_event_id=b.economic_event_id)
        return b

    await s.flush()
    # Approved, unpaid, non-travel bill for the settlement walkthrough.
    await bill("ganesh", "Office Supplies", 18_500, date(2026, 11, 8), date(2026, 11, 25), "approved", inv="SGP/2611/044", desc="Brochures and letterheads")
    # Awaiting approval, due within 7 days.
    await bill("aws", "IT & Cloud", 42_300, date(2026, 11, 1), date(2026, 11, 26), "submitted", inv="AWSIN-2026-10-88812", desc="Cloud services, October")
    await bill("kaveri", "Events", 9_600, date(2026, 11, 14), date(2026, 11, 24), "submitted", inv="KC-1187", desc="Client meet lunch")
    # Settled history (gives charts real spent figures).
    await bill("aws", "IT & Cloud", 39_800, date(2026, 10, 1), date(2026, 10, 25), "approved", settled_ref="NEFT-88123", inv="AWSIN-2026-09-77120")
    await bill("bluedart", "Logistics", 6_200, date(2026, 10, 20), date(2026, 11, 4), "approved", settled_ref="NEFT-88410", inv="BD-55021")

    # Another employee's pending claim (cross-actor tests; Arjun must not see it).
    c = Claim(workspace_id=W, ref="pending", beneficiary_party_id=neha_p.id, submitter_id=priya.id, merchant="Meru Cabs",
              description="Airport taxi", amount_paise=1_350 * L, business_date=date(2026, 11, 18), line_id=lines["Conveyance"].id,
              reservation_treatment="none")
    s.add(c)
    await s.flush()
    c.ref = f"C{c.id}"

    # Company-card payment evidence for the "company already paid" path.
    s.add_all([
        CompanyPayment(workspace_id=W, payee_name="Sunrise Residency Pune", amount_paise=3_200 * L, paid_on=date(2026, 11, 10), reference="CARD-7781"),
        CompanyPayment(workspace_id=W, payee_name="IndiGo Airlines", amount_paise=6_850 * L, paid_on=date(2026, 11, 12), reference="CARD-7794"),
    ])

    inv = [
        ("acme", "INV-2026-101", date(2026, 10, 1), date(2026, 10, 31), 1_25_000, 0),
        ("acme", "INV-2026-131", date(2026, 11, 10), date(2026, 12, 10), 38_000, 0),
        ("acmetl", "INV-2026-118", date(2026, 11, 1), date(2026, 12, 15), 60_000, 0),
        ("nimbus", "INV-2026-097", date(2026, 9, 20), date(2026, 11, 5), 82_500, 0),
        ("patel", "INV-2026-122", date(2026, 11, 5), date(2026, 12, 5), 2_10_000, 0),
        ("lotus", "INV-2026-104", date(2026, 10, 3), date(2026, 11, 12), 47_200, 20_000),
    ]
    for key, num, issued, due, amt, paid in inv:
        s.add(Invoice(workspace_id=W, number=num, customer_party_id=customers[key].id, issue_date=issued, due_date=due,
                      amount_paise=amt * L, paid_paise=paid * L))
    await s.flush()
    return {"workspace_id": W, "priya_id": priya.id, "arjun_id": arjun.id, "travel_line_id": lines["Travel"].id,
            "reservation_id": rs.id, "arjun_party_id": arjun_p.id, "priya_party_id": priya_p.id, "neha_claim_ref": c.ref}


async def reset_and_seed(url: str | None = None) -> dict:
    sm = db.configure(url)
    async with db.engine().begin() as conn:
        tables = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    async with sm() as s, s.begin():
        return await seed(s)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", required=True)
    ap.parse_args()
    from dotenv import load_dotenv

    load_dotenv()
    print(asyncio.run(reset_and_seed()))
