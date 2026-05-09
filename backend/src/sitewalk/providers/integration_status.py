from collections.abc import Mapping

from sitewalk.contracts import (
    ProviderAvailability,
    ProviderBoundary,
    ProviderIntegration,
    ProviderIntegrationStatus,
    ReviewExportProvider,
    ReviewExportProviderStatus,
)
from sitewalk.review_export.provider_status import (
    build_review_export_provider_statuses,
)

OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"


def build_provider_integration_statuses(
    *,
    env: Mapping[str, str],
    review_statuses: list[ReviewExportProviderStatus] | None = None,
) -> list[ProviderIntegrationStatus]:
    """Return truthful demo readiness for every provider integration."""
    review_statuses_by_provider = {
        status.provider: status
        for status in (
            review_statuses
            if review_statuses is not None
            else build_review_export_provider_statuses(env=env)
        )
    }

    return [
        _active_status(
            provider=ProviderIntegration.LOCAL_REPLAY,
            boundary=ProviderBoundary.PERCEPTION,
            detail="Local replay perception is active for the demo.",
        ),
        ProviderIntegrationStatus(
            provider=ProviderIntegration.RUNPOD_YOLO,
            boundary=ProviderBoundary.PERCEPTION,
            availability=ProviderAvailability.UNCONFIGURED,
            detail=(
                "RunPod YOLO boundary is scaffolded; endpoint client is not "
                "configured, so local replay remains active."
            ),
        ),
        _active_status(
            provider=ProviderIntegration.LOCAL_INCIDENT_REPORT,
            boundary=ProviderBoundary.INCIDENT_REPORTING,
            detail="Local deterministic incident report is active for opened incidents.",
        ),
        _credential_scaffold_status(
            provider=ProviderIntegration.OPENAI_FOUNDRY,
            provider_name="OpenAI/Foundry",
            boundary=ProviderBoundary.INCIDENT_REPORTING,
            env=env,
            env_var=OPENAI_API_KEY_ENV,
        ),
        _active_status(
            provider=ProviderIntegration.LOCAL_CLEARANCE,
            boundary=ProviderBoundary.VERIFICATION,
            detail="Active deterministic clearance verifier is powering closure checks.",
        ),
        _credential_scaffold_status(
            provider=ProviderIntegration.GEMINI_ROBOTICS_ER,
            provider_name="Gemini Robotics-ER",
            boundary=ProviderBoundary.VERIFICATION,
            env=env,
            env_var=GEMINI_API_KEY_ENV,
        ),
        _review_export_status(
            provider=ProviderIntegration.LOCAL_REVIEW,
            status_provider=ReviewExportProvider.LOCAL_REVIEW,
            statuses=review_statuses_by_provider,
        ),
        _review_export_status(
            provider=ProviderIntegration.ENCORD,
            status_provider=ReviewExportProvider.ENCORD,
            statuses=review_statuses_by_provider,
        ),
    ]


def _active_status(
    *,
    provider: ProviderIntegration,
    boundary: ProviderBoundary,
    detail: str,
) -> ProviderIntegrationStatus:
    return ProviderIntegrationStatus(
        provider=provider,
        boundary=boundary,
        availability=ProviderAvailability.AVAILABLE,
        detail=detail,
    )


def _review_export_status(
    *,
    provider: ProviderIntegration,
    status_provider: ReviewExportProvider,
    statuses: dict[ReviewExportProvider, ReviewExportProviderStatus],
) -> ProviderIntegrationStatus:
    status = statuses[status_provider]

    return ProviderIntegrationStatus(
        provider=provider,
        boundary=ProviderBoundary.REVIEW_EXPORT,
        availability=status.availability,
        detail=status.detail,
    )


def _credential_scaffold_status(
    *,
    provider: ProviderIntegration,
    provider_name: str,
    boundary: ProviderBoundary,
    env: Mapping[str, str],
    env_var: str,
) -> ProviderIntegrationStatus:
    is_configured = env.get(env_var, "").strip() != ""
    boundary_label = boundary.value.replace("_", " ")

    return ProviderIntegrationStatus(
        provider=provider,
        boundary=boundary,
        availability=(
            ProviderAvailability.CONFIGURED
            if is_configured
            else ProviderAvailability.UNCONFIGURED
        ),
        detail=(
            f"{provider_name} credentials are configured for the "
            f"{boundary_label} scaffold."
            if is_configured
            else (
                f"{provider_name} scaffold is unavailable until credentials are "
                "configured."
            )
        ),
    )
