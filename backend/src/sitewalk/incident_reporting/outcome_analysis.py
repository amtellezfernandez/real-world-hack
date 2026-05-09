from collections.abc import Mapping
from dataclasses import dataclass
from importlib import import_module

from sitewalk.review_export.incident_packet import (
    EncordIncidentExportPacket,
    IncidentOutcomeReport,
    build_local_outcome_report,
)

OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_MODEL_ENV = "OPENAI_MODEL"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


@dataclass(frozen=True)
class OpenAIOutcomeConfig:
    """Normalized OpenAI outcome analysis configuration."""

    api_key: str | None
    model: str


def build_openai_outcome_config_from_env(
    *,
    env: Mapping[str, str],
) -> OpenAIOutcomeConfig:
    """Build normalized OpenAI config from environment-shaped values."""
    return OpenAIOutcomeConfig(
        api_key=_normalized_config_value(env.get(OPENAI_API_KEY_ENV)),
        model=_normalized_config_value(env.get(OPENAI_MODEL_ENV))
        or DEFAULT_OPENAI_MODEL,
    )


def is_openai_outcome_configured(*, config: OpenAIOutcomeConfig) -> bool:
    """Return whether OpenAI outcome analysis can be attempted."""
    return config.api_key is not None


def analyze_incident_outcome(
    *,
    config: OpenAIOutcomeConfig,
    packet: EncordIncidentExportPacket,
) -> IncidentOutcomeReport:
    """Analyze an incident packet with OpenAI when available, else local logic."""
    if not is_openai_outcome_configured(config=config):
        return build_local_outcome_report(packet)

    try:
        return analyze_incident_outcome_with_openai(config=config, packet=packet)
    except Exception:
        return build_local_outcome_report(packet)


def analyze_incident_outcome_with_openai(
    *,
    config: OpenAIOutcomeConfig,
    packet: EncordIncidentExportPacket,
) -> IncidentOutcomeReport:
    """Generate a structured incident outcome report through OpenAI."""
    try:
        openai_module = import_module("openai")
    except ImportError as exc:  # pragma: no cover - depends on optional SDK.
        raise RuntimeError("Install the optional openai package first.") from exc

    client = openai_module.OpenAI(api_key=config.api_key)
    response = client.responses.parse(
        model=config.model,
        input=[
            {
                "role": "system",
                "content": (
                    "You analyze robot safety incident packets. Use only the "
                    "provided ontology vocabulary for recommended_dataset_labels. "
                    "Do not authorize safety closure or claim compliance."
                ),
            },
            {
                "role": "user",
                "content": build_openai_outcome_prompt(packet=packet),
            },
        ],
        text_format=IncidentOutcomeReport,
    )

    parsed_response = response.output_parsed
    if parsed_response is None:
        raise RuntimeError("OpenAI returned no structured outcome report.")

    return parsed_response


def build_openai_outcome_prompt(*, packet: EncordIncidentExportPacket) -> str:
    """Build the compact structured prompt for outcome analysis."""
    ontology = packet.ontology
    objects = ", ".join(item.name for item in ontology.objects)
    classifications = {
        item.name: item.options
        for item in ontology.classifications
        if len(item.options) > 0
    }
    frame_summaries = [
        {
            "role": frame.role,
            "frame_id": frame.evidence_frame.id,
            "image_ref": frame.evidence_frame.image_ref,
            "objects": [label.name for label in frame.objects],
            "classifications": frame.classifications.model_dump(mode="json"),
        }
        for frame in packet.frames
    ]

    return (
        f"Incident id: {packet.incident.id}\n"
        f"Zone id: {packet.incident.zone_id}\n"
        f"Incident state: {packet.incident.state.value}\n"
        f"Review labels: {', '.join(packet.review_sample.labels)}\n"
        f"Allowed ontology objects: {objects}\n"
        f"Allowed classification values: {classifications}\n"
        f"Frame summaries: {frame_summaries}\n"
        "Return a concise outcome analysis with summary, worked, "
        "failed_or_risky, recommended_dataset_labels, and operator_review_needed."
    )


def _normalized_config_value(value: str | None) -> str | None:
    if value is None:
        return None

    stripped_value = value.strip()
    if stripped_value == "":
        return None

    return stripped_value
