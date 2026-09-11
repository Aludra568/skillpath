from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Конфигурация приложения. Значения читаются из переменных окружения или .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SkillPath — Performance Review"
    secret_key: str = "dev-secret-change-me"
    access_token_ttl_minutes: int = 60 * 12

    data_dir: Path = BASE_DIR / "data"
    database_url: str = ""
    static_dir: Path = BASE_DIR / "frontend" / "dist"

    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{(self.data_dir / 'skillpath.db').as_posix()}"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings
