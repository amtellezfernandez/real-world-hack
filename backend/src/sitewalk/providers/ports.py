from collections.abc import Awaitable, Callable

from sitewalk.contracts import (
    AlertEvent,
    ClearanceVerification,
    CriticalZone,
    EvidenceFrame,
    IncidentReport,
    Observation,
    ReviewSample,
    SafetyIncident,
)

type PerceptionSource = Callable[[EvidenceFrame, CriticalZone], Awaitable[Observation]]
type IncidentReporter = Callable[[SafetyIncident], Awaitable[IncidentReport]]
type VoiceBroadcaster = Callable[[AlertEvent], Awaitable[AlertEvent]]
type ClearanceVerifier = Callable[
    [SafetyIncident, EvidenceFrame, Observation],
    Awaitable[ClearanceVerification],
]
type ReviewExporter = Callable[[ReviewSample], Awaitable[ReviewSample]]
