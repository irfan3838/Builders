from functools import lru_cache

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
    openai_model_extract: str = ""
    openai_model_transcribe: str = "gpt-transcribe"

    upload_max_bytes: int = 10 * 1024 * 1024
    upload_max_pages: int = 5
    storage_backend: str = "local"  # local | s3
    storage_local_dir: str = ".uploads"
    s3_bucket: str = ""
    aws_region: str = "us-west-2"

    proposal_ttl_seconds: int = 600

    @property
    def agent_model(self) -> str:
        return self.openai_model_strong or self.openai_model_fast

    @property
    def extract_model(self) -> str:
        return self.openai_model_extract or self.agent_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
