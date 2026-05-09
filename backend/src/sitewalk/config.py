from functools import cache
from importlib.metadata import version as distribution_version

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from sitewalk.providers.gemini_robotics_er_config import (
    DEFAULT_GEMINI_ROBOTICS_ER_MODEL,
    DEFAULT_GEMINI_ROBOTICS_ER_TIMEOUT_MILLISECONDS,
    GEMINI_API_KEY_ENV,
    GEMINI_ROBOTICS_ER_MODEL_ENV,
    GEMINI_ROBOTICS_ER_THINKING_BUDGET_ENV,
    GEMINI_ROBOTICS_ER_TIMEOUT_MILLISECONDS_ENV,
)


class Settings(BaseSettings):
    """Runtime settings for the RobotOps Sentinel backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SITEWALK_",
        extra="ignore",
    )

    service_name: str = "sitewalk-sentinel-api"
    version: str = Field(default_factory=lambda: distribution_version("sitewalk"))
    gemini_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(GEMINI_API_KEY_ENV, "SITEWALK_GEMINI_API_KEY"),
    )
    gemini_robotics_er_model: str = Field(
        default=DEFAULT_GEMINI_ROBOTICS_ER_MODEL,
        validation_alias=AliasChoices(
            GEMINI_ROBOTICS_ER_MODEL_ENV,
            "SITEWALK_GEMINI_ROBOTICS_ER_MODEL",
        ),
    )
    gemini_robotics_er_thinking_budget: int = Field(
        default=0,
        ge=0,
        validation_alias=AliasChoices(
            GEMINI_ROBOTICS_ER_THINKING_BUDGET_ENV,
            "SITEWALK_GEMINI_ROBOTICS_ER_THINKING_BUDGET",
        ),
    )
    gemini_robotics_er_timeout_milliseconds: int = Field(
        default=DEFAULT_GEMINI_ROBOTICS_ER_TIMEOUT_MILLISECONDS,
        gt=0,
        validation_alias=AliasChoices(
            GEMINI_ROBOTICS_ER_TIMEOUT_MILLISECONDS_ENV,
            "SITEWALK_GEMINI_ROBOTICS_ER_TIMEOUT_MILLISECONDS",
        ),
    )
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
