import pytest

from sitewalk.contracts import AlertEvent, AlertProvider
from sitewalk.voice.mistral_voxtral import (
    MistralVoxtralAlertRequest,
    MistralVoxtralAlertResult,
    build_mistral_voxtral_broadcaster,
)

pytestmark = pytest.mark.anyio


async def test_mistral_voxtral_broadcaster_returns_alert_event_contract(
    approved_alert_event: AlertEvent,
) -> None:
    requests: list[MistralVoxtralAlertRequest] = []

    async def synthesize_alert(
        request: MistralVoxtralAlertRequest,
    ) -> MistralVoxtralAlertResult:
        requests.append(request)
        return MistralVoxtralAlertResult(
            audio_ref="assets/audio/mistral-voxtral-alert.wav",
            transcript=request.alert_text,
        )

    broadcaster = build_mistral_voxtral_broadcaster(
        client=synthesize_alert,
        model="voxtral-mini-latest",
    )

    alert_event = await broadcaster(approved_alert_event)

    assert alert_event.incident_id == approved_alert_event.incident_id
    assert alert_event.approval_actor == "demo-supervisor"
    assert alert_event.alert_text == approved_alert_event.alert_text
    assert alert_event.provider == AlertProvider.MISTRAL
    assert alert_event.timestamp == approved_alert_event.timestamp
    assert alert_event.audio_ref == "assets/audio/mistral-voxtral-alert.wav"
    assert len(requests) == 1
    assert requests[0].model == "voxtral-mini-latest"
    assert requests[0].incident_id == approved_alert_event.incident_id
    assert requests[0].alert_text == approved_alert_event.alert_text


async def test_mistral_voxtral_broadcaster_rejects_transcript_drift(
    approved_alert_event: AlertEvent,
) -> None:
    async def synthesize_alert(
        request: MistralVoxtralAlertRequest,
    ) -> MistralVoxtralAlertResult:
        return MistralVoxtralAlertResult(
            audio_ref="assets/audio/mistral-voxtral-alert.wav",
            transcript=f"{request.alert_text} Please hurry.",
        )

    broadcaster = build_mistral_voxtral_broadcaster(
        client=synthesize_alert,
        model="voxtral-mini-latest",
    )

    with pytest.raises(ValueError, match="Mistral transcript must match"):
        await broadcaster(approved_alert_event)


async def test_mistral_voxtral_result_requires_audio_reference() -> None:
    with pytest.raises(ValueError):
        MistralVoxtralAlertResult(audio_ref="", transcript="approved alert")
