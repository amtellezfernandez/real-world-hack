import base64
import binascii
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal, Self

from google import genai
from google.genai import types
from pydantic import Field, model_validator

from sitewalk.contracts import ContractModel

INLINE_IMAGE_BASE64_MAX_LENGTH = 1_500_000
GEMINI_BOX_SCALE = 1000
INCIDENT_OBJECT_LABELS = (
    "person",
    "pallet",
    "box",
    "cart",
    "crate",
    "forklift",
    "robot",
    "blocked_exit",
    "obstruction",
)
ALLOWED_SEMANTIC_BLOCKERS = frozenset({"person"})
PERSON_BLOCKER_ALIASES = frozenset(
    {
        "adult",
        "boy",
        "child",
        "girl",
        "human",
        "human being",
        "man",
        "men",
        "people",
        "person",
        "woman",
        "women",
    }
)
# Keep INCIDENT_OBJECT_LABELS above for easy rollback to incident-only detection.
# To restore it, add the enum back to the schema label property and use the
# previous "Allowed labels: ..." prompt wording.
GEMINI_OBJECT_DETECTION_PROMPT = (
    "Detect visible objects in this camera frame. Return each object with a "
    "concise label, optional confidence, and box_2d."
)
GEMINI_OBJECT_DETECTION_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "detections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {
                        "type": "string",
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "box_2d": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 4,
                        "maxItems": 4,
                    },
                },
                "required": ["label", "box_2d"],
            },
        },
    },
    "required": ["detections"],
}
type InlineImageMimeType = Literal["image/jpeg", "image/png", "image/webp"]


class GeminiDetectionBox(ContractModel):
    """Normalized detection box in image coordinates."""

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


class GeminiObjectDetection(ContractModel):
    """Incident-relevant object detected by Gemini Robotics-ER."""

    label: str = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    box: GeminiDetectionBox


class GeminiObjectDetectionRequest(ContractModel):
    """Inline camera frame for Gemini Robotics-ER object detection."""

    image_base64: str = Field(min_length=1, max_length=INLINE_IMAGE_BASE64_MAX_LENGTH)
    mime_type: InlineImageMimeType = "image/jpeg"


class GeminiObjectDetectionResponse(ContractModel):
    """Gemini Robotics-ER object detections for a camera frame."""

    model: str
    detected_at: datetime
    detections: list[GeminiObjectDetection] = Field(default_factory=list)


class GeminiRawDetection(ContractModel):
    """Gemini structured-output detection with 0-1000 y/x box order."""

    label: str = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    box_2d: list[float] = Field(min_length=4, max_length=4)


class GeminiRawDetectionResponse(ContractModel):
    """Raw structured response returned by Gemini."""

    detections: list[GeminiRawDetection] = Field(default_factory=list)


type GeminiObjectDetectionClient = Callable[
    [GeminiObjectDetectionRequest],
    Awaitable[GeminiObjectDetectionResponse],
]
type GeminiSemanticStatusClient = Callable[
    [GeminiObjectDetectionRequest],
    Awaitable[GeminiSemanticStatusResult],
]


class PathState(StrEnum):
    """Semantic state of the visible path."""

    CLEAR = "clear"
    BLOCKED = "blocked"


class GeminiSemanticStatusResult(ContractModel):
    """Structured semantic status for the visible path."""

    state: PathState
    blocking_object: str | None = Field(default=None)
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1)


GEMINI_SEMANTIC_STATUS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "state": {
            "type": "string",
            "enum": [state.value for state in PathState],
        },
        "blocking_object": {
            "type": "string",
            "nullable": True,
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
        },
        "rationale": {
            "type": "string",
        },
    },
    "required": ["state", "confidence", "rationale"],
}


def build_google_genai_object_detection_client(
    *,
    client: genai.Client,
    model: str,
) -> GeminiObjectDetectionClient:
    """Build a Gemini Robotics-ER object detection client."""
    if model.strip() == "":
        raise ValueError("Gemini model is required")

    config = build_gemini_object_detection_config()

    async def detect_objects(
        request: GeminiObjectDetectionRequest,
    ) -> GeminiObjectDetectionResponse:
        image_bytes = decode_inline_image(request.image_base64)
        response = await client.aio.models.generate_content(
            model=model,
            contents=[
                types.Part.from_text(text=GEMINI_OBJECT_DETECTION_PROMPT),
                types.Part.from_bytes(data=image_bytes, mime_type=request.mime_type),
            ],
            config=config,
        )

        if isinstance(response.parsed, GeminiRawDetectionResponse):
            raw_response = response.parsed
        else:
            response_text = response.text
            if response_text is None:
                raise ValueError("Gemini Robotics-ER returned no detection response")

            raw_response = GeminiRawDetectionResponse.model_validate_json(response_text)

        return GeminiObjectDetectionResponse(
            model=model,
            detected_at=datetime.now(UTC),
            detections=[
                normalize_gemini_detection(detection)
                for detection in raw_response.detections
            ],
        )

    return detect_objects


def build_google_genai_semantic_status_client(
    *,
    client: genai.Client,
    model: str,
    thinking_budget: int = 0,
) -> GeminiSemanticStatusClient:
    """Build a Gemini Robotics-ER semantic status client."""
    if model.strip() == "":
        raise ValueError("Gemini model is required")

    if thinking_budget < 0:
        raise ValueError("thinking budget must be non-negative")

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=GEMINI_SEMANTIC_STATUS_RESPONSE_SCHEMA,
        temperature=0,
        thinking_config=types.ThinkingConfig(thinking_budget=thinking_budget),
        system_instruction=(
            "You classify whether the visible path ahead is clear or blocked. "
            "Use blocked only when a person in the foreground or immediate "
            "travel path occupies or obscures the path. People in the "
            "background, off to the side, or not intersecting the path are not "
            "blockers. Always use blocking_object='person' for humans; never "
            "use woman, man, people, or other demographic labels. Do not mark "
            "boxes, furniture, fixed scene elements, ceilings, walls, cabinets, "
            "doors, shelves, counters, or camera angle as blockers. Return JSON "
            "only."
        ),
    )

    async def describe_status(
        request: GeminiObjectDetectionRequest,
    ) -> GeminiSemanticStatusResult:
        image_bytes = decode_inline_image(request.image_base64)
        response = await client.aio.models.generate_content(
            model=model,
            contents=[
                types.Part.from_text(
                    text=(
                        "Classify the path in this frame. Use state=blocked "
                        "only when a foreground person directly blocks or "
                        "obscures the immediate path. If a human blocks the "
                        "path, set blocking_object exactly to 'person'. Do not "
                        "return woman, man, people, human, or demographic "
                        "labels. "
                        "Use state=clear only when the visible path is not "
                        "blocked by a foreground person. If people are only in "
                        "the background, off to the side, or not intersecting "
                        "the path, use state=clear. If only objects, walls, "
                        "ceiling, cabinets, counters, doors, shelves, or "
                        "camera angle limit the view, use state=clear."
                    ),
                ),
                types.Part.from_bytes(data=image_bytes, mime_type=request.mime_type),
            ],
            config=config,
        )

        if isinstance(response.parsed, GeminiSemanticStatusResult):
            return normalize_semantic_status(response.parsed)

        if response.text is None or response.text.strip() == "":
            raise ValueError("Gemini Robotics-ER returned no semantic status")

        return normalize_semantic_status(
            GeminiSemanticStatusResult.model_validate_json(response.text)
        )

    return describe_status


def build_gemini_object_detection_config() -> types.GenerateContentConfig:
    """Build Gemini structured-output config for object detection."""
    return types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=GEMINI_OBJECT_DETECTION_RESPONSE_SCHEMA,
        system_instruction=(
            "You detect only incident-relevant objects in warehouse camera frames. "
            "Return JSON only. Use bounding boxes in [y_min, x_min, y_max, x_max] "
            "order normalized from 0 to 1000."
        ),
        temperature=0,
        thinking_config=types.ThinkingConfig(
            thinking_level=types.ThinkingLevel.LOW,
        ),
    )


def build_gemini_object_detection_prompt() -> str:
    """Build the detection prompt for a single camera frame."""
    return GEMINI_OBJECT_DETECTION_PROMPT


def decode_inline_image(image_base64: str) -> bytes:
    """Decode a base64 inline image payload."""
    try:
        return base64.b64decode(image_base64, validate=True)
    except binascii.Error as error:
        raise ValueError("image_base64 must be valid base64") from error


def normalize_gemini_detection(
    detection: GeminiRawDetection,
) -> GeminiObjectDetection:
    """Convert Gemini 0-1000 [y, x, y, x] boxes to normalized x/y boxes."""
    y_min, x_min, y_max, x_max = detection.box_2d

    return GeminiObjectDetection(
        label=detection.label,
        confidence=detection.confidence,
        box=GeminiDetectionBox(
            x_min=clamp_unit(x_min / GEMINI_BOX_SCALE),
            y_min=clamp_unit(y_min / GEMINI_BOX_SCALE),
            x_max=clamp_unit(x_max / GEMINI_BOX_SCALE),
            y_max=clamp_unit(y_max / GEMINI_BOX_SCALE),
        ),
    )


def normalize_semantic_status(
    status: GeminiSemanticStatusResult,
) -> GeminiSemanticStatusResult:
    """Keep blocked limited to people and movable obstacle objects."""
    if status.state != PathState.BLOCKED:
        return status

    blocking_object = (status.blocking_object or "").strip().lower()

    if blocking_object in PERSON_BLOCKER_ALIASES:
        return status.model_copy(update={"blocking_object": "person"})

    if blocking_object in ALLOWED_SEMANTIC_BLOCKERS:
        return status

    return GeminiSemanticStatusResult(
        state=PathState.CLEAR,
        blocking_object=None,
        confidence=status.confidence,
        rationale=(
            "No foreground person is blocking the path. "
            f"Original assessment: {status.rationale}"
        ),
    )


def clamp_unit(value: float) -> float:
    """Clamp a normalized value to the image coordinate range."""
    return min(max(value, 0), 1)
