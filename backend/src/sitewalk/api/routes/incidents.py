import asyncio
from collections.abc import AsyncIterator, Iterable, Iterator
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from sitewalk.api.dependencies import AppContainerDep
from sitewalk.api.demo_replay_service import approve_incident_alert
from sitewalk.api.routes.demo_replay import ASSESSED_BLOCKED_EXIT_REPLAY
from sitewalk.api.state import AppContainer
from sitewalk.contracts import (
    ApproveAlertRequest,
    AuditPacket,
    ClearanceVerification,
    ClearanceVerificationResponse,
    IncidentCommandResponse,
    IncidentDetail,
    IncidentState,
    ObservationStreamBox,
    ObservationStreamEvent,
    ObservationStreamIncident,
    ObservationStreamZone,
    ReplayFrame,
    SafetyIncident,
    VerificationVerdict,
)

router = APIRouter(prefix="/api", tags=["incidents"])


@router.get(
    "/observations/stream",
    response_class=StreamingResponse,
    responses={
        status.HTTP_200_OK: {
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
            "description": "Server-sent observation event stream.",
        },
    },
)
async def stream_observations() -> StreamingResponse:
    return StreamingResponse(
        _stream_observation_events(),
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
        media_type="text/event-stream",
    )


@router.get("/incidents/{incident_id}")
async def get_incident(incident_id: str) -> IncidentDetail:
    frame, incident = _get_latest_incident_detail_source(incident_id)
    recommendation = (
        incident.incident_report.recommended_action
        if incident.incident_report is not None
        else "Review the latest observation and dispatch a supervisor if needed."
    )

    return IncidentDetail(
        incident_id=incident.id,
        state=incident.state,
        incident_report=incident.incident_report,
        severity=incident.severity,
        recommendation=recommendation,
        latest_observation=frame.observation,
    )


@router.post("/incidents/{incident_id}/approve-alert")
async def approve_alert(
    incident_id: str,
    approval: ApproveAlertRequest,
    container: AppContainerDep,
) -> IncidentCommandResponse:
    cache_key = f"{incident_id}:{approval.decision}:{approval.idempotency_key}"
    cached_response = container.approval_idempotency.get(cache_key)
    if cached_response is not None:
        return cached_response

    source_incident = _get_open_incident(incident_id)
    approved_incident = approve_incident_alert(
        incident=source_incident,
        approval_actor=approval.approval_actor,
        timestamp=datetime.now(UTC),
        alert_text=approval.alert_text,
    )
    alert_event = approved_incident.alert_events[-1]

    response = IncidentCommandResponse(
        incident_id=approved_incident.id,
        state=approved_incident.state,
        alert_event=alert_event,
    )
    _remember_approval_response(container, cache_key, response)
    return response


@router.post("/incidents/{incident_id}/verify-clearance")
async def verify_clearance(incident_id: str) -> ClearanceVerificationResponse:
    incident, verification = _get_clear_incident(incident_id)

    return ClearanceVerificationResponse(
        incident_id=incident.id,
        state=IncidentState.VERIFIED_CLEAR,
        verification=verification,
    )


@router.get("/incidents/{incident_id}/audit-packet")
async def get_audit_packet(incident_id: str) -> AuditPacket:
    incident, _verification = _get_clear_incident(incident_id)

    if incident.audit_packet is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="incident does not have an audit packet",
        )

    return incident.audit_packet


async def _stream_observation_events() -> AsyncIterator[str]:
    for event_chunk in OBSERVATION_STREAM_CHUNKS:
        yield event_chunk
        await asyncio.sleep(0.25)


def _build_stream_event(frame: ReplayFrame) -> ObservationStreamEvent:
    incident = frame.assessment.incident
    stream_incident = (
        None
        if incident is None
        else ObservationStreamIncident(id=incident.id, state=incident.state)
    )

    return ObservationStreamEvent(
        frame_id=frame.evidence_frame.id,
        boxes=[
            ObservationStreamBox(
                label=annotation.label,
                confidence=annotation.confidence,
            )
            for annotation in frame.evidence_frame.annotations
        ],
        zone=ObservationStreamZone(
            state=frame.observation.observed_state,
            dwell_seconds=frame.observation.dwell_duration_seconds,
        ),
        incident=stream_incident,
    )


def _format_observation_stream_event(frame: ReplayFrame) -> str:
    payload = _build_stream_event(frame)
    return f"event: observation\ndata: {payload.model_dump_json()}\n\n"


def _iter_incident_frames(*, reverse: bool) -> Iterator[tuple[ReplayFrame, SafetyIncident]]:
    frames: Iterable[ReplayFrame] = (
        reversed(ASSESSED_BLOCKED_EXIT_REPLAY.frames)
        if reverse
        else ASSESSED_BLOCKED_EXIT_REPLAY.frames
    )

    for frame in frames:
        incident = frame.assessment.incident
        if incident is not None:
            yield frame, incident


def _get_latest_incident_detail_source(
    incident_id: str,
) -> tuple[ReplayFrame, SafetyIncident]:
    for frame, incident in _iter_incident_frames(reverse=True):
        if incident.id == incident_id:
            return frame, incident

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="incident not found",
    )


def _get_open_incident(incident_id: str) -> SafetyIncident:
    for _frame, incident in _iter_incident_frames(reverse=False):
        if incident.id == incident_id and incident.state == IncidentState.INCIDENT_OPEN:
            return incident

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="open incident not found",
    )


def _get_clear_incident(incident_id: str) -> tuple[SafetyIncident, ClearanceVerification]:
    for _frame, incident in _iter_incident_frames(reverse=True):
        verification = incident.verification
        if (
            incident.id == incident_id
            and verification is not None
            and verification.verdict == VerificationVerdict.CLEAR
        ):
            return incident, verification

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="clear incident not found",
    )


def _remember_approval_response(
    container: AppContainer,
    cache_key: str,
    response: IncidentCommandResponse,
) -> None:
    container.approval_idempotency[cache_key] = response
    container.approval_idempotency.move_to_end(cache_key)

    while (
        len(container.approval_idempotency)
        > container.approval_idempotency_max_entries
    ):
        container.approval_idempotency.popitem(last=False)


OBSERVATION_STREAM_CHUNKS = tuple(
    _format_observation_stream_event(frame)
    for frame in ASSESSED_BLOCKED_EXIT_REPLAY.frames
)
