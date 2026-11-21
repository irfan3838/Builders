"""A workflow = one user action: a one-line trigger description, the few tools it may use, a checklist the small
model follows, and code-verified outcomes. The model never decides that a workflow is done; `verify` does."""

from __future__ import annotations

from dataclasses import dataclass, field

# Tools every workflow may use: tappable clarifying questions and next-step chips. Never confirm/cancel: only the
# engine confirms or cancels, and only from the user's own words.
COMMON_TOOLS = ("ask_choice",)
# Only the engine calls these: confirm/cancel from the user's own words, and next-step chips from the workflow's
# structured reply (saves one model round trip per answer).
ENGINE_ONLY = {"confirm_pending_proposal", "cancel_pending_proposal", "suggest_next_actions"}


@dataclass(frozen=True)
class Workflow:
    name: str
    module: str
    when: str  # one line for the picker menu: what the user says, and NOT-for counter-examples
    tools: tuple[str, ...]  # the only tools this workflow may call (plus COMMON_TOOLS)
    checklist: tuple[str, ...]  # ordered steps the small model follows
    # Verification: the workflow succeeded if any of these tools returned ok (or a proposal was created, or the user
    # was asked a question, or the action was refused by the server). Empty = any listed tool ok counts.
    required: tuple[str, ...] = ()
    roles: frozenset[str] | None = None  # None = any role the tools allow; the server enforces every rule anyway

    @property
    def all_tools(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(self.tools + COMMON_TOOLS))

    def menu_line(self) -> str:
        return f"- {self.name}: {self.when}"


# Server codes after which a plain spoken explanation IS the correct outcome (no retry, no escalation).
REFUSAL_CODES = {"FORBIDDEN", "SELF_APPROVAL", "ALREADY_SETTLED", "INVALID_STATE", "UNSUPPORTED", "DUPLICATE"}
# Codes after which asking the user is the correct next step (the workflow stays active for the answer).
ASK_CODES = {"AMBIGUOUS", "NOT_FOUND", "VALIDATION", "NO_LOCATION", "LIMIT_REACHED", "EXTRACTION_FAILED"}


@dataclass
class Outcome:
    status: str  # done | proposal | asked | refused | failed
    reason: str = ""
    tools_ok: list[str] = field(default_factory=list)


def verify(wf: Workflow, tool_log: list[dict], reply: str, ui: list[dict]) -> Outcome:
    """Code check of the checklist outcome from what actually happened (tool log, cards, reply)."""
    ok = [t["tool"] for t in tool_log if t["outcome"] == "ok"]
    if not reply.strip():
        return Outcome("failed", "empty reply: always end with the spoken answer in 'say'", ok)
    if not wf.tools:  # a reply-only workflow (general_reply): done when it said something
        return Outcome("done", tools_ok=ok)
    codes = {t["outcome"] for t in tool_log if t["outcome"] != "ok"}
    if any(t.startswith("propose_") for t in ok):
        return Outcome("proposal", tools_ok=ok)
    if "ask_choice" in ok:
        return Outcome("asked", tools_ok=ok)
    if codes & REFUSAL_CODES:
        return Outcome("refused", tools_ok=ok)
    wanted = set(wf.required or wf.tools)
    if wanted & set(ok):
        return Outcome("done", tools_ok=ok)
    asked = reply.rstrip().endswith(("?", "？")) or "?" in reply[-80:]
    if asked and (codes & ASK_CODES or not tool_log or set(ok) - set(COMMON_TOOLS)):
        return Outcome("asked", tools_ok=ok)
    if asked:
        return Outcome("asked", reason="asked without a tool result", tools_ok=ok)
    if not tool_log:
        return Outcome("failed", "answered without calling any of its tools", ok)
    return Outcome("failed", f"no required tool succeeded (outcomes: {sorted(codes) or 'none'})", ok)
