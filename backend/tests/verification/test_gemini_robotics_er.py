from datetime import UTC, datetime

import pytest

from sitewalk.contracts import (
    EvidenceFrame,
    EvidenceSource,
    IncidentState,
    Observation,
    ObservedState,
    SafetyIncident,
    Severity,
    VerificationVerdict,
)
from sitewalk.demo_data import PRIMARY_DEMO_ZONE
from sitewalk.providers.ports import ClearanceVerifier
from sitewalk.verification.gemini_robotics_er import (
    GEMINI_ROBOTICS_ER_1_6_MODEL,
    GeminiClearanceVerificationRequest,
    GeminiClearanceVerificationResult,
    GeminiInlineImage,
    build_gemini_clearance_config,
    build_gemini_clearance_contents,
    build_google_genai_client,
    build_gemini_robotics_er_clearance_verifier,
)

pytestmark = pytest.mark.anyio
GEMINI_MODEL = GEMINI_ROBOTICS_ER_1_6_MODEL


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def make_alert_broadcast_incident() -> SafetyIncident:
    return SafetyIncident(
        id="incident-exit-b3-20260508T120030Z",
        zone_id=PRIMARY_DEMO_ZONE.id,
        state=IncidentState.ALERT_BROADCAST,
        severity=Severity.HIGH,
        before_evidence_frame_id="frame-workcell-sustained-blocked",
    )


def make_after_frame(frame_id: str) -> EvidenceFrame:
    return EvidenceFrame(
        id=frame_id,
        source=EvidenceSource.REPLAY,
        timestamp=datetime(2026, 5, 8, 12, 0, 45, tzinfo=UTC),
        image_ref="assets/demo/workcell-clear.svg",
    )


async def load_gemini_image(frame: EvidenceFrame) -> GeminiInlineImage:
    return GeminiInlineImage(
        mime_type="image/svg+xml",
        data=b"<svg />",
    )


def make_after_observation(
    *,
    after_frame: EvidenceFrame,
    observed_state: ObservedState,
) -> Observation:
    return Observation(
        zone_id=PRIMARY_DEMO_ZONE.id,
        observed_state=observed_state,
        dwell_duration_seconds=0,
        evidence_frame_id=after_frame.id,
        confidence=0.93,
    )


def make_gemini_result(
    *,
    verdict: VerificationVerdict,
    rationale: str,
    confidence: float = 0.82,
) -> GeminiClearanceVerificationResult:
    return GeminiClearanceVerificationResult(
        verdict=verdict,
        confidence=confidence,
        rationale=rationale,
    )


def make_gemini_request() -> GeminiClearanceVerificationRequest:
    return GeminiClearanceVerificationRequest(
        incident_id="incident-workcell",
        zone_id=PRIMARY_DEMO_ZONE.id,
        before_evidence_frame_id="frame-before",
        after_evidence_frame_id="frame-after",
        after_observation_confidence=0.93,
        after_image=GeminiInlineImage(
            mime_type="image/svg+xml",
            data=b"<svg />",
        ),
        model=GEMINI_MODEL,
    )


def make_recording_verifier(
    *,
    result: GeminiClearanceVerificationResult,
) -> tuple[list[GeminiClearanceVerificationRequest], ClearanceVerifier]:
    requests: list[GeminiClearanceVerificationRequest] = []

    async def verify_clearance(
        request: GeminiClearanceVerificationRequest,
    ) -> GeminiClearanceVerificationResult:
        requests.append(request)
        return result

    return requests, build_gemini_robotics_er_clearance_verifier(
        client=verify_clearance,
        load_image=load_gemini_image,
        model=GEMINI_MODEL,
    )


async def test_gemini_clearance_verifier_returns_clear_verdict_contract() -> None:
    requests, verifier = make_recording_verifier(
        result=make_gemini_result(
            verdict=VerificationVerdict.CLEAR,
            confidence=0.91,
            rationale="After frame shows the emergency workcell is clear.",
        ),
    )
    after_frame = make_after_frame("frame-workcell-after-clear")

    verification = await verifier(
        make_alert_broadcast_incident(),
        after_frame,
        make_after_observation(
            after_frame=after_frame,
            observed_state=ObservedState.CLEAR,
        ),
    )

    assert verification.verdict == VerificationVerdict.CLEAR
    assert verification.confidence == 0.91
    assert (
        verification.rationale == "After frame shows the emergency workcell is clear."
    )
    assert verification.after_evidence_frame_id == after_frame.id
    assert len(requests) == 1
    assert requests[0].incident_id == "incident-exit-b3-20260508T120030Z"
    assert requests[0].model == GEMINI_MODEL
    assert requests[0].after_evidence_frame_id == after_frame.id
    assert requests[0].after_image.data == b"<svg />"


@pytest.mark.parametrize(
    ("provider_verdict", "rationale"),
    [
        (
            VerificationVerdict.STILL_BLOCKED,
            "After frame still shows an obstruction.",
        ),
        (
            VerificationVerdict.UNCERTAIN,
            "After frame is not sufficient to verify clearance.",
        ),
    ],
)
async def test_gemini_clearance_verifier_returns_provider_non_clear_verdicts(
    provider_verdict: VerificationVerdict,
    rationale: str,
) -> None:
    requests, verifier = make_recording_verifier(
        result=make_gemini_result(
            verdict=provider_verdict,
            rationale=rationale,
        ),
    )
    after_frame = make_after_frame("frame-workcell-after-review")

    verification = await verifier(
        make_alert_broadcast_incident(),
        after_frame,
        make_after_observation(
            after_frame=after_frame,
            observed_state=ObservedState.CLEAR,
        ),
    )

    assert verification.verdict == provider_verdict
    assert verification.confidence == 0.82
    assert verification.rationale == rationale
    assert verification.after_evidence_frame_id == after_frame.id
    assert len(requests) == 1


@pytest.mark.parametrize(
    ("observed_state", "expected_verdict"),
    [
        (ObservedState.BLOCKED, VerificationVerdict.STILL_BLOCKED),
        (ObservedState.UNCERTAIN, VerificationVerdict.UNCERTAIN),
        (ObservedState.CAMERA_UNAVAILABLE, VerificationVerdict.UNCERTAIN),
    ],
)
async def test_gemini_clearance_verifier_skips_provider_for_non_clear_observations(
    observed_state: ObservedState,
    expected_verdict: VerificationVerdict,
) -> None:
    requests, verifier = make_recording_verifier(
        result=make_gemini_result(
            verdict=VerificationVerdict.CLEAR,
            rationale="Provider claims the path is clear.",
        ),
    )
    after_frame = make_after_frame("frame-workcell-after-review")

    verification = await verifier(
        make_alert_broadcast_incident(),
        after_frame,
        make_after_observation(
            after_frame=after_frame,
            observed_state=observed_state,
        ),
    )

    assert verification.verdict == expected_verdict
    assert verification.confidence == 0.93
    assert verification.after_evidence_frame_id == after_frame.id
    assert requests == []


def test_gemini_clearance_contents_include_prompt_and_image() -> None:
    contents = build_gemini_clearance_contents(make_gemini_request())

    assert len(contents) == 2
    assert contents[0].text is not None
    assert "incident-workcell" in contents[0].text
    assert "clear, still_blocked, or uncertain" in contents[0].text
    assert contents[1].inline_data is not None
    assert contents[1].inline_data.mime_type == "image/svg+xml"
    assert contents[1].inline_data.data == b"<svg />"


def test_gemini_clearance_config_uses_structured_output() -> None:
    config = build_gemini_clearance_config(thinking_budget=0)

    assert config.response_mime_type == "application/json"
    assert config.response_schema == GeminiClearanceVerificationResult
    assert config.temperature == 0
    assert config.thinking_config is not None
    assert config.thinking_config.thinking_budget == 0


def test_google_genai_clearance_client_rejects_blank_api_key() -> None:
    with pytest.raises(ValueError, match="Gemini API key is required"):
        build_google_genai_client(api_key=" ")


def test_google_genai_clearance_client_rejects_invalid_timeout() -> None:
    with pytest.raises(ValueError, match="timeout milliseconds must be positive"):
        build_google_genai_client(api_key="test-key", timeout_milliseconds=0)


async def test_gemini_clearance_verifier_rejects_mismatched_after_observation() -> None:
    requests, verifier = make_recording_verifier(
        result=make_gemini_result(
            verdict=VerificationVerdict.CLEAR,
            confidence=0.91,
            rationale="After frame shows the emergency workcell is clear.",
        ),
    )
    after_frame = make_after_frame("frame-workcell-after-clear")
    mismatched_observation = Observation(
        zone_id=PRIMARY_DEMO_ZONE.id,
        observed_state=ObservedState.CLEAR,
        dwell_duration_seconds=0,
        evidence_frame_id="frame-different",
        confidence=0.93,
    )

    with pytest.raises(
        ValueError,
        match="after observation evidence_frame_id must match evidence frame id",
    ):
        await verifier(
            make_alert_broadcast_incident(),
            after_frame,
            mismatched_observation,
        )

    assert requests == []


@pytest.mark.parametrize(
    "incident",
    [
        SafetyIncident(
            id="incident-exit-b3-20260508T120030Z",
            zone_id=PRIMARY_DEMO_ZONE.id,
            state=IncidentState.INCIDENT_OPEN,
            severity=Severity.HIGH,
            before_evidence_frame_id="frame-workcell-sustained-blocked",
        ),
        SafetyIncident(
            id="incident-exit-b3-20260508T120030Z",
            zone_id="zone-other",
            state=IncidentState.ALERT_BROADCAST,
            severity=Severity.HIGH,
            before_evidence_frame_id="frame-workcell-sustained-blocked",
        ),
    ],
)
async def test_gemini_clearance_verifier_rejects_invalid_local_inputs(
    incident: SafetyIncident,
) -> None:
    requests, verifier = make_recording_verifier(
        result=make_gemini_result(
            verdict=VerificationVerdict.CLEAR,
            rationale="Provider claims the path is clear.",
        ),
    )
    after_frame = make_after_frame("frame-workcell-after-clear")

    with pytest.raises(ValueError):
        await verifier(
            incident,
            after_frame,
            make_after_observation(
                after_frame=after_frame,
                observed_state=ObservedState.CLEAR,
            ),
        )

    assert requests == []
