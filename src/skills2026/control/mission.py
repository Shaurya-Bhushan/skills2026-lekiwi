from __future__ import annotations

import sys
from dataclasses import dataclass

from skills2026.control.competition import CompetitionRunner
from skills2026.control.tasks import MISSION_PRESETS, TASKS


@dataclass
class MissionRunner:
    profile: object
    mission_name: str
    target_color: str | None = None
    target_slot: str | None = None

    @classmethod
    def from_profile(
        cls,
        profile,
        mission_name: str,
        target_color: str | None = None,
        target_slot: str | None = None,
    ) -> "MissionRunner":
        if mission_name not in MISSION_PRESETS:
            raise ValueError(f"Unknown mission '{mission_name}'. Available: {sorted(MISSION_PRESETS)}")
        return cls(
            profile=profile,
            mission_name=mission_name,
            target_color=target_color,
            target_slot=target_slot,
        )

    def run(self, max_cycles_per_primitive: int = 500) -> int:
        task_names = MISSION_PRESETS[self.mission_name]
        for task_name in task_names:
            task = TASKS[task_name]
            if not task.enabled:
                continue

            print(f"\n== {task.label} ==")
            print(task.description)
            if task.manual_note and sys.stdin.isatty():
                input(f"{task.manual_note}\nPress Enter when the robot is ready for this task.")

            for primitive_name in task.primitive_sequence:
                runner = CompetitionRunner.from_profile(
                    profile=self.profile,
                    primitive_name=primitive_name,
                    target_color=task.target_color or self.target_color,
                    target_slot=task.target_slot or self.target_slot,
                )
                code = runner.run(max_cycles=max_cycles_per_primitive)
                if code != 0:
                    print(f"Mission stopped during '{task.label}' on primitive '{primitive_name}'.")
                    return code

        print(f"\nMission '{self.mission_name}' completed.")
        return 0
