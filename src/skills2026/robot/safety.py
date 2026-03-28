from __future__ import annotations

from dataclasses import dataclass

from skills2026.constants import ARM_JOINT_KEYS, BASE_VEL_KEYS
from skills2026.profile import CompetitionChecklist


@dataclass
class SafetyController:
    max_linear_speed: float = 0.15
    max_theta_speed: float = 45.0
    max_joint_step: float = 3.0

    def apply(self, action: dict[str, float], current_pose: dict[str, float]) -> dict[str, float]:
        safe = dict(action)
        safe["x.vel"] = max(-self.max_linear_speed, min(self.max_linear_speed, float(safe["x.vel"])))
        safe["y.vel"] = max(-self.max_linear_speed, min(self.max_linear_speed, float(safe["y.vel"])))
        safe["theta.vel"] = max(-self.max_theta_speed, min(self.max_theta_speed, float(safe["theta.vel"])))

        for joint in ARM_JOINT_KEYS:
            current = float(current_pose.get(joint, 0.0))
            target = float(safe.get(joint, current))
            delta = target - current
            if delta > self.max_joint_step:
                target = current + self.max_joint_step
            elif delta < -self.max_joint_step:
                target = current - self.max_joint_step
            safe[joint] = target

        for key in BASE_VEL_KEYS:
            safe.setdefault(key, 0.0)
        return safe


def checklist_ready(checklist: CompetitionChecklist) -> tuple[bool, list[str]]:
    missing = []
    if not checklist.kill_switch_ready:
        missing.append("kill_switch_ready")
    if not checklist.wiring_diagram_ready:
        missing.append("wiring_diagram_ready")
    if not checklist.tabletop_stand_ready:
        missing.append("tabletop_stand_ready")
    if not checklist.local_only_mode_confirmed:
        missing.append("local_only_mode_confirmed")
    return (len(missing) == 0, missing)

