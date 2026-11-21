from __future__ import annotations

import functools
import inspect
import logging
import time
from dataclasses import dataclass, field

from app.actor import Actor
from app.errors import DomainError

log = logging.getLogger("munshi.tools")


@dataclass
class MunshiContext:
    """Passed to every tool via RunContextWrapper. Identity comes only from here, never from model args."""

    actor: Actor
    channel: str = "text"  # text | live | realtime | ptt
    ui: list[dict] = field(default_factory=list)  # cards for the client, in order
    tool_log: list[dict] = field(default_factory=list)

    def show(self, card: dict) -> None:
        self.ui.append(card)


def safe_tool(fn):
    """Convert DomainError into a structured result the agent can explain; log name, latency, outcome."""

    @functools.wraps(fn)
    async def wrapper(ctx, *args, **kwargs):
        t0 = time.perf_counter()
        outcome = "ok"
        try:
            result = await fn(ctx, *args, **kwargs)
            if isinstance(result, dict) and result.get("ok") is False:
                outcome = result.get("code", "error")
            return result
        except DomainError as e:
            outcome = e.code
            return e.as_dict()
        finally:
            entry = {"tool": fn.__name__, "outcome": outcome, "ms": int((time.perf_counter() - t0) * 1000)}
            ctx.context.tool_log.append(entry)
            log.info("tool %s", entry)

    wrapper.__signature__ = inspect.signature(fn)
    return wrapper
