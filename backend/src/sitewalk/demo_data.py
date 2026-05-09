from sitewalk.contracts import (
    CriticalZone,
    CriticalZonePolicy,
    Severity,
    ZonePoint,
    ZoneType,
)

PRIMARY_DEMO_ZONE = CriticalZone(
    id="zone-workcell-a2",
    name="Robot Workcell A-2",
    zone_type=ZoneType.ROBOT_WORKCELL,
    geometry=[
        ZonePoint(x=0.14, y=0.18),
        ZonePoint(x=0.58, y=0.18),
        ZonePoint(x=0.58, y=0.82),
        ZonePoint(x=0.14, y=0.82),
    ],
    policy=CriticalZonePolicy(
        dwell_threshold_seconds=30,
        severity=Severity.HIGH,
        escalation_channel="floor_supervisor",
    ),
)
