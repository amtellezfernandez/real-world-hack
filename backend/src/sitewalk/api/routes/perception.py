from fastapi import APIRouter, HTTPException

from datetime import UTC, datetime

from sitewalk.api.dependencies import ObjectDetectionClientDep, SemanticStatusClientDep
from sitewalk.perception.gemini_robotics_er import (
    GeminiObjectDetectionRequest,
    GeminiObjectDetectionResponse,
    GeminiSemanticStatusResult,
    PathState,
)
from sitewalk.contracts import ContractModel

router = APIRouter(prefix="/api/perception", tags=["perception"])


class SemanticStatusResponse(ContractModel):
    """Semantic status result for a camera frame."""

    assessed_at: datetime
    status: GeminiSemanticStatusResult


@router.post("/detect")
async def detect_incident_objects(
    request: GeminiObjectDetectionRequest,
    detect_objects: ObjectDetectionClientDep,
) -> GeminiObjectDetectionResponse:
    """Detect incident-relevant objects in a camera frame."""
    if detect_objects is None:
        raise HTTPException(
            status_code=503,
            detail="Object detection provider is not configured.",
        )

    try:
        return await detect_objects(request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail="Gemini Robotics-ER object detection failed.",
        ) from error


@router.post("/semantic-status")
async def describe_semantic_status(
    request: GeminiObjectDetectionRequest,
    describe_status: SemanticStatusClientDep,
) -> SemanticStatusResponse:
    """Describe the semantic status of a camera frame."""
    if describe_status is None:
        raise HTTPException(
            status_code=503,
            detail="Semantic status provider is not configured.",
        )

    try:
        status = await describe_status(request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail="Gemini Robotics-ER semantic status failed.",
        ) from error

    print(format_semantic_status_log(status), flush=True)
    return SemanticStatusResponse(assessed_at=datetime.now(UTC), status=status)


def format_semantic_status_log(status: GeminiSemanticStatusResult) -> str:
    """Format semantic status for terminal logs."""
    if status.state == PathState.BLOCKED:
        return format_colored_semantic_status_log(
            color_code="31",
            label="BLOCKED",
            status=status,
        )

    return format_colored_semantic_status_log(
        color_code="32",
        label="CLEAR",
        status=status,
    )


def format_colored_semantic_status_log(
    *,
    color_code: str,
    label: str,
    status: GeminiSemanticStatusResult,
) -> str:
    """Format a semantic status with an ANSI color."""
    return (
        f"\033[{color_code}m"
        f"[semantic-status] [{label}] "
        f"state={status.state.value} "
        f"blocking_object={status.blocking_object or 'none'} "
        f"confidence={status.confidence:.2f} "
        f"rationale={status.rationale}"
        "\033[0m"
    )
