from collections.abc import Awaitable, Callable

from pydantic import Field

from sitewalk.contracts import AlertEvent, AlertProvider, ContractModel
from sitewalk.providers.ports import VoiceBroadcaster
from sitewalk.voice.synthesis import (
    SynthesizedVoiceResult,
    build_synthesized_voice_broadcaster,
)


class MistralVoxtralAlertRequest(ContractModel):
    """Mistral/Voxtral alert synthesis request."""

    alert_text: str = Field(min_length=1)
    incident_id: str
    model: str


class MistralVoxtralAlertResult(SynthesizedVoiceResult):
    """Mistral/Voxtral alert synthesis result."""


type MistralVoxtralClient = Callable[
    [MistralVoxtralAlertRequest],
    Awaitable[MistralVoxtralAlertResult],
]


def build_mistral_voxtral_broadcaster(
    *,
    client: MistralVoxtralClient,
    model: str,
) -> VoiceBroadcaster:
    """Build a Mistral/Voxtral broadcaster behind the voice port."""

    def build_request(alert_event: AlertEvent) -> MistralVoxtralAlertRequest:
        return MistralVoxtralAlertRequest(
            alert_text=alert_event.alert_text,
            incident_id=alert_event.incident_id,
            model=model,
        )

    return build_synthesized_voice_broadcaster(
        build_request=build_request,
        client=client,
        provider=AlertProvider.MISTRAL,
        transcript_error="Mistral transcript must match approved alert text",
    )
