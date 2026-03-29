from __future__ import annotations

import sys
from pathlib import Path

from skills2026.commands.shared import maybe_start_local_host
from skills2026.control.competition import CompetitionRunner
from skills2026.control.pickup_validation import (
    PickupValidationRunner,
    default_pickup_report_path,
    get_pickup_validation_scenarios,
    missing_pickup_validation_poses,
    pickup_validation_pose_warnings,
    save_pickup_validation_report,
)
from skills2026.profile import load_profile


def run(args) -> int:
    profile = load_profile(args.profile)
    scenarios = get_pickup_validation_scenarios(args.suite)
    missing_poses = missing_pickup_validation_poses(profile, scenarios)
    if missing_poses:
        raise ValueError(
            "Pickup validation cannot start because these service poses are still empty: "
            + ", ".join(missing_poses)
        )
    pose_warnings = pickup_validation_pose_warnings(profile, scenarios)
    if pose_warnings:
        raise ValueError(
            "Pickup validation refused to run because some saved pickup poses are internally inconsistent:\n- "
            + "\n- ".join(pose_warnings)
        )

    report_path = Path(args.report_path) if args.report_path else default_pickup_report_path(
        profile.profile_name,
        args.suite,
    )
    pause_between_trials = sys.stdin.isatty() and not args.no_pause

    host_process = maybe_start_local_host(profile)
    try:
        runner = PickupValidationRunner(
            profile=profile,
            suite_name=args.suite,
            scenarios=scenarios,
            trials_per_scenario=args.trials,
            build_runner=lambda scenario: CompetitionRunner.from_profile(
                profile=profile,
                primitive_name=scenario.primitive_name,
                target_color=scenario.target_color,
                target_slot=scenario.target_slot,
            ),
        )
        report = runner.run(
            max_cycles=args.max_cycles,
            pause_between_trials=pause_between_trials,
            fail_fast=args.fail_fast,
        )
    finally:
        if host_process is not None:
            host_process.terminate()

    save_pickup_validation_report(report, report_path)
    print(f"\nPickup validation report saved to {report_path}")
    print(
        f"Overall pickup success: {report.total_successes}/{report.total_attempts} "
        f"({report.overall_success_rate:.0%})"
    )
    if report.all_passed:
        print("Pickup validation passed for every attempted trial.")
        return 0

    print("Pickup validation found at least one failed trial. Tune the setup before relying on match-day automation.")
    return 1
