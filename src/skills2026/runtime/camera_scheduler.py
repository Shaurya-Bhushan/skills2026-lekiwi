from __future__ import annotations

from dataclasses import dataclass

from skills2026.profile import RuntimeBudget


@dataclass
class SchedulerSnapshot:
    wrist_enabled: bool
    front_fps_scale: float
    overload_strikes: int


class CameraScheduler:
    def __init__(self, budget: RuntimeBudget):
        self.budget = budget
        self.wrist_enabled = True
        self.front_fps_scale = 1.0
        self.overload_strikes = 0
        self.healthy_strikes = 0
        self.precision_requested = False

    def request_precision(self, enabled: bool) -> None:
        self.precision_requested = enabled

    def should_use_wrist(self) -> bool:
        return self.wrist_enabled and self.precision_requested

    def observe_loop_duration(self, dt_s: float) -> SchedulerSnapshot:
        target_s = 1.0 / self.budget.loop_hz
        overloaded = dt_s > target_s * self.budget.overload_ratio

        if overloaded:
            self.overload_strikes += 1
            self.healthy_strikes = 0
        else:
            self.overload_strikes = max(self.overload_strikes - 1, 0)
            if self.overload_strikes == 0:
                self.healthy_strikes += 1
            else:
                self.healthy_strikes = 0

        if (
            self.wrist_enabled
            and self.overload_strikes >= self.budget.overload_strikes_before_disabling_wrist
        ):
            self.wrist_enabled = False
            self.healthy_strikes = 0

        if not self.wrist_enabled and self.overload_strikes == 0 and self.healthy_strikes >= 5:
            self.wrist_enabled = True
            self.front_fps_scale = 1.0
            self.healthy_strikes = 0

        if self.overload_strikes >= self.budget.overload_strikes_before_throttling_front:
            self.front_fps_scale = 0.75

        return SchedulerSnapshot(
            wrist_enabled=self.wrist_enabled,
            front_fps_scale=self.front_fps_scale,
            overload_strikes=self.overload_strikes,
        )
