from datetime import UTC, datetime

import pytest

from sitewalk.api.demo_replay_service import approve_incident_alert
from sitewalk.contracts import (
    EvidenceFrame,
    EvidenceSource,
    IncidentState,
    Observation,
    ObservedState,
    SafetyIncident,
    VerificationVerdict,
)
from sitewalk.demo_data import PRIMARY_DEMO_ZONE
from sitewalk.safety import assess_observation
from sitewalk.verification.clearance import (
    build_local_clearance_verifier,
    verify_clearance,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def make_evidence_frame(
    *,
    frame_id: str,
    seconds: int,
    image_ref: str,
) -> EvidenceFrame:
    return EvidenceFrame(
        id=frame_id,
        source=EvidenceSource.REPLAY,
        timestamp=datetime(2026, 5, 8, 12, 0, seconds, tzinfo=UTC),
        image_ref=image_ref,
    )


def make_observation(
    *,
    evidence_frame: EvidenceFrame,
    observed_state: ObservedState,
    dwell_seconds: float,
) -> Observation:
    return Observation(
        zone_id=PRIMARY_DEMO_ZONE.id,
        observed_state=observed_state,
        dwell_duration_seconds=dwell_seconds,
        evidence_frame_id=evidence_frame.id,
        confidence=0.94,
    )


def make_alert_broadcast_incident() -> tuple[EvidenceFrame, SafetyIncident]:
    before_frame = make_evidence_frame(
        frame_id="frame-workcell-sustained",
        seconds=30,
        image_ref="assets/demo/workcell-blocked.svg",
    )
    assessment = assess_observation(
        zone=PRIMARY_DEMO_ZONE,
        evidence_frame=before_frame,
        observation=make_observation(
            evidence_frame=before_frame,
            observed_state=ObservedState.BLOCKED,
            dwell_seconds=30,
        ),
    )

    assert assessment.incident is not None
    return before_frame, approve_incident_alert(
        incident=assessment.incident,
        approval_actor="demo-supervisor",
        timestamp=datetime(2026, 5, 8, 12, 0, 35, tzinfo=UTC),
    )


def test_blocked_after_evidence_keeps_incident_open() -> None:
    _, incident = make_alert_broadcast_incident()
    after_frame = make_evidence_frame(
        frame_id="frame-workcell-still-blocked",
        seconds=40,
        image_ref="assets/demo/workcell-blocked.svg",
    )

    verified_incident = verify_clearance(
        incident=incident,
        after_evidence_frame=after_frame,
        after_observation=make_observation(
            evidence_frame=after_frame,
            observed_state=ObservedState.BLOCKED,
            dwell_seconds=40,
        ),
    )

    assert verified_incident.state == IncidentState.CLEARING
    assert verified_incident.verification is not None
    assert verified_incident.verification.verdict == VerificationVerdict.STILL_BLOCKED
    assert verified_incident.verification.after_evidence_frame_id == after_frame.id


def test_clear_after_evidence_marks_incident_verified_clear() -> None:
    _, incident = make_alert_broadcast_incident()
    after_frame = make_evidence_frame(
        frame_id="frame-workcell-after-clear",
        seconds=45,
        image_ref="assets/demo/workcell-clear.svg",
    )

    verified_incident = verify_clearance(
        incident=incident,
        after_evidence_frame=after_frame,
        after_observation=make_observation(
            evidence_frame=after_frame,
            observed_state=ObservedState.CLEAR,
            dwell_seconds=0,
        ),
    )

    assert verified_incident.state == IncidentState.VERIFIED_CLEAR
    assert verified_incident.verification is not None
    assert verified_incident.verification.verdict == VerificationVerdict.CLEAR
    assert verified_incident.verification.after_evidence_frame_id == after_frame.id
    assert verified_incident.alert_events == incident.alert_events


async def test_local_clearance_verifier_uses_clearance_port_contract() -> None:
    _, incident = make_alert_broadcast_incident()
    after_frame = make_evidence_frame(
        frame_id="frame-workcell-after-clear",
        seconds=45,
        image_ref="assets/demo/workcell-clear.svg",
    )
    verifier = build_local_clearance_verifier()

    verification = await verifier(
        incident,
        after_frame,
        make_observation(
            evidence_frame=after_frame,
            observed_state=ObservedState.CLEAR,
            dwell_seconds=0,
        ),
    )

    assert verification.verdict == VerificationVerdict.CLEAR
    assert verification.after_evidence_frame_id == after_frame.id


def test_clear_after_still_blocked_evidence_marks_incident_verified_clear() -> None:
    _, incident = make_alert_broadcast_incident()
    still_blocked_frame = make_evidence_frame(
        frame_id="frame-workcell-still-blocked",
        seconds=40,
        image_ref="assets/demo/workcell-blocked.svg",
    )
    clear_frame = make_evidence_frame(
        frame_id="frame-workcell-after-clear",
        seconds=45,
        image_ref="assets/demo/workcell-clear.svg",
    )

    clearing_incident = verify_clearance(
        incident=incident,
        after_evidence_frame=still_blocked_frame,
        after_observation=make_observation(
            evidence_frame=still_blocked_frame,
            observed_state=ObservedState.BLOCKED,
            dwell_seconds=40,
        ),
    )
    verified_incident = verify_clearance(
        incident=clearing_incident,
        after_evidence_frame=clear_frame,
        after_observation=make_observation(
            evidence_frame=clear_frame,
            observed_state=ObservedState.CLEAR,
            dwell_seconds=0,
        ),
    )

    assert verified_incident.state == IncidentState.VERIFIED_CLEAR
    assert verified_incident.verification is not None
    assert verified_incident.verification.verdict == VerificationVerdict.CLEAR
    assert verified_incident.verification.after_evidence_frame_id == clear_frame.id


def test_uncertain_after_evidence_keeps_incident_open_for_review() -> None:
    _, incident = make_alert_broadcast_incident()
    after_frame = make_evidence_frame(
        frame_id="frame-workcell-after-uncertain",
        seconds=45,
        image_ref="assets/demo/workcell-clear.svg",
    )

    verified_incident = verify_clearance(
        incident=incident,
        after_evidence_frame=after_frame,
        after_observation=make_observation(
            evidence_frame=after_frame,
            observed_state=ObservedState.UNCERTAIN,
            dwell_seconds=0,
        ),
    )

    assert verified_incident.state == IncidentState.CLEARING
    assert verified_incident.verification is not None
    assert verified_incident.verification.verdict == VerificationVerdict.UNCERTAIN
