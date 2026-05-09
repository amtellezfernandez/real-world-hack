from collections.abc import Awaitable, Callable

from pydantic import Field

from sitewalk.contracts import AlertEvent, AlertProvider, ContractModel
from sitewalk.providers.ports import VoiceBroadcaster


class SynthesizedVoiceResult(ContractModel):
    """Provider voice synthesis result with transcript and audio reference."""

    audio_ref: str = Field(min_length=1)
    transcript: str = Field(min_length=1)


type SynthesizedVoiceClient[RequestT, ResultT: SynthesizedVoiceResult] = Callable[
    [RequestT],
    Awaitable[ResultT],
]
type VoiceRequestBuilder[RequestT] = Callable[[AlertEvent], RequestT]


def build_synthesized_voice_broadcaster[
    RequestT,
    ResultT: SynthesizedVoiceResult,
](
    *,
    build_request: VoiceRequestBuilder[RequestT],
    client: SynthesizedVoiceClient[RequestT, ResultT],
    provider: AlertProvider,
    transcript_error: str,
) -> VoiceBroadcaster:
    """Build a transcript-preserving provider voice broadcaster."""

    async def broadcast(alert_event: AlertEvent) -> AlertEvent:
        result = await client(build_request(alert_event))

        if result.transcript != alert_event.alert_text:
            raise ValueError(transcript_error)

        return AlertEvent(
            incident_id=alert_event.incident_id,
            approval_actor=alert_event.approval_actor,
            alert_text=alert_event.alert_text,
            provider=provider,
            timestamp=alert_event.timestamp,
            audio_ref=result.audio_ref,
        )

    return broadcast
