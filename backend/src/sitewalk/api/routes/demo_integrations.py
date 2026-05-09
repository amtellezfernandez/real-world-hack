from pathlib import Path

from fastapi import APIRouter
from pydantic import Field
from starlette.concurrency import run_in_threadpool

from sitewalk.api.dependencies import SettingsDep
from sitewalk.api.routes.demo_replay import ASSESSED_BLOCKED_EXIT_REPLAY
from sitewalk.config import build_provider_env
from sitewalk.contracts import ContractModel
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

    before_image_path: str | None = Field(default=None)
    after_image_path: str | None = Field(default=None)
    include_openai_report: bool = True


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

    return await run_in_threadpool(
        export_incident_packet_to_encord,
        config=encord_config,
        packet=packet,
        before_image_path=path_or_none(request.before_image_path),
        after_image_path=path_or_none(request.after_image_path),
    )


def path_or_none(value: str | None) -> Path | None:
    """Convert an optional request path into a Path."""
    if value is None or value.strip() == "":
        return None

    return Path(value)


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
