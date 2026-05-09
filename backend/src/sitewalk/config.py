from collections.abc import Mapping
from functools import cache
from importlib.metadata import version as distribution_version

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from sitewalk.providers.gemini_robotics_er_config import (
    DEFAULT_GEMINI_OBJECT_DETECTION_MODEL,
    DEFAULT_GEMINI_ROBOTICS_ER_MODEL,
    DEFAULT_GEMINI_ROBOTICS_ER_TIMEOUT_MILLISECONDS,
    GEMINI_API_KEY_ENV,
    GEMINI_OBJECT_DETECTION_MODEL_ENV,
    GEMINI_ROBOTICS_ER_MODEL_ENV,
    GEMINI_ROBOTICS_ER_THINKING_BUDGET_ENV,
    GEMINI_ROBOTICS_ER_TIMEOUT_MILLISECONDS_ENV,
    GEMINI_SEMANTIC_STATUS_MODEL_ENV,
)


class Settings(BaseSettings):
    """Runtime settings for the RobotOps Sentinel backend."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
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
    gemini_object_detection_model: str = Field(
        default=DEFAULT_GEMINI_OBJECT_DETECTION_MODEL,
        validation_alias=AliasChoices(
            GEMINI_OBJECT_DETECTION_MODEL_ENV,
            "SITEWALK_GEMINI_OBJECT_DETECTION_MODEL",
        ),
    )
    gemini_semantic_status_model: str = Field(
        default=DEFAULT_GEMINI_ROBOTICS_ER_MODEL,
        validation_alias=AliasChoices(
            GEMINI_SEMANTIC_STATUS_MODEL_ENV,
            "SITEWALK_GEMINI_SEMANTIC_STATUS_MODEL",
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
    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "SITEWALK_OPENAI_API_KEY"),
    )
    openai_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_MODEL", "SITEWALK_OPENAI_MODEL"),
    )
    encord_ssh_key_file: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "ENCORD_SSH_KEY_FILE",
            "SITEWALK_ENCORD_SSH_KEY_FILE",
        ),
    )
    encord_project_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ENCORD_PROJECT_ID", "SITEWALK_ENCORD_PROJECT_ID"),
    )
    encord_dataset_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ENCORD_DATASET_ID", "SITEWALK_ENCORD_DATASET_ID"),
    )
    encord_storage_folder: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "ENCORD_STORAGE_FOLDER",
            "SITEWALK_ENCORD_STORAGE_FOLDER",
        ),
    )
    encord_domain: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ENCORD_DOMAIN", "SITEWALK_ENCORD_DOMAIN"),
    )
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
            "http://127.0.0.1:5177",
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:5177",
        ],
    )
    cors_origin_regex: str = r"^(https?://(127\.0\.0\.1|localhost)(:\d+)?|https://.*\.trycloudflare\.com)$"


@cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


def build_provider_env(settings: Settings) -> Mapping[str, str]:
    """Return provider-oriented environment values from resolved settings."""
    env: dict[str, str] = {}

    for key, value in (
        ("OPENAI_API_KEY", settings.openai_api_key),
        ("OPENAI_MODEL", settings.openai_model),
        ("ENCORD_SSH_KEY_FILE", settings.encord_ssh_key_file),
        ("ENCORD_PROJECT_ID", settings.encord_project_id),
        ("ENCORD_DATASET_ID", settings.encord_dataset_id),
        ("ENCORD_STORAGE_FOLDER", settings.encord_storage_folder),
        ("ENCORD_DOMAIN", settings.encord_domain),
        ("GEMINI_API_KEY", settings.gemini_api_key),
        ("GEMINI_ROBOTICS_ER_MODEL", settings.gemini_robotics_er_model),
        ("GEMINI_OBJECT_DETECTION_MODEL", settings.gemini_object_detection_model),
        ("GEMINI_SEMANTIC_STATUS_MODEL", settings.gemini_semantic_status_model),
        (
            "GEMINI_ROBOTICS_ER_THINKING_BUDGET",
            str(settings.gemini_robotics_er_thinking_budget),
        ),
        (
            "GEMINI_ROBOTICS_ER_TIMEOUT_MILLISECONDS",
            str(settings.gemini_robotics_er_timeout_milliseconds),
        ),
    ):
        if value is not None and value != "":
            env[key] = value

    return env
