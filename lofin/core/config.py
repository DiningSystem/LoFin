from functools import lru_cache
from typing import Literal

from pydantic import Field, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["local", "test", "prod"] = "local"
    log_level: str = "INFO"
    database_url: str = "sqlite+aiosqlite:///./lofin.db"
    redis_url: RedisDsn | str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "lofin_discussions"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    ollama_embed_model: str = "nomic-embed-text"
    llm_timeout_seconds: float = 60.0
    reddit_client_id: str | None = None
    reddit_client_secret: str | None = None
    reddit_user_agent: str = "lofin-local/0.1"
    finnhub_api_key: str | None = None
    rss_feeds: list[str] = Field(default_factory=lambda: ["https://feeds.a.dj.com/rss/RSSMarketsMain.xml"])
    default_subreddits: list[str] = Field(default_factory=lambda: ["stocks", "investing", "wallstreetbets", "ETFs"])
    retention_days: int = 30
    delete_low_score_after_days: int = 7
    keep_high_signal_forever: bool = True
    high_signal_score: float = 0.75
    worker_poll_seconds: float = 5.0
    request_retry_attempts: int = 3

    @field_validator("rss_feeds", "default_subreddits", mode="before")
    @classmethod
    def split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
