from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    groq_api_key: str = ""
    gemini_api_key: str = ""

    sentinelai_host: str = "0.0.0.0"
    sentinelai_port: int = 8000
    agents_api_port: int = 8001
    rate_limit_per_session: int = 8

    database_url: str = "sqlite:///./data/logs.db"
    chroma_persist_dir: str = "./data/chroma"
    agent_profiles_path: str = str(Path(__file__).parent / "agent_profiles.yaml")

    # Security event monitoring (D-050).
    events_enabled: bool = True
    events_retention_days: int = 30
    events_min_severity: Literal["info", "low", "medium", "high", "critical"] = "info"

    # Runtime Gateway (D-049) — separate service, server-side policy only.
    gateway_port: int = 8002
    gateway_block_on_injection: bool = True
    gateway_request_pii_action: Literal["allow", "redact", "block"] = "redact"
    gateway_response_pii_action: Literal["allow", "redact", "block"] = "redact"
    gateway_store_raw_content: bool = False
    # Off by default so the gateway stays stateless (D-049); on = metadata-only SecurityEvent rows.
    gateway_record_events: bool = False

    env: str = "development"
    # Comma-separated origins allowed to call this proxy from a browser (D-034: CORS
    # matters once a separately-hosted frontend, e.g. React, is a different origin).
    allowed_origins: str = "http://localhost:3000,http://localhost:8501"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
