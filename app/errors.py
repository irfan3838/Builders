"""Typed domain errors. Tools turn these into structured results the agent can explain."""

from typing import Any


class DomainError(Exception):
    def __init__(self, code: str, message: str, **details: Any):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def as_dict(self) -> dict[str, Any]:
        return {"ok": False, "code": self.code, "message": self.message, **self.details}


# Codes used across services (kept as constants so tests and prompts agree).
NOT_FOUND = "NOT_FOUND"
FORBIDDEN = "FORBIDDEN"
INVALID_STATE = "INVALID_STATE"
SELF_APPROVAL = "SELF_APPROVAL"
ALREADY_SETTLED = "ALREADY_SETTLED"
STALE_PROPOSAL = "STALE_PROPOSAL"
PROPOSAL_CLOSED = "PROPOSAL_CLOSED"
PROPOSAL_EXPIRED = "PROPOSAL_EXPIRED"
CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
AMBIGUOUS = "AMBIGUOUS"
DUPLICATE = "DUPLICATE"
UNSUPPORTED = "UNSUPPORTED"
VALIDATION = "VALIDATION"
