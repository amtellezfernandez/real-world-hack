from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sitewalk.api.routes import (
    demo_integrations,
    demo_replay,
    health,
    incidents,
    motion,
    perception,
    product_contract,
)
from sitewalk.api.state import AppContainer
from sitewalk.config import Settings, get_settings
from sitewalk.perception.gemini_robotics_er import (
    GeminiObjectDetectionClient,
    GeminiSemanticStatusClient,
    build_google_genai_object_detection_client,
    build_google_genai_semantic_status_client,
)
from sitewalk.verification.gemini_robotics_er import build_google_genai_client


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
    application.state.sitewalk = AppContainer(
        settings=resolved_settings,
        object_detection_client=build_object_detection_client(
            resolved_settings,
        ),
        semantic_status_client=build_semantic_status_client(resolved_settings),
    )
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
    application.include_router(perception.router)
    application.include_router(product_contract.router)
    return application


def build_object_detection_client(
    settings: Settings,
) -> GeminiObjectDetectionClient | None:
    """Build the configured object detection provider once per app instance."""
    if settings.gemini_api_key is None or settings.gemini_api_key.strip() == "":
        return None

    client = build_google_genai_client(
        api_key=settings.gemini_api_key,
        timeout_milliseconds=settings.gemini_robotics_er_timeout_milliseconds,
    )
    return build_google_genai_object_detection_client(
        client=client,
        model=settings.gemini_object_detection_model,
    )


def build_semantic_status_client(
    settings: Settings,
) -> GeminiSemanticStatusClient | None:
    """Build the configured semantic status provider once per app instance."""
    if settings.gemini_api_key is None or settings.gemini_api_key.strip() == "":
        return None

    client = build_google_genai_client(
        api_key=settings.gemini_api_key,
        timeout_milliseconds=settings.gemini_robotics_er_timeout_milliseconds,
    )
    return build_google_genai_semantic_status_client(
        client=client,
        model=settings.gemini_semantic_status_model,
        thinking_budget=settings.gemini_robotics_er_thinking_budget,
    )


app = create_app()
