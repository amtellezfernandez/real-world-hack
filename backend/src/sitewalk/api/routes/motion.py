from __future__ import annotations

import math

from fastapi import APIRouter

from sitewalk.api.dependencies import AppContainerDep
from sitewalk.api.state import AppContainer
from sitewalk.contracts import MotionEstimate, MotionSample

router = APIRouter(prefix="/api/motion", tags=["motion"])

_SAMPLE_WINDOW = 4
_TRANSLATION_SCALE = 1.35
_SPEED_SCALE = 0.55


@router.post("/estimate")
async def estimate_motion(
    sample: MotionSample,
    container: AppContainerDep,
) -> MotionEstimate:
    with container.motion_lock:
        previous_frame = container.motion_previous_frame

        if previous_frame is None:
            _set_motion_previous_frame(container, sample.pixels)
            return _current_estimate(container, confidence=0)

        motion = _estimate_frame_motion(
            previous=previous_frame,
            current=sample.pixels,
            width=sample.width,
            height=sample.height,
        )

        if motion.magnitude > 0:
            delta_x = -motion.shift_x * _TRANSLATION_SCALE
            delta_y = -motion.shift_y * _TRANSLATION_SCALE
            _set_motion_pose_x(container, _clamp(container.motion_pose_x + delta_x, 4, 96))
            _set_motion_pose_y(container, _clamp(container.motion_pose_y + delta_y, 4, 96))
            if abs(delta_x) + abs(delta_y) > 0.4:
                _set_motion_heading(
                    container,
                    _wrap_heading((math.atan2(delta_y, delta_x) * 180) / math.pi),
                )

        _set_motion_previous_frame(container, sample.pixels)
        return _current_estimate(container, confidence=motion.confidence, speed=motion.magnitude)


@router.post("/reset")
async def reset_motion(container: AppContainerDep) -> MotionEstimate:
    with container.motion_lock:
        _set_motion_previous_frame(container, None)
        _set_motion_pose_x(container, 24)
        _set_motion_pose_y(container, 76)
        _set_motion_heading(container, 90)
        return _current_estimate(container, confidence=0)


def _current_estimate(
    container: AppContainer,
    *,
    confidence: float,
    speed: float = 0,
) -> MotionEstimate:
    return MotionEstimate(
        x=container.motion_pose_x,
        y=container.motion_pose_y,
        heading=container.motion_heading,
        speed=round(speed * _SPEED_SCALE, 6),
        confidence=confidence,
    )


def _estimate_frame_motion(
    *,
    previous: list[int],
    current: list[int],
    width: int,
    height: int,
) -> _FrameMotion:
    best_shift_x = 0
    best_shift_y = 0
    best_score = float("inf")

    for shift_y in range(-_SAMPLE_WINDOW, _SAMPLE_WINDOW + 1):
        for shift_x in range(-_SAMPLE_WINDOW, _SAMPLE_WINDOW + 1):
            score = 0
            matched = 0

            for y in range(_SAMPLE_WINDOW, height - _SAMPLE_WINDOW):
                previous_y = y + shift_y
                if previous_y < 0 or previous_y >= height:
                    continue

                for x in range(_SAMPLE_WINDOW, width - _SAMPLE_WINDOW):
                    previous_x = x + shift_x
                    if previous_x < 0 or previous_x >= width:
                        continue

                    current_index = y * width + x
                    previous_index = previous_y * width + previous_x
                    score += abs(current[current_index] - previous[previous_index])
                    matched += 1

            normalized = score / matched if matched else float("inf")
            if normalized < best_score:
                best_score = normalized
                best_shift_x = shift_x
                best_shift_y = shift_y

    magnitude = (best_shift_x**2 + best_shift_y**2) ** 0.5
    confidence = max(0.0, min(1.0, (10 - best_score) / 10))
    return _FrameMotion(
        shift_x=best_shift_x,
        shift_y=best_shift_y,
        magnitude=magnitude,
        confidence=confidence,
    )


def _clamp(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)


def _wrap_heading(value: float) -> float:
    normalized = value % 360
    return normalized + 360 if normalized < 0 else normalized


def _set_motion_previous_frame(container: AppContainer, value: list[int] | None) -> None:
    object.__setattr__(container, "motion_previous_frame", value)


def _set_motion_pose_x(container: AppContainer, value: float) -> None:
    object.__setattr__(container, "motion_pose_x", value)


def _set_motion_pose_y(container: AppContainer, value: float) -> None:
    object.__setattr__(container, "motion_pose_y", value)


def _set_motion_heading(container: AppContainer, value: float) -> None:
    object.__setattr__(container, "motion_heading", _wrap_heading(value))


class _FrameMotion:
    def __init__(self, *, shift_x: int, shift_y: int, magnitude: float, confidence: float) -> None:
        self.shift_x = shift_x
        self.shift_y = shift_y
        self.magnitude = magnitude
        self.confidence = confidence
