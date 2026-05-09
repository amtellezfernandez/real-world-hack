from collections.abc import Mapping

from sitewalk.contracts import (
    ProviderAvailability,
    ReviewExportProvider,
    ReviewExportProviderStatus,
)
from sitewalk.review_export.encord_config import (
    EncordConfig,
    build_encord_config_from_env,
    is_encord_configured,
)


def build_review_export_provider_statuses(
    *,
    env: Mapping[str, str],
) -> list[ReviewExportProviderStatus]:
    """Return review export status without importing provider SDKs."""
    encord_config = build_encord_config_from_env(env=env)

    return [
        ReviewExportProviderStatus(
            provider=ReviewExportProvider.LOCAL_REVIEW,
            availability=ProviderAvailability.AVAILABLE,
            detail="Local review queue is available.",
        ),
        ReviewExportProviderStatus(
            provider=ReviewExportProvider.ENCORD,
            availability=get_encord_availability(config=encord_config),
            detail=get_encord_export_status_detail(config=encord_config),
        ),
    ]


def get_encord_availability(
    *,
    config: EncordConfig,
) -> ProviderAvailability:
    """Return whether Encord has enough config for export attempts."""
    if is_encord_configured(config=config):
        return ProviderAvailability.CONFIGURED

    return ProviderAvailability.UNCONFIGURED


def get_encord_export_status_detail(
    *,
    config: EncordConfig,
) -> str:
    """Return operator-facing Encord export status detail."""
    if is_encord_configured(config=config):
        return (
            "Encord SSH credentials and project are configured; incident evidence "
            "can be prepared for Encord export."
        )

    return (
        "Encord export unavailable: ENCORD_SSH_KEY_FILE and ENCORD_PROJECT_ID "
        "are not configured; local review queue remains available."
    )
