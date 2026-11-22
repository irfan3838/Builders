from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    log_level: str = "info"
    app_origin: str = "http://localhost:8000"
    session_secret: str = "dev-only-change-me"

    database_url: str = "postgresql+asyncpg://munshi:munshi-local-only@localhost:5433/munshi"
    test_database_url: str = "postgresql+asyncpg://munshi:munshi-local-only@localhost:5433/munshi_test"

    openai_model_fast: str = "gpt-5.4-mini"
    openai_model_strong: str = ""
    openai_model_voice: str = "gpt-live-1.1"
    openai_voice_name: str = "marin"
    openai_voice_speed: float = 1.15  # 0.25-1.5; dropped automatically if the live endpoint rejects it
    openai_model_extract: str = ""
    openai_model_transcribe: str = "gpt-transcribe"
    # Workflow engine (docs: app/agent/workflows/README.md). Off = the single Purser agent loop, unchanged.
    purser_workflows: bool = False
    openai_model_workflow: str = ""  # cheap tier for the picker and workflow runs; default = OPENAI_MODEL_FAST
    openai_model_escalation: str = "gpt-6-sol"  # stronger model for unknown cases and failed checklists

    upload_max_bytes: int = 10 * 1024 * 1024
    upload_max_pages: int = 5
    # Contracts are longer than bills: their own limits. "Us" in a contract: these names plus the workspace name.
    contract_max_pages: int = 15
    contract_max_bytes: int = 25 * 1024 * 1024
    our_party_names: str = "Dzruptiv AI,Dzruptiv,Druptiv,Dzruptive"
    storage_backend: str = "local"  # local | s3
    storage_local_dir: str = ".uploads"
    s3_bucket: str = ""
    aws_region: str = "us-west-2"

    proposal_ttl_seconds: int = 600

    # email (Gmail SMTP with an app password). Real email only to allow-listed demo addresses.
    gmail_address: str = ""
    gmail_app_password: str = ""
    email_allowed_recipients: str = ""
    # Standard email signature. Company defaults to the workspace name; phone/website lines are added when set.
    signature_company: str = ""
    signature_phone: str = ""
    signature_website: str = ""
    # Google Calendar (one organizer account, OAuth refresh token from scripts/google_oauth.py). Creates events with a
    # Meet link; Google emails the invites. Unset (or the Terraform placeholder) = meetings are recorded without a link.
    google_client_id: str = ""
    google_client_secret: str = ""
    google_refresh_token: str = ""
    calendar_timezone: str = "Asia/Kolkata"
    # The ONE Purser login whose real Gmail + Calendar the refresh token above belongs to. Everyone else uses demo data.
    google_linked_email: str = ""
    # Flight search (SerpAPI Google Flights). Unset = flight search falls back to a labelled sample list.
    serpapi_api_key: str = ""
    # Revenue FX: "ecb" fetches Frankfurter (ECB reference rates); "fixture" uses fixed quotes (tests, offline demo).
    fx_provider: str = "ecb"

    @field_validator("gmail_address", "gmail_app_password", "email_allowed_recipients", "google_client_id",
                     "google_client_secret", "google_refresh_token", "google_linked_email", "serpapi_api_key", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v

    @property
    def flights_enabled(self) -> bool:
        return bool(self.serpapi_api_key) and self.serpapi_api_key != "replace-me"

    @property
    def email_allowlist(self) -> set[str]:
        return {e.strip().lower() for e in self.email_allowed_recipients.split(",") if e.strip()}

    @property
    def email_enabled(self) -> bool:
        return bool(self.gmail_address and self.gmail_app_password)

    @property
    def calendar_enabled(self) -> bool:
        vals = (self.google_client_id, self.google_client_secret, self.google_refresh_token)
        return all(v and v != "replace-me" for v in vals)

    @property
    def ai_enabled(self) -> bool:
        """No-key mode when False: the app boots and every screen works; agent and voice turns explain how to enable AI."""
        import os

        key = os.getenv("OPENAI_API_KEY", "").strip()
        return bool(key) and key != "replace-me"

    @property
    def agent_model(self) -> str:
        return self.openai_model_strong or self.openai_model_fast

    @property
    def workflow_model(self) -> str:
        return self.openai_model_workflow or self.openai_model_fast

    @property
    def extract_model(self) -> str:
        return self.openai_model_extract or self.agent_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
