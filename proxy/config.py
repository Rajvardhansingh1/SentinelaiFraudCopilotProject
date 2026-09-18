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

    env: str = "development"
    # Comma-separated origins allowed to call this proxy from a browser (D-034: CORS
    # matters once a separately-hosted frontend, e.g. React, is a different origin).
    allowed_origins: str = "http://localhost:3000,http://localhost:8501"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
