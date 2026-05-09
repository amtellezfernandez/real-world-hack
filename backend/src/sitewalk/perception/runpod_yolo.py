from collections.abc import Callable, Collection, Sequence
from functools import lru_cache
from typing import Self

from pydantic import Field, model_validator
from shapely import Polygon, box

from sitewalk.contracts import (
    ContractModel,
    CriticalZone,
    EvidenceFrame,
    Observation,
    ObservedState,
)
from sitewalk.providers.ports import PerceptionSource

type DwellDurationResolver = Callable[[EvidenceFrame, CriticalZone], float]
type Point = tuple[float, float]
type Bounds = tuple[float, float, float, float]
type ZoneGeometry = tuple[Polygon, Bounds]

DEFAULT_BLOCKING_LABELS = frozenset({"box", "cart", "crate", "pallet"})


class YoloBox(ContractModel):
    """Normalized YOLO bounding box."""

    x_min: float = Field(ge=0, le=1)
    y_min: float = Field(ge=0, le=1)
    x_max: float = Field(ge=0, le=1)
    y_max: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_bounds(self) -> Self:
        if self.x_min >= self.x_max:
            raise ValueError("x_min must be less than x_max")

        if self.y_min >= self.y_max:
            raise ValueError("y_min must be less than y_max")

        return self


class YoloDetection(ContractModel):
    """Provider-neutral YOLO detection payload."""

    label: str
    confidence: float = Field(ge=0, le=1)
    box: YoloBox


class YoloFrameDetections(ContractModel):
    """YOLO detections for one evidence frame."""

    frame_id: str
    detections: list[YoloDetection] = Field(default_factory=list)


def build_yolo_perception_source(
    *,
    frame_detections: Sequence[YoloFrameDetections],
    blocking_labels: Collection[str] = DEFAULT_BLOCKING_LABELS,
    min_confidence: float = 0.5,
    resolve_dwell_seconds: DwellDurationResolver | None = None,
) -> PerceptionSource:
    """Build an async perception source from normalized YOLO detections."""
    if min_confidence < 0 or min_confidence > 1:
        raise ValueError("min_confidence must be between 0 and 1")

    frame_detections_by_id = index_frame_detections(frame_detections)
    blocking_label_set = frozenset(blocking_labels)

    async def perceive(
        evidence_frame: EvidenceFrame,
        zone: CriticalZone,
    ) -> Observation:
        yolo_frame_detections = frame_detections_by_id.get(evidence_frame.id)

        if yolo_frame_detections is None:
            return build_observation(
                confidence=None,
                dwell_seconds=0,
                evidence_frame=evidence_frame,
                observed_state=ObservedState.UNCERTAIN,
                zone=zone,
            )

        return observe_yolo_detections(
            blocking_labels=blocking_label_set,
            detections=yolo_frame_detections.detections,
            evidence_frame=evidence_frame,
            min_confidence=min_confidence,
            resolve_dwell_seconds=resolve_dwell_seconds,
            zone=zone,
        )

    return perceive


def observe_yolo_detections(
    *,
    blocking_labels: Collection[str] = DEFAULT_BLOCKING_LABELS,
    detections: Sequence[YoloDetection],
    evidence_frame: EvidenceFrame,
    min_confidence: float = 0.5,
    resolve_dwell_seconds: DwellDurationResolver | None = None,
    zone: CriticalZone,
) -> Observation:
    """Convert YOLO detections into the stable critical-zone observation model."""
    zone_polygon, zone_bounds = create_zone_geometry(create_zone_geometry_key(zone))
    max_confident_overlap_confidence = None
    max_overlap_confidence = None

    for detection in detections:
        if detection.label not in blocking_labels:
            continue

        if not box_intersects_polygon(detection.box, zone_polygon, zone_bounds):
            continue

        if (
            max_overlap_confidence is None
            or detection.confidence > max_overlap_confidence
        ):
            max_overlap_confidence = detection.confidence

        if detection.confidence < min_confidence:
            continue

        if (
            max_confident_overlap_confidence is None
            or detection.confidence > max_confident_overlap_confidence
        ):
            max_confident_overlap_confidence = detection.confidence

    if max_confident_overlap_confidence is not None:
        dwell_seconds = (
            resolve_dwell_seconds(evidence_frame, zone)
            if resolve_dwell_seconds is not None
            else 0
        )

        return build_observation(
            confidence=max_confident_overlap_confidence,
            dwell_seconds=dwell_seconds,
            evidence_frame=evidence_frame,
            observed_state=ObservedState.BLOCKED,
            zone=zone,
        )

    if max_overlap_confidence is not None:
        return build_observation(
            confidence=max_overlap_confidence,
            dwell_seconds=0,
            evidence_frame=evidence_frame,
            observed_state=ObservedState.UNCERTAIN,
            zone=zone,
        )

    return build_observation(
        confidence=None,
        dwell_seconds=0,
        evidence_frame=evidence_frame,
        observed_state=ObservedState.CLEAR,
        zone=zone,
    )


def index_frame_detections(
    frame_detections: Sequence[YoloFrameDetections],
) -> dict[str, YoloFrameDetections]:
    frame_detections_by_id: dict[str, YoloFrameDetections] = {}

    for yolo_frame_detections in frame_detections:
        if yolo_frame_detections.frame_id in frame_detections_by_id:
            raise ValueError("YOLO frame ids must be unique")

        frame_detections_by_id[yolo_frame_detections.frame_id] = yolo_frame_detections

    return frame_detections_by_id


def create_zone_geometry_key(zone: CriticalZone) -> tuple[Point, ...]:
    return tuple((point.x, point.y) for point in zone.geometry)


@lru_cache(maxsize=64)
def create_zone_geometry(points: tuple[Point, ...]) -> ZoneGeometry:
    polygon = Polygon(points)
    min_x, min_y, max_x, max_y = polygon.bounds

    return polygon, (min_x, min_y, max_x, max_y)


def box_intersects_polygon(
    yolo_box: YoloBox,
    polygon: Polygon,
    polygon_bounds: Bounds,
) -> bool:
    min_x, min_y, max_x, max_y = polygon_bounds

    if (
        yolo_box.x_min >= max_x
        or yolo_box.x_max <= min_x
        or yolo_box.y_min >= max_y
        or yolo_box.y_max <= min_y
    ):
        return False

    detection_box = box(
        yolo_box.x_min,
        yolo_box.y_min,
        yolo_box.x_max,
        yolo_box.y_max,
    )

    return detection_box.intersects(polygon)


def build_observation(
    *,
    confidence: float | None,
    dwell_seconds: float,
    evidence_frame: EvidenceFrame,
    observed_state: ObservedState,
    zone: CriticalZone,
) -> Observation:
    """Build an evidence-linked observation from adapter output."""
    return Observation(
        zone_id=zone.id,
        observed_state=observed_state,
        dwell_duration_seconds=dwell_seconds,
        evidence_frame_id=evidence_frame.id,
        confidence=confidence,
    )
