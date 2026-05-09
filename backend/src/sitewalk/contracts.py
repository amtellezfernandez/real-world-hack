from datetime import datetime
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContractModel(BaseModel):
    """Base model for public product contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ZoneType(StrEnum):
    """Supported critical-zone categories."""

    EMERGENCY_EXIT = "emergency_exit"
    WALKWAY = "walkway"
    FORKLIFT_LANE = "forklift_lane"
    ROBOT_WORKCELL = "robot_workcell"


class ObservedState(StrEnum):
    """Observed state of a monitored critical zone."""

    CLEAR = "clear"
    BLOCKED = "blocked"
    UNCERTAIN = "uncertain"
    CAMERA_UNAVAILABLE = "camera_unavailable"


class IncidentState(StrEnum):
    """Policy-controlled safety incident lifecycle states."""

    CLEAR = "clear"
    DWELL = "dwell"
    INCIDENT_OPEN = "incident_open"
    ALERT_PENDING = "alert_pending"
    ALERT_BROADCAST = "alert_broadcast"
    CLEARING = "clearing"
    VERIFIED_CLEAR = "verified_clear"
    CLOSED = "closed"
    UNCERTAIN = "uncertain"


class DemoTimingMode(StrEnum):
    """Demo replay pacing modes."""

    STAGE = "stage"
    REAL_TIME = "real_time"


class Severity(StrEnum):
    """Incident severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceSource(StrEnum):
    """Evidence frame source categories."""

    CAMERA = "camera"
    REPLAY = "replay"
    UPLOADED_IMAGE = "uploaded_image"
    GENERATED_TEST_FRAME = "generated_test_frame"


class VerificationVerdict(StrEnum):
    """Clearance verification verdicts."""

    CLEAR = "clear"
    STILL_BLOCKED = "still_blocked"
    UNCERTAIN = "uncertain"


class ExportStatus(StrEnum):
    """Review/export availability states."""

    LOCAL_ONLY = "local_only"
    EXPORT_PENDING = "export_pending"
    EXPORTED = "exported"
    EXPORT_UNAVAILABLE = "export_unavailable"


class ReviewDecision(StrEnum):
    """Human review decisions for evidence samples."""

    ACCEPTED = "accepted"
    CORRECTED = "corrected"
    REJECTED = "rejected"
    PENDING = "pending"


class ReviewExportProvider(StrEnum):
    """Review export destinations exposed to product code."""

    LOCAL_REVIEW = "local_review"
    ENCORD = "encord"


class ProviderBoundary(StrEnum):
    """Backend-only integration boundaries."""

    PERCEPTION = "perception"
    INCIDENT_REPORTING = "incident_reporting"
    VERIFICATION = "verification"
    REVIEW_EXPORT = "review_export"


class ProviderIntegration(StrEnum):
    """Concrete provider integrations exposed for demo readiness."""

    LOCAL_REPLAY = "local_replay"
    RUNPOD_YOLO = "runpod_yolo"
    LOCAL_INCIDENT_REPORT = "local_incident_report"
    OPENAI_FOUNDRY = "openai_foundry"
    LOCAL_CLEARANCE = "local_clearance"
    GEMINI_ROBOTICS_ER = "gemini_robotics_er"
    LOCAL_REVIEW = "local_review"
    ENCORD = "encord"


class ProviderAvailability(StrEnum):
    """Provider availability and configuration state."""

    AVAILABLE = "available"
    CONFIGURED = "configured"
    UNCONFIGURED = "unconfigured"


class ReviewExportProviderStatus(ContractModel):
    """Availability status for a review/eval destination."""

    provider: ReviewExportProvider
    availability: ProviderAvailability
    detail: str


class ProviderIntegrationStatus(ContractModel):
    """Readiness status for a concrete provider integration."""

    provider: ProviderIntegration
    boundary: ProviderBoundary
    availability: ProviderAvailability
    detail: str


class ZonePoint(ContractModel):
    """Normalized image coordinate for a zone polygon."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class CriticalZonePolicy(ContractModel):
    """Policy controlling when observations become incidents."""

    dwell_threshold_seconds: float = Field(gt=0)
    severity: Severity
    escalation_channel: str


class CriticalZone(ContractModel):
    """Site-defined physical area monitored for safety violations."""

    id: str
    name: str
    zone_type: ZoneType
    geometry: list[ZonePoint] = Field(min_length=3)
    policy: CriticalZonePolicy


class DemoTimingOption(ContractModel):
    """Single replay pacing option for demo controls."""

    mode: DemoTimingMode
    label: str
    frame_interval_ms: int = Field(gt=0)
    playback_dwell_seconds: float = Field(gt=0)
    playback_clearance_seconds: float = Field(gt=0)
    requires_external_providers: bool


class DemoTiming(ContractModel):
    """Replay timing options that do not change lifecycle states."""

    default_mode: DemoTimingMode
    options: list[DemoTimingOption] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_default_mode(self) -> Self:
        modes = [option.mode for option in self.options]

        if len(set(modes)) != len(modes):
            raise ValueError("timing option modes must be unique")

        if self.default_mode not in set(modes):
            raise ValueError("default timing mode must be present in options")

        return self


class EvidenceAnnotation(ContractModel):
    """Label attached to an evidence frame."""

    label: str
    confidence: float = Field(ge=0, le=1)


class EvidenceFrame(ContractModel):
    """Frame or image reference supporting an observation or incident."""

    id: str
    source: EvidenceSource
    timestamp: datetime
    image_ref: str
    annotations: list[EvidenceAnnotation] = Field(default_factory=list)


class Observation(ContractModel):
    """Evidence-backed critical-zone observation."""

    zone_id: str
    observed_state: ObservedState
    dwell_duration_seconds: float = Field(ge=0)
    evidence_frame_id: str
    confidence: float | None = Field(default=None, ge=0, le=1)


class IncidentReport(ContractModel):
    """Structured explanation generated for an opened incident."""

    hazard: str
    severity: Severity
    evidence_summary: str
    rationale: str
    recommended_action: str
    alert_text_candidate: str


class AlertEvent(ContractModel):
    """Human-approved alert transcript record."""

    incident_id: str
    approval_actor: str
    alert_text: str
    timestamp: str


class ClearanceVerification(ContractModel):
    """Before/after visual clearance verification record."""

    verdict: VerificationVerdict
    confidence: float = Field(ge=0, le=1)
    rationale: str
    after_evidence_frame_id: str


class AuditPacket(ContractModel):
    """Closed incident evidence package."""

    incident_id: str
    before_frame_id: str
    after_frame_id: str
    before_timestamp: datetime
    after_timestamp: datetime
    alert_transcript: str
    verification_verdict: VerificationVerdict


class ReviewSample(ContractModel):
    """Review/eval sample produced from a closed incident."""

    incident_id: str
    before_frame_id: str
    after_frame_id: str
    labels: list[str]
    human_decision: ReviewDecision
    export_status: ExportStatus


class ObservationStreamZone(ContractModel):
    """Zone state emitted over the live observation stream."""

    state: ObservedState
    dwell_seconds: float = Field(ge=0)


class ObservationStreamIncident(ContractModel):
    """Incident state emitted over the live observation stream."""

    id: str
    state: IncidentState


class ObservationStreamBox(ContractModel):
    """Detection annotation emitted over the live observation stream."""

    label: str
    confidence: float = Field(ge=0, le=1)


class ObservationStreamEvent(ContractModel):
    """Single observation event for the live operations UI."""

    frame_id: str
    boxes: list[ObservationStreamBox] = Field(default_factory=list)
    zone: ObservationStreamZone
    incident: ObservationStreamIncident | None = None


class ApproveAlertRequest(ContractModel):
    """Human alert approval command."""

    approval_actor: str = Field(min_length=1)
    decision: Literal["approved"]
    alert_text: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)


class IncidentCommandResponse(ContractModel):
    """Result for incident state-changing commands."""

    incident_id: str
    state: IncidentState
    alert_event: AlertEvent | None = None


class ClearanceVerificationResponse(ContractModel):
    """Result for a clearance verification command."""

    incident_id: str
    state: IncidentState
    verification: ClearanceVerification


class SafetyIncident(ContractModel):
    """Operational record for a critical-zone safety violation."""

    id: str
    zone_id: str
    state: IncidentState
    severity: Severity
    before_evidence_frame_id: str
    incident_report: IncidentReport | None = None
    alert_events: list[AlertEvent] = Field(default_factory=list)
    verification: ClearanceVerification | None = None
    audit_packet: AuditPacket | None = None
    review_sample: ReviewSample | None = None

    @model_validator(mode="after")
    def validate_evidence_package(self) -> Self:
        if self.state in {IncidentState.VERIFIED_CLEAR, IncidentState.CLOSED}:
            if self.verification is None:
                raise ValueError("verified incidents must include verification")

            if self.verification.verdict != VerificationVerdict.CLEAR:
                raise ValueError("verified clear incidents must have a clear verdict")

        if self.state != IncidentState.CLOSED:
            if (
                self.incident_report is not None
                and self.incident_report.severity != self.severity
            ):
                raise ValueError(
                    "incident report severity must match incident severity",
                )

            return self

        if (
            self.incident_report is not None
            and self.incident_report.severity != self.severity
        ):
            raise ValueError("incident report severity must match incident severity")

        if self.audit_packet is None or self.review_sample is None:
            raise ValueError("closed incidents must include audit and review evidence")

        if self.audit_packet.incident_id != self.id:
            raise ValueError("audit packet incident_id must match incident id")

        if self.review_sample.incident_id != self.id:
            raise ValueError("review sample incident_id must match incident id")

        if self.audit_packet.before_frame_id != self.before_evidence_frame_id:
            raise ValueError("audit packet before frame must match incident")

        if self.review_sample.before_frame_id != self.before_evidence_frame_id:
            raise ValueError("review sample before frame must match incident")

        if self.verification is None:
            raise ValueError("closed incidents must include verification")

        if (
            self.audit_packet.after_frame_id
            != self.verification.after_evidence_frame_id
        ):
            raise ValueError("audit packet after frame must match verification")

        if (
            self.review_sample.after_frame_id
            != self.verification.after_evidence_frame_id
        ):
            raise ValueError("review sample after frame must match verification")

        if self.audit_packet.verification_verdict != self.verification.verdict:
            raise ValueError("audit packet verdict must match verification")

        return self


class IncidentDetail(ContractModel):
    """Incident snapshot for the detail panel."""

    incident_id: str
    state: IncidentState
    incident_report: IncidentReport | None = None
    severity: Severity
    recommendation: str
    latest_observation: Observation


class ObservationAssessment(ContractModel):
    """Policy assessment for a critical-zone observation."""

    incident_state: IncidentState
    policy_reason: str
    incident: SafetyIncident | None = None

    @model_validator(mode="after")
    def validate_incident_state(self) -> Self:
        incident_required_states = {
            IncidentState.INCIDENT_OPEN,
            IncidentState.ALERT_PENDING,
            IncidentState.ALERT_BROADCAST,
            IncidentState.CLEARING,
            IncidentState.VERIFIED_CLEAR,
            IncidentState.CLOSED,
        }
        verification_required_states = {
            IncidentState.CLEARING,
            IncidentState.VERIFIED_CLEAR,
            IncidentState.CLOSED,
        }

        if self.incident is None:
            if self.incident_state in incident_required_states:
                raise ValueError("incident assessments must include an incident")

            return self

        if self.incident.state != self.incident_state:
            raise ValueError("incident state must match assessment incident_state")

        if (
            self.incident_state in verification_required_states
            and self.incident.verification is None
        ):
            raise ValueError("clearance assessments must include verification")

        return self


class ObservationReplayFrame(ContractModel):
    """Replay frame containing perception evidence and observation only."""

    id: str
    label: str
    evidence_frame: EvidenceFrame
    observation: Observation

    @model_validator(mode="after")
    def validate_observation_evidence(self) -> Self:
        if self.observation.evidence_frame_id != self.evidence_frame.id:
            raise ValueError(
                "observation evidence_frame_id must match evidence_frame id",
            )

        return self


class ObservationReplay(ContractModel):
    """Controlled replay source before safety lifecycle assessment."""

    id: str
    name: str
    zone: CriticalZone
    timing: DemoTiming
    frames: list[ObservationReplayFrame] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_frame_zones(self) -> Self:
        if any(frame.observation.zone_id != self.zone.id for frame in self.frames):
            raise ValueError("frame observation zone_id must match replay zone id")

        return self


class ReplayFrame(ContractModel):
    """Single replay frame paired with its critical-zone observation."""

    id: str
    label: str
    evidence_frame: EvidenceFrame
    observation: Observation
    assessment: ObservationAssessment

    @model_validator(mode="after")
    def validate_observation_evidence(self) -> Self:
        if self.observation.evidence_frame_id != self.evidence_frame.id:
            raise ValueError(
                "observation evidence_frame_id must match evidence_frame id",
            )

        return self


class DemoReplay(ContractModel):
    """Controlled replay source for the primary robotics supervision demo."""

    id: str
    name: str
    zone: CriticalZone
    timing: DemoTiming
    frames: list[ReplayFrame] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_frame_zones(self) -> Self:
        if any(frame.observation.zone_id != self.zone.id for frame in self.frames):
            raise ValueError("frame observation zone_id must match replay zone id")

        return self


class HealthResponse(ContractModel):
    """Backend readiness response."""

    service: str
    status: Literal["ready"]
    version: str


class ProductContract(ContractModel):
    """Contract catalog shared with the frontend."""

    primary_workflow: Literal["robot_workcell_obstruction"]
    observation_states: list[ObservedState]
    incident_states: list[IncidentState]
    severity_levels: list[Severity]
    zone_types: list[ZoneType]
    provider_boundaries: list[ProviderBoundary]
    review_export_provider_statuses: list[ReviewExportProviderStatus]
    provider_integration_statuses: list[ProviderIntegrationStatus]
    reference_zone: CriticalZone
    reference_evidence_frame: EvidenceFrame
    reference_observation: Observation
    reference_incident: SafetyIncident
