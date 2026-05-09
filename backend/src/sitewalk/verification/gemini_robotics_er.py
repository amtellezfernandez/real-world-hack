from collections.abc import Awaitable, Callable

from sitewalk.contracts import (
    ClearanceVerification,
    ContractModel,
    EvidenceFrame,
    Observation,
    ObservedState,
    SafetyIncident,
    VerificationVerdict,
)
from sitewalk.providers.ports import ClearanceVerifier
from sitewalk.verification.clearance import (
    build_clearance_verification,
    validate_clearance_inputs,
)


class GeminiClearanceVerificationRequest(ContractModel):
    """Gemini Robotics-ER clearance verification request."""

    incident_id: str
    zone_id: str
    before_evidence_frame_id: str
    after_evidence_frame_id: str
    model: str


class GeminiClearanceVerificationResult(ContractModel):
    """Gemini Robotics-ER clearance verification result."""

    verdict: VerificationVerdict
    confidence: float
    rationale: str


type GeminiClearanceVerificationClient = Callable[
    [GeminiClearanceVerificationRequest],
    Awaitable[GeminiClearanceVerificationResult],
]


def build_gemini_robotics_er_clearance_verifier(
    *,
    client: GeminiClearanceVerificationClient,
    model: str,
) -> ClearanceVerifier:
    """Build a Gemini Robotics-ER verifier behind the clearance port."""

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

        if after_observation.observed_state != ObservedState.CLEAR:
            return build_clearance_verification(
                after_evidence_frame=after_evidence_frame,
                after_observation=after_observation,
            )

        result = await client(
            GeminiClearanceVerificationRequest(
                incident_id=incident.id,
                zone_id=incident.zone_id,
                before_evidence_frame_id=incident.before_evidence_frame_id,
                after_evidence_frame_id=after_evidence_frame.id,
                model=model,
            ),
        )

        return ClearanceVerification(
            verdict=result.verdict,
            confidence=result.confidence,
            rationale=result.rationale,
            after_evidence_frame_id=after_evidence_frame.id,
        )

    return verify
