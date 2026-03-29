from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, TextIO

from skills2026.control.primitives import PRIMITIVES
from skills2026.paths import LOGS_DIR, ensure_workspace_dirs


@dataclass(frozen=True)
class PickupValidationScenario:
    name: str
    label: str
    primitive_name: str
    focus: str
    setup_note: str
    target_color: str | None = None
    target_slot: str | None = None


@dataclass(frozen=True)
class PickupTrialResult:
    scenario_name: str
    primitive_name: str
    trial_index: int
    exit_code: int
    duration_s: float
    success: bool
    error: str = ""


@dataclass
class PickupScenarioSummary:
    scenario: PickupValidationScenario
    trials: list[PickupTrialResult] = field(default_factory=list)

    @property
    def successes(self) -> int:
        return sum(1 for trial in self.trials if trial.success)

    @property
    def attempts(self) -> int:
        return len(self.trials)

    @property
    def success_rate(self) -> float:
        return (self.successes / self.attempts) if self.attempts else 0.0

    def to_dict(self) -> dict:
        return {
            "scenario": asdict(self.scenario),
            "successes": self.successes,
            "attempts": self.attempts,
            "success_rate": self.success_rate,
            "trials": [asdict(trial) for trial in self.trials],
        }


@dataclass
class PickupValidationReport:
    profile_name: str
    suite_name: str
    trials_per_scenario: int
    created_at: str
    scenario_summaries: list[PickupScenarioSummary]

    @property
    def total_attempts(self) -> int:
        return sum(summary.attempts for summary in self.scenario_summaries)

    @property
    def total_successes(self) -> int:
        return sum(summary.successes for summary in self.scenario_summaries)

    @property
    def overall_success_rate(self) -> float:
        return (self.total_successes / self.total_attempts) if self.total_attempts else 0.0

    @property
    def all_passed(self) -> bool:
        return all(summary.successes == summary.attempts for summary in self.scenario_summaries)

    def to_dict(self) -> dict:
        return {
            "profile_name": self.profile_name,
            "suite_name": self.suite_name,
            "trials_per_scenario": self.trials_per_scenario,
            "created_at": self.created_at,
            "total_attempts": self.total_attempts,
            "total_successes": self.total_successes,
            "overall_success_rate": self.overall_success_rate,
            "all_passed": self.all_passed,
            "scenarios": [summary.to_dict() for summary in self.scenario_summaries],
        }


PICKUP_VALIDATION_SUITES: dict[str, tuple[PickupValidationScenario, ...]] = {
    "core": (
        PickupValidationScenario(
            name="single_target_debris",
            label="Single Target Debris Pickup",
            primitive_name="pick_debris",
            focus="baseline pickup with one easy object",
            setup_note=(
                "Place one wood piece in the normal debris pickup area with no nearby distractors. "
                "Reset it to roughly the same place before each trial."
            ),
        ),
        PickupValidationScenario(
            name="cluttered_debris",
            label="Cluttered Debris Pickup",
            primitive_name="pick_debris",
            focus="multi-object selection with a similar nearby distractor",
            setup_note=(
                "Place the target wood piece with a second similar wood piece nearby so both are visible. "
                "Keep the intended target closest to the saved pickup lane."
            ),
        ),
        PickupValidationScenario(
            name="wrist_motion_debris",
            label="Wrist Motion Stress Test",
            primitive_name="pick_debris",
            focus="camera motion during final approach",
            setup_note=(
                "Run the normal debris pickup while watching for wrist-camera motion during the last approach. "
                "Use the same object, but allow a slightly off-center starting pose."
            ),
        ),
        PickupValidationScenario(
            name="partial_occlusion_debris",
            label="Partial Occlusion Stress Test",
            primitive_name="pick_debris",
            focus="gripper partially hiding the object during grasp",
            setup_note=(
                "Place the wood piece so the gripper will partially cover it near the final grasp. "
                "This checks recovery when the wrist view briefly loses the target."
            ),
        ),
        PickupValidationScenario(
            name="lighting_shift_debris",
            label="Lighting Shift Stress Test",
            primitive_name="pick_debris",
            focus="pickup under slightly dimmer or harsher lighting",
            setup_note=(
                "Repeat the debris pickup with the lighting slightly dimmer, brighter, or with more shadow than usual. "
                "Do not move the camera mounts between trials."
            ),
        ),
    ),
    "ecu": (
        PickupValidationScenario(
            name="fuse_supply_pickup",
            label="Fuse Supply Pickup",
            primitive_name="pick_fuse",
            target_color="green",
            target_slot="fuse_supply",
            focus="colored cylindrical pickup from the fuse supply area",
            setup_note="Place the green fuse in the normal fuse supply area and reset it between trials.",
        ),
        PickupValidationScenario(
            name="board_supply_pickup",
            label="Board Supply Pickup",
            primitive_name="pick_board",
            target_slot="board_supply",
            focus="flat board pickup from the board supply area",
            setup_note="Place the board in the normal board supply area with the front camera seeing the whole tray.",
        ),
        PickupValidationScenario(
            name="transformer_supply_pickup",
            label="Transformer Supply Pickup",
            primitive_name="pick_transformer",
            target_slot="transformer_supply",
            focus="larger structured pickup from the transformer supply area",
            setup_note="Place the transformer part in the supply area and make sure the arm has clear retract space.",
        ),
        PickupValidationScenario(
            name="steve_pickup",
            label="Steve Pickup",
            primitive_name="pick_steve",
            target_slot="steve_source",
            focus="small human figure pickup from the Steve source area",
            setup_note="Place Steve in the normal source area and keep the lobby route clear for follow-up checks later.",
        ),
    ),
}
PICKUP_VALIDATION_SUITES["all"] = (
    PICKUP_VALIDATION_SUITES["core"] + PICKUP_VALIDATION_SUITES["ecu"]
)


def get_pickup_validation_scenarios(suite_name: str) -> tuple[PickupValidationScenario, ...]:
    if suite_name not in PICKUP_VALIDATION_SUITES:
        raise ValueError(
            f"Unknown pickup validation suite '{suite_name}'. "
            f"Available: {sorted(PICKUP_VALIDATION_SUITES)}"
        )
    return PICKUP_VALIDATION_SUITES[suite_name]


def missing_pickup_validation_poses(profile, scenarios: tuple[PickupValidationScenario, ...]) -> list[str]:
    required: set[str] = set()
    for scenario in scenarios:
        spec = PRIMITIVES[scenario.primitive_name]
        required.update((spec.coarse_pose, spec.action_pose, spec.retract_pose))
    return sorted(name for name in required if not profile.service_poses.get(name))


def default_pickup_report_path(profile_name: str, suite_name: str) -> Path:
    ensure_workspace_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return LOGS_DIR / f"pickup_validation_{profile_name}_{suite_name}_{timestamp}.json"


@dataclass
class PickupValidationRunner:
    profile: object
    suite_name: str
    scenarios: tuple[PickupValidationScenario, ...]
    trials_per_scenario: int
    build_runner: Callable[[PickupValidationScenario], object]
    output: TextIO = sys.stdout
    input_stream: TextIO = sys.stdin

    def _pause_prompt(self, scenario: PickupValidationScenario, trial_index: int) -> str:
        return (
            f"\n[{scenario.label}] Trial {trial_index}/{self.trials_per_scenario}\n"
            f"Focus: {scenario.focus}\n"
            f"Setup: {scenario.setup_note}\n"
            "Press Enter when the robot and object are ready."
        )

    def run(
        self,
        *,
        max_cycles: int = 500,
        pause_between_trials: bool = True,
        fail_fast: bool = False,
    ) -> PickupValidationReport:
        scenario_summaries: list[PickupScenarioSummary] = []

        for scenario in self.scenarios:
            print(f"\n== {scenario.label} ==", file=self.output)
            print(f"Primitive: {scenario.primitive_name}", file=self.output)
            print(f"Focus: {scenario.focus}", file=self.output)
            print(f"Setup: {scenario.setup_note}", file=self.output)

            summary = PickupScenarioSummary(scenario=scenario)
            for trial_index in range(1, self.trials_per_scenario + 1):
                if pause_between_trials and self.input_stream.isatty():
                    input(self._pause_prompt(scenario, trial_index))
                else:
                    print(
                        f"Trial {trial_index}/{self.trials_per_scenario}: reset the scene before continuing.",
                        file=self.output,
                    )

                start_s = time.perf_counter()
                exit_code = 1
                error = ""
                try:
                    runner = self.build_runner(scenario)
                    exit_code = int(runner.run(max_cycles=max_cycles))
                except Exception as exc:
                    error = str(exc)
                duration_s = time.perf_counter() - start_s
                result = PickupTrialResult(
                    scenario_name=scenario.name,
                    primitive_name=scenario.primitive_name,
                    trial_index=trial_index,
                    exit_code=exit_code,
                    duration_s=duration_s,
                    success=exit_code == 0,
                    error=error,
                )
                summary.trials.append(result)
                status = "PASS" if result.success else "FAIL"
                detail = f"{status} in {duration_s:.1f}s"
                if error:
                    detail = f"{detail} ({error})"
                print(f"  Trial {trial_index}: {detail}", file=self.output)

                if fail_fast and not result.success:
                    print("  Stopping early because --fail-fast is enabled.", file=self.output)
                    break

            print(
                f"  Scenario success: {summary.successes}/{summary.attempts} "
                f"({summary.success_rate:.0%})",
                file=self.output,
            )
            scenario_summaries.append(summary)

            if fail_fast and summary.successes != summary.attempts:
                break

        report = PickupValidationReport(
            profile_name=self.profile.profile_name,
            suite_name=self.suite_name,
            trials_per_scenario=self.trials_per_scenario,
            created_at=datetime.now().isoformat(timespec="seconds"),
            scenario_summaries=scenario_summaries,
        )
        return report


def save_pickup_validation_report(report: PickupValidationReport, target: Path) -> Path:
    ensure_workspace_dirs()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return target
