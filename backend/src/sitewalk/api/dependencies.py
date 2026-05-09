from typing import Annotated

from fastapi import Depends, Request

from sitewalk.api.state import AppContainer
from sitewalk.config import Settings


async def app_container_dependency(request: Request) -> AppContainer:
    """Return typed runtime dependencies for FastAPI path operations."""
    container: AppContainer = request.app.state.sitewalk
    return container


AppContainerDep = Annotated[AppContainer, Depends(app_container_dependency)]


async def settings_dependency(container: AppContainerDep) -> Settings:
    """Return runtime settings for FastAPI path operations."""
    return container.settings


SettingsDep = Annotated[Settings, Depends(settings_dependency)]
