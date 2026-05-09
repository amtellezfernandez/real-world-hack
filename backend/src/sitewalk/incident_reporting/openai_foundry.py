from collections.abc import Awaitable, Callable

from pydantic import Field

from sitewalk.contracts import (
    ContractModel,
    IncidentReport,
    IncidentState,
    SafetyIncident,
    Severity,
)
from sitewalk.providers.ports import IncidentReporter

type OpenAIIncidentReportClient = Callable[
    ["OpenAIIncidentReportRequest"],
    Awaitable["OpenAIIncidentReportResult | OpenAIIncidentReportRefusal"],
]

INCIDENT_REPORT_REQUIRED_FIELDS = tuple(IncidentReport.model_fields)

REQUIRED_INCIDENT_REPORT_FIELDS = (
    "hazard",
    "severity",
    "evidence_summary",
    "rationale",
    "recommended_action",
    "alert_text_candidate",
)

if INCIDENT_REPORT_REQUIRED_FIELDS != REQUIRED_INCIDENT_REPORT_FIELDS:
    raise RuntimeError("incident report schema fields changed")


class OpenAIIncidentReportRequest(ContractModel):
    """Structured-output request for an OpenAI/Foundry incident report."""

    incident_id: str
    before_evidence_frame_id: str
    model: str
    required_fields: tuple[str, ...]
    response_schema_name: str
    severity: Severity
    system_prompt: str
    user_prompt: str
    zone_id: str


class OpenAIIncidentReportResult(ContractModel):
    """Structured incident-report fields returned by the provider."""

    hazard: str = Field(min_length=1)
    severity: Severity
    evidence_summary: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    recommended_action: str = Field(min_length=1)
    alert_text_candidate: str = Field(min_length=1)


class OpenAIIncidentReportRefusal(ContractModel):
    """Provider refusal returned instead of the requested structured report."""

    refusal: str = Field(min_length=1)


def build_openai_foundry_incident_reporter(
    *,
    client: OpenAIIncidentReportClient,
    model: str,
) -> IncidentReporter:
    """Build an incident reporter backed by OpenAI structured output."""

    async def report_incident(incident: SafetyIncident) -> IncidentReport:
        if incident.state != IncidentState.INCIDENT_OPEN:
            raise ValueError("incident report enrichment requires an open incident")

        result = await client(
            build_openai_incident_report_request(incident=incident, model=model),
        )

        if isinstance(result, OpenAIIncidentReportRefusal):
            raise ValueError("structured incident report was refused")

        if result.severity != incident.severity:
            raise ValueError("structured report severity must match incident severity")

        return IncidentReport(
            hazard=result.hazard,
            severity=result.severity,
            evidence_summary=result.evidence_summary,
            rationale=result.rationale,
            recommended_action=result.recommended_action,
            alert_text_candidate=result.alert_text_candidate,
        )

    return report_incident


def build_openai_incident_report_request(
    *,
    incident: SafetyIncident,
    model: str,
) -> OpenAIIncidentReportRequest:
    """Build the structured-output request sent through the provider client."""
    incident_report = incident.incident_report

    if incident_report is None:
        raise ValueError("incident must include deterministic report context")

    return OpenAIIncidentReportRequest(
        incident_id=incident.id,
        before_evidence_frame_id=incident.before_evidence_frame_id,
        model=model,
        required_fields=INCIDENT_REPORT_REQUIRED_FIELDS,
        response_schema_name="sitewalk_incident_report",
        severity=incident.severity,
        system_prompt=(
            "You write concise safety incident reports from structured evidence. "
            "Do not authorize closure, broadcast alerts, or make compliance claims."
        ),
        user_prompt=(
            f"Incident {incident.id} is open for zone {incident.zone_id}. "
            f"Severity is {incident.severity.value}. "
            f"Before evidence frame is {incident.before_evidence_frame_id}. "
            "Existing deterministic report: "
            f"hazard={incident_report.hazard!r}; "
            f"evidence_summary={incident_report.evidence_summary!r}; "
            f"rationale={incident_report.rationale!r}; "
            f"recommended_action={incident_report.recommended_action!r}; "
            f"alert_text_candidate={incident_report.alert_text_candidate!r}. "
            "Return hazard, severity, evidence_summary, rationale, "
            "recommended_action, and alert_text_candidate."
        ),
        zone_id=incident.zone_id,
    )
