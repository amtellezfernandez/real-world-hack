from datetime import datetime

from sitewalk.contracts import AlertEvent, AlertProvider, SafetyIncident


def broadcast_local_audio_alert(
    *,
    incident: SafetyIncident,
    approval_actor: str,
    timestamp: datetime,
) -> AlertEvent:
    """Return the local audio alert event for a human-approved incident."""
    if incident.incident_report is None:
        raise ValueError("incident must include an incident report before alerting")

    return AlertEvent(
        incident_id=incident.id,
        approval_actor=approval_actor,
        alert_text=incident.incident_report.alert_text_candidate,
        provider=AlertProvider.LOCAL_AUDIO,
        timestamp=timestamp.isoformat(),
        audio_ref="assets/audio/local-alert.wav",
    )
