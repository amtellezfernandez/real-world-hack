import base64
from binascii import Error as BinasciiError
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from fastapi import APIRouter
from pydantic import Field
from starlette.concurrency import run_in_threadpool

from sitewalk.api.dependencies import AppContainerDep
from sitewalk.api.dependencies import SettingsDep
from sitewalk.api.routes.demo_replay import ASSESSED_BLOCKED_EXIT_REPLAY
from sitewalk.config import build_provider_env
from sitewalk.contracts import ContractModel, ExportStatus
from sitewalk.incident_reporting.outcome_analysis import (
    OpenAIOutcomeConfig,
    analyze_incident_outcome,
    analyze_incident_outcome_with_openai,
    build_openai_outcome_config_from_env,
)
from sitewalk.review_export.encord_config import build_encord_config_from_env
from sitewalk.review_export.encord_live import (
    EncordIncidentExportResult,
    EncordOntologyCreationResult,
    create_robot_safety_ontology,
    export_incident_packet_to_encord,
)
from sitewalk.review_export.encord_ontology import (
    EncordOntologySpec,
    build_robot_safety_ontology_spec,
)
from sitewalk.review_export.incident_packet import (
    EncordIncidentExportPacket,
    IncidentOutcomeDatasetLabels,
    IncidentOutcomeReport,
    build_demo_replay_encord_packet,
    build_local_outcome_report,
)

router = APIRouter(prefix="/api/demo-replay", tags=["demo integrations"])


class OpenAIOutcomeResponse(ContractModel):
    """Outcome report plus the provider selected for analysis."""

    provider: str
    report: IncidentOutcomeReport


class EncordExportRequest(ContractModel):
    """Optional live Encord upload request for demo evidence."""

    before_image_data_url: str | None = Field(default=None)
    after_image_data_url: str | None = Field(default=None)
    before_image_path: str | None = Field(default=None)
    after_image_path: str | None = Field(default=None)
    include_openai_report: bool = True


class LiveIncidentSignalRequest(ContractModel):
    """Live frame payload sent by the browser for the active incident."""

    image_data_url: str = Field(min_length=1)
    blocking_object: str | None = Field(default=None)
    confidence: float | None = Field(default=None, ge=0, le=1)
    rationale: str | None = Field(default=None)


class LiveIncidentSignalResponse(ContractModel):
    """Status for a live incident signal."""

    status: Literal["accepted", "exported", "failed"]
    detail: str
    packet: EncordIncidentExportPacket | None = None
    provider_sample_ids: list[str] = Field(default_factory=list)


@router.get("/encord/ontology")
async def get_demo_encord_ontology() -> EncordOntologySpec:
    """Return the Encord ontology expected by incident exports."""
    return build_robot_safety_ontology_spec()


@router.post("/encord/ontology")
async def create_demo_encord_ontology(
    settings: SettingsDep,
) -> EncordOntologyCreationResult:
    """Create the Encord ontology when live credentials are configured."""
    config = build_encord_config_from_env(env=build_provider_env(settings))
    return await run_in_threadpool(create_robot_safety_ontology, config=config)


@router.get("/encord/export-packet")
async def get_demo_encord_export_packet() -> EncordIncidentExportPacket:
    """Return the Encord-ready incident packet without any provider calls."""
    packet = build_demo_replay_encord_packet(replay=ASSESSED_BLOCKED_EXIT_REPLAY)
    return packet.model_copy(update={"outcome_report": build_local_outcome_report(packet)})


@router.post("/report/openai")
async def analyze_demo_replay_with_openai(
    settings: SettingsDep,
) -> OpenAIOutcomeResponse:
    """Analyze the closed replay incident with OpenAI or local fallback."""
    provider_env = build_provider_env(settings)
    config = build_openai_outcome_config_from_env(env=provider_env)
    packet = build_demo_replay_encord_packet(replay=ASSESSED_BLOCKED_EXIT_REPLAY)
    provider, report = await run_in_threadpool(
        analyze_outcome_with_provider_label,
        config=config,
        packet=packet,
    )

    return OpenAIOutcomeResponse(provider=provider, report=report)


@router.post("/export/encord")
async def export_demo_replay_to_encord(
    request: EncordExportRequest,
    settings: SettingsDep,
) -> EncordIncidentExportResult:
    """Upload before/after incident evidence to Encord when configured."""
    provider_env = build_provider_env(settings)
    openai_config = build_openai_outcome_config_from_env(env=provider_env)
    packet_without_report = build_demo_replay_encord_packet(
        replay=ASSESSED_BLOCKED_EXIT_REPLAY,
    )
    outcome_report = (
        await run_in_threadpool(
            analyze_incident_outcome,
            config=openai_config,
            packet=packet_without_report,
        )
        if request.include_openai_report
        else build_local_outcome_report(packet_without_report)
    )
    packet = build_demo_replay_encord_packet(
        replay=ASSESSED_BLOCKED_EXIT_REPLAY,
        outcome_report=outcome_report,
    )
    encord_config = build_encord_config_from_env(env=provider_env)

    try:
        with TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            before_image_path = resolve_upload_image_path(
                data_url=request.before_image_data_url,
                path=request.before_image_path,
                temp_dir=temp_dir,
                role="before",
            )
            after_image_path = resolve_upload_image_path(
                data_url=request.after_image_data_url,
                path=request.after_image_path,
                temp_dir=temp_dir,
                role="after",
            )

            return await run_in_threadpool(
                export_incident_packet_to_encord,
                config=encord_config,
                packet=packet,
                before_image_path=before_image_path,
                after_image_path=after_image_path,
            )
    except ValueError as exc:
        return EncordIncidentExportResult(
            status=ExportStatus.EXPORT_UNAVAILABLE,
            detail=str(exc),
            packet=packet,
        )


@router.post("/incident/open")
async def open_live_incident(
    request: LiveIncidentSignalRequest,
    container: AppContainerDep,
) -> LiveIncidentSignalResponse:
    """Store the before frame for the current live incident."""
    opened_at = datetime.now(UTC).isoformat()
    with container.live_incident_lock:
        object.__setattr__(
            container,
            "live_incident_before_image_data_url",
            request.image_data_url,
        )
        object.__setattr__(container, "live_incident_after_image_data_url", None)
        object.__setattr__(
            container,
            "live_incident_blocking_object",
            request.blocking_object,
        )
        object.__setattr__(
            container,
            "live_incident_blocked_rationale",
            request.rationale,
        )
        object.__setattr__(
            container,
            "live_incident_blocked_confidence",
            request.confidence,
        )
        object.__setattr__(container, "live_incident_opened_at", opened_at)

    return LiveIncidentSignalResponse(
        status="accepted",
        detail="Before frame stored. Resolve the incident to export to Encord.",
    )


@router.post("/incident/resolve")
async def resolve_live_incident(
    request: LiveIncidentSignalRequest,
    container: AppContainerDep,
    settings: SettingsDep,
) -> LiveIncidentSignalResponse:
    """Resolve the live incident and export the stored frames to Encord."""
    with container.live_incident_lock:
        before_image_data_url = container.live_incident_before_image_data_url
        blocking_object = container.live_incident_blocking_object
        blocked_rationale = container.live_incident_blocked_rationale
        blocked_confidence = container.live_incident_blocked_confidence
        opened_at = container.live_incident_opened_at
        object.__setattr__(
            container,
            "live_incident_after_image_data_url",
            request.image_data_url,
        )

    if before_image_data_url is None:
        return LiveIncidentSignalResponse(
            status="failed",
            detail="Open the incident before resolving it.",
        )

    provider_env = build_provider_env(settings)
    packet_without_report = build_demo_replay_encord_packet(
        replay=ASSESSED_BLOCKED_EXIT_REPLAY,
    )
    outcome_report = build_live_incident_outcome_report(
        packet=packet_without_report,
        blocking_object=blocking_object,
        blocked_rationale=blocked_rationale,
        blocked_confidence=blocked_confidence,
        opened_at=opened_at,
        resolved_at=datetime.now(UTC).isoformat(),
        clear_rationale=request.rationale,
        clear_confidence=request.confidence,
    )
    packet = build_demo_replay_encord_packet(
        replay=ASSESSED_BLOCKED_EXIT_REPLAY,
        outcome_report=outcome_report,
    )
    packet = packet.model_copy(
        update={
            "metadata": {
                **packet.metadata,
                "source": "live_webcam",
                "blocked_state": "blocked",
                "resolved_state": "not_blocked",
                "blocking_object": blocking_object or "unknown",
                "blocked_confidence": format_optional_confidence(blocked_confidence),
                "clear_confidence": format_optional_confidence(request.confidence),
                "blocked_rationale": blocked_rationale or "",
                "clear_rationale": request.rationale or "",
                "opened_at": opened_at or "",
                "resolved_at": datetime.now(UTC).isoformat(),
            },
        },
    )
    encord_config = build_encord_config_from_env(env=provider_env)

    try:
        with TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            before_image_path = write_data_url_image(
                temp_dir=temp_dir,
                data_url=before_image_data_url,
                role="before",
            )
            after_image_path = write_data_url_image(
                temp_dir=temp_dir,
                data_url=request.image_data_url,
                role="after",
            )
            result = await run_in_threadpool(
                export_incident_packet_to_encord,
                config=encord_config,
                packet=packet,
                before_image_path=before_image_path,
                after_image_path=after_image_path,
            )
    except ValueError as exc:
        return LiveIncidentSignalResponse(
            status="failed",
            detail=str(exc),
            packet=packet,
        )

    with container.live_incident_lock:
        if result.status == ExportStatus.EXPORTED:
            object.__setattr__(container, "live_incident_before_image_data_url", None)
            object.__setattr__(container, "live_incident_after_image_data_url", None)
            object.__setattr__(container, "live_incident_blocking_object", None)
            object.__setattr__(container, "live_incident_blocked_rationale", None)
            object.__setattr__(container, "live_incident_blocked_confidence", None)
            object.__setattr__(container, "live_incident_opened_at", None)

    if result.status == ExportStatus.EXPORTED:
        return LiveIncidentSignalResponse(
            status="exported",
            detail=result.detail,
            packet=result.packet,
            provider_sample_ids=result.provider_sample_ids,
        )

    return LiveIncidentSignalResponse(
        status="failed",
        detail=result.detail,
        packet=result.packet,
        provider_sample_ids=result.provider_sample_ids,
    )


def path_or_none(value: str | None) -> Path | None:
    """Convert an optional request path into a Path."""
    if value is None or value.strip() == "":
        return None

    return Path(value)


def resolve_upload_image_path(
    *,
    data_url: str | None,
    path: str | None,
    temp_dir: Path,
    role: str,
) -> Path | None:
    """Materialize an upload image path from either a path or a data URL."""
    if data_url is not None and data_url.strip() != "":
        return write_data_url_image(temp_dir=temp_dir, data_url=data_url, role=role)

    return path_or_none(path)


def write_data_url_image(*, temp_dir: Path, data_url: str, role: str) -> Path:
    """Persist a base64 data URL image to disk for Encord upload."""
    if not data_url.startswith("data:") or "," not in data_url:
        raise ValueError(f"{role} image data must be a data URL.")

    header, payload = data_url.split(",", 1)
    if ";base64" not in header:
        raise ValueError(f"{role} image data URL must use base64 encoding.")

    mime_type = header[5:].split(";", 1)[0]
    suffix = ".jpg" if "jpeg" in mime_type or "jpg" in mime_type else ".png"

    try:
        decoded = base64.b64decode(payload, validate=True)
    except (BinasciiError, ValueError) as exc:
        raise ValueError(f"{role} image data URL could not be decoded.") from exc

    output_path = temp_dir / f"{role}{suffix}"
    output_path.write_bytes(decoded)
    return output_path


def build_live_incident_outcome_report(
    *,
    packet: EncordIncidentExportPacket,
    blocking_object: str | None,
    blocked_rationale: str | None,
    blocked_confidence: float | None,
    opened_at: str | None,
    resolved_at: str,
    clear_rationale: str | None,
    clear_confidence: float | None,
) -> IncidentOutcomeReport:
    """Build the outcome report for the live before/after webcam incident."""
    before_frame = packet.frames[0]
    after_frame = packet.frames[-1]
    blocker = blocking_object or "unknown obstacle"
    blocked_confidence_text = format_optional_confidence(blocked_confidence)
    clear_confidence_text = format_optional_confidence(clear_confidence)

    return IncidentOutcomeReport(
        summary=(
            "Live webcam incident transitioned from blocked to not blocked. "
            f"Gemini Robotics-ER reported blocker={blocker} "
            f"confidence={blocked_confidence_text} at {opened_at or 'unknown time'}; "
            f"then reported clear confidence={clear_confidence_text} at {resolved_at}. "
            f"Blocked rationale: {blocked_rationale or 'not provided'} "
            f"Clear rationale: {clear_rationale or 'not provided'}"
        ),
        worked=[
            "Captured the blocked frame when the robot stopped.",
            "Captured the not-blocked frame when the path cleared.",
            "Exported the before/after image pair with this live incident summary.",
        ],
        failed_or_risky=[
            "The live packet uses the demo ontology metadata while the images come from the webcam.",
        ],
        recommended_dataset_labels=IncidentOutcomeDatasetLabels(
            zone_state_before=before_frame.classifications.zone_state,
            zone_state_after=after_frame.classifications.zone_state,
            verification_result=after_frame.classifications.verification_result,
            review_decision=after_frame.classifications.review_decision,
        ),
        operator_review_needed=False,
    )


def format_optional_confidence(confidence: float | None) -> str:
    """Format optional confidence for Encord metadata."""
    if confidence is None:
        return "unknown"

    return f"{confidence:.2f}"


def analyze_outcome_with_provider_label(
    *,
    config: OpenAIOutcomeConfig,
    packet: EncordIncidentExportPacket,
) -> tuple[str, IncidentOutcomeReport]:
    """Return the outcome report and the provider that actually produced it."""
    if config.api_key is None:
        return "local", build_local_outcome_report(packet)

    try:
        return "openai", analyze_incident_outcome_with_openai(
            config=config,
            packet=packet,
        )
    except Exception:
        return "local", build_local_outcome_report(packet)
