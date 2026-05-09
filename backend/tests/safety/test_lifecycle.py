from datetime import UTC, datetime

from sitewalk.contracts import (
    EvidenceFrame,
    EvidenceSource,
    IncidentState,
    Observation,
    ObservedState,
)
from sitewalk.demo_data import PRIMARY_DEMO_ZONE
from sitewalk.safety.lifecycle import assess_observation


def make_evidence_frame(frame_id: str, seconds: int) -> EvidenceFrame:
    return EvidenceFrame(
        id=frame_id,
        source=EvidenceSource.REPLAY,
        timestamp=datetime(2026, 5, 8, 12, 0, seconds, tzinfo=UTC),
        image_ref="assets/demo/workcell-blocked.svg",
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


def test_transient_blockage_remains_in_dwell_without_incident() -> None:
    evidence_frame = make_evidence_frame("frame-workcell-transient", 8)

    assessment = assess_observation(
        zone=PRIMARY_DEMO_ZONE,
        evidence_frame=evidence_frame,
        observation=make_observation(
            evidence_frame=evidence_frame,
            observed_state=ObservedState.BLOCKED,
            dwell_seconds=8,
        ),
    )

    assert assessment.incident_state == IncidentState.DWELL
    assert assessment.incident is None
    assert "8.0s of 30.0s" in assessment.policy_reason


def test_sustained_blockage_opens_high_severity_incident() -> None:
    evidence_frame = make_evidence_frame("frame-workcell-sustained", 30)

    assessment = assess_observation(
        zone=PRIMARY_DEMO_ZONE,
        evidence_frame=evidence_frame,
        observation=make_observation(
            evidence_frame=evidence_frame,
            observed_state=ObservedState.BLOCKED,
            dwell_seconds=30,
        ),
    )

    assert assessment.incident_state == IncidentState.INCIDENT_OPEN
    assert assessment.incident is not None
    assert assessment.incident.zone_id == PRIMARY_DEMO_ZONE.id
    assert assessment.incident.severity == PRIMARY_DEMO_ZONE.policy.severity
    assert assessment.incident.before_evidence_frame_id == evidence_frame.id
    assert assessment.incident.incident_report is not None
    assert assessment.incident.incident_report.hazard == "Blocked robot workcell"


def test_uncertain_observation_does_not_become_clear() -> None:
    evidence_frame = make_evidence_frame("frame-workcell-uncertain", 12)

    assessment = assess_observation(
        zone=PRIMARY_DEMO_ZONE,
        evidence_frame=evidence_frame,
        observation=make_observation(
            evidence_frame=evidence_frame,
            observed_state=ObservedState.UNCERTAIN,
            dwell_seconds=0,
        ),
    )

    assert assessment.incident_state == IncidentState.UNCERTAIN
    assert assessment.incident is None
    assert assessment.policy_reason == "Observation is uncertain."


def test_camera_unavailable_observation_does_not_become_clear() -> None:
    evidence_frame = make_evidence_frame("frame-workcell-unavailable", 12)

    assessment = assess_observation(
        zone=PRIMARY_DEMO_ZONE,
        evidence_frame=evidence_frame,
        observation=make_observation(
            evidence_frame=evidence_frame,
            observed_state=ObservedState.CAMERA_UNAVAILABLE,
            dwell_seconds=0,
        ),
    )

    assert assessment.incident_state == IncidentState.UNCERTAIN
    assert assessment.incident is None
    assert assessment.policy_reason == "Camera feed is unavailable."
