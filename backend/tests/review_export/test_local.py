from datetime import UTC, datetime

import pytest

from sitewalk.contracts import (
    AlertEvent,
    ClearanceVerification,
    EvidenceFrame,
    EvidenceSource,
    ExportStatus,
    IncidentReport,
    IncidentState,
    ReviewSample,
    ReviewDecision,
    SafetyIncident,
    Severity,
    VerificationVerdict,
)
from sitewalk.review_export.local import attach_local_evidence_package


def make_frame(*, frame_id: str, seconds: int, image_ref: str) -> EvidenceFrame:
    return EvidenceFrame(
        id=frame_id,
        source=EvidenceSource.REPLAY,
        timestamp=datetime(2026, 5, 8, 12, 0, seconds, tzinfo=UTC),
        image_ref=image_ref,
    )


def make_verified_clear_incident() -> SafetyIncident:
    return SafetyIncident(
        id="incident-zone-workcell-a2-frame-workcell-sustained-blocked",
        zone_id="zone-workcell-a2",
        state=IncidentState.VERIFIED_CLEAR,
        severity=Severity.HIGH,
        before_evidence_frame_id="frame-workcell-sustained-blocked",
        incident_report=IncidentReport(
            hazard="Blocked robot workcell",
            severity=Severity.HIGH,
            evidence_summary=(
                "frame-workcell-sustained-blocked shows Robot Workcell A-2 blocked."
            ),
            rationale="Robot Workcell A-2 has been blocked for 30.0s.",
            recommended_action="Dispatch a floor supervisor to clear the obstruction.",
            alert_text_candidate="Robotics notice: clear the obstruction at Robot Workcell A-2.",
        ),
        alert_events=[
            AlertEvent(
                incident_id="incident-zone-workcell-a2-frame-workcell-sustained-blocked",
                approval_actor="demo-supervisor",
                alert_text="Robotics notice: clear the obstruction at Robot Workcell A-2.",
                timestamp="2026-05-08T12:00:35+00:00",
            ),
        ],
        verification=ClearanceVerification(
            verdict=VerificationVerdict.CLEAR,
            confidence=0.97,
            rationale="After evidence shows the critical zone is clear.",
            after_evidence_frame_id="frame-workcell-after-clear",
        ),
    )


def test_attach_local_evidence_package_builds_audit_and_review_sample() -> None:
    before_frame = make_frame(
        frame_id="frame-workcell-sustained-blocked",
        seconds=30,
        image_ref="assets/demo/workcell-blocked.svg",
    )
    after_frame = make_frame(
        frame_id="frame-workcell-after-clear",
        seconds=45,
        image_ref="assets/demo/workcell-clear.svg",
    )

    incident = attach_local_evidence_package(
        incident=make_verified_clear_incident(),
        before_evidence_frame=before_frame,
        after_evidence_frame=after_frame,
    )

    assert incident.state == IncidentState.CLOSED
    assert incident.audit_packet is not None
    assert incident.audit_packet.incident_id == incident.id
    assert incident.audit_packet.before_frame_id == before_frame.id
    assert incident.audit_packet.after_frame_id == after_frame.id
    assert incident.audit_packet.before_timestamp == before_frame.timestamp
    assert incident.audit_packet.after_timestamp == after_frame.timestamp
    assert incident.audit_packet.alert_transcript == (
        "Robotics notice: clear the obstruction at Robot Workcell A-2."
    )
    assert incident.audit_packet.verification_verdict == VerificationVerdict.CLEAR
    assert incident.review_sample == ReviewSample(
        incident_id=incident.id,
        before_frame_id=before_frame.id,
        after_frame_id=after_frame.id,
        labels=["blocked_robot_workcell", "verified_clear"],
        human_decision=ReviewDecision.PENDING,
        export_status=ExportStatus.LOCAL_ONLY,
    )


def test_attach_local_evidence_package_rejects_open_incident() -> None:
    open_incident = make_verified_clear_incident()
    open_incident = SafetyIncident(
        id=open_incident.id,
        zone_id=open_incident.zone_id,
        state=IncidentState.CLEARING,
        severity=open_incident.severity,
        before_evidence_frame_id=open_incident.before_evidence_frame_id,
        incident_report=open_incident.incident_report,
        alert_events=open_incident.alert_events,
        verification=open_incident.verification,
    )

    with pytest.raises(ValueError, match="verified_clear incidents"):
        attach_local_evidence_package(
            incident=open_incident,
            before_evidence_frame=make_frame(
                frame_id="frame-workcell-sustained-blocked",
                seconds=30,
                image_ref="assets/demo/workcell-blocked.svg",
            ),
            after_evidence_frame=make_frame(
                frame_id="frame-workcell-after-clear",
                seconds=45,
                image_ref="assets/demo/workcell-clear.svg",
            ),
        )
