from dataclasses import dataclass

FINANCE_APPROVER = "finance_approver"
ADMIN = "admin"  # finance approver + HR/admin
HR_ADMIN = "hr_admin"
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
        """Finance approval rights."""
        return self.role in (FINANCE_APPROVER, ADMIN)

    @property
    def is_hr(self) -> bool:
        """HR/admin rights: onboarding, company-wide announcements, all leave."""
        return self.role in (ADMIN, HR_ADMIN)
