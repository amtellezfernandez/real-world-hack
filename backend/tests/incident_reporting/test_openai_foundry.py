from datetime import UTC, datetime

import pytest

from sitewalk.contracts import (
    EvidenceFrame,
    EvidenceSource,
    IncidentState,
    IncidentReport,
    Observation,
    ObservedState,
    SafetyIncident,
    Severity,
)
from sitewalk.demo_data import PRIMARY_DEMO_ZONE
from sitewalk.incident_reporting.openai_foundry import (
    OpenAIIncidentReportRefusal,
    OpenAIIncidentReportRequest,
    OpenAIIncidentReportResult,
    build_openai_foundry_incident_reporter,
)
from sitewalk.safety import assess_observation

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def make_open_incident() -> SafetyIncident:
    evidence_frame = EvidenceFrame(
        id="frame-workcell-sustained",
        source=EvidenceSource.REPLAY,
        timestamp=datetime(2026, 5, 8, 12, 0, 30, tzinfo=UTC),
        image_ref="assets/demo/workcell-blocked.svg",
    )
    assessment = assess_observation(
        zone=PRIMARY_DEMO_ZONE,
        evidence_frame=evidence_frame,
        observation=Observation(
            zone_id=PRIMARY_DEMO_ZONE.id,
            observed_state=ObservedState.BLOCKED,
            dwell_duration_seconds=30,
            evidence_frame_id=evidence_frame.id,
            confidence=0.94,
        ),
    )

    assert assessment.incident is not None
    return assessment.incident


async def test_openai_foundry_reporter_returns_structured_incident_report() -> None:
    requests: list[OpenAIIncidentReportRequest] = []

    async def generate_report(
        request: OpenAIIncidentReportRequest,
    ) -> OpenAIIncidentReportResult:
        requests.append(request)
        return OpenAIIncidentReportResult(
            hazard="Blocked robot workcell",
            severity=Severity.HIGH,
            evidence_summary=(
                "Frame frame-workcell-sustained shows an object inside zone-workcell-a2."
            ),
            rationale="The obstruction persisted long enough to meet policy.",
            recommended_action="Send a robotics supervisor to clear the workcell.",
            alert_text_candidate=(
                "Robotics notice: clear the obstruction at Robot Workcell A-2."
            ),
        )

    reporter = build_openai_foundry_incident_reporter(
        client=generate_report,
        model="gpt-5.1",
    )

    report = await reporter(make_open_incident())

    assert report == IncidentReport(
        hazard="Blocked robot workcell",
        severity=Severity.HIGH,
        evidence_summary=(
            "Frame frame-workcell-sustained shows an object inside zone-workcell-a2."
        ),
        rationale="The obstruction persisted long enough to meet policy.",
        recommended_action="Send a robotics supervisor to clear the workcell.",
        alert_text_candidate=(
            "Robotics notice: clear the obstruction at Robot Workcell A-2."
        ),
    )
    assert len(requests) == 1
    assert requests[0].model == "gpt-5.1"
    assert requests[0].incident_id.startswith("incident-zone-workcell-a2")
    assert requests[0].severity == Severity.HIGH
    assert requests[0].response_schema_name == "sitewalk_incident_report"
    assert requests[0].required_fields == (
        "hazard",
        "severity",
        "evidence_summary",
        "rationale",
        "recommended_action",
        "alert_text_candidate",
    )
    assert "Existing deterministic report:" in requests[0].user_prompt
    assert "Blocked robot workcell" in requests[0].user_prompt
    assert "Dispatch a robotics supervisor" in requests[0].user_prompt


async def test_openai_foundry_reporter_rejects_provider_refusal() -> None:
    async def refuse_report(
        request: OpenAIIncidentReportRequest,
    ) -> OpenAIIncidentReportRefusal:
        return OpenAIIncidentReportRefusal(refusal=f"refused {request.incident_id}")

    reporter = build_openai_foundry_incident_reporter(
        client=refuse_report,
        model="gpt-5.1",
    )

    with pytest.raises(ValueError, match="structured incident report was refused"):
        await reporter(make_open_incident())


async def test_openai_foundry_reporter_rejects_severity_mismatch() -> None:
    async def generate_report(
        request: OpenAIIncidentReportRequest,
    ) -> OpenAIIncidentReportResult:
        return OpenAIIncidentReportResult(
            hazard="Blocked robot workcell",
            severity=Severity.LOW,
            evidence_summary=f"Frame {request.before_evidence_frame_id} is blocked.",
            rationale="The obstruction persisted long enough to meet policy.",
            recommended_action="Send a robotics supervisor to clear the workcell.",
            alert_text_candidate=(
                "Robotics notice: clear the obstruction at Robot Workcell A-2."
            ),
        )

    reporter = build_openai_foundry_incident_reporter(
        client=generate_report,
        model="gpt-5.1",
    )

    with pytest.raises(
        ValueError,
        match="structured report severity must match incident severity",
    ):
        await reporter(make_open_incident())


async def test_openai_foundry_reporter_rejects_non_open_incident() -> None:
    async def generate_report(
        request: OpenAIIncidentReportRequest,
    ) -> OpenAIIncidentReportResult:
        return OpenAIIncidentReportResult(
            hazard="Blocked robot workcell",
            severity=Severity.HIGH,
            evidence_summary=f"Frame {request.before_evidence_frame_id} is blocked.",
            rationale="The obstruction persisted long enough to meet policy.",
            recommended_action="Send a robotics supervisor to clear the workcell.",
            alert_text_candidate=(
                "Robotics notice: clear the obstruction at Robot Workcell A-2."
            ),
        )

    open_incident = make_open_incident()
    reporter = build_openai_foundry_incident_reporter(
        client=generate_report,
        model="gpt-5.1",
    )

    with pytest.raises(
        ValueError,
        match="incident report enrichment requires an open incident",
    ):
        await reporter(
            SafetyIncident(
                id=open_incident.id,
                zone_id=open_incident.zone_id,
                state=IncidentState.ALERT_PENDING,
                severity=open_incident.severity,
                before_evidence_frame_id=open_incident.before_evidence_frame_id,
                incident_report=open_incident.incident_report,
            ),
        )


def test_safety_incident_rejects_report_severity_mismatch() -> None:
    open_incident = make_open_incident()

    with pytest.raises(
        ValueError,
        match="incident report severity must match incident severity",
    ):
        SafetyIncident(
            id=open_incident.id,
            zone_id=open_incident.zone_id,
            state=open_incident.state,
            severity=open_incident.severity,
            before_evidence_frame_id=open_incident.before_evidence_frame_id,
            incident_report=IncidentReport(
                hazard="Blocked robot workcell",
                severity=Severity.LOW,
                evidence_summary=(
                    "frame-workcell-sustained shows Robot Workcell A-2 blocked."
                ),
                rationale="Robot Workcell A-2 has been blocked for 30.0s.",
                recommended_action=(
                    "Dispatch a floor supervisor to clear the obstruction."
                ),
                alert_text_candidate=(
                    "Robotics notice: clear the obstruction at Robot Workcell A-2."
                ),
            ),
        )
