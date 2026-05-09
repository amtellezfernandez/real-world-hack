from typing import Literal

from pydantic import Field

from sitewalk.contracts import (
    ContractModel,
    CriticalZone,
    DemoReplay,
    EvidenceFrame,
    IncidentState,
    ReplayFrame,
    ReviewSample,
    SafetyIncident,
    VerificationVerdict,
)
from sitewalk.review_export.encord_ontology import (
    EncordOntologySpec,
    build_robot_safety_ontology_spec,
)

FrameRole = Literal["before", "after"]
ObjectLabelName = Literal["robot_path", "obstruction", "safe_drop_zone", "human", "robot"]
ZoneStateLabel = Literal["clear", "blocked", "uncertain"]
RobotActionLabel = Literal["none", "stopped", "remove_obstruction", "manual_intervention"]
VerificationResultLabel = Literal["cleared", "still_blocked", "unsafe", "uncertain"]


class NormalizedBoundingBox(ContractModel):
    """Normalized bounding box coordinates for Encord-ready labels."""

    x_min: float = Field(ge=0, le=1)
    y_min: float = Field(ge=0, le=1)
    x_max: float = Field(ge=0, le=1)
    y_max: float = Field(ge=0, le=1)


class NormalizedPoint(ContractModel):
    """Normalized point in image coordinates."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class EncordObjectLabel(ContractModel):
    """Object annotation to create or review in Encord."""

    name: ObjectLabelName
    polygon: list[NormalizedPoint] | None = None
    bounding_box: NormalizedBoundingBox | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class EncordFrameClassification(ContractModel):
    """Frame-level classification values aligned to the Encord ontology."""

    zone_state: ZoneStateLabel
    approval_state: Literal["pending", "approved", "rejected"]
    robot_action: RobotActionLabel
    verification_result: VerificationResultLabel
    review_decision: Literal["accepted", "corrected", "rejected", "pending"]


class EncordIncidentFrame(ContractModel):
    """One before/after frame prepared for Encord incident logging."""

    role: FrameRole
    evidence_frame: EvidenceFrame
    objects: list[EncordObjectLabel]
    classifications: EncordFrameClassification


class IncidentOutcomeDatasetLabels(ContractModel):
    """Ontology-aligned dataset labels recommended by outcome analysis."""

    zone_state_before: ZoneStateLabel
    zone_state_after: ZoneStateLabel
    verification_result: VerificationResultLabel
    review_decision: Literal["accepted", "corrected", "rejected", "pending"]


class IncidentOutcomeReport(ContractModel):
    """Structured analysis of an incident outcome."""

    summary: str = Field(min_length=1)
    worked: list[str]
    failed_or_risky: list[str]
    recommended_dataset_labels: IncidentOutcomeDatasetLabels
    operator_review_needed: bool


class EncordIncidentExportPacket(ContractModel):
    """Complete Encord-ready incident packet."""

    ontology: EncordOntologySpec
    incident: SafetyIncident
    review_sample: ReviewSample
    frames: list[EncordIncidentFrame] = Field(min_length=2)
    outcome_report: IncidentOutcomeReport | None = None
    metadata: dict[str, str]


def build_demo_replay_encord_packet(
    *,
    replay: DemoReplay,
    outcome_report: IncidentOutcomeReport | None = None,
) -> EncordIncidentExportPacket:
    """Build an Encord-ready packet from the current closed demo replay."""
    closed_frame = find_closed_incident_frame(replay)
    incident = closed_frame.assessment.incident

    if incident is None:
        raise ValueError("closed replay frame must include an incident")

    if incident.review_sample is None:
        raise ValueError("closed incident must include review sample")

    before_frame = find_replay_frame_by_evidence_id(
        replay=replay,
        evidence_frame_id=incident.before_evidence_frame_id,
    )
    after_frame = find_replay_frame_by_evidence_id(
        replay=replay,
        evidence_frame_id=incident.review_sample.after_frame_id,
    )

    return EncordIncidentExportPacket(
        ontology=build_robot_safety_ontology_spec(),
        incident=incident,
        review_sample=incident.review_sample,
        frames=[
            build_encord_incident_frame(
                role="before",
                replay_frame=before_frame,
                zone=replay.zone,
                incident=incident,
            ),
            build_encord_incident_frame(
                role="after",
                replay_frame=after_frame,
                zone=replay.zone,
                incident=incident,
            ),
        ],
        outcome_report=outcome_report,
        metadata={
            "incident_id": incident.id,
            "zone_id": replay.zone.id,
            "zone_name": replay.zone.name,
            "source_replay_id": replay.id,
            "source_replay_name": replay.name,
        },
    )


def find_closed_incident_frame(replay: DemoReplay) -> ReplayFrame:
    """Return the frame containing the closed incident."""
    for frame in reversed(replay.frames):
        incident = frame.assessment.incident
        if incident is not None and incident.state == IncidentState.CLOSED:
            return frame

    raise ValueError("demo replay does not include a closed incident")


def find_replay_frame_by_evidence_id(
    *,
    replay: DemoReplay,
    evidence_frame_id: str,
) -> ReplayFrame:
    """Find a replay frame by its evidence frame id."""
    for frame in replay.frames:
        if frame.evidence_frame.id == evidence_frame_id:
            return frame

    raise ValueError(f"evidence frame not found: {evidence_frame_id}")


def build_encord_incident_frame(
    *,
    role: FrameRole,
    replay_frame: ReplayFrame,
    zone: CriticalZone,
    incident: SafetyIncident,
) -> EncordIncidentFrame:
    """Map a replay frame to the Encord incident ontology."""
    is_before = role == "before"
    verification_result = map_verification_result(incident=incident, role=role)
    zone_state: ZoneStateLabel = "blocked" if is_before else (
        "clear" if verification_result == "cleared" else "uncertain"
    )
    labels = [
        EncordObjectLabel(
            name="robot_path",
            polygon=[
                NormalizedPoint(x=point.x, y=point.y)
                for point in zone.geometry
            ],
        ),
    ]

    if is_before:
        labels.append(
            EncordObjectLabel(
                name="obstruction",
                bounding_box=NormalizedBoundingBox(
                    x_min=0.32,
                    y_min=0.34,
                    x_max=0.58,
                    y_max=0.78,
                ),
                confidence=replay_frame.observation.confidence,
            ),
        )

    return EncordIncidentFrame(
        role=role,
        evidence_frame=replay_frame.evidence_frame,
        objects=labels,
        classifications=EncordFrameClassification(
            zone_state=zone_state,
            approval_state="approved",
            robot_action="remove_obstruction" if is_before else "none",
            verification_result=verification_result,
            review_decision=incident.review_sample.human_decision.value
            if incident.review_sample is not None
            else "pending",
        ),
    )


def map_verification_result(
    *,
    incident: SafetyIncident,
    role: FrameRole,
) -> VerificationResultLabel:
    """Map app verification states to the Encord ontology vocabulary."""
    if role == "before":
        return "still_blocked"

    if incident.verification is None:
        return "uncertain"

    if incident.verification.verdict == VerificationVerdict.CLEAR:
        return "cleared"

    if incident.verification.verdict == VerificationVerdict.STILL_BLOCKED:
        return "still_blocked"

    return "uncertain"


def build_local_outcome_report(packet: EncordIncidentExportPacket) -> IncidentOutcomeReport:
    """Build a deterministic report when OpenAI is unavailable."""
    before_frame = packet.frames[0]
    after_frame = packet.frames[-1]

    return IncidentOutcomeReport(
        summary=(
            f"Incident {packet.incident.id} moved from "
            f"{before_frame.classifications.zone_state} to "
            f"{after_frame.classifications.verification_result} after human "
            "approval and clearance verification."
        ),
        worked=[
            "The system preserved before and after evidence.",
            "The incident did not close until visual clearance evidence was present.",
            "The approved action and final review label are ready for Encord.",
        ],
        failed_or_risky=[
            "The current demo packet uses a single camera view.",
            "The obstruction box is derived from demo metadata, not a live detector.",
        ],
        recommended_dataset_labels=IncidentOutcomeDatasetLabels(
            zone_state_before=before_frame.classifications.zone_state,
            zone_state_after=after_frame.classifications.zone_state,
            verification_result=after_frame.classifications.verification_result,
            review_decision=after_frame.classifications.review_decision,
        ),
        operator_review_needed=False,
    )
