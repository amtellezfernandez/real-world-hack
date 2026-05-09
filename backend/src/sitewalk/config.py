from functools import cache
from importlib.metadata import version as distribution_version

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the RobotOps Sentinel backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SITEWALK_",
        extra="ignore",
    )

    service_name: str = "sitewalk-sentinel-api"
    version: str = Field(default_factory=lambda: distribution_version("sitewalk"))
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
    )


@cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
