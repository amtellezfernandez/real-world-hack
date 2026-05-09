from sitewalk.contracts import (
    CriticalZone,
    EvidenceFrame,
    IncidentState,
    IncidentReport,
    Observation,
    ObservationAssessment,
    ObservedState,
    SafetyIncident,
)


def format_dwell_progress_reason(
    *,
    dwell_seconds: float,
    threshold_seconds: float,
) -> str:
    """Format policy reason for blocked observations still below threshold."""
    return f"Blocked for {dwell_seconds}s of {threshold_seconds}s dwell threshold."


def format_dwell_met_reason(
    *,
    dwell_seconds: float,
    threshold_seconds: float,
) -> str:
    """Format policy reason for blocked observations that meet threshold."""
    return f"Blocked for {dwell_seconds}s, meeting the {threshold_seconds}s dwell threshold."


def assess_observation(
    *,
    zone: CriticalZone,
    evidence_frame: EvidenceFrame,
    observation: Observation,
) -> ObservationAssessment:
    """Assess an evidence-backed observation against zone policy."""
    if observation.zone_id != zone.id:
        raise ValueError("observation zone_id must match zone id")

    if observation.evidence_frame_id != evidence_frame.id:
        raise ValueError("observation evidence_frame_id must match evidence frame id")

    match observation.observed_state:
        case ObservedState.CLEAR:
            return ObservationAssessment(
                incident_state=IncidentState.CLEAR,
                policy_reason="Zone is clear.",
            )
        case ObservedState.UNCERTAIN:
            return ObservationAssessment(
                incident_state=IncidentState.UNCERTAIN,
                policy_reason="Observation is uncertain.",
            )
        case ObservedState.CAMERA_UNAVAILABLE:
            return ObservationAssessment(
                incident_state=IncidentState.UNCERTAIN,
                policy_reason="Camera feed is unavailable.",
            )
        case ObservedState.BLOCKED:
            if observation.dwell_duration_seconds < zone.policy.dwell_threshold_seconds:
                return ObservationAssessment(
                    incident_state=IncidentState.DWELL,
                    policy_reason=format_dwell_progress_reason(
                        dwell_seconds=observation.dwell_duration_seconds,
                        threshold_seconds=zone.policy.dwell_threshold_seconds,
                    ),
                )

            return ObservationAssessment(
                incident_state=IncidentState.INCIDENT_OPEN,
                policy_reason=format_dwell_met_reason(
                    dwell_seconds=observation.dwell_duration_seconds,
                    threshold_seconds=zone.policy.dwell_threshold_seconds,
                ),
                incident=build_blocked_workcell_incident(
                    zone=zone,
                    evidence_frame=evidence_frame,
                    dwell_seconds=observation.dwell_duration_seconds,
                ),
            )


def build_blocked_workcell_incident(
    *,
    zone: CriticalZone,
    evidence_frame: EvidenceFrame,
    dwell_seconds: float,
) -> SafetyIncident:
    """Build the deterministic incident opened by sustained blocked workcells."""
    return SafetyIncident(
        id=f"incident-{zone.id}-{evidence_frame.id}",
        zone_id=zone.id,
        state=IncidentState.INCIDENT_OPEN,
        severity=zone.policy.severity,
        before_evidence_frame_id=evidence_frame.id,
        incident_report=IncidentReport(
            hazard="Blocked robot workcell",
            severity=zone.policy.severity,
            evidence_summary=(
                f"{evidence_frame.id} shows {zone.name} blocked for {dwell_seconds}s."
            ),
            rationale=(
                f"{zone.name} has been blocked for {dwell_seconds}s, meeting "
                f"the {zone.policy.dwell_threshold_seconds}s dwell threshold."
            ),
            recommended_action="Dispatch a robotics supervisor to clear the obstruction.",
            alert_text_candidate=f"Robotics notice: clear the obstruction at {zone.name}.",
        ),
    )
