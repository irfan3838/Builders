"""Contracts module: clause scanner, metadata, liability bearer/cap/notice/survival, store reads, propose->confirm
actions, role gates, attention items, HTTP. Rules only: CONTRACTS_MODEL=off in every test (no model calls).
Business date pinned to 2026-11-21. Postgres only for the DB tests."""

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app import db
from app.actor import Actor
from app.agent.tools import finance as finance_tools
from app.errors import FORBIDDEN, INVALID_STATE, NOT_FOUND, VALIDATION, DomainError
from app.models import Contract, ContractDeadline, ContractFinding, Document, Extraction
from app.services import intake, proposals, records
from app.services.contracts import liability, metadata, review, scan, store
from app.services.contracts.catalogue import rules as catalogue_rules
from seed.contract_samples import LIVE_DEMO, NDA_COPILOT_FIXTURE, SEEDED
from tests.conftest import make_actor
from tests.test_api_intake import client_for

TODAY = date(2026, 11, 21)
OURS = ("purserdemotraders", "dzruptiv")


@pytest.fixture(autouse=True)
def rules_only(monkeypatch):
    monkeypatch.setenv("CONTRACTS_MODEL", "off")
    monkeypatch.setattr("app.services.records.today_ist", lambda: TODAY)


# ---------------------------------------------------------------- helpers


def by_type(r: dict, key: str) -> list[dict]:
    return [f for f in r["findings"] if f["clause_type"] == key]


def one(r: dict, key: str) -> dict:
    got = by_type(r, key)
    assert len(got) == 1, f"expected one {key}, got {len(got)}: {[f['clause_type'] for f in r['findings']]}"
    return got[0]


def dl(r: dict, kind: str) -> list[date]:
    return [date.fromisoformat(d["due_on"]) for d in r["deadlines"] if d["kind"] == kind]


async def analyse(text, filename="x.pdf"):
    return await review.analyse(text, filename, OURS, use_model=False)


def role_actor(base: Actor, role: str) -> Actor:
    return Actor(base.user_id, base.workspace_id, role, base.party_id, base.display_name, base.conversation_id)


async def propose_confirm(actor, kind, args, via="button"):
    async with db.session_scope() as s:
        p = await proposals.create(s, actor, kind, args)
    async with db.session_scope() as s:
        out = await proposals.confirm(s, actor, p.id, via=via)
    return p, out


async def stage_document(actor, text=None, filename=None, sha="c" * 64, with_text=True) -> int:
    """A classified-as-contract document with a staged review on its extraction (as review._review leaves it)."""
    text = text or LIVE_DEMO["text"]
    filename = filename or LIVE_DEMO["filename"]
    staged = await analyse(text, filename)
    if with_text:
        staged.update(text=text, text_source="pdf_text", pages=2, vision_pages=[], unread_pages=[], coverage_note=None)
    async with db.session_scope() as s:
        d = Document(workspace_id=actor.workspace_id, uploader_id=actor.user_id, storage_key="test/contract", filename=filename,
                     sha256=sha, media_type="application/pdf", pages=2, size_bytes=1000, status="inspected")
        s.add(d)
        await s.flush()
        s.add(Extraction(workspace_id=actor.workspace_id, document_id=d.id, doc_type="contract", arithmetic="ok",
                         fields={"contract_review": staged}))
        return d.id


async def contract_by_ref(ref: str) -> Contract:
    async with db.session_scope() as s:
        return (await s.execute(select(Contract).where(Contract.ref == ref))).scalars().one()


async def findings_of(ref: str) -> list[ContractFinding]:
    async with db.session_scope() as s:
        c = (await s.execute(select(Contract).where(Contract.ref == ref))).scalars().one()
        return list((await s.execute(select(ContractFinding).where(ContractFinding.contract_id == c.id).order_by(ContractFinding.start))).scalars())


async def deadlines_of(ref: str) -> list[ContractDeadline]:
    async with db.session_scope() as s:
        c = (await s.execute(select(Contract).where(Contract.ref == ref))).scalars().one()
        return list((await s.execute(select(ContractDeadline).where(ContractDeadline.contract_id == c.id))).scalars())


# ================================================================ 1. copilot NDA fixture (rules only)


async def test_copilot_nda_fixture_findings():
    r = await analyse(NDA_COPILOT_FIXTURE)
    got = {(f["clause_type"], f["risk"], f["confidence"], f["state"]) for f in r["findings"]}
    assert ("confidentiality", "standard", "low", "tagged") in got
    assert ("unlimited_liability", "high", "low", "proposed") in got
    assert ("broad_indemnity", "high", "low", "proposed") in got
    assert ("payment_terms", "standard", "low", "tagged") in got
    assert ("governing_law", "standard", "low", "tagged") in got
    assert r["scanned_by_model"] is False and r["liability_by_model"] is False


async def test_copilot_nda_bearer_and_beneficiary():
    r = await analyse(NDA_COPILOT_FIXTURE)
    unl, ind = one(r, "unlimited_liability"), one(r, "broad_indemnity")
    assert unl["liability"]["bearer"] == "us"
    assert ind["liability"]["bearer"] == "us"
    assert "Client" in ind["liability"]["beneficiary"]
    assert unl["liability"]["cap_basis"] == "no cap"


# ================================================================ 2. quote grounding


def seg(text: str, start: int = 100) -> scan.Segment:
    return scan.Segment(start, start + len(text), text)


def test_locate_rejects_short_quote():
    s = seg("The Supplier shall indemnify the Client against all claims.")
    assert scan.locate(s, "indemni") is None  # 7 chars
    assert scan.locate(s, "  Client  ") is None  # 6 chars after normalising


def test_locate_exactly_eight_chars_ok():
    s = seg("The Supplier shall indemnify the Client.")
    span = scan.locate(s, "indemnif")
    assert span is not None and s.text[span[0] - s.start: span[1] - s.start] == "indemnif"


def test_locate_rejects_quote_not_in_segment():
    s = seg("The Supplier shall indemnify the Client against all claims.")
    assert scan.locate(s, "The Supplier shall pay all damages") is None


def test_locate_tolerates_whitespace_case_and_quotes():
    s = seg("The  Supplier\nshall   indemnify the Client.")
    span = scan.locate(s, "“the supplier SHALL indemnify”")
    assert span is not None
    got = s.text[span[0] - s.start: span[1] - s.start]
    assert got == "The  Supplier\nshall   indemnify"


def test_locate_offsets_are_absolute():
    s = seg("Alpha beta gamma delta epsilon.", start=500)
    a, b = scan.locate(s, "gamma delta")
    assert (a, b) == (500 + 11, 500 + 22)


def test_note_ok_drops_note_with_foreign_number():
    s = seg("The cap is 12 months of fees.")
    assert scan._note_ok("Cap is 12 months.", s) == "Cap is 12 months."
    assert scan._note_ok("Cap is 24 months.", s) is None
    assert scan._note_ok("   ", s) is None
    assert scan._note_ok(None, s) is None


def test_note_ok_truncates_long_note():
    s = seg("Plain clause.")
    assert len(scan._note_ok("word " * 200, s)) <= scan.NOTE_MAX


def test_segments_split_on_numbered_headings_and_blank_lines():
    text = "Intro line.\n\n1. First clause here.\n2. Second clause here.\nmore of second.\n\nTail."
    segs = scan.segments(text)
    assert [s.text.strip() for s in segs] == ["Intro line.", "1. First clause here.", "2. Second clause here.\nmore of second.", "Tail."]
    for s in segs:
        assert text[s.start: s.stop] == s.text


def test_segments_cut_long_paragraph():
    text = ("Sentence number one is here. " * 200).strip()
    segs = scan.segments(text)
    assert len(segs) >= 4 and all(len(s.text) <= scan.SEGMENT_MAX for s in segs)
    assert "".join(s.text for s in segs) == text


def test_dedup_keeps_surer_overlap_and_join_merges_close_pieces():
    a = scan.Found("confidentiality", 0, 50, "a" * 50, "standard", "low")
    b = scan.Found("confidentiality", 10, 60, "b" * 50, "standard", "high")
    assert scan._dedup([a, b]) == [b]
    other = scan.Found("governing_law", 5, 9, "x" * 4, "standard", "low")
    assert len(scan._dedup([a, other])) == 2
    text = "x" * 400
    p1 = scan.Found("broad_indemnity", 0, 50, text[0:50], "medium", "low")
    p2 = scan.Found("broad_indemnity", 100, 150, text[100:150], "high", "high", "note")
    [j] = scan._join(text, [p1, p2])
    assert (j.start, j.stop, j.risk, j.confidence, j.note) == (0, 150, "high", "high", "note")
    far = scan.Found("broad_indemnity", 350, 390, text[350:390], "high", "low")
    assert len(scan._join(text, [p1, far])) == 2


async def test_scan_rules_only_reports_patterns_only():
    found, by_model = await scan.scan(NDA_COPILOT_FIXTURE, catalogue_rules(), use_model=True)
    assert by_model is False  # CONTRACTS_MODEL=off
    assert found and all(f.confidence == "low" for f in found)
    for f in found:
        assert f.quote == NDA_COPILOT_FIXTURE[f.start: f.stop]


# ================================================================ 3. LIVE_DEMO MSA


async def test_live_demo_msa_details_and_liabilities():
    r = await analyse(LIVE_DEMO["text"], LIVE_DEMO["filename"])
    assert r["counterparty"] == "Northwind Labs Inc"
    d = r["details"]
    assert d["effective_on"]["value"] == "2026-12-01"
    assert d["expiry_on"]["value"] == "2029-11-30"  # 36 months minus a day
    lol = one(r, "limitation_of_liability")["liability"]
    assert lol["cap_paise"] is None and "fees paid" in lol["cap_basis"]
    assert len(lol["carve_outs"]) >= 1
    ut = one(r, "unilateral_termination")["liability"]
    assert ut["bearer"] == "counterparty" and ut["notice_days"] == 30
    assert dl(r, "survival_end") == [date(2031, 11, 30)]  # expiry + 2 years
    assert dl(r, "expiry") == [date(2029, 11, 30)]


async def test_live_demo_clean_name_has_no_company_tail():
    r = await analyse(LIVE_DEMO["text"], LIVE_DEMO["filename"])
    assert "incorporated" not in r["counterparty"] and "," not in r["counterparty"]
    assert review.clean_name("Northwind Labs Inc, a company incorporated in Delaware") == "Northwind Labs Inc"
    assert review.clean_name('Foo Bar Ltd (hereinafter "Client")') == "Foo Bar Ltd"


# ================================================================ 4. Lotus MSA


async def test_lotus_msa():
    r = await analyse(SEEDED["msa_lotus"]["text"], SEEDED["msa_lotus"]["filename"])
    lol = one(r, "limitation_of_liability")["liability"]
    assert lol["cap_paise"] == 100_000_000
    assert lol["bearer"] == "us" and len(lol["carve_outs"]) >= 1
    assert one(r, "auto_renewal")["liability"]["notice_days"] == 60
    assert dl(r, "expiry") == [date(2027, 2, 28)]
    assert dl(r, "renewal_notice") == [date(2027, 2, 28) - timedelta(days=60)]
    assert dl(r, "survival_end") == [date(2030, 2, 28)]


async def test_lotus_cap_basis_keeps_amount():
    r = await analyse(SEEDED["msa_lotus"]["text"], SEEDED["msa_lotus"]["filename"])
    assert "10,00,000" in one(r, "limitation_of_liability")["liability"]["cap_basis"]


# ================================================================ 5. one-way NDA


async def test_one_way_nda_parties_and_hold_harmless():
    text = SEEDED["nda_nimbus_oneway"]["text"]
    parties = liability.defined_parties(text)
    assert parties["recipient"] == "Purser Demo Traders Private Limited"
    assert parties["discloser"] == "Nimbus Retail Private Limited"
    r = await analyse(text, SEEDED["nda_nimbus_oneway"]["filename"])
    assert one(r, "broad_indemnity")["liability"]["bearer"] == "us"
    assert r["counterparty"] == "Nimbus Retail Private Limited"
    assert dl(r, "expiry") == [date(2027, 6, 9)]


# ================================================================ 6. vendor contract (Ganesh)


async def test_vendor_defined_terms_make_supplier_the_counterparty():
    text = SEEDED["vendor_ganesh"]["text"]
    parties = liability.defined_parties(text)
    assert parties["supplier"] == "Shree Ganesh Printers"
    # mapping wins over the 'supplier = us' role-word assumption
    assert liability.resolve("the Supplier", parties, OURS, "Shree Ganesh Printers") == "counterparty"
    assert liability.resolve("the Supplier", {}, OURS, None) == "us"  # no mapping: role word assumption
    r = await analyse(text, SEEDED["vendor_ganesh"]["filename"])
    lol = one(r, "limitation_of_liability")["liability"]
    assert lol["cap_paise"] == 20_000_000 and lol["bearer"] == "counterparty"
    assert dl(r, "renewal_notice") == [date(2026, 12, 19) - timedelta(days=15)]
    assert dl(r, "expiry") == [date(2026, 12, 19)]


# ================================================================ 7. parse_cap / small readers


@pytest.mark.parametrize("phrase,paise", [
    ("shall not exceed Rs. 10,00,000 only", 100_000_000),
    ("shall not exceed INR 2,00,000", 20_000_000),
    ("shall not exceed ₹5 lakh", 50_000_000),
    ("shall not exceed 1.5 crore rupees", 1_500_000_000),
    ("shall not exceed Rupees 50,000", 5_000_000),
])
def test_parse_cap_inr(phrase, paise):
    got, basis = liability.parse_cap(phrase)
    assert got == paise and basis


def test_parse_cap_usd_keeps_basis_no_paise():
    got, basis = liability.parse_cap("The liability shall not exceed USD 50,000 in aggregate")
    assert got is None and "USD 50,000" in basis


def test_parse_cap_no_amount():
    got, basis = liability.parse_cap("shall not exceed the fees paid in the preceding twelve months")
    assert got is None and "fees paid" in basis


@pytest.mark.parametrize("s,days", [
    ("sixty (60) days' prior written notice", 60), ("thirty days written notice", 30), ("two months notice", 60),
    ("15 days' notice", 15), ("no period here", None)])
def test_notice_days(s, days):
    assert liability.notice_days(s) == days


@pytest.mark.parametrize("s,months", [
    ("shall survive for a period of three (3) years", 36), ("shall survive for a period of 6 months", 6), ("nothing", None)])
def test_survival_months(s, months):
    assert liability.survival_months(s) == months


def test_resolve_variants():
    assert liability.resolve(None, {}, OURS, None) == "unclear"
    assert liability.resolve("each party", {}, OURS, None) == "mutual"
    assert liability.resolve("Purser Demo Traders", {}, OURS, None) == "us"
    assert liability.resolve("Acme Traders Private Limited", {}, OURS, "Acme Traders Private Limited") == "counterparty"
    assert liability.resolve("the Client", {}, OURS, None) == "counterparty"
    assert liability.resolve("the Recipient", {"recipient": "Purser Demo Traders Pvt"}, OURS, "Nimbus") == "us"
    assert liability.resolve("the Recipient", {"recipient": "Nimbus Retail"}, OURS, "Nimbus Retail") == "counterparty"
    assert liability.resolve("the Mystery", {}, OURS, None) == "unclear"


def test_carve_outs_rules_finds_not_apply_sentence():
    text = ("1. Limitation of Liability. The liability of the Supplier shall not exceed Rs. 5,00,000. "
            "This limitation shall not apply to fraud.\n")
    start = text.index("The liability")
    found = scan.Found("limitation_of_liability", start, start + 40, text[start: start + 40], "standard", "low")
    outs = liability.carve_outs_rules(text, found)
    assert any("fraud" in c["quote"] for c in outs)
    for c in outs:
        assert text[c["start"]: c["stop"]].split()[:1] == c["quote"].split()[:1]


def test_metadata_rules_effective_expiry():
    d = metadata.rules(LIVE_DEMO["text"], LIVE_DEMO["filename"])
    assert d.effective_on.value == date(2026, 12, 1) and d.expiry_on.value == date(2029, 11, 30)
    assert metadata.add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert metadata.end_of_term(date(2026, 12, 1), 36) == date(2029, 11, 30)


async def test_metadata_read_rules_only():
    d = await metadata.read(LIVE_DEMO["text"], LIVE_DEMO["filename"], OURS, use_model=False)
    assert d.client is not None and d.client.value.startswith("Northwind Labs Inc")
    assert d.effective_on.value == date(2026, 12, 1)


def test_roles_helpers():
    base = Actor(1, 1, "admin", None, "x")
    assert review.can_view(base) and review.can_decide(base)
    fa = role_actor(base, "finance_approver")
    assert review.can_view(fa) and not review.can_decide(fa)
    for role in ("employee", "hr_admin"):
        a = role_actor(base, role)
        assert not review.can_view(a) and not review.can_decide(a)


def test_guess_type_and_title():
    assert review.guess_type(NDA_COPILOT_FIXTURE, "x.pdf") == "nda"
    assert review.guess_type(LIVE_DEMO["text"], "x.pdf") == "msa"
    assert review.guess_type("hello", "supply agreement.pdf") == "vendor"
    assert review.guess_type("hello", "notes.pdf") == "other"
    assert "Master Services Agreement".lower() in review.guess_title(LIVE_DEMO["text"], "f.pdf").lower()


# ================================================================ seed sanity


async def test_seed_creates_four_contracts(seeded):
    assert [seeded[f"contract_{k}_ref"] for k in ("nda_acme", "msa_lotus", "nda_nimbus_oneway", "vendor_ganesh")] == ["AG1", "AG2", "AG3", "AG4"]
    async with db.session_scope() as s:
        n = len((await s.execute(select(Contract))).scalars().all())
    assert n == 4


# ================================================================ 8. role gates on reads


async def test_reads_forbidden_for_employee_and_hr(seeded):
    base = await make_actor(seeded, "priya")
    for a in (await make_actor(seeded, "arjun"), await make_actor(seeded, "neha"), role_actor(base, "hr_admin")):
        async with db.session_scope() as s:
            for coro in (store.liabilities(s, a), store.by_mention(s, a, "AG1"), store.caps(s, a), store.deadlines(s, a),
                         store.search(s, a)):
                with pytest.raises(DomainError) as e:
                    await coro
                assert e.value.code == FORBIDDEN


async def test_finance_approver_can_read(seeded):
    fa = role_actor(await make_actor(seeded, "priya"), "finance_approver")
    async with db.session_scope() as s:
        assert await store.liabilities(s, fa)
        assert (await store.by_mention(s, fa, "AG1")).ref == "AG1"
        assert len(await store.search(s, fa)) == 4
        assert await store.caps(s, fa)


async def test_finance_approver_decide_actions_forbidden(seeded):
    fa = role_actor(await make_actor(seeded, "priya"), "finance_approver")
    async with db.session_scope() as s:
        f = (await s.execute(select(ContractFinding).where(ContractFinding.state == "proposed"))).scalars().first()
        fid = f.id
    for kind, args in (("review_contract_finding", {"finding_id": fid, "decision": "accept"}),
                       ("set_contract_status", {"contract": "AG1", "status": "terminated"}),
                       ("set_contract_details", {"contract": "AG1", "title": "New title"}),
                       ("rescan_contract", {"contract": "AG1"})):
        async with db.session_scope() as s:
            with pytest.raises(DomainError) as e:
                await proposals.create(s, fa, kind, args)
        assert e.value.code == FORBIDDEN, kind


async def test_employee_cannot_create_contract(seeded):
    arjun = await make_actor(seeded, "arjun")
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await proposals.create(s, arjun, "create_contract", {"document_id": 1})
    assert e.value.code == FORBIDDEN


# ================================================================ store reads (seeded)


async def test_liabilities_filters(seeded):
    admin = await make_actor(seeded, "priya")
    async with db.session_scope() as s:
        allr = await store.liabilities(s, admin)
        us = await store.liabilities(s, admin, bearer="us")
        cp = await store.liabilities(s, admin, bearer="counterparty")
        high = await store.liabilities(s, admin, risk="high")
        ag1 = await store.liabilities(s, admin, contract="AG1")
    assert allr and all(r["risk"] in ("high", "medium", "low") for r in allr)
    assert us and all(r["bearer"] == "us" for r in us)
    assert cp and all(r["bearer"] == "counterparty" for r in cp)
    assert high and all(r["risk"] == "high" for r in high)
    assert ag1 and all(r["contract"] == "AG1" for r in ag1)
    assert [r["risk"] for r in allr] == sorted((r["risk"] for r in allr), key=["high", "medium", "low"].index)


async def test_caps_view(seeded):
    admin = await make_actor(seeded, "priya")
    async with db.session_scope() as s:
        caps = await store.caps(s, admin)
    by_c = {c["contract"]: c for c in caps}
    assert by_c["AG2"]["cap"] == "₹10,00,000.00" or "10,00,000" in by_c["AG2"]["cap"]
    assert by_c["AG2"]["carve_outs"]
    assert "20,00,00" not in (by_c["AG4"]["cap"] or "") and "2,00,000" in by_c["AG4"]["cap"]
    assert by_c["AG1"]["cap"] is None and by_c["AG1"]["cap_basis"] == "no cap"


async def test_by_mention_variants(seeded):
    admin = await make_actor(seeded, "priya")
    async with db.session_scope() as s:
        assert (await store.by_mention(s, admin, "AG2")).ref == "AG2"
        assert (await store.by_mention(s, admin, "ag2")).ref == "AG2"
        assert (await store.by_mention(s, admin, 3)).ref == "AG3"
        assert (await store.by_mention(s, admin, "Lotus Hospitality")).ref == "AG2"
        with pytest.raises(DomainError) as e:
            await store.by_mention(s, admin, "AG99")
        assert e.value.code == NOT_FOUND


async def test_search_filters(seeded):
    admin = await make_actor(seeded, "priya")
    async with db.session_scope() as s:
        assert [r["ref"] for r in await store.search(s, admin, contract_type="nda")] == ["AG1", "AG3"]
        assert [r["ref"] for r in await store.search(s, admin, words="Lotus")] == ["AG2"]
        assert [r["ref"] for r in await store.search(s, admin, counterparty="ganesh")] == ["AG4"]
        assert await store.search(s, admin, status="terminated") == []
        rows = await store.search(s, admin)
    assert next(r for r in rows if r["ref"] == "AG1")["open_flags"] == 2


async def test_contract_view_shape(seeded):
    admin = await make_actor(seeded, "priya")
    async with db.session_scope() as s:
        c = await store.by_mention(s, admin, "AG2")
        fs, ds = await store.load_full(s, c)
        v = store.contract_view(c, fs, ds)
    assert v["ref"] == "AG2" and v["expiry_on"] == "2027-02-28" and v["status"] == "active"
    assert v["open_flags"] == 2 and v["binds_us"] == 2
    assert {d["kind"] for d in v["deadlines"]} == {"expiry", "renewal_notice", "survival_end"}
    assert [d["due_on"] for d in v["deadlines"]] == sorted(d["due_on"] for d in v["deadlines"])
    assert "caveat" in v["coverage"]


# ================================================================ 12. injection strings


@pytest.mark.parametrize("evil", ["x' OR 1=1 --", "'; DROP TABLE contracts; --", "%' OR '1'='1", "AG1; select 1", "\\", "%", "_"])
async def test_injection_strings_are_inert(seeded, evil):
    admin = await make_actor(seeded, "priya")
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await store.by_mention(s, admin, evil)
        assert e.value.code in (NOT_FOUND, "AMBIGUOUS")
    async with db.session_scope() as s:
        if evil not in ("%", "_"):  # LIKE wildcards are matched by ilike (documented below)
            assert await store.search(s, admin, words=evil) == []
            assert await store.search(s, admin, counterparty=evil) == []
            assert await store.liabilities(s, admin, counterparty=evil) == []
    async with db.session_scope() as s:
        assert len((await s.execute(select(Contract))).scalars().all()) == 4  # table intact


async def test_search_percent_is_literal(seeded):
    admin = await make_actor(seeded, "priya")
    async with db.session_scope() as s:
        assert await store.search(s, admin, words="%") == []


# ================================================================ 9. proposals


async def test_create_contract_confirm_persists_everything(seeded):
    admin = await make_actor(seeded, "priya")
    doc_id = await stage_document(admin)
    p, out = await propose_confirm(admin, "create_contract", {"document_id": doc_id})
    assert out.status == "executed", out
    ref = out.receipt.effects[0]["ref"]
    assert ref == "AG5"  # four seeded
    c = await contract_by_ref(ref)
    assert c.counterparty_name == "Northwind Labs Inc" and c.contract_type == "msa"
    assert c.effective_on == date(2026, 12, 1) and c.expiry_on == date(2029, 11, 30) and c.document_id == doc_id
    fs = await findings_of(ref)
    staged = await analyse(LIVE_DEMO["text"], LIVE_DEMO["filename"])
    assert len(fs) == len(staged["findings"]) and all(f.source == "ai" for f in fs)
    assert {f.state for f in fs} == {"tagged", "proposed"}
    ds = await deadlines_of(ref)
    assert {d.kind for d in ds} == {"expiry", "survival_end"}
    async with db.session_scope() as s:
        d = await s.get(Document, doc_id)
        assert d.outcome == "contract" and d.status == "closed"


async def test_create_contract_second_for_same_document_refused(seeded):
    admin = await make_actor(seeded, "priya")
    doc_id = await stage_document(admin)
    await propose_confirm(admin, "create_contract", {"document_id": doc_id})
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await proposals.create(s, admin, "create_contract", {"document_id": doc_id})
    assert e.value.code == INVALID_STATE


async def test_create_contract_without_review_refused(seeded):
    admin = await make_actor(seeded, "priya")
    async with db.session_scope() as s:
        d = Document(workspace_id=admin.workspace_id, uploader_id=admin.user_id, storage_key="k", filename="f.pdf", sha256="d" * 64,
                     media_type="application/pdf", pages=1, size_bytes=10, status="inspected")
        s.add(d)
        await s.flush()
        s.add(Extraction(workspace_id=admin.workspace_id, document_id=d.id, doc_type="contract", arithmetic="ok", fields={}))
        did = d.id
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await proposals.create(s, admin, "create_contract", {"document_id": did})
    assert e.value.code == INVALID_STATE


async def test_create_contract_counterparty_not_in_text_is_validation(seeded):
    admin = await make_actor(seeded, "priya")
    doc_id = await stage_document(admin)
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await proposals.create(s, admin, "create_contract", {"document_id": doc_id, "counterparty": "Totally Invented Corp"})
    assert e.value.code == VALIDATION


async def test_create_contract_bad_type_is_validation(seeded):
    admin = await make_actor(seeded, "priya")
    doc_id = await stage_document(admin)
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await proposals.create(s, admin, "create_contract", {"document_id": doc_id, "contract_type": "lease"})
    assert e.value.code == VALIDATION


async def test_create_contract_stale_when_document_changes(seeded):
    admin = await make_actor(seeded, "priya")
    doc_id = await stage_document(admin)
    async with db.session_scope() as s:
        p = await proposals.create(s, admin, "create_contract", {"document_id": doc_id})
    async with db.session_scope() as s:
        d = await s.get(Document, doc_id)
        d.version += 1
    async with db.session_scope() as s:
        out = await proposals.confirm(s, admin, p.id, via="button")
    assert out.status == "stale"
    async with db.session_scope() as s:
        assert (await s.execute(select(Contract).where(Contract.document_id == doc_id))).scalars().first() is None


async def _a_flag(ref="AG2", clause="broad_indemnity") -> ContractFinding:
    return next(f for f in await findings_of(ref) if f.clause_type == clause)


async def test_review_finding_accept_reject_modify(seeded):
    admin = await make_actor(seeded, "priya")
    ind = await _a_flag("AG2", "broad_indemnity")
    dat = await _a_flag("AG2", "data_liability")
    async with db.session_scope() as s:
        before = {r["finding_id"] for r in await store.liabilities(s, admin, contract="AG2")}
    assert ind.id in before and dat.id in before

    _, out = await propose_confirm(admin, "review_contract_finding", {"finding_id": ind.id, "decision": "accept", "comment": "ok"})
    assert out.status == "executed"
    f = await _a_flag("AG2", "broad_indemnity")
    assert f.state == "accepted" and f.reviewer_id == admin.user_id and f.reviewed_at and f.version == ind.version + 1
    async with db.session_scope() as s:
        now = {r["finding_id"] for r in await store.liabilities(s, admin, contract="AG2")}
        undecided = {r["finding_id"] for r in await store.liabilities(s, admin, contract="AG2", include_decided=False)}
    assert ind.id in now and ind.id not in undecided

    _, out = await propose_confirm(admin, "review_contract_finding", {"finding_id": ind.id, "decision": "reject"})
    assert out.status == "executed"
    async with db.session_scope() as s:
        assert ind.id not in {r["finding_id"] for r in await store.liabilities(s, admin, contract="AG2")}

    _, out = await propose_confirm(admin, "review_contract_finding",
                                   {"finding_id": dat.id, "decision": "modify", "risk": "standard", "explanation": "ordinary"})
    assert out.status == "executed"
    f = await _a_flag("AG2", "data_liability")
    assert f.state == "modified" and f.risk == "standard" and f.explanation == "ordinary"
    async with db.session_scope() as s:
        assert dat.id not in {r["finding_id"] for r in await store.liabilities(s, admin, contract="AG2")}


async def test_review_finding_modify_bearer(seeded):
    admin = await make_actor(seeded, "priya")
    ind = await _a_flag("AG2", "broad_indemnity")
    assert ind.bearer == "us"
    await propose_confirm(admin, "review_contract_finding", {"finding_id": ind.id, "decision": "modify", "bearer": "mutual"})
    f = await _a_flag("AG2", "broad_indemnity")
    assert f.bearer == "mutual" and f.liability_source == "reviewer" and f.state == "modified"


async def test_tagged_clause_cannot_be_accepted_or_rejected(seeded):
    admin = await make_actor(seeded, "priya")
    tagged = await _a_flag("AG2", "governing_law")
    assert tagged.state == "tagged"
    for decision in ("accept", "reject"):
        async with db.session_scope() as s:
            with pytest.raises(DomainError) as e:
                await proposals.create(s, admin, "review_contract_finding", {"finding_id": tagged.id, "decision": decision})
        assert e.value.code == INVALID_STATE
    # but modify can raise the risk
    _, out = await propose_confirm(admin, "review_contract_finding", {"finding_id": tagged.id, "decision": "modify", "risk": "high"})
    assert out.status == "executed"
    async with db.session_scope() as s:
        assert tagged.id in {r["finding_id"] for r in await store.liabilities(s, admin, contract="AG2")}


@pytest.mark.parametrize("args", [
    {"decision": "approve"}, {"decision": "modify"}, {"decision": "modify", "risk": "extreme"},
    {"decision": "modify", "bearer": "nobody"}, {"decision": "accept", "risk": "extreme"}])
async def test_review_finding_validation(seeded, args):
    admin = await make_actor(seeded, "priya")
    ind = await _a_flag("AG2", "broad_indemnity")
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await proposals.create(s, admin, "review_contract_finding", {"finding_id": ind.id, **args})
    assert e.value.code == VALIDATION


async def test_review_finding_unknown_id(seeded):
    admin = await make_actor(seeded, "priya")
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await proposals.create(s, admin, "review_contract_finding", {"finding_id": 99999, "decision": "accept"})
    assert e.value.code == NOT_FOUND


async def test_review_finding_stale_when_version_changes(seeded):
    admin = await make_actor(seeded, "priya")
    ind = await _a_flag("AG2", "broad_indemnity")
    async with db.session_scope() as s:
        p = await proposals.create(s, admin, "review_contract_finding", {"finding_id": ind.id, "decision": "accept"})
    async with db.session_scope() as s:
        row = await s.get(ContractFinding, ind.id)
        row.version += 1
    async with db.session_scope() as s:
        out = await proposals.confirm(s, admin, p.id, via="button")
    assert out.status == "stale"
    assert (await _a_flag("AG2", "broad_indemnity")).state == "proposed"


async def test_set_details_counterparty_not_in_text_is_validation(seeded):
    admin = await make_actor(seeded, "priya")
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await proposals.create(s, admin, "set_contract_details", {"contract": "AG2", "counterparty": "Phantom Holdings"})
    assert e.value.code == VALIDATION


@pytest.mark.parametrize("args", [{}, {"expiry_on": "31/12/2027"}, {"effective_on": "2027-01-01", "expiry_on": "2026-01-01"},
                                  {"contract_type": "lease"}])
async def test_set_details_validation(seeded, args):
    admin = await make_actor(seeded, "priya")
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await proposals.create(s, admin, "set_contract_details", {"contract": "AG2", **args})
    assert e.value.code == VALIDATION


async def test_set_details_expiry_recomputes_deadlines(seeded):
    admin = await make_actor(seeded, "priya")
    new_exp = date(2027, 6, 30)
    _, out = await propose_confirm(admin, "set_contract_details", {"contract": "AG2", "expiry_on": new_exp.isoformat()})
    assert out.status == "executed"
    c = await contract_by_ref("AG2")
    assert c.expiry_on == new_exp and c.version == 2
    ds = {d.kind: d.due_on for d in await deadlines_of("AG2")}
    assert ds["expiry"] == new_exp
    assert ds["renewal_notice"] == new_exp - timedelta(days=60)
    assert ds["survival_end"] == date(2030, 6, 30)


async def test_set_details_title_and_counterparty_keeps_deadlines(seeded):
    admin = await make_actor(seeded, "priya")
    before = sorted((d.kind, d.due_on) for d in await deadlines_of("AG2"))
    _, out = await propose_confirm(admin, "set_contract_details",
                                   {"contract": "AG2", "title": "Lotus MSA renamed", "counterparty": "Lotus Hospitality Private Limited"})
    assert out.status == "executed"
    c = await contract_by_ref("AG2")
    assert c.title == "Lotus MSA renamed"
    assert sorted((d.kind, d.due_on) for d in await deadlines_of("AG2")) == before


async def test_set_status_terminated_then_active_refused(seeded):
    admin = await make_actor(seeded, "priya")
    _, out = await propose_confirm(admin, "set_contract_status", {"contract": "AG4", "status": "terminated"})
    assert out.status == "executed"
    assert (await contract_by_ref("AG4")).status == "terminated"
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await proposals.create(s, admin, "set_contract_status", {"contract": "AG4", "status": "active"})
    assert e.value.code == INVALID_STATE
    # a terminated contract's deadlines leave the reminders
    async with db.session_scope() as s:
        assert all(d["contract"] != "AG4" for d in await store.deadlines(s, admin, 365))


async def test_set_status_same_and_bad_values_refused(seeded):
    admin = await make_actor(seeded, "priya")
    for status, code in (("active", INVALID_STATE), ("closed", VALIDATION), ("", VALIDATION)):
        async with db.session_scope() as s:
            with pytest.raises(DomainError) as e:
                await proposals.create(s, admin, "set_contract_status", {"contract": "AG4", "status": status})
        assert e.value.code == code


async def test_set_status_expired_then_active_is_allowed(seeded):
    admin = await make_actor(seeded, "priya")
    await propose_confirm(admin, "set_contract_status", {"contract": "AG4", "status": "expired"})
    _, out = await propose_confirm(admin, "set_contract_status", {"contract": "AG4", "status": "active"})
    assert out.status == "executed" and (await contract_by_ref("AG4")).status == "active"


async def test_rescan_keeps_reviewed_decisions(seeded):
    admin = await make_actor(seeded, "priya")
    ind = await _a_flag("AG2", "broad_indemnity")
    await propose_confirm(admin, "review_contract_finding", {"finding_id": ind.id, "decision": "reject"})
    n_before = len(await findings_of("AG2"))
    _, out = await propose_confirm(admin, "rescan_contract", {"contract": "AG2"})
    assert out.status == "executed"
    fs = await findings_of("AG2")
    rejected = [f for f in fs if f.clause_type == "broad_indemnity"]
    assert len(rejected) == 1 and rejected[0].id == ind.id and rejected[0].state == "rejected"
    assert len(fs) == n_before  # nothing duplicated
    assert len({(f.clause_type, f.start) for f in fs}) == len(fs)
    ds = {d.kind for d in await deadlines_of("AG2")}
    assert {"expiry", "renewal_notice", "survival_end"} <= ds


async def test_rescan_is_idempotent(seeded):
    admin = await make_actor(seeded, "priya")
    await propose_confirm(admin, "rescan_contract", {"contract": "AG3"})
    first = sorted((f.clause_type, f.start, f.state) for f in await findings_of("AG3"))
    await propose_confirm(admin, "rescan_contract", {"contract": "AG3"})
    assert sorted((f.clause_type, f.start, f.state) for f in await findings_of("AG3")) == first


# ================================================================ 10. attention items


async def test_attention_for_admin_includes_contract_items(seeded):
    admin = await make_actor(seeded, "priya")
    async with db.session_scope() as s:
        items = await finance_tools._attention(s, admin)
    kinds = [(i["kind"], i["ref"]) for i in items if i["kind"].startswith("contract_")]
    # Ganesh (AG4) renewal notice 2026-12-04 is 13 days after 2026-11-21; Lotus (AG2) 2026-12-30 is 39 days out
    assert ("contract_renewal_notice", "AG4") in kinds
    assert ("contract_renewal_notice", "AG2") not in kinds
    flags = [i for i in items if i["kind"] == "contract_flags"]
    assert len(flags) == 1 and flags[0]["ref"] == "6 open" and flags[0]["detail"].startswith("4 contract(s)")
    ag4 = next(i for i in items if i["kind"] == "contract_renewal_notice")
    assert ag4["date"] == "2026-12-04" and ag4["detail"] == "renewal notice in 13 days"


async def test_attention_window_edges(seeded, monkeypatch):
    admin = await make_actor(seeded, "priya")
    monkeypatch.setattr("app.services.records.today_ist", lambda: date(2026, 12, 4))  # due today: included (days_left 0)
    async with db.session_scope() as s:
        items = await finance_tools._attention(s, admin)
    assert any(i["kind"] == "contract_renewal_notice" and i["ref"] == "AG4" and "in 0 days" in i["detail"] for i in items)
    monkeypatch.setattr("app.services.records.today_ist", lambda: date(2026, 12, 5))  # past: gone
    async with db.session_scope() as s:
        items = await finance_tools._attention(s, admin)
    assert not any(i["kind"] == "contract_renewal_notice" and i["ref"] == "AG4" for i in items)
    monkeypatch.setattr("app.services.records.today_ist", lambda: date(2026, 11, 4))  # 30 days before: included
    async with db.session_scope() as s:
        items = await finance_tools._attention(s, admin)
    assert any(i["kind"] == "contract_renewal_notice" and i["ref"] == "AG4" for i in items)
    monkeypatch.setattr("app.services.records.today_ist", lambda: date(2026, 11, 3))  # 31 days: outside
    async with db.session_scope() as s:
        items = await finance_tools._attention(s, admin)
    assert not any(i["kind"] == "contract_renewal_notice" and i["ref"] == "AG4" for i in items)


async def test_attention_flags_clear_after_all_decided(seeded):
    admin = await make_actor(seeded, "priya")
    async with db.session_scope() as s:
        open_ids = [r["finding_id"] for r in await store.liabilities(s, admin, include_decided=False)]
    for fid in open_ids:
        await propose_confirm(admin, "review_contract_finding", {"finding_id": fid, "decision": "accept"})
    async with db.session_scope() as s:
        items = await finance_tools._attention(s, admin)
    assert not [i for i in items if i["kind"] == "contract_flags"]


async def test_attention_employee_sees_no_contract_items(seeded):
    for who in ("arjun", "neha"):
        a = await make_actor(seeded, who)
        async with db.session_scope() as s:
            items = await finance_tools._attention(s, a)
        assert not [i for i in items if i["kind"].startswith("contract_")]


async def test_attention_finance_approver_sees_deadlines_not_flags(seeded):
    fa = role_actor(await make_actor(seeded, "priya"), "finance_approver")
    async with db.session_scope() as s:
        items = await finance_tools._attention(s, fa)
    kinds = {i["kind"] for i in items}
    assert "contract_renewal_notice" in kinds and "contract_flags" not in kinds


# ================================================================ intake: contract outcome, DOCX


async def test_close_accepts_contract_outcome(seeded):
    admin = await make_actor(seeded, "priya")
    doc_id = await stage_document(admin, sha="e" * 64)
    async with db.session_scope() as s:
        d = await records.document(s, admin, doc_id)
        await intake.close(s, admin, d, "contract", "Saved as contract AGx")
    async with db.session_scope() as s:
        assert (await records.document(s, admin, doc_id)).outcome == "contract"
        with pytest.raises(DomainError):
            await intake.close(s, admin, await records.document(s, admin, doc_id), "contract", "again")


async def test_accept_upload_docx_accepted():
    assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in intake.ALLOWED


# ================================================================ 11. HTTP


async def test_http_contract_admin_ok_employee_forbidden(seeded):
    c = await client_for()
    r = await c.get("/api/contracts/AG1")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ref"] == "AG1" and body["liabilities"] and body["coverage"]["caveat"]
    assert (await c.get("/api/contracts/AG99")).status_code == 404
    await c.aclose()
    e = await client_for("arjun@purser.demo")
    assert (await e.get("/api/contracts/AG1")).status_code == 403
    assert (await e.get("/api/contracts/liabilities")).status_code == 403
    assert (await e.get("/api/contracts/deadlines")).status_code == 403
    await e.aclose()


async def test_http_unauthenticated_rejected(seeded):
    import httpx

    from app.main import app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000") as c:
        assert (await c.get("/api/contracts/AG1")).status_code == 401


async def test_http_liabilities_bearer_filter(seeded):
    c = await client_for()
    r = await c.get("/api/contracts/liabilities", params={"bearer": "us"})
    assert r.status_code == 200
    rows = r.json()["rows"]
    assert rows and all(x["bearer"] == "us" for x in rows)
    r2 = await c.get("/api/contracts/liabilities", params={"bearer": "counterparty"})
    assert all(x["bearer"] == "counterparty" for x in r2.json()["rows"])
    r3 = await c.get("/api/contracts/liabilities", params={"undecided_only": "true", "contract": "AG1"})
    assert {x["contract"] for x in r3.json()["rows"]} == {"AG1"}
    await c.aclose()


async def test_http_deadlines(seeded):
    c = await client_for()
    rows = (await c.get("/api/contracts/deadlines", params={"days": 400})).json()["rows"]
    assert rows and [r["due_on"] for r in rows] == sorted(r["due_on"] for r in rows)
    assert all(r["days_left"] >= 0 for r in rows)
    await c.aclose()


async def test_http_finding_context_marks_span_inside_excerpt(seeded):
    c = await client_for()
    async with db.session_scope() as s:
        fs = (await s.execute(select(ContractFinding).where(ContractFinding.clause_type == "limitation_of_liability",
                                                             ContractFinding.cap_paise.is_not(None)))).scalars().all()
        fid = fs[0].id
    r = await c.get(f"/api/contracts/findings/{fid}/context")
    assert r.status_code == 200, r.text
    j = r.json()
    marks = j["marks"]
    f_mark = next(m for m in marks if m["kind"] == "finding")
    assert 0 <= f_mark["start"] < f_mark["stop"] <= len(j["excerpt"])
    assert "aggregate liability" in j["excerpt"][f_mark["start"]: f_mark["stop"]]
    for m in marks:
        assert 0 <= m["start"] < m["stop"] <= len(j["excerpt"])
    assert any(m["kind"] == "carve_out" for m in marks)
    co = next(m for m in marks if m["kind"] == "carve_out")
    assert "shall not apply" in j["excerpt"][co["start"]: co["stop"]]
    assert (await c.get("/api/contracts/findings/999999/context")).status_code == 404
    await c.aclose()


async def test_http_injection_in_path_and_params(seeded):
    c = await client_for()
    r = await c.get("/api/contracts/x' OR 1=1 --")
    assert r.status_code == 404
    r = await c.get("/api/contracts/liabilities", params={"counterparty": "x' OR 1=1 --", "contract": "AG1"})
    assert r.status_code == 200 and r.json()["rows"] == []
    await c.aclose()


async def test_http_review_view_pending_and_staged(seeded):
    admin = await make_actor(seeded, "priya")
    doc_id = await stage_document(admin, sha="f" * 64)
    c = await client_for()
    r = await c.get(f"/api/contracts/review/{doc_id}")
    assert r.status_code == 200, r.text
    assert r.json()["pending"] is False
    await c.aclose()
