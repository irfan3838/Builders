"""In-process event fan-out to the browser (SSE), keyed by conversation. One container in this release."""

from __future__ import annotations

import asyncio
import itertools
from collections import defaultdict

_subs: dict[str, set[asyncio.Queue]] = defaultdict(set)
_seq = itertools.count(1)


def publish(conversation_id: str, event: dict) -> None:
    ev = {"id": next(_seq), **event}
    for q in list(_subs.get(conversation_id, ())):
        if q.qsize() < 200:
            q.put_nowait(ev)


def subscribe(conversation_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _subs[conversation_id].add(q)
    return q


def unsubscribe(conversation_id: str, q: asyncio.Queue) -> None:
    _subs[conversation_id].discard(q)
    if not _subs[conversation_id]:
        _subs.pop(conversation_id, None)
