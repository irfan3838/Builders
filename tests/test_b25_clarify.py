"""B3 gate: ask_choice (2-5 options, chart registry validation, per-topic cap of 3, reset by build_chart)."""

import pytest
from sqlalchemy import select

from app import db
from app.agent.tools import charts as chart_tools
from app.agent.tools import clarify
from app.errors import VALIDATION
from app.models import Conversation
from app.services import charts
from tests.conftest import make_actor
from tests.test_intake_extra import call


def opts(*pairs):
    return [{"label": l, "value": v} for l, v in pairs]


TWO = opts(("A", "a"), ("B", "b"))


async def ask(actor, question="Which one?", options=TWO, **kw):
    return await call(clarify.ask_choice, actor, question=question, options=options, **kw)


async def counts(actor):
    async with db.session_scope() as s:
        return dict((await s.get(Conversation, actor.conversation_id)).clarify_counts)


async def test_choice_card_shape(seeded):
    a = await make_actor(seeded)
    out, ctx = await ask(a, "  Which   month? ", opts(("This month", "2026-11"), ("Last month", "2026-10"), ("Q3", "q3")), topic="general")
    assert out["ok"] is True and out["asked"] == 1 and out["remaining"] == 2 and "STOP" in out["instruction"]
    (card,) = ctx.ui
    assert card["card"] == "choice" and card["question"] == "Which month?" and card["topic"] == "general"
    assert card["step"] == 1 and card["max"] == 3 and len(card["id"]) == 12
    assert card["options"] == [{"label": "This month", "value": "2026-11"}, {"label": "Last month", "value": "2026-10"}, {"label": "Q3", "value": "q3"}]
    assert await counts(a) == {"general": 1}


async def test_truncation_and_dedupe(seeded):
    a = await make_actor(seeded)
    out, ctx = await ask(a, "q" * 300, opts(("x" * 100, "v" * 100), ("y", "w"), ("z", "w"), ("  ", "blank"), ("empty value", "  ")))
    assert out["ok"] is True
    card = ctx.ui[0]
    assert len(card["question"]) == 160
    assert card["options"][0] == {"label": "x" * 40, "value": "v" * 80}
    assert [o["value"] for o in card["options"]] == ["v" * 80, "w"]  # duplicate value, blank label, blank value all dropped


@pytest.mark.parametrize("options", [[], opts(("A", "a")), opts(("A", "a"), ("B", "a")), opts(*[(f"L{i}", f"v{i}") for i in range(6)])])
async def test_option_count_must_be_2_to_5(seeded, options):
    a = await make_actor(seeded)
    out, ctx = await ask(a, options=options)
    assert out["ok"] is False and out["code"] == VALIDATION and ctx.ui == []
    assert await counts(a) == {}  # a rejected question does not consume the budget


async def test_five_options_ok_and_blank_question_rejected(seeded):
    a = await make_actor(seeded)
    out, _ = await ask(a, options=opts(*[(f"L{i}", f"v{i}") for i in range(5)]))
    assert out["ok"] is True
    out, ctx = await ask(a, question="   ")
    assert out["ok"] is False and out["code"] == VALIDATION and ctx.ui == []


async def test_chart_options_validated_against_registry(seeded):
    a = await make_actor(seeded)
    reg = charts.options(a)
    measure = reg["sources"][0]["measures"][0]["name"]
    measure2 = reg["sources"][0]["measures"][1]["name"]
    dim = reg["sources"][0]["dimensions"][0]["name"]
    ctype = reg["chart_types"][0]
    ok, ctx = await ask(a, options=opts(("M1", measure), ("M2", measure2)), topic="chart", kind="measure")
    assert ok["ok"] is True and ctx.ui[0]["topic"] == "chart"
    ok, _ = await ask(a, options=opts(("D", dim), ("Other", ctype)), topic="chart", kind="dimension")
    assert ok["ok"] is False and ok["code"] == VALIDATION and ctype not in ok.get("allowed", []) or dim in ok["allowed"]
    ok, _ = await ask(a, options=opts(("T1", reg["chart_types"][0]), ("T2", reg["chart_types"][1])), topic="chart", kind="chart_type")
    assert ok["ok"] is True


async def test_chart_invalid_registry_values_rejected(seeded):
    a = await make_actor(seeded)
    for kind in ("measure", "dimension", "chart_type"):
        out, ctx = await ask(a, options=opts(("Fake 1", "not_a_real_name"), ("Fake 2", "also_fake")), topic="chart", kind=kind)
        assert out["ok"] is False and out["code"] == VALIDATION, kind
        assert "not_a_real_name" in out["message"] and ctx.ui == []
        assert isinstance(out["allowed"], list) and out["allowed"] and len(out["allowed"]) <= 40
    assert await counts(a) == {}


async def test_chart_registry_is_per_actor(seeded):
    """An employee's registry has no finance sources, so a finance measure cannot be offered to them as a button."""
    arjun, priya = await make_actor(seeded, "arjun"), await make_actor(seeded)
    fin_measure = next(m["name"] for s in charts.options(priya)["sources"] for m in s["measures"]
                       if m["name"] not in {x["name"] for s2 in charts.options(arjun)["sources"] for x in s2["measures"]})
    other = charts.options(priya)["sources"][0]["measures"][0]["name"]
    out, _ = await ask(arjun, options=opts(("Fin", fin_measure), ("Other", other)), topic="chart", kind="measure")
    assert out["ok"] is False and out["code"] == VALIDATION


async def test_chart_kind_time_range_and_other_not_registry_checked(seeded):
    a = await make_actor(seeded)
    out, _ = await ask(a, options=opts(("This FY", "fy"), ("Last 30 days", "30d")), topic="chart", kind="time_range")
    assert out["ok"] is True
    out, _ = await ask(a, options=opts(("x", "anything"), ("y", "goes")), topic="chart", kind="other")
    assert out["ok"] is True


async def test_registry_not_checked_for_flight_topic(seeded):
    a = await make_actor(seeded)
    out, _ = await ask(a, options=opts(("Mumbai", "BOM"), ("Delhi", "DEL")), topic="flight", kind="origin")
    assert out["ok"] is True


async def test_cap_of_three_per_topic_then_limit_reached(seeded):
    a = await make_actor(seeded)
    for n in (1, 2, 3):
        out, ctx = await ask(a, f"Q{n}?", topic="general")
        assert out["ok"] and out["asked"] == n and out["remaining"] == 3 - n and ctx.ui[0]["step"] == n
    out, ctx = await ask(a, "Q4?", topic="general")
    assert out["ok"] is False and out["code"] == "LIMIT_REACHED" and out["asked"] == 3
    assert ctx.ui == []  # no card on the 4th
    assert "proceed now" in out["message"]
    out, ctx = await ask(a, "Q5?", topic="general")
    assert out["code"] == "LIMIT_REACHED" and ctx.ui == [] and (await counts(a)) == {"general": 3}


async def test_topics_are_independent(seeded):
    a = await make_actor(seeded)
    for _ in range(3):
        await ask(a, topic="flight")
    assert (await ask(a, topic="flight"))[0]["code"] == "LIMIT_REACHED"
    out, ctx = await ask(a, topic="general")
    assert out["ok"] is True and out["asked"] == 1 and ctx.ui
    assert await counts(a) == {"flight": 3, "general": 1}


async def test_cap_is_per_conversation(seeded):
    a = await make_actor(seeded)
    b = await make_actor(seeded)  # same user, new conversation
    assert a.conversation_id != b.conversation_id
    for _ in range(3):
        await ask(a, topic="chart", options=opts(("x", "a"), ("y", "b")), kind="other")
    assert (await ask(a, topic="chart", kind="other"))[0]["code"] == "LIMIT_REACHED"
    out, _ = await ask(b, topic="chart", kind="other")
    assert out["ok"] is True and out["asked"] == 1


async def test_build_chart_success_resets_chart_count(seeded):
    a = await make_actor(seeded)
    for _ in range(3):
        await ask(a, topic="chart", kind="other")
    await ask(a, topic="general")
    assert (await ask(a, topic="chart", kind="other"))[0]["code"] == "LIMIT_REACHED"
    out, ctx = await call(chart_tools.build_chart, a, spec={"measures": ["receivables_outstanding"], "dimension": "customer"})
    assert out["ok"] is True, out
    assert await counts(a) == {"chart": 0, "general": 1}
    out, _ = await ask(a, topic="chart", kind="other")
    assert out["ok"] is True and out["asked"] == 1


async def test_failed_build_chart_does_not_reset(seeded):
    a = await make_actor(seeded)
    for _ in range(3):
        await ask(a, topic="chart", kind="other")
    out, _ = await call(chart_tools.build_chart, a, spec={"measures": ["receivables_outstanding", "budget_spent"], "dimension": "customer"})
    assert out["ok"] is False and out["code"] == VALIDATION
    assert (await counts(a))["chart"] == 3


async def test_no_conversation_means_no_persisted_count(seeded):
    """Without a conversation there is nowhere to count: every question is allowed (documented behaviour)."""
    a = await make_actor(seeded, conversation=False)
    for _ in range(5):
        out, _ = await ask(a)
        assert out["ok"] is True and out["asked"] == 1


async def test_bump_and_current_helpers(seeded):
    a = await make_actor(seeded)
    assert await clarify.current(a, "chart") == 0
    assert await clarify.bump(a, "chart") == 1 and await clarify.bump(a, "chart") == 2
    assert await clarify.current(a, "chart") == 2
    assert await clarify.bump(a, "chart", reset=True) == 0 and await clarify.current(a, "chart") == 0
