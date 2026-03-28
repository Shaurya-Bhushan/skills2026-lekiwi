from __future__ import annotations

from skills2026.commands.shared import maybe_start_local_host
from skills2026.control.mission import MissionRunner
from skills2026.profile import load_profile
from skills2026.robot.safety import checklist_ready


def run(args) -> int:
    profile = load_profile(args.profile)
    if args.mode_name not in {"ecu", "mission"}:
        raise ValueError("Only `competition ecu` and `competition mission` are currently supported.")

    ready, missing = checklist_ready(profile.checklist)
    if not ready:
        print(f"Competition checklist incomplete: {', '.join(missing)}")
        return 1

    host_process = maybe_start_local_host(profile)
    try:
        if args.mode_name == "mission":
            if args.backend == "act":
                raise ValueError(
                    "ACT backend currently supports `competition ecu` primitives only. "
                    "Use the scripted mission runner for full-task sequencing."
                )
            runner = MissionRunner.from_profile(
                profile=profile,
                mission_name=args.mission_name,
                target_color=args.target_color,
                target_slot=args.target_slot,
            )
            return runner.run(max_cycles_per_primitive=args.max_cycles)

        if args.backend == "act":
            from skills2026.policy.act import ACTRunner

            runner = ACTRunner.from_profile(
                profile=profile,
                primitive_name=args.primitive,
                policy_path=args.policy_path,
                dataset_name=args.dataset_name or None,
                task=args.task or None,
                device_name=args.policy_device or None,
            )
        else:
            from skills2026.control.competition import CompetitionRunner

            runner = CompetitionRunner.from_profile(
                profile=profile,
                primitive_name=args.primitive,
                target_color=args.target_color,
                target_slot=args.target_slot,
            )
        return runner.run(max_cycles=args.max_cycles)
    finally:
        if host_process is not None:
            host_process.terminate()
