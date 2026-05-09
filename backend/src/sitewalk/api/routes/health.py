from fastapi import APIRouter

from sitewalk.api.dependencies import SettingsDep
from sitewalk.contracts import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health")
async def get_health(settings: SettingsDep) -> HealthResponse:
    """Return backend readiness."""
    return HealthResponse(
        service=settings.service_name,
        status="ready",
        version=settings.version,
    )
