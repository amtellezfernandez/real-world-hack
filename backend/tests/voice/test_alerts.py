from datetime import UTC, datetime

from sitewalk.contracts import (
    EvidenceFrame,
    EvidenceSource,
    Observation,
    ObservedState,
)
from sitewalk.demo_data import PRIMARY_DEMO_ZONE
from sitewalk.safety import assess_observation
from sitewalk.voice.alerts import broadcast_local_audio_alert


def test_local_audio_broadcaster_returns_alert_event() -> None:
    evidence_frame = EvidenceFrame(
        id="frame-workcell-sustained",
        source=EvidenceSource.REPLAY,
        timestamp=datetime(2026, 5, 8, 12, 0, 30, tzinfo=UTC),
        image_ref="assets/demo/workcell-blocked.svg",
    )
    assessment = assess_observation(
        zone=PRIMARY_DEMO_ZONE,
        evidence_frame=evidence_frame,
        observation=Observation(
            zone_id=PRIMARY_DEMO_ZONE.id,
            observed_state=ObservedState.BLOCKED,
            dwell_duration_seconds=30,
            evidence_frame_id=evidence_frame.id,
            confidence=0.94,
        ),
    )

    assert assessment.incident is not None
    alert_event = broadcast_local_audio_alert(
        incident=assessment.incident,
        approval_actor="demo-supervisor",
        timestamp=datetime(2026, 5, 8, 12, 0, 35, tzinfo=UTC),
    )

    assert alert_event.approval_actor == "demo-supervisor"
    assert alert_event.provider == "local_audio"
    assert alert_event.alert_text == (
        "Robotics notice: clear the obstruction at Robot Workcell A-2."
    )
    assert alert_event.audio_ref == "assets/audio/local-alert.wav"
