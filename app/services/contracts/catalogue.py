"""The shipped clause catalogue: copilot `ctr_0001_contracts.py` CLAUSE_TYPES, unchanged (key, name, high risk,
standard explanation, patterns, attributes). Purser has no clause-type settings page, so it lives in code."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

CONTRACT_TYPES = {"nda": "NDA", "msa": "MSA", "sow": "SoW", "vendor": "Vendor agreement", "other": "Other"}

CLAUSE_TYPES: tuple[tuple[str, str, bool, str, list[str], list[str]], ...] = (
    (
        "unlimited_liability", "Unlimited liability", True,
        "Our liability is not capped: one claim could cost more than the contract is worth.",
        [r"unlimited liabilit", r"liabilit\w*\s+(shall|will)\s+not\s+be\s+(limited|capped)",
         r"without\s+(any\s+)?(limit|cap)\w*\s+(of|on|to)\s+(its\s+|our\s+)?liabilit",
         r"no\s+(limit|cap)\w*\s+(of|on)\s+liabilit"],
        [],
    ),
    (
        "broad_indemnity", "Broad indemnity", True,
        "We indemnify the client for a wide range of losses, possibly ones we did not cause.",
        [r"indemnif\w+.{0,120}(any and all|all claims|whatsoever|howsoever|regardless of)",
         r"hold\s+harmless"],
        [],
    ),
    (
        "data_liability", "Data loss liability", True,
        "We carry the risk of the client's data being lost, corrupted or breached.",
        [r"(loss|breach|corruption|destruction)\s+of\s+(any\s+)?(client\s+|customer\s+)?data",
         r"data\s+(loss|breach)"],
        [],
    ),
    (
        "unilateral_termination", "One-sided termination", True,
        "The client may end the contract at will, while we may not: our revenue can stop at short notice.",
        [r"terminat\w+.{0,80}(at any time|for convenience|without cause|at its sole discretion)"],
        [],
    ),
    (
        "auto_renewal", "Automatic renewal", False,
        "The contract renews by itself unless notice is given: the notice date must be tracked.",
        [r"automatic(ally)?\s+renew", r"auto-?renew"],
        [],
    ),
    (
        "ip_assignment", "IP assignment", True,
        "Our intellectual property (tools, code we reuse) may pass to the client.",
        [r"(assign|transfer)\w*\s.{0,60}(right|title|interest).{0,60}intellectual\s+property",
         r"work\s+made\s+for\s+hire"],
        [],
    ),
    (
        "limitation_of_liability", "Limitation of liability", False,
        "Caps each side's liability; check the cap and what it leaves out.",
        [r"limitation\s+of\s+liabilit", r"aggregate\s+liabilit\w*.{0,80}(shall\s+not|will\s+not)\s+exceed"],
        [],
    ),
    (
        "payment_terms", "Payment terms", False,
        "When the client pays us.",
        [r"\bnet\s+\d{1,3}\b", r"within\s+\d{1,3}\s+days\s+of\s+(the\s+)?(receipt|date|invoice)",
         r"payment\s+terms"],
        ["Net 15", "Net 30", "Net 45", "Net 60", "Net 90"],
    ),
    (
        "termination", "Termination", False,
        "How and when either side may end the contract.",
        [r"\bterminat(e|ion)\b.{0,60}\bnotice\b"],
        [],
    ),
    (
        "confidentiality", "Confidentiality", False,
        "What each side must keep confidential, and for how long.",
        [r"confidential\s+information", r"\bconfidentiality\b"],
        [],
    ),
    (
        "governing_law", "Governing law", False,
        "Which country's law applies and where disputes are heard.",
        [r"governing\s+law", r"governed\s+by\s+(and\s+construed\s+in\s+accordance\s+with\s+)?the\s+laws?\s+of"],
        [],
    ),
    (
        "service_levels", "Service levels", False,
        "Service levels we promise, and what missing one costs us.",
        [r"service\s+level", r"\bSLA\b", r"uptime"],
        [],
    ),
)

NAMES = {k: n for k, n, *_ in CLAUSE_TYPES}
HIGH_RISK = {k for k, _, hr, *_ in CLAUSE_TYPES if hr}

# Clause types whose wording creates or limits something we may owe: these get the liability pass.
LIABILITY_TYPES = {
    "unlimited_liability", "broad_indemnity", "data_liability", "limitation_of_liability", "auto_renewal",
    "termination", "unilateral_termination", "ip_assignment",
}


@dataclass(frozen=True)
class Rule:
    """A clause type as the scan sees it."""

    key: str
    name: str
    high_risk: bool
    explanation: str
    patterns: tuple[re.Pattern[str], ...]

    @classmethod
    def of(cls, key: str, name: str, high_risk: bool, explanation: str, patterns: Sequence[str]) -> Rule:
        compiled = []
        for p in patterns:
            try:
                compiled.append(re.compile(p, re.I | re.S))
            except re.error:
                continue
        return cls(key, name, high_risk, explanation, tuple(compiled))


def rules() -> list[Rule]:
    return [Rule.of(k, n, hr, ex, pats) for k, n, hr, ex, pats, _ in CLAUSE_TYPES]
