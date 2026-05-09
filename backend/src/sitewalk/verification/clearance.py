from sitewalk.contracts import (
    ClearanceVerification,
    EvidenceFrame,
    IncidentState,
    Observation,
    ObservedState,
    SafetyIncident,
    VerificationVerdict,
)
from sitewalk.providers.ports import ClearanceVerifier


def verify_clearance(
    *,
    incident: SafetyIncident,
    after_evidence_frame: EvidenceFrame,
    after_observation: Observation,
) -> SafetyIncident:
    """Verify whether after evidence clears an alerted or clearing incident."""
    validate_clearance_inputs(
        incident=incident,
        after_evidence_frame=after_evidence_frame,
        after_observation=after_observation,
    )

    verification = build_clearance_verification(
        after_evidence_frame=after_evidence_frame,
        after_observation=after_observation,
    )
    next_state = (
        IncidentState.VERIFIED_CLEAR
        if verification.verdict == VerificationVerdict.CLEAR
        else IncidentState.CLEARING
    )
    return build_verified_incident(
        incident=incident,
        state=next_state,
        verification=verification,
    )


def build_clearance_verification(
    *,
    after_evidence_frame: EvidenceFrame,
    after_observation: Observation,
) -> ClearanceVerification:
    """Build the deterministic clearance verification for after evidence."""
    match after_observation.observed_state:
        case ObservedState.CLEAR:
            return ClearanceVerification(
                verdict=VerificationVerdict.CLEAR,
                confidence=after_observation.confidence or 0,
                rationale="After evidence shows the critical zone is clear.",
                after_evidence_frame_id=after_evidence_frame.id,
            )
        case ObservedState.BLOCKED:
            return ClearanceVerification(
                verdict=VerificationVerdict.STILL_BLOCKED,
                confidence=after_observation.confidence or 0,
                rationale=(
                    "After evidence still shows an obstruction in the critical zone."
                ),
                after_evidence_frame_id=after_evidence_frame.id,
            )
        case ObservedState.UNCERTAIN | ObservedState.CAMERA_UNAVAILABLE:
            return ClearanceVerification(
                verdict=VerificationVerdict.UNCERTAIN,
                confidence=after_observation.confidence or 0,
                rationale="After evidence is insufficient to verify clearance.",
                after_evidence_frame_id=after_evidence_frame.id,
            )


def validate_clearance_inputs(
    *,
    incident: SafetyIncident,
    after_evidence_frame: EvidenceFrame,
    after_observation: Observation,
) -> None:
    """Validate deterministic clearance verifier preconditions."""
    if incident.state not in {IncidentState.ALERT_BROADCAST, IncidentState.CLEARING}:
        raise ValueError(
            "only alert_broadcast or clearing incidents can be verified for closure",
        )

    if after_observation.evidence_frame_id != after_evidence_frame.id:
        raise ValueError(
            "after observation evidence_frame_id must match evidence frame id"
        )

    if after_observation.zone_id != incident.zone_id:
        raise ValueError("after observation zone_id must match incident zone id")


def build_local_clearance_verifier() -> ClearanceVerifier:
    """Build the deterministic verifier behind the clearance port."""

    async def verify(
        incident: SafetyIncident,
        after_evidence_frame: EvidenceFrame,
        after_observation: Observation,
    ) -> ClearanceVerification:
        validate_clearance_inputs(
            incident=incident,
            after_evidence_frame=after_evidence_frame,
            after_observation=after_observation,
        )

        return build_clearance_verification(
            after_evidence_frame=after_evidence_frame,
            after_observation=after_observation,
        )

    return verify


def build_verified_incident(
    *,
    incident: SafetyIncident,
    state: IncidentState,
    verification: ClearanceVerification,
) -> SafetyIncident:
    """Copy incident data while applying a clearance verification result."""
    return SafetyIncident(
        id=incident.id,
        zone_id=incident.zone_id,
        state=state,
        severity=incident.severity,
        before_evidence_frame_id=incident.before_evidence_frame_id,
        incident_report=incident.incident_report,
        alert_events=incident.alert_events,
        verification=verification,
        audit_packet=incident.audit_packet,
        review_sample=incident.review_sample,
    )
