"""Demo enrichment on top of seed v1. ALL DATA IS SYNTHETIC: fictional people, vendors, clients and agreements.

Only used with `python -m seed.seed_v1 --reset --demo` (the AWS demo). Tests keep the plain seed, so every figure
they assert (Travel 45,000 -> 45,200, Rs 5,42,700 legacy receivables, Office Supplies at its Nov limit, the October
close recommendation for Events / IT & Cloud) is unchanged: the enrichment never posts to the six original lines.

Three hooks, called from `seed_v1.seed(demo=True)`:
  enrich_core       before the Jul-Sep history close: people, leave, new budget lines, bills, claims, messages
  enrich_revenue    after the base revenue rows: five more clients (USD and INR, monthly, quarterly, ended, one-off)
  enrich_contracts  after the base contracts: four more agreements, read with the deterministic rules only
"""

from __future__ import annotations

from datetime import date, timedelta

from argon2 import PasswordHasher
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Bill, BudgetLine, Claim, LeaveRequest, Message, OnboardingTask, Party, Policy, Settlement, User
from app.services import budget, people
from app.services.records import normalize_name

L = 100  # paise per rupee
TODAY = date(2026, 11, 21)
LABEL = "SYNTHETIC TEST DOCUMENT - fictional parties, not a real agreement."

# ------------------------------------------------------------------ people
# (name, department, designation, role, manager key or None for the admin, start date, language)
PEOPLE: list[tuple[str, str, str, str, str | None, date, str]] = [
    ("Rohan Kulkarni", "Engineering", "Head of Engineering", "employee", None, date(2023, 9, 4), "english"),
    ("Aditi Rao", "Engineering", "Senior Backend Engineer", "employee", "Rohan Kulkarni", date(2024, 1, 15), "english"),
    ("Karthik Subramanian", "Engineering", "Frontend Engineer", "employee", "Rohan Kulkarni", date(2024, 6, 3), "english"),
    ("Farhan Ali", "Engineering", "DevOps Engineer", "employee", "Rohan Kulkarni", date(2025, 4, 7), "hinglish"),
    ("Pooja Nair", "Engineering", "QA Engineer", "employee", "Rohan Kulkarni", date(2025, 7, 21), "english"),
    ("Siddharth Jain", "Engineering", "Data Engineer", "employee", "Rohan Kulkarni", date(2026, 11, 16), "hinglish"),
    ("Vikram Singh", "Sales", "Head of Sales", "employee", None, date(2023, 7, 10), "hinglish"),
    ("Kavya Reddy", "Sales", "Enterprise Account Executive", "employee", "Vikram Singh", date(2024, 3, 11), "english"),
    ("Imran Shaikh", "Sales", "Inside Sales Executive", "employee", "Vikram Singh", date(2025, 9, 1), "hinglish"),
    ("Tanvi Deshpande", "Marketing", "Marketing Manager", "employee", None, date(2024, 2, 5), "english"),
    ("Aman Gupta", "Marketing", "Content Strategist", "employee", "Tanvi Deshpande", date(2025, 1, 13), "hinglish"),
    ("Ritika Bose", "Marketing", "Performance Marketer", "employee", "Tanvi Deshpande", date(2025, 10, 6), "english"),
    ("Suresh Patil", "Operations", "Operations Manager", "employee", None, date(2023, 8, 21), "hindi"),
    ("Lakshmi Menon", "Operations", "Logistics Coordinator", "employee", "Suresh Patil", date(2024, 11, 4), "english"),
    ("Deepak Yadav", "Operations", "Warehouse Supervisor", "employee", "Suresh Patil", date(2025, 5, 19), "hindi"),
    ("Ananya Desai", "Finance", "Accounts Lead", "finance_approver", None, date(2023, 10, 2), "english"),
    ("Harsh Agarwal", "Finance", "Accounts Executive", "employee", "Ananya Desai", date(2025, 3, 3), "hinglish"),
    ("Meera Joshi", "HR", "HR Lead", "hr_admin", None, date(2024, 4, 1), "hinglish"),
    ("Nikhil Verma", "HR", "Talent Acquisition Specialist", "employee", "Meera Joshi", date(2025, 8, 18), "english"),
    ("Shalini Pillai", "Admin", "Office Administrator", "employee", "Suresh Patil", date(2024, 9, 9), "english"),
    ("Gaurav Malhotra", "Sales", "Key Account Manager", "employee", "Vikram Singh", date(2024, 12, 2), "hinglish"),
    ("Zoya Khan", "Engineering", "Product Designer", "employee", "Rohan Kulkarni", date(2025, 2, 17), "english"),
]
# Joins on Monday 30 Nov: invited, onboarding checklist in progress (the "onboarding status" demo).
NEW_JOINER = ("Sana Qureshi", "Marketing", "Social Media Executive", "Tanvi Deshpande", date(2026, 11, 30))

# (person, type, start, end, state, reason). Past = approved and used; Dec = pending or approved; one rejected.
LEAVES = [
    ("Aditi Rao", "EL", date(2026, 10, 19), date(2026, 10, 23), "approved", "Diwali trip home"),
    ("Karthik Subramanian", "SL", date(2026, 11, 9), date(2026, 11, 10), "approved", "Viral fever"),
    ("Kavya Reddy", "CL", date(2026, 11, 13), date(2026, 11, 13), "approved", "Personal work"),
    ("Suresh Patil", "EL", date(2026, 9, 14), date(2026, 9, 18), "approved", "Village visit"),
    ("Tanvi Deshpande", "CL", date(2026, 10, 30), date(2026, 10, 30), "approved", "Bank work"),
    ("Deepak Yadav", "SL", date(2026, 11, 2), date(2026, 11, 4), "approved", "Back injury, certificate shared"),
    ("Harsh Agarwal", "CL", date(2026, 8, 24), date(2026, 8, 25), "approved", "Cousin's wedding"),
    ("Farhan Ali", "EL", date(2026, 12, 21), date(2026, 12, 31), "submitted", "Year-end vacation, Kashmir"),
    ("Rohan Kulkarni", "EL", date(2026, 12, 24), date(2026, 12, 31), "submitted", "Family holiday, Goa"),
    ("Ritika Bose", "CL", date(2026, 11, 26), date(2026, 11, 26), "submitted", "Passport appointment"),
    ("Imran Shaikh", "CL", date(2026, 12, 3), date(2026, 12, 4), "submitted", "Sister's engagement"),
    ("Lakshmi Menon", "EL", date(2026, 12, 14), date(2026, 12, 18), "approved", "Onam family visit (late)"),
    ("Aman Gupta", "CL", date(2026, 11, 23), date(2026, 11, 27), "rejected", "Short trip"),
    ("Pooja Nair", "SL", date(2026, 11, 19), date(2026, 11, 20), "approved", "Migraine"),
]

# ------------------------------------------------------------------ budget lines (separate from the six base lines)
# category -> (department, (Jul-Oct, Nov, Dec-Mar) monthly plan in rupees, Jul/Aug/Sep imported actuals)
NEW_LINES: dict[str, tuple[str, tuple[int, int, int], tuple[int, int, int]]] = {
    "Marketing": ("Marketing", (60_000, 60_000, 60_000), (52_000, 64_500, 58_200)),
    "Software & SaaS": ("Engineering", (35_000, 35_000, 35_000), (33_400, 34_600, 36_100)),
    "Professional Fees": ("Finance", (25_000, 25_000, 25_000), (25_000, 18_000, 30_500)),
    "Rent & Utilities": ("Admin", (1_40_000, 1_40_000, 1_40_000), (1_38_200, 1_41_300, 1_39_600)),
    "Recruitment & Training": ("HR", (30_000, 30_000, 30_000), (12_000, 40_000, 22_500)),
    "Client Entertainment": ("Sales", (12_000, 12_000, 12_000), (9_200, 11_400, 14_600)),
}

VENDORS: dict[str, tuple[str, list[str]]] = {
    "prestige": ("Prestige Cowork Spaces (synthetic)", ["Prestige Cowork"]),
    "power": ("Bengaluru City Power Co (synthetic)", ["City Power"]),
    "cloudnest": ("CloudNest Software Pvt Ltd (synthetic)", ["CloudNest"]),
    "devstack": ("DevStack Tools Inc (synthetic)", ["DevStack"]),
    "kapoor": ("Kapoor & Associates, Chartered Accountants (synthetic)", ["Kapoor and Associates", "Kapoor CA"]),
    "lexwise": ("LexWise Legal LLP (synthetic)", ["LexWise"]),
    "pixel": ("Pixelcraft Media (synthetic)", ["Pixelcraft"]),
    "adreach": ("AdReach Digital (synthetic)", ["AdReach"]),
    "talentbridge": ("TalentBridge Recruiters (synthetic)", ["TalentBridge"]),
    "skillforge": ("SkillForge Academy (synthetic)", ["SkillForge"]),
    "chai": ("Chai Point Corporate (synthetic)", ["Chai Point"]),
    "fibernet": ("FiberNet Broadband (synthetic)", ["FiberNet"]),
}

# (vendor, line, rupees, bill date, due date, state, settlement ref, invoice no, description)
# state: submitted | approved | rejected. A settlement ref means paid.
BILLS = [
    # October: mostly paid (charts get real spend)
    ("prestige", "Rent & Utilities", 1_20_000, date(2026, 10, 1), date(2026, 10, 7), "approved", "NEFT-90211", "PCS/OCT/2026/118", "Office rent, October (24 seats)"),
    ("power", "Rent & Utilities", 14_860, date(2026, 10, 9), date(2026, 10, 24), "approved", "BBPS-55102", "BCP-7781-OCT", "Electricity, October"),
    ("fibernet", "Rent & Utilities", 4_720, date(2026, 10, 5), date(2026, 10, 20), "approved", "AUTO-11873", "FN-OCT-55410", "Leased line 200 Mbps, October"),
    ("cloudnest", "Software & SaaS", 21_600, date(2026, 10, 1), date(2026, 10, 15), "approved", "CARD-8102", "CN-INV-26-1043", "CRM + helpdesk seats, October"),
    ("devstack", "Software & SaaS", 12_950, date(2026, 10, 3), date(2026, 10, 18), "approved", "CARD-8117", "DS-260310", "Code hosting and CI minutes, October"),
    ("kapoor", "Professional Fees", 22_500, date(2026, 10, 10), date(2026, 10, 25), "approved", "NEFT-90388", "KA/26-27/061", "GST filing and monthly bookkeeping review, Sep"),
    ("pixel", "Marketing", 38_000, date(2026, 10, 12), date(2026, 10, 27), "approved", "NEFT-90410", "PXM-0921", "Product explainer video, phase 1"),
    ("adreach", "Marketing", 24_500, date(2026, 10, 31), date(2026, 11, 10), "approved", "NEFT-90517", "ARD-26-1007", "Search and LinkedIn ads, October"),
    ("talentbridge", "Recruitment & Training", 36_000, date(2026, 10, 15), date(2026, 10, 30), "approved", "NEFT-90455", "TBR/1188", "Placement fee: Data Engineer hire"),
    ("chai", "Client Entertainment", 6_300, date(2026, 10, 22), date(2026, 11, 6), "approved", "UPI-77120", "CPC-26-3321", "Client workshop refreshments"),
    # November: a realistic open book (paid, approved-unpaid incl. overdue, awaiting approval, one rejected)
    ("prestige", "Rent & Utilities", 1_20_000, date(2026, 11, 1), date(2026, 11, 7), "approved", None, "PCS/NOV/2026/131", "Office rent, November (24 seats)"),
    ("fibernet", "Rent & Utilities", 4_720, date(2026, 11, 5), date(2026, 11, 20), "approved", "AUTO-12011", "FN-NOV-56022", "Leased line 200 Mbps, November"),
    ("power", "Rent & Utilities", 15_940, date(2026, 11, 10), date(2026, 11, 25), "submitted", None, "BCP-7781-NOV", "Electricity, November"),
    ("cloudnest", "Software & SaaS", 21_600, date(2026, 11, 1), date(2026, 11, 15), "approved", "CARD-8233", "CN-INV-26-1177", "CRM + helpdesk seats, November"),
    ("devstack", "Software & SaaS", 13_480, date(2026, 11, 3), date(2026, 11, 18), "approved", None, "DS-261103", "Code hosting and CI minutes, November"),
    ("kapoor", "Professional Fees", 22_500, date(2026, 11, 10), date(2026, 11, 25), "submitted", None, "KA/26-27/074", "GST filing and bookkeeping review, Oct"),
    ("lexwise", "Professional Fees", 18_000, date(2026, 11, 14), date(2026, 11, 29), "submitted", None, "LW-2026-219", "Review of Helix Analytics MSA"),
    ("pixel", "Marketing", 27_000, date(2026, 11, 6), date(2026, 11, 21), "approved", None, "PXM-0944", "Product explainer video, phase 2"),
    ("adreach", "Marketing", 26_800, date(2026, 11, 18), date(2026, 11, 28), "submitted", None, "ARD-26-1102", "Search and LinkedIn ads, 1-15 Nov"),
    ("pixel", "Marketing", 9_500, date(2026, 11, 12), date(2026, 11, 27), "rejected", None, "PXM-0950", "Extra revision round (not in scope)"),
    ("skillforge", "Recruitment & Training", 14_400, date(2026, 11, 11), date(2026, 11, 26), "approved", None, "SFA-26-447", "Cloud certification course, 2 seats"),
    ("talentbridge", "Recruitment & Training", 9_000, date(2026, 11, 17), date(2026, 12, 2), "submitted", None, "TBR/1231", "Job board posting pack"),
]

# (employee, line, merchant, rupees, date, state, description). state: submitted | approved | settled
CLAIMS = [
    ("Kavya Reddy", "Client Entertainment", "The Fatty Bao, Indiranagar (synthetic)", 4_850, date(2026, 11, 6), "settled", "Dinner with Nimbus Retail team"),
    ("Vikram Singh", "Client Entertainment", "Taj Coffee Lounge (synthetic)", 2_340, date(2026, 11, 12), "approved", "Breakfast meeting, Patel Agro"),
    ("Gaurav Malhotra", "Client Entertainment", "Toit Brewpub (synthetic)", 3_900, date(2026, 11, 18), "submitted", "Lotus Hospitality relationship dinner"),
    ("Imran Shaikh", "Client Entertainment", "Cafe Coffee Day (synthetic)", 640, date(2026, 11, 19), "submitted", "Prospect coffee meeting"),
    ("Aditi Rao", "Recruitment & Training", "PyCon India 2026 (synthetic)", 6_500, date(2026, 10, 8), "settled", "Conference ticket"),
    ("Pooja Nair", "Recruitment & Training", "TestCraft Online (synthetic)", 2_999, date(2026, 11, 2), "approved", "Test automation course"),
    ("Karthik Subramanian", "Software & SaaS", "Figma (synthetic receipt)", 1_150, date(2026, 11, 4), "settled", "Design tool seat, November"),
    ("Zoya Khan", "Software & SaaS", "IconStock Pro (synthetic)", 1_799, date(2026, 11, 16), "submitted", "Icon library licence"),
    ("Aman Gupta", "Marketing", "Canvas Prints Co (synthetic)", 3_480, date(2026, 11, 9), "approved", "Standee prints for meetup"),
    ("Ritika Bose", "Marketing", "Meetup venue deposit (synthetic)", 5_000, date(2026, 11, 17), "submitted", "Community meetup venue, 5 Dec"),
    ("Nikhil Verma", "Recruitment & Training", "Campus Connect (synthetic)", 2_200, date(2026, 11, 13), "submitted", "Campus hiring drive travel and stall"),
    ("Shalini Pillai", "Rent & Utilities", "HomeFix Services (synthetic)", 1_850, date(2026, 11, 7), "settled", "AC servicing, meeting room"),
]

POLICIES = [
    ("FIN-2.4", "internet broadband reimbursement wfh", "Internet reimbursement",
     "Employees who work from home at least one day a week can claim up to Rs 1,000 a month for home broadband, with the bill."),
    ("FIN-3.1", "vendor bills payment terms approval", "Vendor bills and approvals",
     "Vendor bills up to Rs 50,000 are approved by the Accounts Lead; above that by the Finance & HR Manager. Bills are paid in the Tuesday and Friday payment runs."),
    ("FIN-2.6", "client entertainment meals", "Client entertainment",
     "Client meals are reimbursed up to Rs 2,500 per attendee, with the names of the client attendees in the claim description."),
    ("HR-4.1", "holidays calendar", "Holiday calendar",
     "The company observes 12 public holidays in FY2026-27. The remaining holidays this year are 25 December (Christmas) and 26 January (Republic Day)."),
    ("HR-6.2", "learning training budget", "Learning budget",
     "Each employee may spend up to Rs 15,000 a year on courses, certifications and conferences, approved by their manager in advance."),
]


def _party(ws: int, kind: str, name: str, aliases: list[str] | None = None) -> Party:
    return Party(workspace_id=ws, kind=kind, name=name, normalized_name=normalize_name(name), aliases=aliases or [])


def _email(name: str, domain: str) -> str:
    first, *rest = name.lower().split()
    return f"{first}.{rest[-1]}@{domain}" if rest else f"{first}@{domain}"


async def enrich_core(s: AsyncSession, *, W: int, admin: User, lines: dict[str, BudgetLine], email_domain: str, fy: str) -> dict:
    """People, leave, budget lines, bills, claims, policies and messages. Runs before the Jul-Sep close so the
    new lines get closed history like the base ones. Returns the Jul-Sep imported actuals for the new lines."""
    ph = PasswordHasher()
    pw_hash = ph.hash(__import__("os").getenv("SEED_PASSWORD", "purser-demo"))

    # ---- people
    users: dict[str, User] = {}
    parties: dict[str, Party] = {}
    for name, dept, desig, role, mgr, start, lang in PEOPLE:
        p = _party(W, "employee", name)
        s.add(p)
        await s.flush()
        u = User(workspace_id=W, email=_email(name, email_domain), display_name=name, role=role, password_hash=pw_hash,
                 party_id=p.id, preferred_language=lang, department=dept, designation=desig,
                 reports_to_id=(users[mgr].id if mgr else admin.id), start_date=start)
        s.add(u)
        await s.flush()
        users[name], parties[name] = u, p
        for code, (_, days) in people.LEAVE_TYPES.items():
            await people.post_leave(s, W, u.id, code, "granted", days, "annual_grant", memo=f"{fy} grant")

    name, dept, desig, mgr, start = NEW_JOINER
    p = _party(W, "employee", name)
    s.add(p)
    await s.flush()
    joiner = User(workspace_id=W, email=_email(name, email_domain), display_name=name, role="employee", password_hash=pw_hash,
                  party_id=p.id, department=dept, designation=desig, reports_to_id=users[mgr].id, start_date=start, status="invited")
    s.add(joiner)
    await s.flush()
    for code, (_, days) in people.LEAVE_TYPES.items():
        await people.post_leave(s, W, joiner.id, code, "granted", days, "annual_grant", memo="Onboarding grant")
    done_titles = 0
    for title, owner, offset in people.ONBOARDING_CHECKLIST:
        done = owner in ("hr", "it") and done_titles < 3
        done_titles += done
        s.add(OnboardingTask(workspace_id=W, user_id=joiner.id, title=title, owner=owner, due_date=start + timedelta(days=offset),
                             status="done" if done else "open", done_by=admin.id if done else None))

    # ---- leave history and open requests
    pending_refs = []
    for who, code, a, b, state, reason in LEAVES:
        u = users[who]
        days = people.working_days(a, b)
        lr = LeaveRequest(workspace_id=W, ref="pending", user_id=u.id, submitted_by=u.id, leave_type=code, start_date=a,
                          end_date=b, days=days, reason=reason, state=state,
                          approver_id=(u.reports_to_id if state in ("approved", "rejected") else None),
                          decision_note=("Overlaps the product launch week; please pick dates in December" if state == "rejected" else None))
        s.add(lr)
        await s.flush()
        lr.ref = f"L{lr.id}"
        if state == "approved":
            await people.post_leave(s, W, u.id, code, "used", days, "leave_approved", source_id=lr.id)
        elif state == "submitted":
            await people.post_leave(s, W, u.id, code, "reserved", days, "leave_requested", source_id=lr.id)
            pending_refs.append(lr.ref)

    # ---- new budget lines with a monthly plan from Jul 2026 (Apr-Jun carry no budget, as for the base lines)
    fy_months = [date(2026, m, 1) for m in range(4, 13)] + [date(2027, m, 1) for m in (1, 2, 3)]
    snapshot: dict[str, tuple[int, int, int]] = {}
    for cat, (dept, (jul_oct, nov, dec_mar), actuals) in NEW_LINES.items():
        ln = BudgetLine(workspace_id=W, category=cat, department=dept, fy=fy)
        s.add(ln)
        await s.flush()
        lines[cat] = ln
        for m in fy_months:
            rupees = 0 if m.month in (4, 5, 6) else jul_oct if m.month in (7, 8, 9, 10) else nov if m.month == 11 else dec_mar
            if rupees:
                await budget.post(s, W, ln.id, "allocation", rupees * L, "opening_allocation", memo=f"{fy} opening allocation", fiscal_month=m)
        snapshot[cat] = actuals

    # ---- vendors and bills
    vendors: dict[str, Party] = {}
    for key, (vname, aliases) in VENDORS.items():
        vendors[key] = _party(W, "vendor", vname, aliases)
        s.add(vendors[key])
    await s.flush()

    approver = users["Ananya Desai"]
    for vkey, cat, rupees, bdate, due, state, paid_ref, inv_no, desc in BILLS:
        b = Bill(workspace_id=W, ref="pending", vendor_party_id=vendors[vkey].id, invoice_no=inv_no, description=desc,
                 amount_paise=rupees * L, business_date=bdate, due_date=due, line_id=lines[cat].id, state=state,
                 settlement_state="settled" if paid_ref else "unpaid", submitter_id=users["Harsh Agarwal"].id,
                 approver_id=(approver.id if state in ("approved", "rejected") else None))
        s.add(b)
        await s.flush()
        b.ref = f"B{b.id}"
        if state == "approved":
            await budget.post(s, W, b.line_id, "committed", b.amount_paise, "bill_approved", source_type="bill", source_id=b.id,
                              fiscal_month=bdate, economic_event_id=b.economic_event_id, memo=f"{b.ref} approved (seed)")
        if paid_ref:
            s.add(Settlement(workspace_id=W, record_type="bill", record_id=b.id, amount_paise=b.amount_paise,
                             business_date=min(due, TODAY), reference=paid_ref, recorded_by=approver.id))
            for bucket, sign in (("committed", -1), ("spent", 1)):
                await budget.post(s, W, b.line_id, bucket, sign * b.amount_paise, "bill_settled", source_type="bill", source_id=b.id,
                                  fiscal_month=bdate, economic_event_id=b.economic_event_id)

    # ---- employee claims
    for who, cat, merchant, rupees, cdate, state, desc in CLAIMS:
        u = users[who]
        c = Claim(workspace_id=W, ref="pending", beneficiary_party_id=parties[who].id, submitter_id=u.id, merchant=merchant,
                  description=desc, amount_paise=rupees * L, business_date=cdate, line_id=lines[cat].id, reservation_treatment="none",
                  state="submitted" if state == "submitted" else "approved",
                  approver_id=(approver.id if state != "submitted" else None),
                  settlement_state="settled" if state == "settled" else "unpaid")
        s.add(c)
        await s.flush()
        c.ref = f"C{c.id}"
        if state != "submitted":
            await budget.post(s, W, c.line_id, "committed", c.amount_paise, "claim_approved", source_type="claim", source_id=c.id,
                              fiscal_month=cdate, economic_event_id=c.economic_event_id, memo=f"{c.ref} approved (seed)")
        if state == "settled":
            s.add(Settlement(workspace_id=W, record_type="claim", record_id=c.id, amount_paise=c.amount_paise,
                             business_date=cdate + timedelta(days=7), reference=f"REIMB-{c.id:04d}", recorded_by=approver.id))
            for bucket, sign in (("committed", -1), ("spent", 1)):
                await budget.post(s, W, c.line_id, bucket, sign * c.amount_paise, "claim_settled", source_type="claim", source_id=c.id,
                                  fiscal_month=cdate, economic_event_id=c.economic_event_id)

    # ---- policies and inbox
    for code, topic, title, body in POLICIES:
        s.add(Policy(workspace_id=W, code=code, topic=topic, title=title, body=body + " (Synthetic demo policy.)"))
    everyone = list(users.values())
    notes = [
        ("announcement", admin, None, "Office closed on 25 December",
         "The office is closed on Friday 25 December for Christmas. Please plan deliveries and client calls around it."),
        ("announcement", users["Meera Joshi"], None, "Welcome Sana Qureshi (joins 30 Nov)",
         "Sana joins Marketing as Social Media Executive on Monday 30 November. Please say hello!"),
    ]
    for kind, sender, _, subject, body in notes:
        for r in everyone + [admin]:
            if r.id != sender.id:
                s.add(Message(workspace_id=W, ref="pending", kind=kind, channel="inbox", sender_id=sender.id,
                              recipient_user_id=r.id, subject=subject, body=body, status="delivered"))
    for sender, subject, body in [
        (users["Rohan Kulkarni"], "Laptop budget for Siddharth", "Siddharth joined on 16 Nov and is still on a loaner laptop. Can we approve a new one this month?"),
        (users["Vikram Singh"], "Acme payment follow-up", "Acme's October invoice is still unpaid. Should I escalate with their finance team?"),
        (users["Ananya Desai"], "Rent for November pending", "Prestige Cowork's November rent (due 7 Nov) is approved but not paid yet. Shall I add it to Tuesday's run?"),
    ]:
        s.add(Message(workspace_id=W, ref="pending", kind="message", channel="inbox", sender_id=sender.id, recipient_user_id=admin.id,
                      subject=subject, body=body, status="delivered"))
    await s.flush()
    from sqlalchemy import select
    for m in (await s.execute(select(Message).where(Message.workspace_id == W, Message.ref == "pending"))).scalars():
        m.ref = f"M{m.id}"
    await s.flush()
    return {"snapshot": snapshot, "employees": len(users) + 1, "pending_leave_refs": pending_refs}


def enrich_revenue(ss, rv) -> dict:
    """Five more clients, written through the revenue services (sync session, inside `run_sync`)."""
    from app.services.revenue import clients as cl
    from app.services.revenue import cycles, fx_months, reminders
    from app.services.revenue import invoices as rinv

    fx_months.apply(ss, rv, "USD", [(2026, 7)], 83_100_000, [])
    fx_months.apply(ss, rv, "USD", [(2026, 8)], 83_250_000, [])

    def months_of(client_id):
        return {(i.year, i.month): i for i in rinv.list_invoices(ss, rv, client_id=client_id)}

    # Helix Analytics: USD $2,200/month retainer from Jul, all paid to date except November (sent, not yet due).
    hx = cl.create_client(ss, rv, name="Helix Analytics (synthetic)", currency="USD")
    cycles.apply(ss, rv, hx, cycles.CycleIn(2026, 7, 2_200_00, "USD", 1, "advance", "monthly"))
    rows = months_of(hx.id)
    for (y, m), sent_on, paid_on in [((2026, 7), date(2026, 7, 2), date(2026, 7, 24)), ((2026, 8), date(2026, 8, 3), date(2026, 8, 26)),
                                     ((2026, 9), date(2026, 9, 2), date(2026, 9, 29)), ((2026, 10), date(2026, 10, 1), date(2026, 10, 27))]:
        rinv.set_status(ss, rv, rows[(y, m)], "sent", on=sent_on)
        rinv.record_payment(ss, rv, rows[(y, m)], amount_paise=None, received_on=paid_on, settled=True)
    rinv.set_status(ss, rv, rows[(2026, 11)], "sent", on=date(2026, 11, 2))

    # Sahyadri Hospitals: INR Rs 1,20,000/month from Aug. Aug-Sep paid, October overdue, November sent.
    sh = cl.create_client(ss, rv, name="Sahyadri Hospitals (synthetic)", currency="INR")
    cycles.apply(ss, rv, sh, cycles.CycleIn(2026, 8, 1_20_000_00, "INR", 1, "advance", "monthly"))
    rows = months_of(sh.id)
    for (y, m), sent_on, paid_on in [((2026, 8), date(2026, 8, 1), date(2026, 8, 30)), ((2026, 9), date(2026, 9, 1), date(2026, 10, 3))]:
        rinv.set_status(ss, rv, rows[(y, m)], "sent", on=sent_on)
        rinv.record_payment(ss, rv, rows[(y, m)], amount_paise=None, received_on=paid_on, settled=True)
    rinv.set_status(ss, rv, rows[(2026, 10)], "sent", on=date(2026, 10, 1))
    rinv.set_status(ss, rv, rows[(2026, 11)], "sent", on=date(2026, 11, 2))

    # Trident Logistics: INR Rs 75,000/month billed quarterly in arrears. Q2 (Jul-Sep) invoice part paid.
    tl = cl.create_client(ss, rv, name="Trident Logistics (synthetic)", currency="INR")
    cycles.apply(ss, rv, tl, cycles.CycleIn(2026, 7, 75_000_00, "INR", 3, "arrears", "combined"))
    q2 = months_of(tl.id)[(2026, 9)]
    rinv.set_status(ss, rv, q2, "sent", on=date(2026, 10, 2))
    rinv.record_payment(ss, rv, q2, amount_paise=1_00_000_00, received_on=date(2026, 11, 12), settled=False)

    # Meridian Learning: a finished INR project (Jul-Oct), fully paid, client ended.
    ml = cl.create_client(ss, rv, name="Meridian Learning (synthetic)", currency="INR")
    done = rinv.create_invoices(ss, rv, client=ml, months=[(2026, 7), (2026, 8), (2026, 9), (2026, 10)], amount_minor=45_000_00,
                                currency="INR", priced=rinv.price(ss, rv, "INR"))
    for inv, paid_on in zip(done, (date(2026, 7, 28), date(2026, 8, 27), date(2026, 9, 28), date(2026, 10, 29)), strict=True):
        rinv.set_status(ss, rv, inv, "sent", on=paid_on.replace(day=2))
        rinv.record_payment(ss, rv, inv, amount_paise=None, received_on=paid_on, settled=True)
    cl.set_client_state(ss, rv, ml, "ended", on=date(2026, 10, 31))

    # Zenith Fintech: one-off USD project invoice ($4,800) for October, sent and overdue.
    zf = cl.create_client(ss, rv, name="Zenith Fintech (synthetic)", currency="USD")
    [z] = rinv.create_invoices(ss, rv, client=zf, months=[(2026, 10)], amount_minor=4_800_00, currency="USD",
                               priced=rinv.price(ss, rv, "USD", months=[(2026, 10)]))
    rinv.set_status(ss, rv, z, "sent", on=date(2026, 10, 6))

    reminders.add(ss, rv, due_on=date(2026, 11, 23), text="Chase Sahyadri Hospitals for the October invoice (Rs 1,20,000)", client_id=sh.id)
    reminders.add(ss, rv, due_on=date(2026, 11, 25), text="Ask Trident Logistics when the Rs 1,25,000 Q2 balance will be paid", client_id=tl.id)
    reminders.add(ss, rv, due_on=date(2026, 11, 27), text="Send Zenith Fintech a statement for the overdue October project invoice", client_id=zf.id)
    return {"demo_clients": 5}


CONTRACTS = {
    "msa_helix": {
        "filename": "Helix Analytics - MSA (SYNTHETIC).pdf",
        "text": f"""MASTER SERVICES AGREEMENT

{LABEL}

This Agreement is entered into on 1 July 2026 between Purser Demo Traders Private Limited (hereinafter referred to as the "Service Provider") and Helix Analytics Inc, a company incorporated in Delaware (hereinafter referred to as the "Client").

1. Term. This Agreement shall remain in force for a period of twelve (12) months from the Effective Date and shall automatically renew for successive one year terms unless either party gives thirty (30) days' prior written notice of non-renewal.

2. Fees. The Client shall pay the fees in each invoice within 30 days of the date of invoice.

3. Limitation of Liability. The aggregate liability of the Service Provider under this Agreement shall not exceed the fees paid by the Client in the twelve (12) months preceding the claim.

4. Confidentiality. The Service Provider shall keep the Client's Confidential Information secret. This obligation shall survive termination for a period of two (2) years.

5. Governing Law. This Agreement is governed by the laws of India.
""",
    },
    "lease_prestige": {
        "filename": "Prestige Cowork - Office Licence (SYNTHETIC).pdf",
        "text": f"""OFFICE SPACE LICENCE AGREEMENT

{LABEL}

This Agreement is entered into on 15 February 2025 between Prestige Cowork Spaces (hereinafter referred to as the "Licensor") and Purser Demo Traders Private Limited (hereinafter referred to as the "Licensee").

1. Term. This Agreement shall remain in force for a period of twenty-four (24) months and shall automatically renew for a further twelve months unless the Licensee gives sixty (60) days' prior written notice.

2. Fees. The Licensee shall pay the monthly licence fee of Rs. 1,20,000 within 7 days of the date of invoice.

3. Indemnity. The Licensee shall indemnify the Licensor against all claims arising from damage to the premises caused by the Licensee.

4. Limitation of Liability. The aggregate liability of the Licensor shall not exceed Rs. 5,00,000.

5. Governing Law. This Agreement is governed by the laws of India.
""",
    },
    "saas_cloudnest": {
        "filename": "CloudNest - Subscription Agreement (SYNTHETIC).pdf",
        "text": f"""SOFTWARE SUBSCRIPTION AGREEMENT

{LABEL}

This Agreement is entered into on 1 January 2026 between CloudNest Software Private Limited (hereinafter referred to as the "Supplier") and Purser Demo Traders Private Limited (hereinafter referred to as the "Customer").

1. Term. This Agreement shall remain in force for a period of twelve (12) months and shall automatically renew for a further twelve months unless the Customer gives thirty (30) days' prior written notice.

2. Payment Terms. The Customer shall pay each invoice within 15 days of receipt.

3. Termination. The Supplier may terminate this Agreement at any time for convenience by giving notice to the Customer.

4. Limitation of Liability. The aggregate liability of the Supplier shall not exceed INR 2,50,000.

5. Data Protection. The Supplier shall be liable for any loss of customer data arising from its systems.

6. Governing Law. This Agreement is governed by the laws of India.
""",
    },
    "nda_zenith": {
        "filename": "Zenith Fintech - Mutual NDA (SYNTHETIC).pdf",
        "text": f"""MUTUAL NON-DISCLOSURE AGREEMENT

{LABEL}

This Agreement is made between Purser Demo Traders Private Limited and Zenith Fintech Private Limited, effective 15 September 2026.

1. Confidential Information. Each party shall keep the other's Confidential Information secret.

2. Term. This Agreement shall remain in force for a period of two (2) years from the date above.

3. Indemnity. The Recipient shall hold harmless the Discloser from any loss arising from unauthorised disclosure by the Recipient.

4. Governing Law. This Agreement is governed by the laws of India.
""",
    },
}
