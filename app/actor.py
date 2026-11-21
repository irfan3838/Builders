from dataclasses import dataclass

FINANCE_APPROVER = "finance_approver"
ADMIN = "admin"  # finance approver + HR/admin
HR_ADMIN = "hr_admin"
EMPLOYEE = "employee"
CEO = "ceo"  # read-only executive: sees every number, changes nothing


@dataclass(frozen=True)
class Actor:
    """The authenticated principal. Always derived from the server session, never from model output."""

    user_id: int
    workspace_id: int
    role: str
    party_id: int | None
    display_name: str
    conversation_id: str | None = None
    email: str = ""

    @property
    def is_approver(self) -> bool:
        """Finance approval rights."""
        return self.role in (FINANCE_APPROVER, ADMIN)

    @property
    def can_read_finance(self) -> bool:
        """May SEE budget, revenue, payables, receivables and company-wide records (not change them)."""
        return self.role in (FINANCE_APPROVER, ADMIN, CEO)

    @property
    def read_only(self) -> bool:
        """May not make any change at all (no proposals, no direct writes)."""
        return self.role == CEO

    @property
    def uses_google(self) -> bool:
        """The one login whose real Gmail and Google Calendar Purser may use (GOOGLE_LINKED_EMAIL)."""
        from app.config import get_settings
        linked = get_settings().google_linked_email.strip().lower()
        return bool(linked) and self.email.lower() == linked and get_settings().calendar_enabled

    @property
    def is_hr(self) -> bool:
        """HR/admin rights: onboarding, company-wide announcements, all leave."""
        return self.role in (ADMIN, HR_ADMIN)
