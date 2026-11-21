"""Gate for the workflow-engine fixes: Hinglish affirmations, _pure_no, bare-yes routing, tool-less workflows,
role menus (employees never see company finance), engine-rendered chips, read-only picker rule. No OpenAI calls."""

import dataclasses

import pytest

from app.agent import tool_access
from app.agent.context import PurserContext
from app.agent.workflows import engine, registry
from app.agent.workflows.spec import Workflow, verify
from app.services.affirmation import Affirmation, classify
from tests.conftest import make_actor
from tests.test_workflows_engine import _fakes, _log, _open_proposal, _say, _state

FINANCE_MODULES = {"budget", "revenue", "contracts"}


# ------------------------------------------------------------------ 1. affirmation
@pytest.mark.parametrize("t", ["bhej do", "bhejo", "submit karo", "submit kar do", "book karo", "book kar do",
                               "approve karo", "approve kar do", "record karo", "record kar do", "schedule karo",
                               "schedule kar do", "confirm karo", "confirm kar do", "Bhej do!", "bhej do please",
                               "haan bhej do"])
def test_hinglish_affirm(t):
    assert classify(t) == Affirmation.AFFIRM


@pytest.mark.parametrize("t,expected", [("nahi mat bhejo", Affirmation.NEGATIVE), ("mat bhejo", Affirmation.NEGATIVE),
                                        ("nahi submit karo", Affirmation.NEGATIVE)])
def test_hinglish_negations_negative(t, expected):
    assert classify(t) == expected


@pytest.mark.parametrize("t", ["bhej do lekin kal", "send it to Neha instead", "bhej do Neha ko",
                               "approve kar do 5000 ka", "book karo kal ke liye", "bhej do but change amount",
                               "submit karo Tuesday"])
def test_extra_content_not_affirm(t):
    assert classify(t) != Affirmation.AFFIRM


# ------------------------------------------------------------------ 2. _pure_no
@pytest.mark.parametrize("t", ["no", "nahi", "cancel kar do", "mat karo", "नहीं", "No.", "nahi nahi"])
def test_pure_no_true(t):
    assert engine._pure_no(t)


@pytest.mark.parametrize("t", ["nahi nahi 2,01,000", "no, Tuesday", "", "nahi 5000", "no send to Neha"])
def test_pure_no_false(t):
    assert not engine._pure_no(t)


async def test_pure_no_cancels_proposal_in_code(seeded, monkeypatch):
    actor = await make_actor(seeded, "priya")
    await _open_proposal(actor, seeded)
    calls = _fakes(monkeypatch, pick="record_payment")
    await _say(actor, "mat karo")
    res = await engine.run(actor, "mat karo")
    assert res.metrics["route"] == "continuation" and not calls["pick"]


async def test_correction_with_amount_reaches_picker(seeded, monkeypatch):
    actor = await make_actor(seeded, "priya")
    await _open_proposal(actor, seeded)
    calls = _fakes(monkeypatch, pick="record_payment")
    await _say(actor, "nahi nahi 2,01,000")
    res = await engine.run(actor, "nahi nahi 2,01,000")
    assert calls["pick"] and res.metrics["route"] != "continuation"


# ------------------------------------------------------------------ 3. yes with no pending proposal
async def test_bare_yes_with_last_offer_goes_to_picker_with_offer(seeded, monkeypatch):
    actor = await make_actor(seeded, "priya")
    _, v = await _state(actor)
    await engine._save(actor, {"last_offer": "show me this month's budget", "recent": [{"u": "a", "a": "b"}]}, v)
    calls = _fakes(monkeypatch, pick="budget_status")
    await engine.run(actor, "yes")
    assert calls["pick"] == ["show me this month's budget"]
    assert calls["run"] and calls["run"][0][0] == "budget_status"


async def test_fresh_conversation_yes_is_canned(seeded, monkeypatch):
    actor = await make_actor(seeded, "priya")
    calls = _fakes(monkeypatch, pick="budget_status")
    res = await engine.run(actor, "haan")
    assert not calls["pick"] and not calls["run"] and not calls["esc"]
    assert "Nothing is waiting" in res.reply or "pending nahi" in res.reply
    assert res.metrics["route"] == "continuation"
    assert res.ctx.tool_log == []


async def test_mid_conversation_approve_kar_do_goes_to_picker(seeded, monkeypatch):
    actor = await make_actor(seeded, "priya")
    _, v = await _state(actor)
    await engine._save(actor, {"recent": [{"u": "leave?", "a": "Neha has a leave request"}]}, v)
    calls = _fakes(monkeypatch, pick="leave_decision")
    res = await engine.run(actor, "approve kar do")
    assert calls["pick"] == ["approve kar do"]
    assert res.metrics["route"] != "continuation"


async def test_bare_yes_without_offer_mid_conversation_goes_to_picker(seeded, monkeypatch):
    actor = await make_actor(seeded, "priya")
    _, v = await _state(actor)
    await engine._save(actor, {"recent": [{"u": "x", "a": "y"}]}, v)
    calls = _fakes(monkeypatch, pick="general_reply")
    await engine.run(actor, "yes")
    assert calls["pick"] == ["yes"]


# ------------------------------------------------------------------ 4. tool-less workflows and verify
def test_toolless_workflows_exist():
    wfs = registry.workflows()
    assert wfs["general_reply"].tools == () and wfs["what_can_you_do"].tools == ()


@pytest.mark.parametrize("reply", ["", "   ", "\n\t"])
def test_empty_reply_fails_for_any_workflow(reply):
    for wf in (registry.workflows()["general_reply"], registry.workflows()["budget_status"],
               Workflow(name="t", module="m", when="w", tools=("get_briefing",), checklist=("x",))):
        out = verify(wf, _log(("get_briefing", "ok")), reply, [])
        assert out.status == "failed" and "empty reply" in out.reason


def test_toolless_nonempty_reply_is_done():
    out = verify(registry.workflows()["general_reply"], [], "Hello there.", [])
    assert out.status == "done"
    assert verify(registry.workflows()["what_can_you_do"], [], "I can help with leave.", []).status == "done"


@pytest.mark.parametrize("who", ["arjun", "priya"])
async def test_toolless_offered_to_every_role(seeded, who):
    base = await make_actor(seeded, who, conversation=False)
    for role in ("employee", "hr_admin", "finance_approver", "admin", "ceo"):
        names = {w.name for w in registry.menu(dataclasses.replace(base, role=role))}
        assert {"general_reply", "what_can_you_do"} <= names, role


# ------------------------------------------------------------------ 5. role menus
async def _menu(seeded, role):
    base = await make_actor(seeded, "priya", conversation=False)
    return {w.name: w for w in registry.menu(dataclasses.replace(base, role=role))}


@pytest.mark.parametrize("role", ["employee", "hr_admin"])
async def test_no_company_finance_for_employee_or_hr(seeded, role):
    menu = await _menu(seeded, role)
    bad = [n for n, w in menu.items() if w.module in FINANCE_MODULES]
    assert not bad, bad


async def test_onboarding_only_admin_and_hr(seeded):
    for role, expected in (("admin", True), ("hr_admin", True), ("employee", False), ("finance_approver", False),
                           ("ceo", False)):
        assert ("onboarding" in await _menu(seeded, role)) is expected, role


async def test_employee_gets_own_workflows(seeded):
    menu = await _menu(seeded, "employee")
    for n in ("document_intake", "leave_balance", "leave_request", "tasks", "raise_ticket", "trip"):
        assert n in menu, n


async def test_finance_roles_get_finance_workflows(seeded):
    for role in ("finance_approver", "admin"):
        mods = {w.module for w in (await _menu(seeded, role)).values()}
        assert FINANCE_MODULES <= mods, (role, mods)


async def test_ceo_gets_read_workflows_not_writes(seeded):
    menu = await _menu(seeded, "ceo")
    for n in ("budget_status", "revenue_overview", "contract_lookup", "briefing"):
        assert n in menu, n
    writes = tool_access.FINANCE_WRITE | tool_access.OTHER_WRITES
    for n, w in menu.items():
        if w.tools:
            assert not all(t.startswith("propose_") or t in writes for t in w.tools), n


@pytest.mark.parametrize("role", ["employee", "hr_admin"])
async def test_employee_tools_never_enable_finance(seeded, role):
    base = await make_actor(seeded, "arjun", conversation=False)
    actor = dataclasses.replace(base, role=role)
    wrapper = registry._ctx(actor)
    finance = tool_access.FINANCE_READ | tool_access.FINANCE_WRITE
    for wf in registry.menu(actor):
        for t in registry.tools_for(wf):
            if tool_access._allowed(t.name, wrapper):
                assert t.name not in finance, (wf.name, t.name)


# ------------------------------------------------------------------ 6. chips
CHIPS = [{"label": "Budget", "utterance": "show the budget"}, {"label": "Revenue", "utterance": "show revenue"}]


def _suggestions(res):
    return [c for c in res.ctx.ui if c.get("card") == "suggestions"]


async def test_done_renders_chips_and_sets_last_offer(seeded, monkeypatch):
    actor = await make_actor(seeded, "priya")

    async def run(wf, actor_, channel, text, brief, metrics):
        ctx = PurserContext(actor=actor_, channel=channel)
        ctx.tool_log.append({"tool": "get_revenue_overview", "outcome": "ok"})
        ctx.chips = list(CHIPS)
        return "Revenue is fine.", ctx

    _fakes(monkeypatch, pick="revenue_overview", run=run)
    res = await engine.run(actor, "revenue?")
    cards = _suggestions(res)
    assert len(cards) == 1 and cards[0]["items"][0]["utterance"] == "show the budget"
    state, _ = await _state(actor)
    assert state["last_offer"] == "show the budget"


async def test_proposal_outcome_has_no_chips(seeded, monkeypatch):
    actor = await make_actor(seeded, "priya")

    async def run(wf, actor_, channel, text, brief, metrics):
        ctx = await _open_proposal(actor_, seeded)
        ctx.chips = list(CHIPS)
        return "Confirm payment?", ctx

    _fakes(monkeypatch, pick="record_payment", run=run)
    res = await engine.run(actor, "Northwind paid")
    assert not _suggestions(res)
    state, _ = await _state(actor)
    assert state["last_offer"] is None


async def test_asked_outcome_has_no_chips(seeded, monkeypatch):
    actor = await make_actor(seeded, "priya")

    async def run(wf, actor_, channel, text, brief, metrics):
        ctx = PurserContext(actor=actor_, channel=channel)
        ctx.tool_log.append({"tool": "ask_choice", "outcome": "ok"})
        ctx.chips = list(CHIPS)
        return "Which one?", ctx

    _fakes(monkeypatch, pick="record_payment", run=run)
    res = await engine.run(actor, "Acme paid")
    assert not _suggestions(res)


def test_suggest_next_actions_is_engine_only():
    from app.agent.workflows import spec
    assert "suggest_next_actions" in spec.ENGINE_ONLY and spec.COMMON_TOOLS == ("ask_choice",)
    for wf in registry.workflows().values():
        assert "suggest_next_actions" not in wf.all_tools


# ------------------------------------------------------------------ 7. read-only picker rule
async def test_readonly_picker_instructions_route_changes_to_general_reply(seeded, monkeypatch):
    base = await make_actor(seeded, "priya", conversation=False)
    captured = {}

    class Res:
        final_output = type("P", (), {"workflow": "general_reply"})()
        raw_responses = []

    async def fake_run(agent, *a, **k):
        captured["instructions"] = agent.instructions
        return Res()

    monkeypatch.setattr(engine.Runner, "run", fake_run)
    monkeypatch.setattr(engine, "_usage", lambda *a, **k: None)
    for role, expect in (("ceo", True), ("admin", False)):
        captured.clear()
        out = await engine._pick(dataclasses.replace(base, role=role), "approve it", {}, None, {})
        assert out == "general_reply"
        assert ("READ-ONLY" in captured["instructions"] and "general_reply" in captured["instructions"]) is expect
