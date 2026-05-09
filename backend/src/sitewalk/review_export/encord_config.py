from collections.abc import Mapping
from dataclasses import dataclass

ENCORD_API_KEY_ENV = "ENCORD_API_KEY"
ENCORD_PROJECT_ID_ENV = "ENCORD_PROJECT_ID"


@dataclass(frozen=True)
class EncordConfig:
    """Normalized Encord export configuration."""

    api_key: str | None
    project_id: str | None


def build_encord_config_from_env(*, env: Mapping[str, str]) -> EncordConfig:
    """Build normalized Encord config from environment values."""
    return EncordConfig(
        api_key=_normalized_config_value(env.get(ENCORD_API_KEY_ENV)),
        project_id=_normalized_config_value(env.get(ENCORD_PROJECT_ID_ENV)),
    )


def normalize_encord_project_id(project_id: str | None) -> str | None:
    """Normalize an Encord project identifier for export requests."""
    return _normalized_config_value(project_id)


def is_encord_configured(*, config: EncordConfig) -> bool:
    """Return whether Encord has the minimum export configuration."""
    return config.api_key is not None and config.project_id is not None


def _normalized_config_value(value: str | None) -> str | None:
    if value is None:
        return None

    stripped_value = value.strip()
    if stripped_value == "":
        return None

    return stripped_value
