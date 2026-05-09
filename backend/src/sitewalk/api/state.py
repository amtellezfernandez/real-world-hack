from dataclasses import dataclass

from sitewalk.config import Settings


@dataclass(frozen=True)
class AppContainer:
    """Typed FastAPI application container."""

    settings: Settings
