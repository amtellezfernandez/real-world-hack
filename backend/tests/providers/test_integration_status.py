from sitewalk.contracts import (
    ProviderAvailability,
    ProviderBoundary,
    ProviderIntegration,
)
from sitewalk.providers.integration_status import build_provider_integration_statuses


def test_provider_integration_statuses_mark_missing_sponsor_credentials_unavailable() -> (
    None
):
    statuses = build_provider_integration_statuses(env={})
    statuses_by_provider = {status.provider: status for status in statuses}

    assert set(statuses_by_provider) == set(ProviderIntegration)
    assert statuses_by_provider[ProviderIntegration.LOCAL_REPLAY].availability == (
        ProviderAvailability.AVAILABLE
    )
    assert statuses_by_provider[ProviderIntegration.LOCAL_REPLAY].boundary == (
        ProviderBoundary.PERCEPTION
    )
    assert statuses_by_provider[ProviderIntegration.RUNPOD_YOLO].availability == (
        ProviderAvailability.UNCONFIGURED
    )
    assert "endpoint client is not configured" in (
        statuses_by_provider[ProviderIntegration.RUNPOD_YOLO].detail
    )
    assert statuses_by_provider[ProviderIntegration.OPENAI_FOUNDRY].availability == (
        ProviderAvailability.UNCONFIGURED
    )
    assert statuses_by_provider[
        ProviderIntegration.LOCAL_INCIDENT_REPORT
    ].availability == (ProviderAvailability.AVAILABLE)
    assert statuses_by_provider[ProviderIntegration.LOCAL_INCIDENT_REPORT].boundary == (
        ProviderBoundary.INCIDENT_REPORTING
    )
    assert statuses_by_provider[
        ProviderIntegration.GEMINI_ROBOTICS_ER
    ].availability == (ProviderAvailability.UNCONFIGURED)
    assert statuses_by_provider[ProviderIntegration.ENCORD].availability == (
        ProviderAvailability.UNCONFIGURED
    )
    assert "local review queue remains available" in (
        statuses_by_provider[ProviderIntegration.ENCORD].detail
    )
    assert all(
        "API_KEY" not in status.detail and "ENDPOINT" not in status.detail
        for status in statuses
    )


def test_provider_integration_statuses_mark_configured_sponsor_scaffolds() -> None:
    statuses = build_provider_integration_statuses(
        env={
            "OPENAI_API_KEY": "openai-key",
            "GEMINI_API_KEY": "gemini-key",
            "MISTRAL_API_KEY": "mistral-key",
            "ELEVENLABS_API_KEY": "elevenlabs-key",
            "ENCORD_API_KEY": "encord-key",
            "ENCORD_PROJECT_ID": "encord-project",
        },
    )
    statuses_by_provider = {status.provider: status for status in statuses}

    assert statuses_by_provider[ProviderIntegration.RUNPOD_YOLO].availability == (
        ProviderAvailability.UNCONFIGURED
    )
    assert statuses_by_provider[ProviderIntegration.OPENAI_FOUNDRY].availability == (
        ProviderAvailability.CONFIGURED
    )
    assert statuses_by_provider[
        ProviderIntegration.GEMINI_ROBOTICS_ER
    ].availability == (ProviderAvailability.CONFIGURED)
    assert statuses_by_provider[ProviderIntegration.MISTRAL].availability == (
        ProviderAvailability.CONFIGURED
    )
    assert statuses_by_provider[ProviderIntegration.ELEVENLABS].availability == (
        ProviderAvailability.CONFIGURED
    )
    assert statuses_by_provider[ProviderIntegration.ENCORD].availability == (
        ProviderAvailability.CONFIGURED
    )
    assert "incident reporting scaffold" in (
        statuses_by_provider[ProviderIntegration.OPENAI_FOUNDRY].detail
    )
    assert all("can be selected" not in status.detail for status in statuses)
