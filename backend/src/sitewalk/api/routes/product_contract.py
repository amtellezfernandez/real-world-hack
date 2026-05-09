from datetime import UTC, datetime
from os import environ

from fastapi import APIRouter

from sitewalk.contracts import (
    EvidenceAnnotation,
    EvidenceFrame,
    EvidenceSource,
    IncidentState,
    Observation,
    ObservedState,
    ProductContract,
    ProviderBoundary,
    SafetyIncident,
    Severity,
    ZoneType,
)
from sitewalk.demo_data import PRIMARY_DEMO_ZONE
from sitewalk.providers.integration_status import build_provider_integration_statuses
from sitewalk.review_export.provider_status import build_review_export_provider_statuses
from sitewalk.voice.provider_status import build_voice_provider_statuses

router = APIRouter(prefix="/api", tags=["contracts"])

REFERENCE_EVIDENCE_FRAME = EvidenceFrame(
    id="frame-reference-blocked",
    source=EvidenceSource.REPLAY,
    timestamp=datetime(2026, 5, 8, 12, 0, 0, tzinfo=UTC),
    image_ref="assets/demo/reference-blocked.jpg",
    annotations=[
        EvidenceAnnotation(label="zone_overlap", confidence=0.94),
    ],
)

REFERENCE_OBSERVATION = Observation(
    zone_id=PRIMARY_DEMO_ZONE.id,
    observed_state=ObservedState.BLOCKED,
    dwell_duration_seconds=30,
    evidence_frame_id=REFERENCE_EVIDENCE_FRAME.id,
    confidence=0.94,
)

REFERENCE_INCIDENT = SafetyIncident(
    id="incident-reference",
    zone_id=PRIMARY_DEMO_ZONE.id,
    state=IncidentState.ALERT_PENDING,
    severity=Severity.HIGH,
    before_evidence_frame_id=REFERENCE_EVIDENCE_FRAME.id,
)

VOICE_PROVIDER_STATUSES = build_voice_provider_statuses(env=environ)
REVIEW_EXPORT_PROVIDER_STATUSES = build_review_export_provider_statuses(env=environ)

REFERENCE_PRODUCT_CONTRACT = ProductContract(
    primary_workflow="robot_workcell_obstruction",
    observation_states=list(ObservedState),
    incident_states=list(IncidentState),
    severity_levels=list(Severity),
    zone_types=list(ZoneType),
    provider_boundaries=list(ProviderBoundary),
    voice_provider_statuses=VOICE_PROVIDER_STATUSES,
    review_export_provider_statuses=REVIEW_EXPORT_PROVIDER_STATUSES,
    provider_integration_statuses=build_provider_integration_statuses(
        env=environ,
        voice_statuses=VOICE_PROVIDER_STATUSES,
        review_statuses=REVIEW_EXPORT_PROVIDER_STATUSES,
    ),
    reference_zone=PRIMARY_DEMO_ZONE,
    reference_evidence_frame=REFERENCE_EVIDENCE_FRAME,
    reference_observation=REFERENCE_OBSERVATION,
    reference_incident=REFERENCE_INCIDENT,
)


@router.get("/product-contract")
async def get_product_contract() -> ProductContract:
    """Return the shared product contract catalog."""
    return REFERENCE_PRODUCT_CONTRACT
