from sitewalk.contracts import AlertProvider, ProviderAvailability
from sitewalk.voice.provider_status import build_voice_provider_statuses


def test_voice_provider_statuses_mark_missing_credentials_unconfigured() -> None:
    statuses = build_voice_provider_statuses(env={})

    statuses_by_provider = {status.provider: status for status in statuses}

    assert statuses_by_provider[AlertProvider.LOCAL_AUDIO].availability == (
        ProviderAvailability.AVAILABLE
    )
    assert statuses_by_provider[AlertProvider.MISTRAL].availability == (
        ProviderAvailability.UNCONFIGURED
    )
    assert statuses_by_provider[AlertProvider.ELEVENLABS].availability == (
        ProviderAvailability.UNCONFIGURED
    )


def test_voice_provider_statuses_mark_configured_credentials_configured() -> None:
    statuses = build_voice_provider_statuses(
        env={
            "MISTRAL_API_KEY": "mistral-key",
            "ELEVENLABS_API_KEY": "elevenlabs-key",
        },
    )

    statuses_by_provider = {status.provider: status for status in statuses}

    assert statuses_by_provider[AlertProvider.MISTRAL].availability == (
        ProviderAvailability.CONFIGURED
    )
    assert statuses_by_provider[AlertProvider.ELEVENLABS].availability == (
        ProviderAvailability.CONFIGURED
    )
