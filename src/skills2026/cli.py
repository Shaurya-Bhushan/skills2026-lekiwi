from __future__ import annotations

import argparse
from importlib import import_module
import sys
from datetime import datetime

from skills2026.logging_utils import configure_logging
from skills2026.paths import LOGS_DIR, ensure_workspace_dirs


def _load_handler(path: str):
    module_name, function_name = path.split(":", maxsplit=1)
    try:
        module = import_module(module_name)
    except ModuleNotFoundError as exc:
        missing = exc.name or "unknown dependency"
        raise RuntimeError(
            "Could not load the selected command because a runtime dependency is missing "
            f"({missing}). Activate the LeRobot environment and install this package there."
        ) from exc
    return getattr(module, function_name)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skills2026", description="LeKiwi ECU service toolkit.")
    parser.add_argument("--profile", default="default", help="Profile name in profiles/<name>.json")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="command", required=True)

    setup_parser = subparsers.add_parser("setup", help="Discover hardware and write a profile.")
    setup_parser.add_argument("--skip-live", action="store_true", help="Skip live pose/calibration capture.")
    setup_parser.set_defaults(handler="skills2026.commands.setup:run")

    doctor_parser = subparsers.add_parser("doctor", help="Run hardware and profile checks.")
    doctor_parser.set_defaults(handler="skills2026.commands.doctor:run")

    ui_parser = subparsers.add_parser("ui", help="Open the beginner setup UI in a browser.")
    ui_parser.add_argument("--host", default="127.0.0.1")
    ui_parser.add_argument("--port", type=int, default=7860)
    ui_parser.add_argument("--share", action="store_true", help="Create a temporary public share link.")
    ui_parser.add_argument("--no-browser", action="store_true", help="Do not automatically open a browser.")
    ui_parser.set_defaults(handler="skills2026.commands.ui:run")

    teleop_parser = subparsers.add_parser("teleop", help="Leader-arm teleoperation.")
    teleop_parser.set_defaults(handler="skills2026.commands.teleop:run")

    record_parser = subparsers.add_parser("record", help="Record a primitive dataset.")
    record_parser.add_argument("primitive", choices=["pick_fuse", "insert_fuse", "pick_board", "insert_board"])
    record_parser.add_argument("--episodes", type=int, default=5)
    record_parser.add_argument("--fps", type=int, default=10)
    record_parser.add_argument("--episode-time-s", type=int, default=30)
    record_parser.add_argument("--dataset-name", default="")
    record_parser.set_defaults(handler="skills2026.commands.record:run")

    replay_parser = subparsers.add_parser("replay", help="Replay a recorded episode.")
    replay_parser.add_argument("dataset_name")
    replay_parser.add_argument("episode", type=int)
    replay_parser.set_defaults(handler="skills2026.commands.replay:run")

    competition_parser = subparsers.add_parser("competition", help="Run competition-mode services.")
    competition_parser.add_argument("mode_name", choices=["ecu"])
    competition_parser.add_argument("--backend", choices=["opencv_fsm", "smolvla"], default=None)
    competition_parser.add_argument(
        "--primitive",
        default="insert_fuse",
        choices=[
            "pick_fuse",
            "insert_fuse",
            "pick_board",
            "insert_board",
            "unlock_transformer_bolts",
            "replace_transformer",
        ],
    )
    competition_parser.add_argument("--target-color", choices=["orange", "green", "blue"], default="green")
    competition_parser.add_argument("--target-slot", default="center")
    competition_parser.add_argument("--task", default="", help="Task prompt for policy-based backends.")
    competition_parser.add_argument("--policy-path", default="", help="Optional fine-tuned policy checkpoint path.")
    competition_parser.add_argument("--policy-device", default="", help="Optional policy device override.")
    competition_parser.add_argument(
        "--allow-base-model",
        action="store_true",
        help="Allow lerobot/smolvla_base for bring-up experiments even though it is not LeKiwi-specific.",
    )
    competition_parser.add_argument("--max-cycles", type=int, default=500)
    competition_parser.set_defaults(handler="skills2026.commands.competition:run")

    return parser


def main(argv: list[str] | None = None) -> int:
    ensure_workspace_dirs()
    parser = build_parser()
    args = parser.parse_args(argv)

    log_path = LOGS_DIR / f"{args.command}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    configure_logging(log_path=log_path, verbose=args.verbose)
    try:
        handler = _load_handler(args.handler)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    try:
        return int(handler(args))
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
