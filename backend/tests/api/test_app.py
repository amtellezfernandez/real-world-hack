from datetime import UTC, datetime

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient, Response
from pydantic import ValidationError

from sitewalk.api.main import app
from sitewalk.api.demo_replay_service import assess_demo_replay
from sitewalk.contracts import (
    AuditPacket,
    ClearanceVerification,
    CriticalZone,
    CriticalZonePolicy,
    DemoReplay,
    DemoTiming,
    DemoTimingMode,
    DemoTimingOption,
    EvidenceFrame,
    EvidenceSource,
    ExportStatus,
    HealthResponse,
    IncidentState,
    MotionEstimate,
    Observation,
    ObservationAssessment,
    ObservationReplay,
    ObservedState,
    ProviderAvailability,
    ProductContract,
    ProviderIntegration,
    ReplayFrame,
    ReviewSample,
    ReviewDecision,
    ReviewExportProvider,
    SafetyIncident,
    Severity,
    VerificationVerdict,
    ZonePoint,
    ZoneType,
)
from sitewalk.perception.replay import (
    build_blocked_exit_replay,
    build_observation_replay_frame,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_app_boots() -> None:
    async with LifespanManager(app):
        pass


async def get_response(path: str) -> Response:
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.get(path)


async def test_health_reports_backend_ready() -> None:
    response = await get_response("/health")

    assert response.status_code == 200
    health = HealthResponse.model_validate(response.json())
    assert health.service == "sitewalk-sentinel-api"
    assert health.status == "ready"
    assert health.version == "0.1.0"


async def test_product_contract_exposes_incident_and_observation_concepts() -> None:
    response = await get_response("/api/product-contract")

    assert response.status_code == 200
    contract = ProductContract.model_validate(response.json())
    assert contract.primary_workflow == "robot_workcell_obstruction"
    assert "blocked" in contract.observation_states
    assert "uncertain" in contract.observation_states
    assert "alert_pending" in contract.incident_states
    assert "closed" in contract.incident_states
    assert contract.reference_evidence_frame.source == EvidenceSource.REPLAY
    assert contract.reference_evidence_frame.image_ref == (
        "assets/demo/reference-blocked.jpg"
    )
    assert contract.reference_evidence_frame.annotations[0].label == "zone_overlap"
    assert [boundary.value for boundary in contract.provider_boundaries] == [
        "perception",
        "incident_reporting",
        "verification",
        "review_export",
    ]
    export_statuses_by_provider = {
        status.provider: status for status in contract.review_export_provider_statuses
    }
    assert export_statuses_by_provider[
        ReviewExportProvider.LOCAL_REVIEW
    ].availability == (ProviderAvailability.AVAILABLE)
    assert export_statuses_by_provider[ReviewExportProvider.ENCORD].availability == (
        ProviderAvailability.UNCONFIGURED
    )
    integration_statuses_by_provider = {
        status.provider: status for status in contract.provider_integration_statuses
    }
    assert set(integration_statuses_by_provider) == set(ProviderIntegration)
    assert integration_statuses_by_provider[
        ProviderIntegration.LOCAL_REPLAY
    ].availability == (ProviderAvailability.AVAILABLE)
    assert integration_statuses_by_provider[
        ProviderIntegration.RUNPOD_YOLO
    ].availability == (ProviderAvailability.UNCONFIGURED)


async def test_demo_replay_exposes_clear_and_blocked_frames() -> None:
    response = await get_response("/api/demo-replay")

    assert response.status_code == 200
    replay = DemoReplay.model_validate(response.json())
    assert replay.id == "blocked-workcell-a2"
    assert replay.zone.name == "Robot Workcell A-2"
    assert replay.timing.default_mode == DemoTimingMode.STAGE
    assert [option.mode for option in replay.timing.options] == [
        DemoTimingMode.STAGE,
        DemoTimingMode.REAL_TIME,
    ]
    assert replay.timing.options[0].frame_interval_ms < (
        replay.timing.options[1].frame_interval_ms
    )
    assert all(
        not option.requires_external_providers for option in replay.timing.options
    )
    assert [frame.observation.observed_state for frame in replay.frames] == [
        ObservedState.CLEAR,
        ObservedState.BLOCKED,
        ObservedState.BLOCKED,
        ObservedState.BLOCKED,
        ObservedState.BLOCKED,
        ObservedState.CLEAR,
    ]
    assert [frame.assessment.incident_state for frame in replay.frames] == [
        IncidentState.CLEAR,
        IncidentState.DWELL,
        IncidentState.INCIDENT_OPEN,
        IncidentState.ALERT_BROADCAST,
        IncidentState.CLEARING,
        IncidentState.CLOSED,
    ]
    assert all(
        frame.evidence_frame.source == EvidenceSource.REPLAY for frame in replay.frames
    )
    assert all(
        frame.observation.evidence_frame_id == frame.evidence_frame.id
        for frame in replay.frames
    )
    assert replay.frames[0].observation.dwell_duration_seconds == 0
    assert replay.frames[1].observation.dwell_duration_seconds > 0
    assert replay.frames[1].evidence_frame.annotations[0].label == "zone_overlap"
    assert replay.frames[2].assessment.incident is not None
    assert replay.frames[3].assessment.incident is not None
    assert replay.frames[3].assessment.incident.alert_events[0].alert_text == (
        "Robotics notice: clear the obstruction at Robot Workcell A-2."
    )
    assert replay.frames[4].assessment.incident is not None
    assert replay.frames[4].assessment.incident.verification is not None
    assert replay.frames[4].assessment.incident.verification.verdict == (
        VerificationVerdict.STILL_BLOCKED
    )
    assert replay.frames[5].assessment.incident is not None
    assert replay.frames[5].assessment.incident.verification is not None
    assert replay.frames[5].assessment.incident.verification.verdict == (
        VerificationVerdict.CLEAR
    )
    assert replay.frames[5].assessment.incident.audit_packet is not None
    assert replay.frames[5].assessment.incident.audit_packet.before_frame_id == (
        "frame-workcell-sustained-blocked"
    )
    assert replay.frames[5].assessment.incident.audit_packet.after_frame_id == (
        "frame-workcell-after-clear"
    )
    assert replay.frames[5].assessment.incident.audit_packet.before_timestamp == (
        datetime(2026, 5, 8, 12, 0, 30, tzinfo=UTC)
    )
    assert replay.frames[5].assessment.incident.audit_packet.after_timestamp == (
        datetime(2026, 5, 8, 12, 0, 45, tzinfo=UTC)
    )
    assert replay.frames[5].assessment.incident.audit_packet.alert_transcript == (
        "Robotics notice: clear the obstruction at Robot Workcell A-2."
    )
    assert replay.frames[5].assessment.incident.audit_packet.verification_verdict == (
        VerificationVerdict.CLEAR
    )
    assert replay.frames[5].assessment.incident.review_sample is not None
    assert (
        replay.frames[5].assessment.incident.review_sample.human_decision
        == ReviewDecision.PENDING
    )
    assert replay.frames[5].assessment.incident.review_sample.export_status == (
        ExportStatus.LOCAL_ONLY
    )


async def test_motion_endpoint_tracks_frame_shift() -> None:
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            base = {"width": 20, "height": 12, "pixels": [0] * 240}
            first = await client.post("/api/motion/estimate", json=base)
            assert first.status_code == 200
            first_estimate = MotionEstimate.model_validate(first.json())
            assert first_estimate.x == 24
            assert first_estimate.y == 76

            shifted_pixels = [0] * 240
            for y in range(4, 7):
                for x in range(6, 9):
                    shifted_pixels[y * 20 + x] = 255

            shifted = {"width": 20, "height": 12, "pixels": shifted_pixels}
            second = await client.post("/api/motion/estimate", json=shifted)
            assert second.status_code == 200
            second_estimate = MotionEstimate.model_validate(second.json())
            assert second_estimate.confidence >= 0
            assert (
                second_estimate.x != first_estimate.x
                or second_estimate.y != first_estimate.y
            )

            reset = await client.post("/api/motion/reset")
            assert reset.status_code == 200
            reset_estimate = MotionEstimate.model_validate(reset.json())
            assert reset_estimate.x == 24
            assert reset_estimate.y == 76

def test_demo_replay_alerts_after_first_incident_frame_not_fixed_index() -> None:
    replay = build_blocked_exit_replay()
    extra_preincident_frame = build_observation_replay_frame(
        id="replay-frame-extra-dwell",
        label="Extra dwell",
        evidence_frame_id="frame-workcell-extra-dwell",
        observed_state=ObservedState.BLOCKED,
        dwell_seconds=12,
        seconds=12,
        image_ref="assets/demo/workcell-blocked.svg",
        annotation_label="zone_overlap",
        confidence=0.91,
    )

    assessed_replay = assess_demo_replay(
        ObservationReplay(
            id=replay.id,
            name=replay.name,
            zone=replay.zone,
            timing=replay.timing,
            frames=[
                *replay.frames[:2],
                extra_preincident_frame,
                *replay.frames[2:],
            ],
        ),
    )

    assert [frame.assessment.incident_state for frame in assessed_replay.frames] == [
        IncidentState.CLEAR,
        IncidentState.DWELL,
        IncidentState.DWELL,
        IncidentState.INCIDENT_OPEN,
        IncidentState.ALERT_BROADCAST,
        IncidentState.CLEARING,
        IncidentState.CLOSED,
    ]


def test_demo_replay_stops_verification_after_closure() -> None:
    replay = build_blocked_exit_replay()
    post_closure_frame = build_observation_replay_frame(
        id="replay-frame-after-closure",
        label="After closure",
        evidence_frame_id="frame-workcell-after-closure",
        observed_state=ObservedState.BLOCKED,
        dwell_seconds=50,
        seconds=50,
        image_ref="assets/demo/workcell-blocked.svg",
        annotation_label="zone_overlap",
        confidence=0.9,
    )

    assessed_replay = assess_demo_replay(
        ObservationReplay(
            id=replay.id,
            name=replay.name,
            zone=replay.zone,
            timing=replay.timing,
            frames=[*replay.frames, post_closure_frame],
        ),
    )

    assert [frame.id for frame in assessed_replay.frames][-1] == (
        "replay-frame-verified-clear"
    )
    assert assessed_replay.frames[-1].assessment.incident_state == IncidentState.CLOSED


def test_observation_assessment_rejects_mismatched_incident_state() -> None:
    evidence_frame = EvidenceFrame(
        id="frame-one",
        source=EvidenceSource.REPLAY,
        timestamp=datetime(2026, 5, 8, 12, 0, 0, tzinfo=UTC),
        image_ref="assets/demo/workcell-blocked.svg",
    )

    with pytest.raises(ValidationError):
        ObservationAssessment(
            incident_state=IncidentState.CLEAR,
            policy_reason="test",
            incident=SafetyIncident(
                id="incident-one",
                zone_id="zone-workcell-a2",
                state=IncidentState.INCIDENT_OPEN,
                severity=Severity.HIGH,
                before_evidence_frame_id=evidence_frame.id,
            ),
        )


def test_observation_assessment_requires_incident_for_incident_open() -> None:
    with pytest.raises(ValidationError):
        ObservationAssessment(
            incident_state=IncidentState.INCIDENT_OPEN,
            policy_reason="test",
        )


@pytest.mark.parametrize(
    "incident_state",
    [
        IncidentState.ALERT_PENDING,
        IncidentState.ALERT_BROADCAST,
        IncidentState.CLEARING,
        IncidentState.CLOSED,
    ],
)
def test_observation_assessment_requires_incident_for_incident_states(
    incident_state: IncidentState,
) -> None:
    with pytest.raises(ValidationError):
        ObservationAssessment(
            incident_state=incident_state,
            policy_reason="test",
        )


@pytest.mark.parametrize(
    "incident_state",
    [
        IncidentState.CLEARING,
        IncidentState.VERIFIED_CLEAR,
        IncidentState.CLOSED,
    ],
)
def test_observation_assessment_requires_verification_for_clearance_states(
    incident_state: IncidentState,
) -> None:
    with pytest.raises(ValidationError):
        ObservationAssessment(
            incident_state=incident_state,
            policy_reason="test",
            incident=SafetyIncident(
                id="incident-one",
                zone_id="zone-workcell-a2",
                state=incident_state,
                severity=Severity.HIGH,
                before_evidence_frame_id="frame-one",
            ),
        )


def test_safety_incident_rejects_closed_without_audit_or_review() -> None:
    with pytest.raises(ValidationError):
        SafetyIncident(
            id="incident-one",
            zone_id="zone-workcell-a2",
            state=IncidentState.CLOSED,
            severity=Severity.HIGH,
            before_evidence_frame_id="frame-before",
            verification=ClearanceVerification(
                verdict=VerificationVerdict.CLEAR,
                confidence=0.97,
                rationale="After evidence shows the critical zone is clear.",
                after_evidence_frame_id="frame-after",
            ),
        )


def test_safety_incident_rejects_closed_with_mismatched_evidence_package() -> None:
    with pytest.raises(ValidationError):
        SafetyIncident(
            id="incident-one",
            zone_id="zone-workcell-a2",
            state=IncidentState.CLOSED,
            severity=Severity.HIGH,
            before_evidence_frame_id="frame-before",
            verification=ClearanceVerification(
                verdict=VerificationVerdict.CLEAR,
                confidence=0.97,
                rationale="After evidence shows the critical zone is clear.",
                after_evidence_frame_id="frame-after",
            ),
            audit_packet=AuditPacket(
                incident_id="incident-one",
                before_frame_id="frame-before",
                after_frame_id="frame-other",
                before_timestamp=datetime(2026, 5, 8, 12, 0, 30, tzinfo=UTC),
                after_timestamp=datetime(2026, 5, 8, 12, 0, 45, tzinfo=UTC),
                alert_transcript="Safety notice: clear the obstruction.",
                verification_verdict=VerificationVerdict.CLEAR,
            ),
            review_sample=ReviewSample(
                incident_id="incident-one",
                before_frame_id="frame-before",
                after_frame_id="frame-after",
                labels=["blocked_robot_workcell", "verified_clear"],
                human_decision=ReviewDecision.PENDING,
                export_status=ExportStatus.LOCAL_ONLY,
            ),
        )


def test_safety_incident_rejects_verified_clear_with_blocked_verdict() -> None:
    with pytest.raises(ValidationError):
        SafetyIncident(
            id="incident-one",
            zone_id="zone-workcell-a2",
            state=IncidentState.VERIFIED_CLEAR,
            severity=Severity.HIGH,
            before_evidence_frame_id="frame-before",
            verification=ClearanceVerification(
                verdict=VerificationVerdict.STILL_BLOCKED,
                confidence=0.97,
                rationale="After evidence still shows an obstruction.",
                after_evidence_frame_id="frame-after",
            ),
        )


def test_demo_timing_rejects_duplicate_modes() -> None:
    with pytest.raises(ValidationError):
        DemoTiming(
            default_mode=DemoTimingMode.STAGE,
            options=[
                DemoTimingOption(
                    mode=DemoTimingMode.STAGE,
                    label="Stage timing",
                    frame_interval_ms=900,
                    playback_dwell_seconds=3,
                    playback_clearance_seconds=2,
                    requires_external_providers=False,
                ),
                DemoTimingOption(
                    mode=DemoTimingMode.STAGE,
                    label="Duplicate stage timing",
                    frame_interval_ms=1200,
                    playback_dwell_seconds=4,
                    playback_clearance_seconds=2,
                    requires_external_providers=False,
                ),
            ],
        )


def test_replay_frame_rejects_mismatched_observation_evidence() -> None:
    evidence_frame = EvidenceFrame(
        id="frame-one",
        source=EvidenceSource.REPLAY,
        timestamp=datetime(2026, 5, 8, 12, 0, 0, tzinfo=UTC),
        image_ref="assets/demo/workcell-clear.svg",
    )

    with pytest.raises(ValidationError):
        ReplayFrame(
            id="replay-frame-clear",
            label="Clear exit",
            evidence_frame=evidence_frame,
            observation=Observation(
                zone_id="zone-workcell-a2",
                observed_state=ObservedState.CLEAR,
                dwell_duration_seconds=0,
                evidence_frame_id="frame-two",
                confidence=0.98,
            ),
            assessment=ObservationAssessment(
                incident_state=IncidentState.CLEAR,
                policy_reason="test",
            ),
        )


def test_demo_replay_rejects_frame_from_another_zone() -> None:
    replay = build_blocked_exit_replay()
    evidence_frame = EvidenceFrame(
        id="frame-one",
        source=EvidenceSource.REPLAY,
        timestamp=datetime(2026, 5, 8, 12, 0, 0, tzinfo=UTC),
        image_ref="assets/demo/workcell-clear.svg",
    )
    replay_frame = ReplayFrame(
        id="replay-frame-clear",
        label="Clear exit",
        evidence_frame=evidence_frame,
        observation=Observation(
            zone_id="zone-other",
            observed_state=ObservedState.CLEAR,
            dwell_duration_seconds=0,
            evidence_frame_id=evidence_frame.id,
            confidence=0.98,
        ),
        assessment=ObservationAssessment(
            incident_state=IncidentState.CLEAR,
            policy_reason="test",
        ),
    )

    with pytest.raises(ValidationError):
        DemoReplay(
            id="blocked-workcell-a2",
            name="Blocked workcell replay",
            zone=CriticalZone(
                id="zone-workcell-a2",
                name="Robot Workcell A-2",
                zone_type=ZoneType.EMERGENCY_EXIT,
                geometry=[
                    ZonePoint(x=0.14, y=0.18),
                    ZonePoint(x=0.58, y=0.18),
                    ZonePoint(x=0.58, y=0.82),
                ],
                policy=CriticalZonePolicy(
                    dwell_threshold_seconds=30,
                    severity=Severity.HIGH,
                    escalation_channel="floor_supervisor",
                ),
            ),
            timing=replay.timing,
            frames=[replay_frame, replay_frame],
        )
