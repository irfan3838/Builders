"""HTTP layer + intake gates that need no model: auth, CSRF, upload outcomes, exact replay, contract close."""

import io

import httpx
import pytest
from pypdf import PdfWriter

from app import db
from app.errors import DomainError
from app.main import app
from app.services import intake, proposals, records
from tests.conftest import add_inspected_document, make_actor

ORIGIN = "http://localhost:8000"
PNG = open("evals/dev/dev_hotel_receipt_synthetic.png", "rb").read()


async def client_for(email="priya@munshi.demo"):
    c = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN, headers={"origin": ORIGIN})
    r = await c.post("/api/auth/login", json={"email": email, "password": "munshi-demo"})
    assert r.status_code == 200, r.text
    c.headers["x-csrf-token"] = r.json()["csrf"]
    conv = (await c.post("/api/conversations")).json()["conversation_id"]
    c.headers["x-conversation-id"] = conv
    return c


def _pdf(encrypted=False, pages=1) -> bytes:
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(200, 200)
    if encrypted:
        w.encrypt("secret")
    b = io.BytesIO()
    w.write(b)
    return b.getvalue()


async def test_login_rejects_bad_password(seeded):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN) as c:
        r = await c.post("/api/auth/login", json={"email": "priya@munshi.demo", "password": "wrong"})
    assert r.status_code == 401


async def test_write_requires_csrf(seeded):
    c = await client_for()
    del c.headers["x-csrf-token"]
    r = await c.post("/api/documents", files={"file": ("r.png", PNG, "image/png")})
    assert r.status_code == 403
    await c.aclose()


async def test_unauthenticated_is_rejected(seeded):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN) as c:
        assert (await c.get("/api/me")).status_code == 401


@pytest.mark.parametrize("name,data,outcome", [
    ("notes.txt", b"hello this is not a receipt", "unsupported"),
    ("locked.pdf", None, "encrypted"),
    ("long.pdf", None, "too_many_pages"),
])
async def test_upload_explicit_outcomes(seeded, name, data, outcome):
    if name == "locked.pdf":
        data = _pdf(encrypted=True)
    if name == "long.pdf":
        data = _pdf(pages=6)
    c = await client_for()
    r = (await c.post("/api/documents", files={"file": (name, data, "application/octet-stream")})).json()
    assert r["outcome"] == outcome and r["document_id"] is None and r["message"]
    await c.aclose()


async def test_exact_replay_returns_existing_document(seeded):
    c = await client_for()
    a = (await c.post("/api/documents", files={"file": ("r.png", PNG, "image/png")})).json()
    b = (await c.post("/api/documents", files={"file": ("again.png", PNG, "image/png")})).json()
    assert a["outcome"] == "accepted" and b["outcome"] == "exact_replay" and b["document_id"] == a["document_id"]
    page = await c.get(f"/api/documents/{a['document_id']}/pages/1")
    assert page.status_code == 200 and page.headers["content-type"] == "image/png"
    await c.aclose()


async def test_employee_cannot_open_other_users_document(seeded):
    priya = await client_for()
    doc = (await priya.post("/api/documents", files={"file": ("r.png", PNG, "image/png")})).json()["document_id"]
    arjun = await client_for("arjun@munshi.demo")
    assert (await arjun.get(f"/api/documents/{doc}/pages/1")).status_code == 404
    await priya.aclose()
    await arjun.aclose()


async def test_contract_closes_without_finance_write(seeded):
    from sqlalchemy import func, select

    from app.models import Bill, BudgetMovement, Claim
    priya = await make_actor(seeded)
    doc = await add_inspected_document(priya, vendor="Acme Traders", total_rupees=500000, doc_type="contract")
    async with db.session_scope() as s:
        before = [(await s.execute(select(func.count()).select_from(m))).scalar_one() for m in (Bill, Claim, BudgetMovement)]
        d = await records.document(s, priya, doc, for_update=True)
        await intake.close(s, priya, d, "contract_out_of_scope", "MSA; contract review not in weekend release")
    async with db.session_scope() as s:
        after = [(await s.execute(select(func.count()).select_from(m))).scalar_one() for m in (Bill, Claim, BudgetMovement)]
        assert (await records.document(s, priya, doc)).outcome == "contract_out_of_scope"
    assert before == after
    with pytest.raises(DomainError):
        async with db.session_scope() as s:
            await proposals.create(s, priya, "submit_bill", {"document_id": doc, "category": "Events", "new_vendor_name": "Acme"})


@pytest.mark.parametrize("fields,expected", [
    ({"total_paise": 480000, "subtotal_paise": 428571, "taxes": [{"amount_paise": 25714}, {"amount_paise": 25715}]}, "ok"),
    ({"total_paise": 500000, "subtotal_paise": 428571, "taxes": [{"amount_paise": 25714}, {"amount_paise": 25715}]}, "mismatch"),
    ({"total_paise": 480000}, "unverifiable"),
    ({"total_paise": 30000, "line_items": [{"amount_paise": 10000}, {"amount_paise": 20000}]}, "ok"),
])
def test_arithmetic_check(fields, expected):
    assert intake.check_arithmetic(fields) == expected


async def test_button_confirm_and_replay(seeded):
    c = await client_for()
    conv = c.headers["x-conversation-id"]
    from app.actor import Actor
    priya = await make_actor(seeded)
    priya = Actor(priya.user_id, priya.workspace_id, priya.role, priya.party_id, priya.display_name, conv)
    doc = await add_inspected_document(priya)
    async with db.session_scope() as s:
        p = await proposals.create(s, priya, "submit_claim", {"document_id": doc, "beneficiary_party_id": seeded["arjun_party_id"],
                                                             "category": "Travel", "reservation_id": seeded["reservation_id"],
                                                             "reservation_treatment": "final"})
    r1 = (await c.post(f"/api/proposals/{p.id}/confirm")).json()
    r2 = (await c.post(f"/api/proposals/{p.id}/confirm")).json()
    assert r1["status"] == "executed" and r2["status"] == "replayed" and r1["receipt"]["ref"] == r2["receipt"]["ref"]
    arjun = await client_for("arjun@munshi.demo")
    assert (await arjun.post(f"/api/proposals/{p.id}/confirm")).status_code == 404  # another actor's proposal
    await c.aclose()
    await arjun.aclose()
