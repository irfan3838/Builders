"""OAuth refresh-token exchange for the linked Google account, with the access token cached until shortly before expiry."""

from __future__ import annotations

import asyncio
import time

import httpx

from app.config import get_settings

TOKEN_URL = "https://oauth2.googleapis.com/token"


class GoogleError(Exception):
    pass


_cache: dict[str, float | str] = {"token": "", "exp": 0.0}
_lock = asyncio.Lock()


async def access_token(client: httpx.AsyncClient | None = None) -> str:
    async with _lock:
        if _cache["token"] and time.time() < float(_cache["exp"]) - 60:
            return str(_cache["token"])
        st = get_settings()
        if not st.calendar_enabled:
            raise GoogleError("Google is not connected (run scripts/google_oauth.py).")
        own = client is None
        client = client or httpx.AsyncClient(timeout=15)
        try:
            r = await client.post(TOKEN_URL, data={"client_id": st.google_client_id, "client_secret": st.google_client_secret,
                                                   "refresh_token": st.google_refresh_token, "grant_type": "refresh_token"})
        finally:
            if own:
                await client.aclose()
        if r.status_code != 200:
            err = r.json().get("error", r.status_code) if r.headers.get("content-type", "").startswith("application/json") else r.status_code
            if err == "invalid_grant":
                raise GoogleError("Google login expired or was revoked; run scripts/google_oauth.py again.")
            raise GoogleError(f"Google token refresh failed ({err}).")
        body = r.json()
        _cache["token"], _cache["exp"] = body["access_token"], time.time() + float(body.get("expires_in", 3600))
        return str(_cache["token"])


def error_text(r: httpx.Response) -> str:
    try:
        return r.json()["error"]["message"][:200]
    except Exception:
        return r.text[:200]


async def call(method: str, url: str, *, params: dict | None = None, json: dict | None = None, timeout: float = 15) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as client:
        headers = {"Authorization": f"Bearer {await access_token(client)}"}
        r = await client.request(method, url, params=params, json=json, headers=headers)
    if r.status_code == 204:
        return {}
    if r.status_code >= 400:
        raise GoogleError(f"Google HTTP {r.status_code}: {error_text(r)}")
    return r.json()
