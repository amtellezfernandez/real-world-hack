from datetime import UTC, datetime

import pytest

from sitewalk.contracts import (
    CriticalZone,
    CriticalZonePolicy,
    EvidenceFrame,
    EvidenceSource,
    IncidentState,
    ObservedState,
    Severity,
    ZonePoint,
    ZoneType,
)
from sitewalk.demo_data import PRIMARY_DEMO_ZONE
from sitewalk.perception.runpod_yolo import (
    YoloBox,
    YoloDetection,
    YoloFrameDetections,
    build_yolo_perception_source,
)
from sitewalk.safety.lifecycle import assess_observation

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def make_frame(frame_id: str) -> EvidenceFrame:
    return EvidenceFrame(
        id=frame_id,
        source=EvidenceSource.CAMERA,
        timestamp=datetime(2026, 5, 8, 12, 0, 0, tzinfo=UTC),
        image_ref=f"camera://dock/{frame_id}",
    )


def make_triangle_zone() -> CriticalZone:
    return CriticalZone(
        id="zone-triangle",
        name="Triangular test zone",
        zone_type=ZoneType.WALKWAY,
        geometry=[
            ZonePoint(x=0.1, y=0.1),
            ZonePoint(x=0.9, y=0.1),
            ZonePoint(x=0.1, y=0.9),
        ],
        policy=CriticalZonePolicy(
            dwell_threshold_seconds=30,
            severity=Severity.HIGH,
            escalation_channel="floor_supervisor",
        ),
    )


async def test_yolo_zone_overlap_enters_existing_perception_port() -> None:
    evidence_frame = make_frame("frame-runpod-overlap")
    perception_source = build_yolo_perception_source(
        frame_detections=[
            YoloFrameDetections(
                frame_id=evidence_frame.id,
                detections=[
                    YoloDetection(
                        label="pallet",
                        confidence=0.93,
                        box=YoloBox(x_min=0.42, y_min=0.42, x_max=0.72, y_max=0.82),
                    ),
                ],
            ),
        ],
        resolve_dwell_seconds=lambda frame, zone: 8,
    )

    observation = await perception_source(evidence_frame, PRIMARY_DEMO_ZONE)
    assessment = assess_observation(
        zone=PRIMARY_DEMO_ZONE,
        evidence_frame=evidence_frame,
        observation=observation,
    )

    assert observation.zone_id == PRIMARY_DEMO_ZONE.id
    assert observation.evidence_frame_id == evidence_frame.id
    assert observation.observed_state == ObservedState.BLOCKED
    assert observation.dwell_duration_seconds == 8
    assert observation.confidence == 0.93
    assert assessment.incident_state == IncidentState.DWELL


async def test_low_confidence_yolo_overlap_is_uncertain() -> None:
    evidence_frame = make_frame("frame-runpod-low-confidence")
    perception_source = build_yolo_perception_source(
        frame_detections=[
            YoloFrameDetections(
                frame_id=evidence_frame.id,
                detections=[
                    YoloDetection(
                        label="pallet",
                        confidence=0.34,
                        box=YoloBox(x_min=0.42, y_min=0.42, x_max=0.72, y_max=0.82),
                    ),
                ],
            ),
        ],
    )

    observation = await perception_source(evidence_frame, PRIMARY_DEMO_ZONE)

    assert observation.observed_state == ObservedState.UNCERTAIN
    assert observation.dwell_duration_seconds == 0
    assert observation.confidence == 0.34


async def test_yolo_detection_outside_zone_reports_clear_without_confidence() -> None:
    evidence_frame = make_frame("frame-runpod-outside-zone")
    perception_source = build_yolo_perception_source(
        frame_detections=[
            YoloFrameDetections(
                frame_id=evidence_frame.id,
                detections=[
                    YoloDetection(
                        label="pallet",
                        confidence=0.91,
                        box=YoloBox(x_min=0.72, y_min=0.18, x_max=0.92, y_max=0.48),
                    ),
                ],
            ),
        ],
    )

    observation = await perception_source(evidence_frame, PRIMARY_DEMO_ZONE)

    assert observation.observed_state == ObservedState.CLEAR
    assert observation.dwell_duration_seconds == 0
    assert observation.confidence is None


async def test_yolo_detection_inside_zone_bounds_but_outside_polygon_is_clear() -> None:
    evidence_frame = make_frame("frame-runpod-outside-polygon")
    perception_source = build_yolo_perception_source(
        frame_detections=[
            YoloFrameDetections(
                frame_id=evidence_frame.id,
                detections=[
                    YoloDetection(
                        label="pallet",
                        confidence=0.93,
                        box=YoloBox(x_min=0.76, y_min=0.76, x_max=0.86, y_max=0.86),
                    ),
                ],
            ),
        ],
    )

    observation = await perception_source(evidence_frame, make_triangle_zone())

    assert observation.observed_state == ObservedState.CLEAR
    assert observation.dwell_duration_seconds == 0
    assert observation.confidence is None


async def test_missing_yolo_result_is_uncertain() -> None:
    evidence_frame = make_frame("frame-runpod-missing")
    perception_source = build_yolo_perception_source(frame_detections=[])

    observation = await perception_source(evidence_frame, PRIMARY_DEMO_ZONE)

    assert observation.observed_state == ObservedState.UNCERTAIN
    assert observation.dwell_duration_seconds == 0
    assert observation.confidence is None


def test_yolo_source_rejects_invalid_min_confidence() -> None:
    with pytest.raises(ValueError, match="min_confidence must be between 0 and 1"):
        build_yolo_perception_source(
            frame_detections=[],
            min_confidence=1.5,
        )

    with pytest.raises(ValueError, match="min_confidence must be between 0 and 1"):
        build_yolo_perception_source(
            frame_detections=[],
            min_confidence=-0.1,
        )


def test_yolo_source_rejects_duplicate_frame_detections() -> None:
    first_frame_detections = YoloFrameDetections(
        frame_id="frame-runpod-duplicate",
        detections=[],
    )
    second_frame_detections = YoloFrameDetections(
        frame_id="frame-runpod-duplicate",
        detections=[],
    )

    with pytest.raises(ValueError, match="YOLO frame ids must be unique"):
        build_yolo_perception_source(
            frame_detections=[first_frame_detections, second_frame_detections],
        )
