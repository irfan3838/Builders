"""Workflow engine gate: registry, verify(), continuation (real DB, no LLM), engine flow with faked LLM steps,
memory bounds and the runner dispatch. Nothing here calls OpenAI."""

import dataclasses

import pytest
from sqlalchemy import select

from app import db
from app.agent import runner, tool_access
from app.agent.context import PurserContext
from app.agent.purser import ALL_TOOLS
from app.agent.workflows import engine, registry
from app.agent.workflows.registry import RegistryError
from app.agent.workflows.spec import Workflow, verify
from app.config import get_settings
from app.models import Conversation, Escalation, Proposal, Receipt
from app.services.confirmation import record_turn
from tests.conftest import make_actor


# ------------------------------------------------------------------ helpers
def _log(*pairs):
    return [{"tool": t, "outcome": o} for t, o in pairs]


def _wf(**kw):
    base = dict(name="t", module="m", when="w", tools=("list_client_invoices", "propose_payment"), checklist=("x",))
    base.update(kw)
    return Workflow(**base)


async def _say(actor, text):
    async with db.session_scope() as s:
        await record_turn(s, actor, text, source="text")


async def _open_proposal(actor, ids):
    ctx = PurserContext(actor=actor)
    out = await engine.invoke(ctx, "propose_payment", {"refs": [ids["northwind_nov_ref"]]})
    assert isinstance(out, dict) and out.get("ok"), out
    async with db.session_scope() as s:  # run_turn does this after the reply is presented; confirm requires it
        from app.services import proposals
        pid = (await s.execute(select(Proposal.id).where(Proposal.conversation_id == actor.conversation_id,
                                                         Proposal.status == "open"))).scalars().first()
        await proposals.mark_presented(s, pid)
    return ctx


async def _state(actor):
    async with db.session_scope() as s:
        c = await s.get(Conversation, actor.conversation_id)
        return dict(c.workflow_state or {}), c.workflow_version


async def _proposal_statuses(actor):
    async with db.session_scope() as s:
        return [p.status for p in (await s.execute(select(Proposal).where(Proposal.conversation_id == actor.conversation_id))).scalars()]


async def _receipts():
    async with db.session_scope() as s:
        return len((await s.execute(select(Receipt))).scalars().all())


def _fakes(monkeypatch, *, pick, run=None, esc=None):
    """pick: str or list of str per call. run/esc: async callables or None for a default."""
    picks = [pick] if isinstance(pick, str) else list(pick)
    calls = {"pick": [], "run": [], "esc": []}

    async def fake_pick(actor, text, state, pending, metrics):
        calls["pick"].append(text)
        return picks[min(len(calls["pick"]) - 1, len(picks) - 1)]

    async def fake_run(wf, actor, channel, text, brief, metrics):
        calls["run"].append((wf.name, brief))
        if run:
            return await run(wf, actor, channel, text, brief, metrics)
        return "Here you go.", PurserContext(actor=actor, channel=channel)

    async def fake_esc(actor, channel, text, wf, trigger, brief, metrics):
        calls["esc"].append(trigger)
        metrics.update(escalated=True, escalation_trigger=trigger, route="escalated")
        if esc:
            return await esc(actor, channel, text, wf, trigger, brief, metrics)
        return "escalated reply", PurserContext(actor=actor, channel=channel)

    monkeypatch.setattr(engine, "_pick", fake_pick)
    monkeypatch.setattr(engine, "_run_workflow", fake_run)
    monkeypatch.setattr(engine, "_escalate", fake_esc)
    return calls


def _ctx_with(actor, log, ui=None):
    c = PurserContext(actor=actor)
    c.tool_log.extend(log)
    c.ui.extend(ui or [])
    return c


# ------------------------------------------------------------------ 1. registry
def test_registry_loads_and_check_passes():
    wfs = registry.workflows()
    assert len(wfs) > 20
    registry.check(wfs)


def test_every_real_tool_is_reachable_from_some_workflow():
    used = set()
    for wf in registry.workflows().values():
        used |= set(wf.all_tools)
    missing = {t.name for t in ALL_TOOLS} - used - {"confirm_pending_proposal", "cancel_pending_proposal", "suggest_next_actions"}  # engine-only
    assert not missing


def test_check_rejects_unknown_tool():
    with pytest.raises(RegistryError, match="unknown tools"):
        registry.check({"a": _wf(name="a", tools=("no_such_tool",))})


def test_check_rejects_engine_only_tool():
    with pytest.raises(RegistryError, match="engine-only"):
        registry.check({"a": _wf(name="a", tools=("confirm_pending_proposal",))})


def test_check_rejects_uncovered_real_tool():
    with pytest.raises(RegistryError, match="not covered"):
        registry.check({"a": _wf(name="a", tools=("propose_payment",))})


def test_check_rejects_required_tool_not_callable():
    with pytest.raises(RegistryError, match="requires tools"):
        registry.check({"a": _wf(name="a", required=("get_fx_rates",))})


async def test_employee_menu_has_no_budget_change(seeded):
    emp = await make_actor(seeded, "arjun", conversation=False)
    assert "budget_change" not in {w.name for w in registry.menu(emp)}


async def test_menu_is_role_filtered(seeded):
    emp = await make_actor(seeded, "arjun", conversation=False)
    admin = await make_actor(seeded, "priya", conversation=False)
    ceo = dataclasses.replace(admin, role="ceo")
    emp_names = {w.name for w in registry.menu(emp)}
    admin_names = {w.name for w in registry.menu(admin)}
    ceo_menu = registry.menu(ceo)
    for finance_only in ("revenue_overview", "record_payment"):
        assert finance_only not in emp_names
        assert finance_only in admin_names
    writes = tool_access.FINANCE_WRITE | tool_access.OTHER_WRITES
    for wf in ceo_menu:
        if not wf.tools:  # tool-less (general_reply) is offered to every role
            continue
        assert not all(t.startswith("propose_") or t in writes for t in wf.tools), wf.name
    assert len(admin_names) >= len(emp_names) and len(admin_names) >= len(ceo_menu)


# ------------------------------------------------------------------ 2. verify
def test_verify_propose_ok_is_proposal():
    assert verify(_wf(), _log(("propose_payment", "ok")), "Confirm?", []).status == "proposal"


def test_verify_ask_choice_is_asked():
    assert verify(_wf(), _log(("ask_choice", "ok")), "Which one", []).status == "asked"


def test_verify_forbidden_is_refused():
    assert verify(_wf(), _log(("propose_payment", "FORBIDDEN")), "Not allowed.", []).status == "refused"


def test_verify_required_tool_ok_is_done():
    assert verify(_wf(required=("list_client_invoices",)), _log(("list_client_invoices", "ok")), "Three invoices.", []).status == "done"


def test_verify_statement_without_tools_fails():
    out = verify(_wf(), [], "All paid.", [])
    assert out.status == "failed"


def test_verify_tool_error_then_question_is_asked():
    assert verify(_wf(), _log(("list_client_invoices", "NOT_FOUND")), "Which client do you mean?", []).status == "asked"


# ------------------------------------------------------------------ 3. continuation (real DB, no LLM)
async def _no_llm(monkeypatch):
    async def boom(*a, **k):
        raise AssertionError("LLM step must not run on a continuation")

    for n in ("_pick", "_run_workflow", "_escalate"):
        monkeypatch.setattr(engine, n, boom)


async def test_haan_confirms_open_proposal(seeded, monkeypatch):
    await _no_llm(monkeypatch)
    actor = await make_actor(seeded, "priya")
    await _open_proposal(actor, seeded)
    await _say(actor, "haan")
    res = await engine.run(actor, "haan")
    assert res.metrics["route"] == "continuation"
    assert "Ho gaya" in res.reply, res.reply
    assert await _receipts() == 1
    assert "open" not in await _proposal_statuses(actor)
    state, _ = await _state(actor)
    assert "active" not in state
    assert state["recent"][-1]["u"] == "haan"


async def test_confirm_with_active_workflow_leaves_memo_line(seeded, monkeypatch):
    actor = await make_actor(seeded, "priya")

    async def run(wf, actor_, channel, text, brief, metrics):
        return "Confirm payment?", await _open_proposal(actor_, seeded)

    _fakes(monkeypatch, pick="record_payment", run=run)
    r1 = await engine.run(actor, "Northwind ka paisa aa gaya")
    assert (await _state(actor))[0]["active"]["name"] == "record_payment"
    await _no_llm(monkeypatch)
    await _say(actor, "haan")
    r2 = await engine.run(actor, "haan")
    assert r2.metrics["route"] == "continuation" and r2.metrics["workflow"] == "record_payment"
    state, _ = await _state(actor)
    assert "active" not in state
    assert state["memo"] and state["memo"][-1].startswith("record_payment:")
    assert await _receipts() == 1
    assert r1.metrics["workflow"] == "record_payment"


async def test_no_cancels_open_proposal(seeded, monkeypatch):
    await _no_llm(monkeypatch)
    actor = await make_actor(seeded, "priya")
    await _open_proposal(actor, seeded)
    await _say(actor, "no")
    res = await engine.run(actor, "no")
    assert res.metrics["route"] == "continuation"
    assert "open" not in await _proposal_statuses(actor)
    assert await _receipts() == 0
    assert "cancel" in res.reply.lower()


async def test_haan_with_nothing_pending_writes_nothing(seeded, monkeypatch):
    await _no_llm(monkeypatch)
    actor = await make_actor(seeded, "priya")
    await _say(actor, "haan")
    res = await engine.run(actor, "haan")
    assert res.metrics["route"] == "continuation"
    assert await _receipts() == 0 and await _proposal_statuses(actor) == []
    assert "pending" in res.reply.lower() or "waiting" in res.reply.lower()


async def test_negative_with_amount_correction_goes_to_picker(seeded, monkeypatch):
    actor = await make_actor(seeded, "priya")
    await _open_proposal(actor, seeded)
    calls = _fakes(monkeypatch, pick="record_payment")
    await _say(actor, "nahi nahi 2,01,000")
    res = await engine.run(actor, "nahi nahi 2,01,000")
    assert calls["pick"], "must reach the picker"
    assert res.metrics["route"] != "continuation"


async def test_longer_negative_with_extra_content_goes_to_picker_not_cancel(seeded, monkeypatch):
    actor = await make_actor(seeded, "priya")
    await _open_proposal(actor, seeded)
    calls = _fakes(monkeypatch, pick="record_payment")
    text = "nahi nahi 2,01,000 hai"
    await _say(actor, text)
    res = await engine.run(actor, text)
    assert calls["pick"], "must reach the picker"
    assert res.metrics["route"] != "continuation"


# ------------------------------------------------------------------ 4. engine flow with fakes
async def test_proposal_keeps_workflow_active(seeded, monkeypatch):
    actor = await make_actor(seeded, "priya")

    async def run(wf, actor_, channel, text, brief, metrics):
        return "Confirm payment?", await _open_proposal(actor_, seeded)

    _fakes(monkeypatch, pick="record_payment", run=run)
    res = await engine.run(actor, "Northwind paid")
    state, _ = await _state(actor)
    assert state["active"]["name"] == "record_payment" and state["active"]["status"] == "proposal"
    assert res.metrics["workflow"] == "record_payment" and res.metrics["escalated"] is False


async def test_read_workflow_is_killed_and_memoed(seeded, monkeypatch):
    actor = await make_actor(seeded, "priya")

    async def run(wf, actor_, channel, text, brief, metrics):
        return "Revenue is fine.", _ctx_with(actor_, _log(("get_revenue_overview", "ok")))

    _fakes(monkeypatch, pick="revenue_overview", run=run)
    await engine.run(actor, "revenue kaisa hai")
    state, _ = await _state(actor)
    assert "active" not in state
    assert state["memo"] == ["revenue_overview: Revenue is fine."]


async def test_none_escalates(seeded, monkeypatch):
    actor = await make_actor(seeded, "priya")
    calls = _fakes(monkeypatch, pick="none")
    res = await engine.run(actor, "something weird")
    assert calls["esc"] == ["no workflow fits"] and calls["run"] == []
    assert res.metrics["escalated"] is True and res.reply == "escalated reply"


async def test_workflow_declines_escalates(seeded, monkeypatch):
    actor = await make_actor(seeded, "priya")

    async def run(wf, actor_, channel, text, brief, metrics):
        return "ESCALATE: needs two tools", PurserContext(actor=actor_)

    calls = _fakes(monkeypatch, pick="revenue_overview", run=run)
    await engine.run(actor, "x")
    assert len(calls["esc"]) == 1 and calls["esc"][0].startswith("workflow declined")
    assert len(calls["run"]) == 1


async def test_failed_checklist_twice_escalates_after_exactly_two_runs(seeded, monkeypatch):
    actor = await make_actor(seeded, "priya")

    async def run(wf, actor_, channel, text, brief, metrics):
        return "All sorted.", PurserContext(actor=actor_)  # statement, no tools -> failed

    calls = _fakes(monkeypatch, pick="revenue_overview", run=run)
    await engine.run(actor, "x")
    assert len(calls["run"]) == 2
    assert "Previous attempt failed" in calls["run"][1][1]
    assert len(calls["esc"]) == 1 and calls["esc"][0].startswith("checklist failed")


async def test_escalation_row_is_logged(seeded, monkeypatch):
    """Uses the real _escalate logging path with only the model call faked."""
    actor = await make_actor(seeded, "priya")

    class R:
        final_output = "strong answer"
        raw_responses: list = []

    async def fake_runner_run(*a, **k):
        return R()

    monkeypatch.setattr(engine.Runner, "run", fake_runner_run)
    monkeypatch.setattr(engine, "build_agent", lambda *a, **k: object())

    async def pick(*a, **k):
        return "none"

    monkeypatch.setattr(engine, "_pick", pick)
    res = await engine.run(actor, "unusual request")
    assert res.reply == "strong answer" and res.metrics["escalated"] is True
    async with db.session_scope() as s:
        rows = (await s.execute(select(Escalation))).scalars().all()
    assert len(rows) == 1 and rows[0].trigger == "no workflow fits" and rows[0].utterance == "unusual request"


async def test_switching_workflow_cancels_pending_proposal(seeded, monkeypatch):
    actor = await make_actor(seeded, "priya")

    async def run1(wf, actor_, channel, text, brief, metrics):
        return "Confirm payment?", await _open_proposal(actor_, seeded)

    _fakes(monkeypatch, pick="record_payment", run=run1)
    await engine.run(actor, "Northwind paid")
    assert "open" in await _proposal_statuses(actor)

    async def run2(wf, actor_, channel, text, brief, metrics):
        return "Revenue is fine.", _ctx_with(actor_, _log(("get_revenue_overview", "ok")))

    calls = _fakes(monkeypatch, pick="revenue_overview", run=run2)
    await engine.run(actor, "actually, how is revenue")
    assert "open" not in await _proposal_statuses(actor)
    assert "NOT made" in calls["run"][0][1]
    assert await _receipts() == 0


async def test_last_offer_used_for_bare_yes(seeded, monkeypatch):
    actor = await make_actor(seeded, "priya")

    async def run(wf, actor_, channel, text, brief, metrics):
        ui = [{"card": "suggestions", "items": [{"utterance": "show overdue invoices"}]}]
        return "Fine.", _ctx_with(actor_, _log(("get_revenue_overview", "ok")), ui)

    _fakes(monkeypatch, pick="revenue_overview", run=run)
    await engine.run(actor, "revenue?")
    assert (await _state(actor))[0]["last_offer"] == "show overdue invoices"
    seen = []

    async def run2(wf, actor_, channel, text, brief, metrics):
        seen.append(text)
        return "Here.", _ctx_with(actor_, _log(("list_client_invoices", "ok")))

    _fakes(monkeypatch, pick="list_invoices", run=run2)
    await _say(actor, "yes")
    await engine.run(actor, "yes")
    assert seen == ["show overdue invoices"]


# ------------------------------------------------------------------ 5. memory bounds
async def test_recent_and_memo_are_bounded(seeded, monkeypatch):
    actor = await make_actor(seeded, "priya")

    async def run(wf, actor_, channel, text, brief, metrics):
        return f"answer {text}", _ctx_with(actor_, _log(("get_revenue_overview", "ok")))

    _fakes(monkeypatch, pick="revenue_overview", run=run)
    for i in range(6):
        await engine.run(actor, f"question {i}")
    state, version = await _state(actor)
    assert len(state["recent"]) == 4 and len(state["memo"]) <= 4
    assert state["recent"][-1]["u"] == "question 5"
    assert version == 6


# ------------------------------------------------------------------ 6. runner dispatch
async def test_run_turn_dispatches_to_engine_when_flag_on(seeded, monkeypatch):
    actor = await make_actor(seeded, "priya")
    monkeypatch.setattr(get_settings(), "purser_workflows", True)

    async def fake_run(a, text, channel="text"):
        return engine.EngineResult("hello", PurserContext(actor=a, channel=channel), {"route": "workflow", "workflow": "x"})

    monkeypatch.setattr(engine, "run", fake_run)
    t = await runner.run_turn(actor, "hi")
    assert t.reply == "hello" and t.metrics["route"] == "workflow"


async def test_run_turn_uses_old_path_when_flag_off(seeded, monkeypatch):
    actor = await make_actor(seeded, "priya")
    monkeypatch.setattr(get_settings(), "purser_workflows", False)

    async def boom(*a, **k):
        raise AssertionError("engine must not run")

    monkeypatch.setattr(engine, "run", boom)

    class R:
        final_output = "old path"
        raw_responses: list = []

    async def fake_runner(*a, **k):
        return R()

    monkeypatch.setattr(runner.Runner, "run", fake_runner)
    monkeypatch.setattr(runner, "build_agent", lambda *a, **k: type("A", (), {"model": "fake"})())
    t = await runner.run_turn(actor, "hi")
    assert t.reply == "old path" and t.metrics["route"] == "agent"
