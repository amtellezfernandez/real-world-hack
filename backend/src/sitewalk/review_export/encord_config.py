from collections.abc import Mapping
from dataclasses import dataclass

ENCORD_DOMAIN_ENV = "ENCORD_DOMAIN"
ENCORD_DATASET_ID_ENV = "ENCORD_DATASET_ID"
ENCORD_PROJECT_ID_ENV = "ENCORD_PROJECT_ID"
ENCORD_SSH_KEY_FILE_ENV = "ENCORD_SSH_KEY_FILE"
ENCORD_STORAGE_FOLDER_ENV = "ENCORD_STORAGE_FOLDER"
DEFAULT_ENCORD_DOMAIN = "https://api.encord.com"
DEFAULT_ENCORD_STORAGE_FOLDER = "AIRW Hack Incidents"


@dataclass(frozen=True)
class EncordConfig:
    """Normalized Encord export configuration."""

    ssh_key_file: str | None
    project_id: str | None
    dataset_id: str | None
    storage_folder: str
    domain: str


def build_encord_config_from_env(*, env: Mapping[str, str]) -> EncordConfig:
    """Build normalized Encord config from environment values."""
    return EncordConfig(
        ssh_key_file=_normalized_config_value(env.get(ENCORD_SSH_KEY_FILE_ENV)),
        project_id=_normalized_config_value(env.get(ENCORD_PROJECT_ID_ENV)),
        dataset_id=_normalized_config_value(env.get(ENCORD_DATASET_ID_ENV)),
        storage_folder=(
            _normalized_config_value(env.get(ENCORD_STORAGE_FOLDER_ENV))
            or DEFAULT_ENCORD_STORAGE_FOLDER
        ),
        domain=(
            _normalized_config_value(env.get(ENCORD_DOMAIN_ENV))
            or DEFAULT_ENCORD_DOMAIN
        ),
    )


def normalize_encord_project_id(project_id: str | None) -> str | None:
    """Normalize an Encord project identifier for export requests."""
    return _normalized_config_value(project_id)


def is_encord_configured(*, config: EncordConfig) -> bool:
    """Return whether Encord has the minimum export configuration."""
    return config.ssh_key_file is not None and config.project_id is not None


def is_encord_dataset_configured(*, config: EncordConfig) -> bool:
    """Return whether Encord can receive incident frame uploads."""
    return is_encord_configured(config=config) and config.dataset_id is not None


def _normalized_config_value(value: str | None) -> str | None:
    if value is None:
        return None

    stripped_value = value.strip()
    if stripped_value == "":
        return None

    return stripped_value
