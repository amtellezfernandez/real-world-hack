from collections import OrderedDict
from dataclasses import dataclass, field
from threading import Lock

from sitewalk.contracts import IncidentCommandResponse
from sitewalk.config import Settings

APPROVAL_IDEMPOTENCY_MAX_ENTRIES = 128


@dataclass(frozen=True)
class AppContainer:
    """Typed FastAPI application container."""

    settings: Settings
    approval_idempotency: OrderedDict[str, IncidentCommandResponse] = field(
        default_factory=OrderedDict,
    )
    motion_lock: Lock = field(default_factory=Lock)
    motion_previous_frame: list[int] | None = None
    motion_pose_x: float = 24
    motion_pose_y: float = 76
    motion_heading: float = 90
    live_incident_lock: Lock = field(default_factory=Lock)
    live_incident_before_image_data_url: str | None = None
    live_incident_after_image_data_url: str | None = None
    approval_idempotency_max_entries: int = APPROVAL_IDEMPOTENCY_MAX_ENTRIES
