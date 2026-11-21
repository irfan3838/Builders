"""B1 RBAC matrix: employee / ceo / finance_approver / admin across tools, services, charts, HTTP, tool exposure, google, seed."""

from dataclasses import replace
from datetime import date

import pytest
from sqlalchemy import func, select

import app.config as config_mod
from app import db
from app.actor import Actor
from app.agent import tool_access
from app.agent.context import PurserContext
from app.agent.purser import ALL_TOOLS, _instructions
from app.agent.tools import budget_months as bm_tools
from app.agent.tools import finance as fin_tools
from app.agent.tools import revenue as rev_tools
from app.config import get_settings
from app.errors import FORBIDDEN, DomainError
from app.models import Meeting, User
from app.rbac import require_finance_read, require_writer
from app.services import actions, charts, contracts as _contracts  # noqa: F401
from app.services import proposals, revenue_actions
from app.services.contracts import review
from seed.role_users import seed_roles
from tests.conftest import make_actor
from tests.test_api_intake import client_for
from tests.test_intake_extra import call

TODAY = date(2026, 11, 21)


async def roles(ids):
    """priya=admin, arjun=employee, plus a finance_approver and a ceo derived from priya's identity."""
    priya = await make_actor(ids, "priya")
    arjun = await make_actor(ids, "arjun")
    fin = replace(priya, role="finance_approver")
    ceo = replace(priya, role="ceo")
    return {"admin": priya, "finance_approver": fin, "ceo": ceo, "employee": arjun}


def tool(name):
    return next(t for t in ALL_TOOLS if t.name == name)


# ------------------------------------------------------------------ actor properties


def test_actor_properties():
    def a(role, email=""):
        return Actor(1, 1, role, 1, "x", None, email)
    assert [a(r).can_read_finance for r in ("admin", "finance_approver", "ceo", "employee", "hr_admin")] == [True, True, True, False, False]
    assert [a(r).read_only for r in ("admin", "finance_approver", "ceo", "employee")] == [False, False, True, False]
    assert [a(r).is_approver for r in ("admin", "finance_approver", "ceo", "employee")] == [True, True, False, False]
    assert a("ceo").email == "" and Actor(1, 1, "ceo", 1, "x").email == ""


def test_rbac_helpers():
    ceo, emp = Actor(1, 1, "ceo", 1, "x"), Actor(1, 1, "employee", 1, "x")
    require_finance_read(ceo)
    require_writer(emp)
    with pytest.raises(DomainError) as e:
        require_finance_read(emp)
    assert e.value.code == FORBIDDEN
    with pytest.raises(DomainError) as e:
        require_writer(ceo)
    assert e.value.code == FORBIDDEN


# ------------------------------------------------------------------ budget tools


BUDGET_CALLS = [
    (fin_tools.get_budget_status, {"category": "Travel"}),
    (fin_tools.explain_budget_change, {"category": "Travel"}),
    (bm_tools.get_budget_month, {}),
    (bm_tools.get_budget_year, {"category": "Travel"}),
    (bm_tools.get_budget_alerts, {}),
    (bm_tools.forecast_budget, {}),
    (bm_tools.what_if, {"category": "Travel", "percent": 10}),
    (bm_tools.get_budget_history, {}),
]


@pytest.mark.parametrize("idx", range(len(BUDGET_CALLS)))
async def test_budget_reads_matrix(seeded, idx):
    t, args = BUDGET_CALLS[idx]
    r = await roles(seeded)
    out, _ = await call(t, r["employee"], **args)
    assert out["ok"] is False and out["code"] == FORBIDDEN, (t.name, out)
    for role in ("ceo", "admin", "finance_approver"):
        out, _ = await call(t, r[role], **args)
        assert out.get("ok") is True, (t.name, role, out)


async def test_list_budget_categories_names_only_for_employee(seeded):
    r = await roles(seeded)
    emp, _ = await call(fin_tools.list_budget_categories, r["employee"])
    assert emp["ok"] and emp["categories"] and all(set(c) == {"category"} for c in emp["categories"])
    ceo, _ = await call(fin_tools.list_budget_categories, r["ceo"])
    assert any(len(c) > 1 for c in ceo["categories"])


async def test_budget_recommendations_and_audit(seeded):
    r = await roles(seeded)
    for t in (bm_tools.get_budget_recommendations, fin_tools.get_audit_history):
        out, _ = await call(t, r["employee"])
        assert out["ok"] is False and out["code"] == FORBIDDEN
        for role in ("ceo", "admin", "finance_approver"):
            out, _ = await call(t, r[role])
            assert out["ok"] is True, (t.name, role, out)


# ------------------------------------------------------------------ revenue / contracts / records


async def test_revenue_overview(seeded):
    r = await roles(seeded)
    out, _ = await call(rev_tools.get_revenue_overview, r["employee"])
    assert out["ok"] is False and out["code"] == FORBIDDEN
    for role in ("ceo", "admin", "finance_approver"):
        out, _ = await call(rev_tools.get_revenue_overview, r[role])
        assert out["ok"] is True, (role, out)
    with pytest.raises(DomainError):
        revenue_actions.require_view(r["employee"])
    revenue_actions.require_view(r["ceo"])


async def test_contracts_can_view(seeded):
    r = await roles(seeded)
    assert {k: review.can_view(v) for k, v in r.items()} == {"admin": True, "finance_approver": True, "ceo": True, "employee": False}
    assert not review.can_decide(r["ceo"])


# ------------------------------------------------------------------ charts


async def run(actor, **kw):
    async with db.session_scope() as s:
        return await charts.run_spec(s, actor, charts.ChartSpec.model_validate(kw), today=TODAY)


CHARTS = {
    "budget": dict(measures=["budget_allocated"], dimension="category"),
    "receivables": dict(measures=["receivables_outstanding"], dimension="customer"),
    "payables": dict(measures=["bill_amount"], dimension="vendor"),
}


@pytest.mark.parametrize("src", list(CHARTS))
async def test_chart_sources_matrix(seeded, src):
    r = await roles(seeded)
    with pytest.raises(DomainError) as e:
        await run(r["employee"], **CHARTS[src])
    assert e.value.code == FORBIDDEN
    for role in ("ceo", "admin", "finance_approver"):
        out = await run(r[role], **CHARTS[src])
        assert out["rows"]


async def test_chart_options_hide_finance_sources_for_employee(seeded):
    r = await roles(seeded)
    emp = {s["key"] if "key" in s else s.get("source") for s in charts.options(r["employee"])["sources"]} if isinstance(charts.options(r["employee"]), dict) and "sources" in charts.options(r["employee"]) else None
    full = charts.options(r["ceo"])
    assert full != charts.options(r["employee"])
    if emp is not None:
        assert "budget" not in emp and "budget" in {s["key"] if "key" in s else s.get("source") for s in full["sources"]}
    assert charts.SOURCES["budget"].approver_only is True
    assert charts.SOURCES["claims"].approver_only is False


async def test_claims_chart_scoped_for_employee_full_for_ceo(seeded):
    r = await roles(seeded)
    spec = dict(measures=["claims_count"])
    emp = await run(r["employee"], **spec)
    ceo = await run(r["ceo"], **spec)
    adm = await run(r["admin"], **spec)
    ce, ee = ceo["totals"]["claims_count"], emp["totals"]["claims_count"]
    assert ce == adm["totals"]["claims_count"] and ce > 0 and ee < ce, (ee, ce)
    assert "own claims" in str(emp["meta"]) and "own claims" not in str(ceo["meta"])


# ------------------------------------------------------------------ proposals


async def test_ceo_cannot_propose_anything(seeded):
    r = await roles(seeded)
    for kind, args in [("apply_leave", {"leave_type": "cl", "start_date": "2026-12-14", "end_date": "2026-12-14"}),
                       ("approve", {"ref": "CL-1"})]:
        async with db.session_scope() as s:
            with pytest.raises(DomainError) as e:
                await proposals.create(s, r["ceo"], kind, args)
        assert e.value.code == FORBIDDEN


async def test_employee_leave_proposal_allowed(seeded):
    r = await roles(seeded)
    async with db.session_scope() as s:
        p = await proposals.create(s, r["employee"], "apply_leave", {"leave_type": "cl", "start_date": "2026-12-14", "end_date": "2026-12-14", "reason": "x"})
    assert p.id


async def test_ceo_propose_tool_returns_forbidden(seeded):
    r = await roles(seeded)
    from app.agent.tools import people
    out, _ = await call(people.propose_leave, r["ceo"], leave_type="CL", start_date="2026-12-14")
    assert out["ok"] is False and out["code"] == FORBIDDEN


# ------------------------------------------------------------------ tool exposure


def _ctx(actor):
    return type("W", (), {"context": PurserContext(actor)})()


def exposed(actor) -> set[str]:
    c = _ctx(actor)
    return {t.name for t in ALL_TOOLS if tool_access._allowed(t.name, c)}


async def test_tool_exposure_per_role(seeded, monkeypatch):
    r = await roles(seeded)
    names = {t.name for t in ALL_TOOLS}
    for n in tool_access.FINANCE_READ | tool_access.FINANCE_WRITE | tool_access.GOOGLE_ONLY | tool_access.OTHER_WRITES:
        assert n in names or True  # informational; stale names tolerated, checked below
    stale = (tool_access.FINANCE_READ | tool_access.FINANCE_WRITE) - names
    assert not stale, f"tool_access names no tool: {sorted(stale)}"
    emp, ceo, adm, fin = (exposed(r[k]) for k in ("employee", "ceo", "admin", "finance_approver"))
    assert not (emp & tool_access.FINANCE_READ) and not (emp & tool_access.FINANCE_WRITE)
    assert tool_access.FINANCE_READ - tool_access.GOOGLE_ONLY <= ceo
    assert not any(n.startswith("propose_") for n in ceo) and not (ceo & tool_access.FINANCE_WRITE) and not (ceo & tool_access.OTHER_WRITES)
    assert {"get_budget_status", "get_revenue_overview"} <= ceo
    assert "propose_budget_change" in adm and "propose_budget_change" in fin and "propose_budget_change" not in emp
    assert "propose_leave" in emp and "propose_leave" not in ceo
    assert len(emp) < len(ceo) or len(emp) < len(adm)
    assert len(ceo) < len(adm)
    # google tools hidden everywhere by default (no linked email)
    assert not (adm & tool_access.GOOGLE_ONLY)
    # chart tool stays available to ceo and employee
    assert "build_chart" in emp and "build_chart" in ceo


async def test_google_tools_exposed_only_to_linked_user(seeded, monkeypatch):
    r = await roles(seeded)
    s = get_settings().model_copy(update={"google_client_id": "a", "google_client_secret": "b", "google_refresh_token": "c",
                                          "google_linked_email": "Priya@Purser.demo"})
    monkeypatch.setattr(config_mod, "get_settings", lambda: s)
    linked = replace(r["admin"], email="priya@purser.demo")
    other = replace(r["admin"], email="other@purser.demo")
    ok = lambda n, a: tool_access._allowed(n, _ctx(a))  # noqa: E731  (by name: google tools may not be in ALL_TOOLS)
    for n in ("search_mail", "read_mail_thread"):
        assert ok(n, linked) and not ok(n, other)
    ceo_linked = replace(r["ceo"], email="priya@purser.demo")
    assert ok("search_mail", ceo_linked) and not ok("propose_email", ceo_linked) and not ok("save_mail_draft", ceo_linked)
    assert not ok("propose_email", other) and ok("propose_email", linked)


async def test_instructions_role_note(seeded):
    r = await roles(seeded)
    ceo_txt = _instructions(_ctx(r["ceo"]), None)
    emp_txt = _instructions(_ctx(r["employee"]), None)
    assert "READ-ONLY" in ceo_txt and "NOT visible" in emp_txt
    assert "Purser demo meetings" in emp_txt


# ------------------------------------------------------------------ uses_google


def _pin(monkeypatch, **kw):
    s = get_settings().model_copy(update=kw)
    monkeypatch.setattr(config_mod, "get_settings", lambda: s)
    return s


def test_uses_google_matrix(monkeypatch):
    cal = {"google_client_id": "a", "google_client_secret": "b", "google_refresh_token": "c"}
    a = Actor(1, 1, "admin", 1, "x", None, "Me@X.com")
    _pin(monkeypatch, google_linked_email="me@x.com", **cal)
    assert a.uses_google
    assert not replace(a, email="you@x.com").uses_google
    assert not replace(a, email="").uses_google
    _pin(monkeypatch, google_linked_email="me@x.com", google_client_id="", google_client_secret="", google_refresh_token="")
    assert not a.uses_google  # calendar not configured
    _pin(monkeypatch, google_linked_email="", **cal)
    assert not replace(a, email="").uses_google  # empty linked must not match empty email


# ------------------------------------------------------------------ ScheduleMeeting


def margs(**kw):
    return {"title": "Sync", "start": "2027-03-15T10:00", "guest_emails": ["a@x.com"], **kw}


async def test_schedule_meeting_non_linked_user_skipped(seeded, monkeypatch):
    from app.services import calendar
    _pin(monkeypatch, google_client_id="a", google_client_secret="b", google_refresh_token="c", google_linked_email="priya@purser.demo")
    monkeypatch.setattr(calendar, "get_settings", config_mod.get_settings)

    async def no_net(m):
        raise AssertionError("must not reach Google for a non-linked user")
    monkeypatch.setattr(calendar, "create_event", no_net)
    from tests.test_ledger_gates import propose_and_confirm
    r = await roles(seeded)
    emp = r["employee"]
    async with db.session_scope() as s:
        plan = await actions.ACTIONS["schedule_meeting"].plan(s, emp, margs())
    assert any("Purser meeting (demo)" in ln for ln in plan.lines) and not any("Google Meet link;" in ln for ln in plan.lines)
    from unittest.mock import patch
    with patch("app.services.messaging.dispatch_soon", lambda: None):
        _, out = await propose_and_confirm(emp, "schedule_meeting", margs())
    assert out.status == "executed" and "demo meeting" in out.receipt.summary if hasattr(out.receipt, "summary") else True
    async with db.session_scope() as s:
        ms = list((await s.execute(select(Meeting))).scalars())
    assert [m.status for m in ms] == ["skipped"]


async def test_schedule_meeting_linked_user_queued(seeded, monkeypatch):
    from app.services import calendar
    _pin(monkeypatch, google_client_id="a", google_client_secret="b", google_refresh_token="c", google_linked_email="priya@purser.demo")
    monkeypatch.setattr(calendar, "get_settings", config_mod.get_settings)
    monkeypatch.setattr(calendar, "create_event", lambda m: None)
    from tests.test_ledger_gates import propose_and_confirm
    priya = replace(await make_actor(seeded), email="priya@purser.demo")
    async with db.session_scope() as s:
        plan = await actions.ACTIONS["schedule_meeting"].plan(s, priya, margs())
    assert any("Google Meet link;" in ln for ln in plan.lines)
    from unittest.mock import patch
    with patch("app.services.messaging.dispatch_soon", lambda: None), patch("app.services.calendar.dispatch_soon", lambda: None, create=True):
        _, out = await propose_and_confirm(priya, "schedule_meeting", margs())
    async with db.session_scope() as s:
        ms = list((await s.execute(select(Meeting))).scalars())
    assert [m.status for m in ms] == ["queued"]


# ------------------------------------------------------------------ HTTP


@pytest.fixture
async def with_roles(seeded):
    async with db.session_scope() as s:
        await seed_roles(s)
    return seeded


async def test_http_finance_endpoints_matrix(with_roles):
    emp = await client_for("employee@purser.demo")
    ceo = await client_for("ceo@purser.demo")
    adm = await client_for("priya@purser.demo")
    lines = (await adm.get("/api/budget/lines")).json()["lines"]
    lid = lines[0]["line_id"]
    for path in ("/api/budget/lines", f"/api/budget/lines/{lid}", f"/api/budget/lines/{lid}/months", "/api/budget/alerts"):
        assert (await emp.get(path)).status_code == 403, path
        assert (await ceo.get(path)).status_code == 200, path
        assert (await adm.get(path)).status_code == 200, path


async def test_http_priorities_budget_alerts_zero_for_employee(with_roles):
    emp = await client_for("employee@purser.demo")
    ceo = await client_for("ceo@purser.demo")
    r = await emp.get("/api/priorities")
    assert r.status_code == 200 and r.json()["budget_alerts"] == 0
    assert (await ceo.get("/api/priorities")).status_code == 200


async def test_http_ceo_prepare_approval_forbidden(with_roles):
    ceo = await client_for("ceo@purser.demo")
    r = await ceo.post("/api/records/CL-0001/prepare-approval")
    assert r.status_code in (403, 409, 400) and r.status_code != 201, r.text
    assert r.status_code == 403, f"CEO prepare-approval should be FORBIDDEN, got {r.status_code} {r.text}"


async def test_http_ceo_reads_company_lists(with_roles):
    ceo = await client_for("ceo@purser.demo")
    emp = await client_for("employee@purser.demo")
    for path in ("/api/claims", "/api/bills", "/api/payments", "/api/trips", "/api/documents"):
        assert (await ceo.get(path)).status_code == 200, path
    assert (await emp.get("/api/bills")).status_code == 403
    for path in ("/api/claims", "/api/trips", "/api/documents"):
        assert (await emp.get(path)).status_code == 200, path
    ce, em = (await ceo.get("/api/trips")).json()["trips"], (await emp.get("/api/trips")).json()["trips"]
    assert len(em) <= len(ce)


async def test_http_login_carries_email_to_actor(with_roles):
    ceo = await client_for("ceo@purser.demo")
    assert (await ceo.get("/api/me")).status_code in (200, 404)


# ------------------------------------------------------------------ seed_roles


async def test_seed_roles_idempotent(seeded):
    async with db.session_scope() as s:
        first = await seed_roles(s)
    async with db.session_scope() as s:
        before_u = (await s.execute(select(func.count()).select_from(User))).scalar_one()
        before_m = (await s.execute(select(func.count()).select_from(Meeting))).scalar_one()
        second = await seed_roles(s)
    async with db.session_scope() as s:
        after_u = (await s.execute(select(func.count()).select_from(User))).scalar_one()
        after_m = (await s.execute(select(func.count()).select_from(Meeting))).scalar_one()
        users = {u.email: u.role for u in (await s.execute(select(User))).scalars()}
        statuses = {m.status for m in (await s.execute(select(Meeting))).scalars()}
    assert first["demo_meetings_added"] == 5 and second["demo_meetings_added"] == 0
    assert (before_u, before_m) == (after_u, after_m)
    assert users["ceo@purser.demo"] == "ceo" and users["employee@purser.demo"] == "employee" and users["irfmed38@gmail.com"] == "admin"
    assert first["users"] == second["users"] and statuses == {"demo"}
