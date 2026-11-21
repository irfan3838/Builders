"""Exchange rates from Frankfurter (ECB reference rates, published once a working day ~16:00 CET).

Ported from copilot services/fx.py, split in two for async Purser:
- `refresh(s, currencies)` (async) fetches the latest quote with a 6 s timeout and caches it in `fx_quotes`.
  Callers run it *before* entering the sync revenue services, so a slow network never blocks the event loop.
- `latest(ss, currency)` (sync) reads the newest cached quote. It is flagged stale when the last refresh
  failed or is older than a day; with nothing cached the caller must give a manual rate.

FX_PROVIDER=fixture swaps the network for fixed quotes (tests and the offline demo). Rates are Decimal
strings turned into integer micro-rupees: never a float.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import FxQuote
from app.services.revenue.money import CURRENCIES, INR, MANUAL_ONLY, MICRO, to_rate_micro

log = logging.getLogger(__name__)

BASE_URL = "https://api.frankfurter.dev/v1"
TIMEOUT_S = 6.0
FRESH_FOR = timedelta(hours=6)  # don't refetch a quote fetched this recently
STALE_AFTER = timedelta(days=1)

# Deterministic quotes for FX_PROVIDER=fixture (synthetic, labelled as such wherever shown).
FIXTURE = {"USD": Decimal("84.1000"), "EUR": Decimal("90.5000"), "GBP": Decimal("106.2000"), "SGD": Decimal("63.4000")}


@dataclass(frozen=True)
class Rate:
    currency: str
    rate_micro: int
    rate_date: date | None  # ECB publication date; None for INR
    source: str  # "ecb" | "inr"
    stale: bool = False


class RateUnavailable(Exception):
    """No live rate and none cached: enter the rate by hand."""


async def _frankfurter(client: httpx.AsyncClient, currency: str) -> tuple[Decimal, date]:
    r = await client.get(f"{BASE_URL}/latest", params={"base": currency, "symbols": INR})
    r.raise_for_status()
    body = r.json(parse_float=Decimal)
    rate = (body.get("rates") or {}).get(INR) if isinstance(body, dict) else None
    day = body.get("date") if isinstance(body, dict) else None
    if rate is None or not isinstance(day, str):
        raise ValueError("no INR rate in the answer")
    return Decimal(str(rate)), date.fromisoformat(day)


async def refresh(s: AsyncSession, currencies: set[str] | list[str], today: date | None = None) -> dict[str, str]:
    """Fetch and cache the latest quote for each foreign ECB currency. Returns {currency: 'fresh'|'cached'|'failed'}.
    Never raises: a failed fetch leaves the cache as it is (latest() will flag it stale)."""
    want = sorted({c for c in currencies if c and c != INR and c in CURRENCIES and c not in MANUAL_ONLY})
    out: dict[str, str] = {}
    if not want:
        return out
    now = datetime.now(UTC)
    provider = get_settings().fx_provider
    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        for ccy in want:
            row = (await s.execute(select(FxQuote).where(FxQuote.currency == ccy).order_by(FxQuote.fetched_at.desc()).limit(1))).scalars().first()
            if row is not None and now - row.fetched_at < FRESH_FOR:
                out[ccy] = "cached"
                continue
            try:
                if provider == "fixture":
                    if ccy not in FIXTURE:
                        raise ValueError("no fixture quote")
                    value, day = FIXTURE[ccy], today or now.date()
                else:
                    value, day = await _frankfurter(client, ccy)
                micro = to_rate_micro(value)
            except (httpx.HTTPError, ValueError, KeyError) as e:
                log.warning("fx refresh failed for %s: %s", ccy, type(e).__name__)
                out[ccy] = "failed"
                continue
            same = (await s.execute(select(FxQuote).where(FxQuote.currency == ccy, FxQuote.rate_date == day))).scalars().first()
            if same is None:
                s.add(FxQuote(currency=ccy, rate_date=day, rate_micro=micro, fetched_at=now))
            else:
                same.rate_micro, same.fetched_at = micro, now
            await s.flush()
            out[ccy] = "fresh"
    return out


def _newest(ss: Session, currency: str) -> FxQuote | None:
    return ss.scalars(select(FxQuote).where(FxQuote.currency == currency).order_by(FxQuote.rate_date.desc()).limit(1)).first()


def latest(ss: Session, currency: str) -> Rate:
    if currency == INR:
        return Rate(INR, MICRO, None, "inr")
    if currency not in CURRENCIES or currency in MANUAL_ONLY:
        raise RateUnavailable(f"The ECB has no {currency} rate: tell me the rate.")
    row = _newest(ss, currency)
    if row is None:
        raise RateUnavailable(f"I couldn't get the {currency} rate right now: tell me the rate.")
    stale = datetime.now(UTC) - row.fetched_at > STALE_AFTER
    return Rate(currency, row.rate_micro, row.rate_date, "ecb", stale=stale)


def cached(ss: Session, currency: str) -> int | None:
    """Newest cached rate (no network): for the 'rate moved' suggestion."""
    if currency == INR:
        return MICRO
    row = _newest(ss, currency)
    return row.rate_micro if row else None
