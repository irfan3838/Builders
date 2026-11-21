"""Cookie session auth + CSRF. The Actor is derived from the server session on every request."""

from __future__ import annotations

import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, Request, Response
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy import select

from app import db
from app.actor import Actor
from app.config import get_settings
from app.models import Conversation, User

COOKIE = "purser_session"
MAX_AGE = 12 * 3600
_ph = PasswordHasher()


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().session_secret, salt="purser-session")


async def login(response: Response, email: str, password: str) -> dict:
    async with db.session_scope() as s:
        u = (await s.execute(select(User).where(User.email == email.strip().lower()))).scalars().first()
        try:
            if u is None or u.status == "disabled":  # disabled logins cannot sign in (same message: no account probing)
                raise VerifyMismatchError
            _ph.verify(u.password_hash, password)
        except VerifyMismatchError:
            raise HTTPException(401, "Invalid email or password") from None
    csrf = secrets.token_urlsafe(24)
    token = _serializer().dumps({"uid": u.id, "csrf": csrf})
    secure = get_settings().app_origin.startswith("https://")
    response.set_cookie(COOKIE, token, max_age=MAX_AGE, httponly=True, secure=secure, samesite="strict", path="/")
    return {"user": {"id": u.id, "name": u.display_name, "role": u.role}, "csrf": csrf}


def _session(request: Request) -> dict:
    raw = request.cookies.get(COOKIE)
    if not raw:
        raise HTTPException(401, "Not signed in")
    try:
        return _serializer().loads(raw, max_age=MAX_AGE)
    except BadSignature:
        raise HTTPException(401, "Session expired") from None


def check_write(request: Request, sess: dict) -> None:
    """Origin + CSRF header on every state-changing browser request."""
    origin = request.headers.get("origin")
    if origin and origin != get_settings().app_origin:
        raise HTTPException(403, "Unexpected origin")
    if request.headers.get("x-csrf-token") != sess.get("csrf"):
        raise HTTPException(403, "CSRF check failed")


async def _actor(request: Request, sess: dict) -> Actor:
    async with db.session_scope() as s:
        u = await s.get(User, sess["uid"])
        if u is None or u.status == "disabled":  # a disabled login is signed out on its next request
            raise HTTPException(401, "Unknown user")
        conv_id = request.headers.get("x-conversation-id") or (
            request.query_params.get("conversation_id") if request.method == "GET" else None)
        if conv_id:
            c = await s.get(Conversation, conv_id)
            if c is None or c.user_id != u.id or c.workspace_id != u.workspace_id:
                raise HTTPException(404, "Conversation not found")
        return Actor(u.id, u.workspace_id, u.role, u.party_id, u.display_name, conv_id, email=u.email)


async def current_actor(request: Request) -> Actor:
    sess = _session(request)
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        check_write(request, sess)
    return await _actor(request, sess)


async def current_csrf(request: Request) -> str:
    return _session(request)["csrf"]


ActorDep = Depends(current_actor)
