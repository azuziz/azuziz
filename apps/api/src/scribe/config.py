from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

API_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings. Every value can be overridden with an environment variable of the same name."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"  # "production" makes missing secrets fatal
    database_url: str = f"sqlite:///{API_ROOT / 'data' / 'scribe.db'}"
    storage_dir: Path = API_ROOT / "data" / "audio"
    # Fernet key (base64). Generate with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    audio_encryption_key: str | None = None
    providers_file: Path = API_ROOT / "providers.toml"

    stt_provider: str = "fake"
    llm_model: str = "fake"
    llm_max_retries: int = 1

    cors_origins: str = "http://localhost:3000"
    max_upload_mb: int = 100

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
