from dataclasses import dataclass

FINANCE_APPROVER = "finance_approver"
EMPLOYEE = "employee"


@dataclass(frozen=True)
class Actor:
    """The authenticated principal. Always derived from the server session, never from model output."""

    user_id: int
    workspace_id: int
    role: str
    party_id: int | None
    display_name: str
    conversation_id: str | None = None

    @property
    def is_approver(self) -> bool:
        return self.role == FINANCE_APPROVER
