from sitewalk.contracts import (
    AuditPacket,
    EvidenceFrame,
    ExportStatus,
    IncidentState,
    ReviewSample,
    ReviewDecision,
    SafetyIncident,
    VerificationVerdict,
)


def attach_local_evidence_package(
    *,
    incident: SafetyIncident,
    before_evidence_frame: EvidenceFrame,
    after_evidence_frame: EvidenceFrame,
) -> SafetyIncident:
    """Attach local audit and review records, then close a verified incident."""
    if incident.state != IncidentState.VERIFIED_CLEAR:
        raise ValueError(
            "only verified_clear incidents can receive an evidence package",
        )

    if incident.verification is None:
        raise ValueError("closed incident evidence package requires verification")

    if incident.verification.verdict != VerificationVerdict.CLEAR:
        raise ValueError("evidence package requires a clear verification verdict")

    if incident.before_evidence_frame_id != before_evidence_frame.id:
        raise ValueError("before evidence frame must match incident before frame id")

    if incident.verification.after_evidence_frame_id != after_evidence_frame.id:
        raise ValueError("after evidence frame must match verification after frame id")

    if len(incident.alert_events) == 0:
        raise ValueError(
            "closed incident evidence package requires an alert transcript"
        )

    audit_packet = AuditPacket(
        incident_id=incident.id,
        before_frame_id=before_evidence_frame.id,
        after_frame_id=after_evidence_frame.id,
        before_timestamp=before_evidence_frame.timestamp,
        after_timestamp=after_evidence_frame.timestamp,
        alert_transcript=incident.alert_events[-1].alert_text,
        verification_verdict=incident.verification.verdict,
    )
    review_sample = ReviewSample(
        incident_id=incident.id,
        before_frame_id=before_evidence_frame.id,
        after_frame_id=after_evidence_frame.id,
        labels=["blocked_robot_workcell", "verified_clear"],
        human_decision=ReviewDecision.PENDING,
        export_status=ExportStatus.LOCAL_ONLY,
    )

    return SafetyIncident(
        id=incident.id,
        zone_id=incident.zone_id,
        state=IncidentState.CLOSED,
        severity=incident.severity,
        before_evidence_frame_id=incident.before_evidence_frame_id,
        incident_report=incident.incident_report,
        alert_events=incident.alert_events,
        verification=incident.verification,
        audit_packet=audit_packet,
        review_sample=review_sample,
    )
