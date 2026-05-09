from fastapi import APIRouter

from sitewalk.api.demo_replay_service import assess_demo_replay
from sitewalk.contracts import DemoReplay
from sitewalk.perception import BLOCKED_EXIT_OBSERVATION_REPLAY

router = APIRouter(prefix="/api", tags=["demo replay"])

ASSESSED_BLOCKED_EXIT_REPLAY = assess_demo_replay(BLOCKED_EXIT_OBSERVATION_REPLAY)


@router.get("/demo-replay")
async def get_demo_replay() -> DemoReplay:
    """Return the controlled replay for the primary operations view."""
    return ASSESSED_BLOCKED_EXIT_REPLAY
