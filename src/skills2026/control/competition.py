from __future__ import annotations

import logging
import time
from dataclasses import dataclass, replace

from skills2026.control.primitives import PRIMITIVES, PrimitiveController
from skills2026.perception.front import FrontPerception
from skills2026.perception.models import DetectionBundle, VisionTarget
from skills2026.perception.wrist import WristPerception
from skills2026.robot.lekiwi_io import LeKiwiIO
from skills2026.robot.safety import SafetyController
from skills2026.runtime.camera_scheduler import CameraScheduler

logger = logging.getLogger(__name__)


@dataclass
class CompetitionRunner:
    io: LeKiwiIO
    controller: PrimitiveController
    front: FrontPerception
    wrist: WristPerception
    scheduler: CameraScheduler
    safety: SafetyController
    last_coarse: VisionTarget | None = None
    last_fine: VisionTarget | None = None
    last_coarse_age: int = 0
    last_fine_age: int = 0
    detection_memory_cycles: int = 3

    @classmethod
    def from_profile(cls, profile, primitive_name: str, target_color: str | None, target_slot: str | None):
        if primitive_name not in PRIMITIVES:
            raise ValueError(f"Unknown primitive '{primitive_name}'. Available: {sorted(PRIMITIVES)}")
        spec = PRIMITIVES[primitive_name]
        if not spec.enabled:
            raise ValueError(
                f"Primitive '{primitive_name}' is intentionally disabled until the simpler ECU tasks are stable."
            )
        controller = PrimitiveController(
            spec=spec,
            profile=profile,
            target_color=target_color,
            target_slot=target_slot,
        )
        return cls(
            io=LeKiwiIO(profile),
            controller=controller,
            front=FrontPerception(),
            wrist=WristPerception(),
            scheduler=CameraScheduler(profile.budget),
            safety=SafetyController(),
        )

    def _reuse_recent_target(
        self,
        fresh_target: VisionTarget | None,
        cached_target: VisionTarget | None,
        cached_age: int,
    ) -> tuple[VisionTarget | None, VisionTarget | None, int]:
        if fresh_target and fresh_target.found:
            return fresh_target, fresh_target, 0
        if cached_target is None:
            return None, None, 0

        next_age = cached_age + 1
        if next_age > self.detection_memory_cycles:
            return None, None, 0

        stale_target = replace(
            cached_target,
            metadata={
                **cached_target.metadata,
                "stale": True,
                "stale_frames": next_age,
            },
        )
        return stale_target, cached_target, next_age

    def run(self, max_cycles: int = 500) -> int:
        self.io.connect()
        last_observation = None
        try:
            for cycle_idx in range(max_cycles):
                loop_start = time.perf_counter()
                observation = self.io.get_observation()
                last_observation = observation
                current_pose = self.io.arm_pose_from_observation(observation)
                front_frame = observation.get("front")
                wrist_frame = observation.get("wrist")

                fresh_coarse = None
                front_stride = 1 if self.scheduler.front_fps_scale >= 1.0 else 2
                should_refresh_front = (
                    front_frame is not None
                    and (
                        cycle_idx % front_stride == 0
                        or self.controller.fsm.state.value in {"detect_global", "approach_coarse"}
                    )
                )
                if should_refresh_front:
                    fresh_coarse = self.front.analyze(
                        front_frame,
                        self.controller.spec.name,
                        calibration=self.io.profile.cameras["front"].calibration.__dict__,
                        target_color=self.controller.target_color,
                        target_slot=self.controller.target_slot,
                    )
                coarse, self.last_coarse, self.last_coarse_age = self._reuse_recent_target(
                    fresh_coarse,
                    self.last_coarse,
                    self.last_coarse_age,
                )

                self.scheduler.request_precision(
                    self.controller.spec.camera_role == "wrist"
                    and wrist_frame is not None
                    and self.controller.fsm.state.value
                    in {
                        "switch_to_wrist_precision",
                        "align_fine",
                        "verify",
                    }
                )

                fine = None
                if wrist_frame is not None and self.scheduler.should_use_wrist():
                    fresh_fine = self.wrist.analyze(
                        wrist_frame,
                        self.controller.spec.name,
                        target_color=self.controller.target_color,
                    )
                    fine, self.last_fine, self.last_fine_age = self._reuse_recent_target(
                        fresh_fine,
                        self.last_fine,
                        self.last_fine_age,
                    )
                elif self.scheduler.should_use_wrist():
                    fine, self.last_fine, self.last_fine_age = self._reuse_recent_target(
                        None,
                        self.last_fine,
                        self.last_fine_age,
                    )

                detections = DetectionBundle(
                    coarse_target=coarse,
                    fine_target=fine,
                    verified=bool(fine and fine.metadata.get("verified") and not fine.metadata.get("stale")),
                    message="",
                )

                decision = self.controller.step(current_pose, detections, self.scheduler.should_use_wrist())
                safe_action = self.safety.apply(self.io.merge_action(decision.action), current_pose)
                self.io.send_action(safe_action)

                if cycle_idx % 10 == 0 or decision.done or decision.failed:
                    logger.info(
                        "cycle=%s state=%s wrist=%s message=%s",
                        cycle_idx,
                        self.controller.fsm.state.value,
                        self.scheduler.should_use_wrist(),
                        decision.message,
                    )

                dt_s = time.perf_counter() - loop_start
                self.scheduler.observe_loop_duration(dt_s)

                if decision.done:
                    self.io.stop_base(observation)
                    return 0
                if decision.failed:
                    self.io.stop_base(observation)
                    return 1

                sleep_s = max((1.0 / self.io.profile.budget.loop_hz) - dt_s, 0.0)
                time.sleep(sleep_s)

            logger.warning("Competition loop timed out.")
            self.io.stop_base(last_observation)
            return 1
        finally:
            self.io.disconnect()
