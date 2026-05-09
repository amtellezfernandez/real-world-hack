from typing import Annotated

from fastapi import Depends, Request

from sitewalk.api.state import AppContainer
from sitewalk.config import Settings
from sitewalk.perception.gemini_robotics_er import (
    GeminiObjectDetectionClient,
    GeminiSemanticStatusClient,
)


async def app_container_dependency(request: Request) -> AppContainer:
    """Return typed runtime dependencies for FastAPI path operations."""
    container: AppContainer = request.app.state.sitewalk
    return container


AppContainerDep = Annotated[AppContainer, Depends(app_container_dependency)]


async def settings_dependency(container: AppContainerDep) -> Settings:
    """Return runtime settings for FastAPI path operations."""
    return container.settings


SettingsDep = Annotated[Settings, Depends(settings_dependency)]


async def object_detection_client_dependency(
    container: AppContainerDep,
) -> GeminiObjectDetectionClient | None:
    """Return the configured object detection client when available."""
    return container.object_detection_client


ObjectDetectionClientDep = Annotated[
    GeminiObjectDetectionClient | None,
    Depends(object_detection_client_dependency),
]


async def semantic_status_client_dependency(
    container: AppContainerDep,
) -> GeminiSemanticStatusClient | None:
    """Return the configured semantic status client when available."""
    return container.semantic_status_client


SemanticStatusClientDep = Annotated[
    GeminiSemanticStatusClient | None,
    Depends(semantic_status_client_dependency),
]
