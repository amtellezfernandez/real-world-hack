from datetime import UTC, datetime

from sitewalk.contracts import (
    EvidenceAnnotation,
    EvidenceFrame,
    EvidenceSource,
    DemoTiming,
    DemoTimingMode,
    DemoTimingOption,
    Observation,
    ObservationReplay,
    ObservationReplayFrame,
    ObservedState,
)
from sitewalk.demo_data import PRIMARY_DEMO_ZONE


def build_blocked_exit_replay() -> ObservationReplay:
    """Build the controlled clear-to-blocked robot workcell replay."""
    return ObservationReplay(
        id="blocked-workcell-a2",
        name="Blocked workcell replay",
        zone=PRIMARY_DEMO_ZONE,
        timing=DemoTiming(
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
                    mode=DemoTimingMode.REAL_TIME,
                    label="Real-time timing",
                    frame_interval_ms=5000,
                    playback_dwell_seconds=30,
                    playback_clearance_seconds=15,
                    requires_external_providers=False,
                ),
            ],
        ),
        frames=[
            build_observation_replay_frame(
                id="replay-frame-clear",
                label="Clear workcell",
                evidence_frame_id="frame-workcell-clear",
                observed_state=ObservedState.CLEAR,
                dwell_seconds=0,
                seconds=0,
                image_ref="assets/demo/workcell-clear.svg",
                annotation_label="zone_clear",
                confidence=0.98,
            ),
            build_observation_replay_frame(
                id="replay-frame-blocked",
                label="Transient blockage",
                evidence_frame_id="frame-workcell-blocked",
                observed_state=ObservedState.BLOCKED,
                dwell_seconds=8,
                seconds=8,
                image_ref="assets/demo/workcell-blocked.svg",
                annotation_label="zone_overlap",
                confidence=0.94,
            ),
            build_observation_replay_frame(
                id="replay-frame-incident",
                label="Sustained blockage",
                evidence_frame_id="frame-workcell-sustained-blocked",
                observed_state=ObservedState.BLOCKED,
                dwell_seconds=30,
                seconds=30,
                image_ref="assets/demo/workcell-blocked.svg",
                annotation_label="zone_overlap",
                confidence=0.94,
            ),
            build_observation_replay_frame(
                id="replay-frame-still-blocked",
                label="Still blocked",
                evidence_frame_id="frame-workcell-still-blocked",
                observed_state=ObservedState.BLOCKED,
                dwell_seconds=40,
                seconds=40,
                image_ref="assets/demo/workcell-blocked.svg",
                annotation_label="zone_overlap",
                confidence=0.92,
            ),
            build_observation_replay_frame(
                id="replay-frame-verified-clear",
                label="Verified clear",
                evidence_frame_id="frame-workcell-after-clear",
                observed_state=ObservedState.CLEAR,
                dwell_seconds=0,
                seconds=45,
                image_ref="assets/demo/workcell-clear.svg",
                annotation_label="zone_clear",
                confidence=0.97,
            ),
        ],
    )


def build_observation_replay_frame(
    *,
    id: str,
    label: str,
    evidence_frame_id: str,
    observed_state: ObservedState,
    dwell_seconds: float,
    seconds: int,
    image_ref: str,
    annotation_label: str,
    confidence: float,
) -> ObservationReplayFrame:
    evidence_frame = EvidenceFrame(
        id=evidence_frame_id,
        source=EvidenceSource.REPLAY,
        timestamp=datetime(2026, 5, 8, 12, 0, seconds, tzinfo=UTC),
        image_ref=image_ref,
        annotations=[
            EvidenceAnnotation(label=annotation_label, confidence=confidence),
        ],
    )

    return ObservationReplayFrame(
        id=id,
        label=label,
        evidence_frame=evidence_frame,
        observation=Observation(
            zone_id=PRIMARY_DEMO_ZONE.id,
            observed_state=observed_state,
            dwell_duration_seconds=dwell_seconds,
            evidence_frame_id=evidence_frame.id,
            confidence=confidence,
        ),
    )


BLOCKED_EXIT_OBSERVATION_REPLAY = build_blocked_exit_replay()
