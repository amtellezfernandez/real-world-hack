from typing import Annotated

from fastapi import Depends, Request

from sitewalk.api.state import AppContainer
from sitewalk.config import Settings


async def settings_dependency(request: Request) -> Settings:
    """Return runtime settings for FastAPI path operations."""
    container: AppContainer = request.app.state.sitewalk
    return container.settings


SettingsDep = Annotated[Settings, Depends(settings_dependency)]
