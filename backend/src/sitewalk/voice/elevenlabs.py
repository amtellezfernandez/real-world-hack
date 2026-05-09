from collections.abc import Awaitable, Callable

from pydantic import Field

from sitewalk.contracts import AlertEvent, AlertProvider, ContractModel
from sitewalk.providers.ports import VoiceBroadcaster
from sitewalk.voice.synthesis import (
    SynthesizedVoiceResult,
    build_synthesized_voice_broadcaster,
)


class ElevenLabsAlertRequest(ContractModel):
    """ElevenLabs alert synthesis request."""

    alert_text: str = Field(min_length=1)
    incident_id: str
    model: str
    voice_id: str


class ElevenLabsAlertResult(SynthesizedVoiceResult):
    """ElevenLabs alert synthesis result."""


type ElevenLabsClient = Callable[
    [ElevenLabsAlertRequest],
    Awaitable[ElevenLabsAlertResult],
]


def build_elevenlabs_broadcaster(
    *,
    client: ElevenLabsClient,
    model: str,
    voice_id: str,
) -> VoiceBroadcaster:
    """Build an ElevenLabs broadcaster behind the voice port."""

    def build_request(alert_event: AlertEvent) -> ElevenLabsAlertRequest:
        return ElevenLabsAlertRequest(
            alert_text=alert_event.alert_text,
            incident_id=alert_event.incident_id,
            model=model,
            voice_id=voice_id,
        )

    return build_synthesized_voice_broadcaster(
        build_request=build_request,
        client=client,
        provider=AlertProvider.ELEVENLABS,
        transcript_error="ElevenLabs transcript must match approved alert text",
    )
