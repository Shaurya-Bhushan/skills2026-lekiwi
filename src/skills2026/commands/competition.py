from __future__ import annotations

from skills2026.commands.shared import maybe_start_local_host
from skills2026.profile import load_profile
from skills2026.robot.safety import checklist_ready


def run(args) -> int:
    profile = load_profile(args.profile)
    if args.mode_name != "ecu":
        raise ValueError("Only `competition ecu` is currently supported.")

    ready, missing = checklist_ready(profile.checklist)
    if not ready:
        print(f"Competition checklist incomplete: {', '.join(missing)}")
        return 1

    backend = args.backend or profile.policy.default_backend
    host_process = maybe_start_local_host(profile)
    try:
        if backend == "smolvla":
            from skills2026.policy.smolvla import SmolVLARunner

            runner = SmolVLARunner.from_profile(
                profile=profile,
                primitive_name=args.primitive,
                task=args.task or None,
                model_id=args.policy_path or None,
                device_name=args.policy_device or None,
                allow_base_model=args.allow_base_model,
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
