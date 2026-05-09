from collections.abc import Mapping

from sitewalk.contracts import (
    AlertProvider,
    ProviderAvailability,
    VoiceProviderStatus,
)

MISTRAL_API_KEY_ENV = "MISTRAL_API_KEY"
ELEVENLABS_API_KEY_ENV = "ELEVENLABS_API_KEY"


def build_voice_provider_statuses(
    *,
    env: Mapping[str, str],
) -> list[VoiceProviderStatus]:
    """Return runtime voice provider availability without importing provider SDKs."""
    return [
        VoiceProviderStatus(
            provider=AlertProvider.LOCAL_AUDIO,
            availability=ProviderAvailability.AVAILABLE,
            detail="Local prebuilt alert audio is available.",
        ),
        _credential_status(
            provider=AlertProvider.MISTRAL,
            provider_name="Mistral",
            env=env,
            env_var=MISTRAL_API_KEY_ENV,
        ),
        _credential_status(
            provider=AlertProvider.ELEVENLABS,
            provider_name="ElevenLabs",
            env=env,
            env_var=ELEVENLABS_API_KEY_ENV,
        ),
    ]


def _credential_status(
    *,
    provider: AlertProvider,
    provider_name: str,
    env: Mapping[str, str],
    env_var: str,
) -> VoiceProviderStatus:
    if env.get(env_var, "").strip() == "":
        return VoiceProviderStatus(
            provider=provider,
            availability=ProviderAvailability.UNCONFIGURED,
            detail=f"{provider_name} credentials are not configured.",
        )

    return VoiceProviderStatus(
        provider=provider,
        availability=ProviderAvailability.CONFIGURED,
        detail=f"{provider_name} credentials are configured.",
    )
