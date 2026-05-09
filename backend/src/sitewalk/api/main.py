from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sitewalk.api.routes import (
    demo_integrations,
    demo_replay,
    health,
    incidents,
    motion,
    product_contract,
)
from sitewalk.api.state import AppContainer
from sitewalk.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the FastAPI application."""
    resolved_settings = settings or get_settings()
    application = FastAPI(
        title="RobotOps Sentinel API",
        license_info={
            "identifier": "LicenseRef-Proprietary",
            "name": "Proprietary hackathon prototype",
        },
        servers=[
            {
                "description": "Local development backend",
                "url": "http://127.0.0.1:8000",
            },
        ],
        summary="Closed-loop robotics supervision backend.",
        version=resolved_settings.version,
    )
    application.state.sitewalk = AppContainer(settings=resolved_settings)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_origin_regex=resolved_settings.cors_origin_regex,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    application.include_router(demo_replay.router)
    application.include_router(demo_integrations.router)
    application.include_router(health.router)
    application.include_router(incidents.router)
    application.include_router(motion.router)
    application.include_router(product_contract.router)
    return application


app = create_app()
