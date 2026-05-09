import pytest

from sitewalk.contracts import AlertEvent, AlertProvider
from sitewalk.voice.elevenlabs import (
    ElevenLabsAlertRequest,
    ElevenLabsAlertResult,
    build_elevenlabs_broadcaster,
)

pytestmark = pytest.mark.anyio


async def test_elevenlabs_broadcaster_returns_alert_event_contract(
    approved_alert_event: AlertEvent,
) -> None:
    requests: list[ElevenLabsAlertRequest] = []

    async def synthesize_alert(
        request: ElevenLabsAlertRequest,
    ) -> ElevenLabsAlertResult:
        requests.append(request)
        return ElevenLabsAlertResult(
            audio_ref="assets/audio/elevenlabs-alert.wav",
            transcript=request.alert_text,
        )

    broadcaster = build_elevenlabs_broadcaster(
        client=synthesize_alert,
        model="eleven_turbo_v2_5",
        voice_id="voice-floor-supervisor",
    )

    alert_event = await broadcaster(approved_alert_event)

    assert alert_event.incident_id == approved_alert_event.incident_id
    assert alert_event.approval_actor == "demo-supervisor"
    assert alert_event.alert_text == approved_alert_event.alert_text
    assert alert_event.provider == AlertProvider.ELEVENLABS
    assert alert_event.timestamp == approved_alert_event.timestamp
    assert alert_event.audio_ref == "assets/audio/elevenlabs-alert.wav"
    assert len(requests) == 1
    assert requests[0].model == "eleven_turbo_v2_5"
    assert requests[0].voice_id == "voice-floor-supervisor"
    assert requests[0].incident_id == approved_alert_event.incident_id
    assert requests[0].alert_text == approved_alert_event.alert_text


async def test_elevenlabs_broadcaster_rejects_transcript_drift(
    approved_alert_event: AlertEvent,
) -> None:
    async def synthesize_alert(
        request: ElevenLabsAlertRequest,
    ) -> ElevenLabsAlertResult:
        return ElevenLabsAlertResult(
            audio_ref="assets/audio/elevenlabs-alert.wav",
            transcript=f"{request.alert_text} Please hurry.",
        )

    broadcaster = build_elevenlabs_broadcaster(
        client=synthesize_alert,
        model="eleven_turbo_v2_5",
        voice_id="voice-floor-supervisor",
    )

    with pytest.raises(ValueError, match="ElevenLabs transcript must match"):
        await broadcaster(approved_alert_event)


async def test_elevenlabs_result_requires_audio_reference() -> None:
    with pytest.raises(ValueError):
        ElevenLabsAlertResult(audio_ref="", transcript="approved alert")
