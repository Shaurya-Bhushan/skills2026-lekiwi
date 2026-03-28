from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from skills2026.control.primitives import PRIMITIVES, PrimitiveController
from skills2026.perception.front import FrontPerception
from skills2026.perception.models import DetectionBundle
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

    def run(self, max_cycles: int = 500) -> int:
        self.io.connect()
        try:
            for cycle_idx in range(max_cycles):
                loop_start = time.perf_counter()
                observation = self.io.get_observation()
                current_pose = self.io.arm_pose_from_observation(observation)
                front_frame = observation.get("front")
                wrist_frame = observation.get("wrist")

                coarse = None
                if front_frame is not None:
                    coarse = self.front.analyze(
                        front_frame,
                        self.controller.spec.name,
                        calibration=self.io.profile.cameras["front"].calibration.__dict__,
                        target_color=self.controller.target_color,
                        target_slot=self.controller.target_slot,
                    )

                self.scheduler.request_precision(
                    self.controller.fsm.state.value
                    in {
                        "switch_to_wrist_precision",
                        "align_fine",
                        "grasp_or_insert",
                        "verify",
                    }
                )

                fine = None
                if wrist_frame is not None and self.scheduler.should_use_wrist():
                    fine = self.wrist.analyze(
                        wrist_frame,
                        self.controller.spec.name,
                        target_color=self.controller.target_color,
                    )

                detections = DetectionBundle(
                    coarse_target=coarse,
                    fine_target=fine,
                    verified=bool(fine and fine.metadata.get("verified")),
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
            self.io.stop_base()
            return 1
        finally:
            self.io.disconnect()

