from collections import OrderedDict
from dataclasses import dataclass, field

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
    approval_idempotency_max_entries: int = APPROVAL_IDEMPOTENCY_MAX_ENTRIES
