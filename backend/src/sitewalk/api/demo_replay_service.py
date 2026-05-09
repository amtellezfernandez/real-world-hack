from datetime import UTC, datetime

from sitewalk.contracts import (
    AlertEvent,
    DemoReplay,
    EvidenceFrame,
    IncidentState,
    ObservationAssessment,
    ObservationReplay,
    ObservationReplayFrame,
    ReplayFrame,
    SafetyIncident,
)
from sitewalk.review_export import attach_local_evidence_package
from sitewalk.safety import assess_observation
from sitewalk.verification import verify_clearance


def assess_demo_replay(replay: ObservationReplay) -> DemoReplay:
    """Apply safety lifecycle policy to a perception replay."""
    assessed_frames, after_frames = build_incident_replay_frames(replay)
    alert_frame = build_approved_alert_frame(assessed_frames)
    before_evidence_frame = get_before_evidence_frame(
        frames=assessed_frames,
        incident=alert_frame.assessment.incident,
    )

    return DemoReplay(
        id=replay.id,
        name=replay.name,
        zone=replay.zone,
        timing=replay.timing,
        frames=[
            *assessed_frames,
            alert_frame,
            *build_verification_frames(
                alert_frame=alert_frame,
                before_evidence_frame=before_evidence_frame,
                after_frames=after_frames,
            ),
        ],
    )


def build_incident_replay_frames(
    replay: ObservationReplay,
) -> tuple[list[ReplayFrame], list[ObservationReplayFrame]]:
    assessed_frames: list[ReplayFrame] = []

    for index, source_frame in enumerate(replay.frames):
        assessed_frame = build_assessed_replay_frame(replay, source_frame)
        assessed_frames.append(assessed_frame)

        if assessed_frame.assessment.incident_state == IncidentState.INCIDENT_OPEN:
            return assessed_frames, replay.frames[index + 1 :]

    return assessed_frames, []


def build_assessed_replay_frame(
    replay: ObservationReplay,
    source_frame: ObservationReplayFrame,
) -> ReplayFrame:
    return build_replay_frame(
        source_frame=source_frame,
        assessment=assess_observation(
            zone=replay.zone,
            evidence_frame=source_frame.evidence_frame,
            observation=source_frame.observation,
        ),
    )


def build_replay_frame(
    *,
    source_frame: ObservationReplayFrame,
    assessment: ObservationAssessment,
) -> ReplayFrame:
    return ReplayFrame(
        id=source_frame.id,
        label=source_frame.label,
        evidence_frame=source_frame.evidence_frame,
        observation=source_frame.observation,
        assessment=assessment,
    )


def build_approved_alert_frame(assessed_frames: list[ReplayFrame]) -> ReplayFrame:
    source_frame = assessed_frames[-1]
    source_assessment = source_frame.assessment

    if source_assessment.incident is None:
        raise ValueError("demo alert frame requires an open incident")

    approved_incident = approve_incident_alert(
        incident=source_assessment.incident,
        approval_actor="demo-supervisor",
        timestamp=datetime(2026, 5, 8, 12, 0, 35, tzinfo=UTC),
    )

    return ReplayFrame(
        id="replay-frame-alert-broadcast",
        label="Approved alert",
        evidence_frame=source_frame.evidence_frame,
        observation=source_frame.observation,
        assessment=ObservationAssessment(
            incident_state=IncidentState.ALERT_BROADCAST,
            policy_reason="Supervisor approved the local floor alert.",
            incident=approved_incident,
        ),
    )


def build_verification_frames(
    *,
    alert_frame: ReplayFrame,
    before_evidence_frame: EvidenceFrame,
    after_frames: list[ObservationReplayFrame],
) -> list[ReplayFrame]:
    current_incident = alert_frame.assessment.incident
    if current_incident is None:
        raise ValueError("verification frames require an alert-broadcast incident")

    verification_frames: list[ReplayFrame] = []

    for source_frame in after_frames:
        if current_incident.state == IncidentState.CLOSED:
            break

        replay_frame = build_verification_frame(
            incident=current_incident,
            before_evidence_frame=before_evidence_frame,
            source_frame=source_frame,
        )

        verified_incident = replay_frame.assessment.incident
        if verified_incident is None:
            raise ValueError("verification frame requires an incident")

        current_incident = verified_incident
        verification_frames.append(replay_frame)

    return verification_frames


def get_before_evidence_frame(
    *,
    frames: list[ReplayFrame],
    incident: SafetyIncident | None,
) -> EvidenceFrame:
    if incident is None:
        raise ValueError("before evidence lookup requires an incident")

    for frame in frames:
        if frame.evidence_frame.id == incident.before_evidence_frame_id:
            return frame.evidence_frame

    raise ValueError("incident before evidence frame not found in replay")


def build_verification_frame(
    *,
    incident: SafetyIncident,
    before_evidence_frame: EvidenceFrame,
    source_frame: ObservationReplayFrame,
) -> ReplayFrame:
    verified_incident = verify_clearance(
        incident=incident,
        after_evidence_frame=source_frame.evidence_frame,
        after_observation=source_frame.observation,
    )
    if verified_incident.state == IncidentState.VERIFIED_CLEAR:
        verified_incident = attach_local_evidence_package(
            incident=verified_incident,
            before_evidence_frame=before_evidence_frame,
            after_evidence_frame=source_frame.evidence_frame,
        )

    verification = verified_incident.verification

    if verification is None:
        raise ValueError("verified incident requires clearance verification")

    return build_replay_frame(
        source_frame=source_frame,
        assessment=ObservationAssessment(
            incident_state=verified_incident.state,
            policy_reason=verification.rationale,
            incident=verified_incident,
        ),
    )


def approve_incident_alert(
    *,
    incident: SafetyIncident,
    approval_actor: str,
    timestamp: datetime,
) -> SafetyIncident:
    if incident.state != IncidentState.INCIDENT_OPEN:
        raise ValueError("only incident_open incidents can be approved for alert")

    if incident.incident_report is None:
        raise ValueError("incident must include an incident report before alerting")

    alert_event = AlertEvent(
        incident_id=incident.id,
        approval_actor=approval_actor,
        alert_text=incident.incident_report.alert_text_candidate,
        timestamp=timestamp.isoformat(),
    )

    return SafetyIncident(
        id=incident.id,
        zone_id=incident.zone_id,
        state=IncidentState.ALERT_BROADCAST,
        severity=incident.severity,
        before_evidence_frame_id=incident.before_evidence_frame_id,
        incident_report=incident.incident_report,
        alert_events=[*incident.alert_events, alert_event],
        verification=incident.verification,
        audit_packet=incident.audit_packet,
        review_sample=incident.review_sample,
    )
