from datetime import UTC, datetime

import pytest

from sitewalk.contracts import AlertEvent, AlertProvider


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def approved_alert_event() -> AlertEvent:
    return AlertEvent(
        incident_id="incident-exit-b3-20260508T120030Z",
        approval_actor="demo-supervisor",
        alert_text="Robotics notice: clear the obstruction at Robot Workcell A-2.",
        provider=AlertProvider.LOCAL_AUDIO,
        timestamp=datetime(2026, 5, 8, 12, 0, 35, tzinfo=UTC).isoformat(),
        audio_ref="assets/audio/local-alert.wav",
    )
