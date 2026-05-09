from collections.abc import Awaitable, Callable

from google import genai
from google.genai import types
from pydantic import Field

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
from sitewalk.providers.gemini_robotics_er_config import (
    DEFAULT_GEMINI_ROBOTICS_ER_MODEL,
    DEFAULT_GEMINI_ROBOTICS_ER_TIMEOUT_MILLISECONDS,
)
from sitewalk.verification.clearance import (
    build_clearance_verification,
    validate_clearance_inputs,
)

GEMINI_ROBOTICS_ER_1_6_MODEL = DEFAULT_GEMINI_ROBOTICS_ER_MODEL


class GeminiInlineImage(ContractModel):
    """Image payload sent to Gemini Robotics-ER."""

    mime_type: str = Field(min_length=1)
    data: bytes = Field(min_length=1)


class GeminiClearanceVerificationRequest(ContractModel):
    """Gemini Robotics-ER clearance verification request."""

    incident_id: str
    zone_id: str
    before_evidence_frame_id: str
    after_evidence_frame_id: str
    after_observation_confidence: float | None = Field(default=None, ge=0, le=1)
    after_image: GeminiInlineImage
    model: str


class GeminiClearanceVerificationResult(ContractModel):
    """Gemini Robotics-ER clearance verification result."""

    verdict: VerificationVerdict
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1)


type GeminiClearanceVerificationClient = Callable[
    [GeminiClearanceVerificationRequest],
    Awaitable[GeminiClearanceVerificationResult],
]
type GeminiInlineImageLoader = Callable[
    [EvidenceFrame],
    Awaitable[GeminiInlineImage],
]


def build_google_genai_client(
    *,
    api_key: str,
    timeout_milliseconds: int = DEFAULT_GEMINI_ROBOTICS_ER_TIMEOUT_MILLISECONDS,
) -> genai.Client:
    """Build an owned Google GenAI client."""
    if api_key.strip() == "":
        raise ValueError("Gemini API key is required")

    if timeout_milliseconds <= 0:
        raise ValueError("timeout milliseconds must be positive")

    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=timeout_milliseconds),
    )


def build_google_genai_clearance_verification_client(
    *,
    client: genai.Client,
    thinking_budget: int = 0,
) -> GeminiClearanceVerificationClient:
    """Build a verifier around an externally owned Gemini SDK client."""
    if thinking_budget < 0:
        raise ValueError("thinking budget must be non-negative")

    config = build_gemini_clearance_config(thinking_budget=thinking_budget)

    async def verify_clearance_with_gemini(
        request: GeminiClearanceVerificationRequest,
    ) -> GeminiClearanceVerificationResult:
        response = await client.aio.models.generate_content(
            model=request.model,
            contents=build_gemini_clearance_contents(request),
            config=config,
        )

        if isinstance(response.parsed, GeminiClearanceVerificationResult):
            return response.parsed

        response_text = response.text
        if response_text is None:
            raise ValueError("Gemini Robotics-ER returned no clearance response")

        return GeminiClearanceVerificationResult.model_validate_json(response_text)

    return verify_clearance_with_gemini


def build_gemini_clearance_contents(
    request: GeminiClearanceVerificationRequest,
) -> list[types.Part]:
    """Build Gemini request parts for clearance verification."""
    return [
        types.Part.from_text(text=build_gemini_clearance_prompt(request)),
        types.Part.from_bytes(
            data=request.after_image.data,
            mime_type=request.after_image.mime_type,
        ),
    ]


def build_gemini_clearance_config(
    *,
    thinking_budget: int,
) -> types.GenerateContentConfig:
    """Build Gemini structured-output config for clearance verification."""
    return types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=GeminiClearanceVerificationResult,
        system_instruction=(
            "You verify whether a robot workcell safety zone is visually clear. "
            "Return only the requested structured JSON. Do not authorize robot "
            "motion, operator action, compliance status, or incident closure."
        ),
        temperature=0,
        thinking_config=types.ThinkingConfig(thinking_budget=thinking_budget),
    )


def build_gemini_clearance_prompt(
    request: GeminiClearanceVerificationRequest,
) -> str:
    """Build the text prompt paired with the after-evidence image."""
    confidence = (
        "unknown"
        if request.after_observation_confidence is None
        else f"{request.after_observation_confidence:.2f}"
    )
    return (
        f"Incident: {request.incident_id}. "
        f"Zone: {request.zone_id}. "
        f"Before evidence frame: {request.before_evidence_frame_id}. "
        f"After evidence frame: {request.after_evidence_frame_id}. "
        "Local perception marked the after evidence clear. "
        f"Local perception confidence: {confidence}. "
        "Inspect the attached after-evidence image and decide whether the "
        "robot workcell safety zone is clear, still_blocked, or uncertain. "
        "Use uncertain when the image is ambiguous, occluded, incomplete, or "
        "insufficient for safety verification."
    )


def build_gemini_robotics_er_clearance_verifier(
    *,
    client: GeminiClearanceVerificationClient,
    load_image: GeminiInlineImageLoader,
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
                after_observation_confidence=after_observation.confidence,
                after_image=await load_image(after_evidence_frame),
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
