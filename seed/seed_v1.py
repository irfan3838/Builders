"""Seed v1 — ALL DATA IS SYNTHETIC. One workspace, two logins (Priya: finance approver, Arjun: employee).

Usage:  uv run python -m seed.seed_v1 --reset
"""

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import date

from argon2 import PasswordHasher
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app import db
from app.models import (
    Base,
    Bill,
    BudgetLine,
    Claim,
    CompanyPayment,
    Contract,
    Invoice,
    InvoicePayment,
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


async def seed(s: AsyncSession, *, workspace_name: str = "Purser Demo Traders Pvt Ltd (SYNTHETIC)", email_domain: str = "purser.demo", demo: bool = False) -> dict:
    ph = PasswordHasher()
    password = os.getenv("SEED_PASSWORD", "purser-demo")
    admin_name = os.getenv("SEED_ADMIN_NAME", "Priya Sharma")  # the finance admin login (AWS demo: "Irfan")
    ws = Workspace(name=workspace_name, seed_version=SEED_VERSION, is_synthetic=True)
    s.add(ws)
    await s.flush()
    W = ws.id

    priya_p, arjun_p, neha_p = (_party(W, "employee", n) for n in (admin_name, "Arjun Mehta", "Neha Iyer"))
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

    # Demo email recipients come only from the allow-list (first -> Arjun, second -> Neha); never invented addresses.
    allow = [e.strip() for e in os.getenv("EMAIL_ALLOWED_RECIPIENTS", "").split(",") if e.strip()] if email_domain == "purser.demo" else []
    priya = User(workspace_id=W, email=f"{admin_name.split()[0].lower()}@{email_domain}", display_name=admin_name, role="admin",
                 password_hash=ph.hash(password), party_id=priya_p.id, preferred_language="hinglish",
                 department="Finance", designation="Finance & HR Manager", start_date=date(2023, 6, 1))
    s.add(priya)
    await s.flush()
    arjun = User(workspace_id=W, email=f"arjun@{email_domain}", display_name="Arjun Mehta", role="employee",
                 password_hash=ph.hash(password), party_id=arjun_p.id, preferred_language="english",
                 department="Sales", designation="Sales Executive", reports_to_id=priya.id, start_date=date(2024, 8, 12),
                 notify_email=allow[0] if allow else None)
    neha = User(workspace_id=W, email=f"neha@{email_domain}", display_name="Neha Iyer", role="employee",
                password_hash=ph.hash(password), party_id=neha_p.id, preferred_language="english",
                department="Sales", designation="Account Manager", reports_to_id=priya.id, start_date=date(2025, 2, 3),
                notify_email=allow[1] if len(allow) > 1 else None)
    s.add_all([arjun, neha])

    alloc = {"Travel": 50_000, "Office Supplies": 40_000, "IT & Cloud": 2_00_000, "Events": 30_000, "Logistics": 25_000, "Conveyance": 15_000}
    dept = {"Travel": "Sales", "Office Supplies": "Admin", "IT & Cloud": "Engineering", "Events": "Marketing", "Logistics": "Operations", "Conveyance": "Sales"}
    lines = {}
    for cat in alloc:
        lines[cat] = BudgetLine(workspace_id=W, category=cat, department=dept[cat], fy=FY)
    s.add_all(lines.values())
    await s.flush()
    # Monthly plan (Purser went live in Jul 2026, so Apr-Jun carry no budget). Annual totals equal `alloc`.
    # (Jul-Oct, Nov, Dec-Mar) monthly amounts in rupees. Travel is planned from the Pune trip month onwards.
    fy_months = [date(2026, m, 1) for m in range(4, 13)] + [date(2027, m, 1) for m in (1, 2, 3)]
    profile = {
        "Travel": (0, 10_000, 10_000), "IT & Cloud": (15_000, 31_000, 27_250), "Events": (2_500, 4_500, 3_875),
        "Office Supplies": (3_000, 11_000, 4_250), "Logistics": (2_000, 3_800, 3_300), "Conveyance": (1_250, 2_000, 2_000),
    }
    for cat, (jul_oct, nov, dec_mar) in profile.items():
        plan = {m: (0 if m.month in (4, 5, 6) else jul_oct if m.month in (7, 8, 9, 10) else nov if m.month == 11 else dec_mar)
                for m in fy_months}
        assert sum(plan.values()) == alloc[cat], cat
        for m, rupees in plan.items():
            if rupees:
                await budget.post(s, W, lines[cat].id, "allocation", rupees * L, "opening_allocation",
                                  memo=f"{FY} opening allocation", fiscal_month=m)

    trip = Trip(workspace_id=W, employee_party_id=arjun_p.id, city="Pune", start_date=date(2026, 11, 16),
                end_date=date(2026, 11, 19), purpose="Client visits, Pune (synthetic)")
    s.add(trip)
    await s.flush()
    rs = Reservation(workspace_id=W, ref="RS1", line_id=lines["Travel"].id, trip_id=trip.id, employee_party_id=arjun_p.id,
                     description="Hotel stay, Pune trip 16-19 Nov", merchant_hint="hotel", amount_paise=5_000 * L)
    s.add(rs)
    await s.flush()
    await budget.post(s, W, lines["Travel"].id, "reserved", rs.amount_paise, "reservation_opened",
                      source_type="reservation", source_id=rs.id, fiscal_month=trip.start_date, memo="RS1 hotel reservation for Arjun's Pune trip")

    async def bill(vkey, cat, rupees, bdate, due, state, settled_ref=None, inv=None, desc=None):
        b = Bill(workspace_id=W, ref="pending", vendor_party_id=vendors[vkey].id, invoice_no=inv, description=desc,
                 amount_paise=rupees * L, business_date=bdate, due_date=due, line_id=lines[cat].id, state=state,
                 settlement_state="settled" if settled_ref else "unpaid", submitter_id=priya.id,
                 approver_id=priya.id if state == "approved" else None)
        s.add(b)
        await s.flush()
        b.ref = f"B{b.id}"
        if state == "approved":
            await budget.post(s, W, b.line_id, "committed", b.amount_paise, "bill_approved", source_type="bill", source_id=b.id, fiscal_month=bdate,
                              economic_event_id=b.economic_event_id, memo=f"{b.ref} approved (seed)")
        if settled_ref:
            s.add(Settlement(workspace_id=W, record_type="bill", record_id=b.id, amount_paise=b.amount_paise,
                             business_date=due or bdate, reference=settled_ref, recorded_by=priya.id))
            await budget.post(s, W, b.line_id, "committed", -b.amount_paise, "bill_settled", source_type="bill", source_id=b.id, fiscal_month=bdate,
                              economic_event_id=b.economic_event_id)
            await budget.post(s, W, b.line_id, "spent", b.amount_paise, "bill_settled", source_type="bill", source_id=b.id, fiscal_month=bdate,
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
        customers[key].currency = "INR"
        row = Invoice(workspace_id=W, number=num, customer_party_id=customers[key].id, issue_date=issued, due_date=due,
                      year=issued.year, month=issued.month, amount_minor=amt * L, currency="INR", fx_rate_micro=1_000_000,
                      fx_source="inr", amount_paise=amt * L, paid_paise=paid * L,
                      status="part_paid" if paid else "sent", kind="regular", moved_paise=0)
        if paid:
            row.payments.append(InvoicePayment(workspace_id=W, received_on=date(2026, 10, 28), amount_paise=paid * L))
        s.add(row)
    await s.flush()
    for row in (await s.execute(select(Invoice).where(Invoice.workspace_id == W))).scalars():
        row.ref = f"S{row.id}"
    await s.flush()

    # ---- people ops (synthetic)
    from app.models import LeaveRequest, Message, Policy
    from app.services import people
    for u in (priya, arjun, neha):
        for code, (_, days) in people.LEAVE_TYPES.items():
            await people.post_leave(s, W, u.id, code, "granted", days, "annual_grant", memo=f"{FY} grant")
    await people.post_leave(s, W, arjun.id, "CL", "used", 3, "leave_approved", memo="Earlier leave this year")
    await people.post_leave(s, W, neha.id, "SL", "used", 1, "leave_approved", memo="Earlier leave this year")
    lr = LeaveRequest(workspace_id=W, ref="pending", user_id=neha.id, submitted_by=neha.id, leave_type="CL",
                      start_date=date(2026, 11, 26), end_date=date(2026, 11, 27), days=2, reason="Family function")
    s.add(lr)
    await s.flush()
    lr.ref = f"L{lr.id}"
    await people.post_leave(s, W, neha.id, "CL", "reserved", 2, "leave_requested", source_id=lr.id)
    for code, topic, title, body in [
        ("HR-3.1", "leave", "Leave entitlement", "Every employee receives 12 days casual leave (CL), 8 days sick leave (SL) and 15 days earned leave (EL) per financial year (April-March). Leave is counted in working days; weekends are not counted. CL cannot exceed 3 consecutive days without manager approval in advance."),
        ("HR-3.2", "leave", "Applying for leave", "Apply through Purser at least 2 working days before casual or earned leave. Sick leave may be applied on the same day; more than 2 consecutive sick days need a medical certificate. Your manager approves; HR may approve when the manager is away."),
        ("HR-3.3", "leave carry forward", "Carry forward", "Up to 10 days of unused earned leave carry forward to the next financial year. Casual and sick leave lapse on 31 March."),
        ("FIN-2.1", "expenses reimbursement", "Travel and expense claims", "Submit claims with the original receipt within 30 days of the expense. Hotel stays are reimbursed up to Rs 5,000 per night in metro cities and Rs 3,500 elsewhere. Reimbursements are paid in the next weekly payment run after approval."),
        ("HR-5.1", "working hours office", "Working hours", "Office hours are 9:30 to 18:30, Monday to Friday. Employees may work from home up to 2 days a week with manager agreement."),
        ("HR-1.2", "onboarding joining", "Joining formalities", "New joiners share PAN, Aadhaar and bank details in the first week, acknowledge the leave, expense and code of conduct policies, and receive a laptop and email account on day one."),
    ]:
        s.add(Policy(workspace_id=W, code=code, topic=topic, title=title, body=body + " (Synthetic demo policy.)"))
    s.add(Message(workspace_id=W, ref="M0", kind="announcement", channel="inbox", sender_id=priya.id, recipient_user_id=arjun.id,
                  subject="Quarter-end expense deadline", body="Please submit all pending expense claims by 30 November.",
                  status="delivered"))
    await s.flush()
    demo_out: dict = {}
    if demo:  # AWS demo only (seed/demo_data.py); tests keep the plain seed
        from seed import demo_data
        demo_out = await demo_data.enrich_core(s, W=W, admin=priya, lines=lines, email_domain=email_domain, fy=FY)

    # ---- budget history: Jul-Sep are an imported historical snapshot (synthetic month-end actuals, no bills).
    # October is left OPEN on purpose: closing it (by voice) completes three closed months and surfaces the trend.
    from app.actor import Actor
    from app.services import budget_months as bm
    admin = Actor(priya.id, W, priya.role, priya_p.id, priya.display_name)
    snapshot = {"IT & Cloud": (15_000, 18_000, 18_000), "Events": (2_400, 1_000, 1_500), "Office Supplies": (3_000, 3_500, 2_900),
                "Logistics": (2_000, 2_100, 1_900), "Conveyance": (1_200, 1_200, 1_300)}
    snapshot.update(demo_out.get("snapshot", {}))
    for i, m in enumerate((date(2026, 7, 1), date(2026, 8, 1), date(2026, 9, 1))):
        for cat, actuals in snapshot.items():
            await budget.post(s, W, lines[cat].id, "spent", actuals[i] * L, "imported_actual", source_type="snapshot",
                              memo=f"Imported historical actual for {m:%b %Y} (synthetic)", fiscal_month=m)
        await s.flush()
        _m, nxt, rows = await bm.plan_close(s, admin, date(2026, 11, 21), m.isoformat()[:7], variances={}, carry_over=[])
        await bm.apply_close(s, admin, m, nxt, rows, None, source="imported_snapshot")
    await s.flush()
    rev = await _seed_revenue(s, admin, customers, demo=demo)
    ctr = await _seed_contracts(s, admin)
    if demo:
        from seed.demo_data import CONTRACTS
        ctr |= await _seed_contracts(s, admin, CONTRACTS)
        ctr |= {"demo_employees": demo_out["employees"], "demo_pending_leave": demo_out["pending_leave_refs"]}
    return {**rev, **ctr, "workspace_id": W, "neha_id": neha.id, "neha_leave_ref": lr.ref, "priya_id": priya.id, "arjun_id": arjun.id, "travel_line_id": lines["Travel"].id,
            "reservation_id": rs.id, "arjun_party_id": arjun_p.id, "priya_party_id": priya_p.id, "neha_claim_ref": c.ref}


async def _seed_contracts(s: AsyncSession, admin, samples: dict | None = None) -> dict:
    """Synthetic agreements (seed/contract_samples.py), read with the deterministic rules only (no model call at seed
    time), so seeded findings carry low confidence and every run gives the same rows."""
    from app.services.contracts import review as ctr_review
    from app.services.contracts import store as ctr_store
    from seed.contract_samples import SEEDED

    ours = await ctr_review.our_names(s, admin)
    out = {}
    for key, c in (samples or SEEDED).items():
        staged = await ctr_review.analyse(c["text"], c["filename"], ours, use_model=False)
        row = Contract(workspace_id=admin.workspace_id, ref="pending", title=staged["title"][:200] + " (synthetic)",
                       contract_type=staged["contract_type"], counterparty_name=staged["counterparty"],
                       party_id=await ctr_store.match_party(s, admin, staged["counterparty"]),
                       effective_on=ctr_store._date((staged["details"].get("effective_on") or {}).get("value")),
                       expiry_on=ctr_store._date((staged["details"].get("expiry_on") or {}).get("value")),
                       details={"evidence": staged["details"], "parties": staged["parties"], "filename": c["filename"], "synthetic": True},
                       text=c["text"], text_source="pdf_text", scanned_by_model=False, created_by=admin.user_id)
        s.add(row)
        await s.flush()
        row.ref = f"AG{row.id}"
        await ctr_store.add_findings(s, admin, row, staged["findings"], staged["deadlines"])
        out[f"contract_{key}_ref"] = row.ref
    return out


async def _seed_revenue(s: AsyncSession, admin, customers: dict, demo: bool = False) -> dict:
    """Revenue demo rows (ALL SYNTHETIC), written through the revenue services so every figure is computed the
    same way as at run time. Business date 21 Nov 2026.

    - Northwind Labs (synthetic): USD retainer $1,500/month from Sep 2026, month rates set by hand for Sep (83.40) and
      Oct (83.90). Oct's rate carries forward, so Nov-Mar (still to raise) are priced at 83.90 until a new rate is set.
      Sep paid (a small short credit shows as FX loss); Oct sent and part paid.
    - Kaveri Foods (synthetic): INR quarterly retainer, Rs 25,000/month billed in advance; Oct-Dec paid.
    - Orbit Design Studio (synthetic): paused client with a sent August invoice.
    - A reminder due today about the Lotus Hospitality balance.
    """
    from app.models import FxQuote
    from app.services.revenue import clients as cl
    from app.services.revenue import cycles, fx_months, reminders
    from app.services.revenue import invoices as rinv
    from app.services.revenue.core import Rev

    today = date(2026, 11, 21)
    # one cached ECB reference quote, labelled synthetic: the offline demo prices from it; a live fetch replaces it.
    # fx_quotes is global (no workspace), so a second seeded workspace must not insert the same quote again.
    quote_on = date(2026, 11, 20)
    if not (await s.execute(select(FxQuote.id).where(FxQuote.currency == "USD", FxQuote.rate_date == quote_on))).first():
        s.add(FxQuote(currency="USD", rate_date=quote_on, rate_micro=84_100_000))
        await s.flush()

    def go(ss) -> dict:
        rv = Rev(admin.workspace_id, admin.user_id, today, channel="seed")
        nw = cl.create_client(ss, rv, name="Northwind Labs (synthetic)", currency="USD")
        fx_months.apply(ss, rv, "USD", [(2026, 9)], 83_400_000, [])
        fx_months.apply(ss, rv, "USD", [(2026, 10)], 83_900_000, [])
        cycles.apply(ss, rv, nw, cycles.CycleIn(2026, 9, 150_000, "USD", 1, "advance", "monthly"))
        rows = {(i.year, i.month): i for i in rinv.list_invoices(ss, rv, client_id=nw.id)}
        sep, octo = rows[(2026, 9)], rows[(2026, 10)]
        rinv.set_status(ss, rv, sep, "sent", on=date(2026, 9, 2))
        rinv.record_payment(ss, rv, sep, amount_paise=124_95_000, received_on=date(2026, 9, 25), settled=True)
        rinv.set_status(ss, rv, octo, "sent", on=date(2026, 10, 3))
        rinv.record_payment(ss, rv, octo, amount_paise=60_000_00, received_on=date(2026, 11, 4), settled=False)

        kv = cl.create_client(ss, rv, name="Kaveri Foods (synthetic)", currency="INR")
        cycles.apply(ss, rv, kv, cycles.CycleIn(2026, 10, 25_000_00, "INR", 3, "advance", "combined"))
        q = {(i.year, i.month): i for i in rinv.list_invoices(ss, rv, client_id=kv.id)}[(2026, 10)]
        rinv.set_status(ss, rv, q, "sent", on=date(2026, 10, 1))
        rinv.record_payment(ss, rv, q, amount_paise=None, received_on=date(2026, 10, 15), settled=True)

        ob = cl.create_client(ss, rv, name="Orbit Design Studio (synthetic)", currency="INR")
        [aug] = rinv.create_invoices(ss, rv, client=ob, months=[(2026, 8)], amount_minor=40_000_00, currency="INR",
                                     priced=rinv.price(ss, rv, "INR"))
        rinv.set_status(ss, rv, aug, "sent", on=date(2026, 8, 5))
        cl.set_client_state(ss, rv, ob, "paused", on=date(2026, 10, 1))

        lotus = customers["lotus"]
        reminders.add(ss, rv, due_on=today, text="Call Lotus Hospitality about the Rs 27,200 balance", client_id=lotus.id)
        if demo:
            from seed.demo_data import enrich_revenue
            enrich_revenue(ss, rv)
        return {"northwind_client_id": nw.id, "northwind_nov_ref": rows[(2026, 11)].ref, "northwind_oct_ref": octo.ref}

    return await s.run_sync(go)


async def reset_and_seed(url: str | None = None, demo: bool = False) -> dict:
    sm = db.configure(url)
    async with db.engine().begin() as conn:
        tables = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    async with sm() as s, s.begin():
        return await seed(s, demo=demo)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", required=True)
    ap.add_argument("--demo", action="store_true", help="add the larger synthetic demo dataset (seed/demo_data.py)")
    args = ap.parse_args()
    from dotenv import load_dotenv

    load_dotenv()
    print(asyncio.run(reset_and_seed(demo=args.demo)))
