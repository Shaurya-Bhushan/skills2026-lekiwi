from __future__ import annotations

import argparse
from importlib import import_module
import sys
from datetime import datetime

from skills2026.logging_utils import configure_logging
from skills2026.paths import LOGS_DIR, ensure_workspace_dirs
from skills2026.control.tasks import MISSION_PRESETS


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
    record_parser.add_argument(
        "primitive",
        choices=[
            "remove_fuse",
            "pick_fuse",
            "insert_fuse",
            "remove_board",
            "pick_board",
            "insert_board",
            "unlock_transformer_bolts",
            "lock_transformer_bolts",
            "pick_transformer",
            "remove_transformer",
            "replace_transformer",
            "pick_steve",
            "deliver_steve_to_lobby",
        ],
    )
    record_parser.add_argument("--episodes", type=int, default=5)
    record_parser.add_argument("--fps", type=int, default=10)
    record_parser.add_argument("--episode-time-s", type=int, default=30)
    record_parser.add_argument("--dataset-name", default="")
    record_parser.add_argument(
        "--append",
        action="store_true",
        help="Append to an existing dataset intentionally. Without this flag, recording refuses to reuse an existing dataset root.",
    )
    record_parser.set_defaults(handler="skills2026.commands.record:run")

    replay_parser = subparsers.add_parser("replay", help="Replay a recorded episode.")
    replay_parser.add_argument("dataset_name")
    replay_parser.add_argument("episode", type=int)
    replay_parser.add_argument(
        "--primitive",
        default="",
        help="Optional primitive label for the replay validation report. Defaults to the dataset manifest primitive.",
    )
    replay_parser.add_argument(
        "--validate",
        action="store_true",
        help="After replay, mark the episode as pass/fail for ACT gating and save a validation report.",
    )
    replay_parser.add_argument(
        "--validation-result",
        choices=["pass", "fail"],
        default="",
        help="Non-interactive replay validation result. Use with `--validate` in scripts.",
    )
    replay_parser.add_argument("--notes", default="", help="Optional notes saved with the replay validation result.")
    replay_parser.add_argument(
        "--report-path",
        default="",
        help="Optional replay validation JSON path. Defaults to data/logs/replay_validation_<dataset>_<episode>.json",
    )
    replay_parser.set_defaults(handler="skills2026.commands.replay:run")

    train_act_parser = subparsers.add_parser(
        "train_act",
        help="Replay-gated ACT training. Refuses datasets that have not been reviewed and pickup-validated.",
    )
    train_act_parser.add_argument(
        "primitive",
        choices=[
            "remove_fuse",
            "pick_fuse",
            "insert_fuse",
            "remove_board",
            "pick_board",
            "insert_board",
            "unlock_transformer_bolts",
            "lock_transformer_bolts",
            "pick_transformer",
            "remove_transformer",
            "replace_transformer",
            "pick_steve",
            "deliver_steve_to_lobby",
        ],
    )
    train_act_parser.add_argument("--dataset-name", default="")
    train_act_parser.add_argument("--policy-device", default="cpu")
    train_act_parser.add_argument("--steps", type=int, default=20000)
    train_act_parser.add_argument("--batch-size", type=int, default=8)
    train_act_parser.add_argument("--output-dir", default="")
    train_act_parser.add_argument("--job-name", default="")
    train_act_parser.add_argument("--wandb", action="store_true", help="Enable Weights & Biases during training.")
    train_act_parser.add_argument("--push-to-hub", action="store_true")
    train_act_parser.add_argument("--policy-repo-id", default="")
    train_act_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved lerobot-train command without starting training.",
    )
    train_act_parser.set_defaults(handler="skills2026.commands.train_act:run")

    pickup_validation_parser = subparsers.add_parser(
        "pickup_validation",
        help="Run repeated pickup stress tests and save a validation report.",
    )
    pickup_validation_parser.add_argument(
        "--suite",
        choices=["core", "ecu", "all"],
        default="core",
        help="`core` checks the generic pickup failure modes. `ecu` checks the main Ontario pickup primitives.",
    )
    pickup_validation_parser.add_argument(
        "--trials",
        type=int,
        default=3,
        help="How many repeated trials to run for each scenario.",
    )
    pickup_validation_parser.add_argument(
        "--max-cycles",
        type=int,
        default=500,
        help="Max control cycles per primitive run.",
    )
    pickup_validation_parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop the validation suite as soon as one trial fails.",
    )
    pickup_validation_parser.add_argument(
        "--no-pause",
        action="store_true",
        help="Do not pause for scene reset between trials, even in an interactive terminal.",
    )
    pickup_validation_parser.add_argument(
        "--report-path",
        default="",
        help="Optional JSON report path. Defaults to data/logs/pickup_validation_<timestamp>.json",
    )
    pickup_validation_parser.set_defaults(handler="skills2026.commands.pickup_validation:run")

    competition_parser = subparsers.add_parser("competition", help="Run competition-mode services.")
    competition_parser.add_argument("mode_name", choices=["ecu", "mission"])
    competition_parser.add_argument(
        "--backend",
        choices=["opencv_fsm", "act"],
        default=None,
        help="Keep OpenCV + FSM as the default. Use `act` only with a trained checkpoint.",
    )
    competition_parser.add_argument(
        "--primitive",
        default="insert_fuse",
        choices=[
            "remove_fuse",
            "pick_fuse",
            "insert_fuse",
            "remove_board",
            "pick_board",
            "insert_board",
            "unlock_transformer_bolts",
            "lock_transformer_bolts",
            "pick_transformer",
            "remove_transformer",
            "replace_transformer",
            "pick_steve",
            "deliver_steve_to_lobby",
            "flip_breaker_on",
        ],
    )
    competition_parser.add_argument(
        "--mission-name",
        choices=sorted(MISSION_PRESETS),
        default="ecu_steve_priority",
        help="Mission preset to run when mode_name is `mission`.",
    )
    competition_parser.add_argument("--target-color", choices=["orange", "green", "blue"], default="green")
    competition_parser.add_argument("--target-slot", default="center")
    competition_parser.add_argument("--task", default="", help="Optional task string passed into ACT inference.")
    competition_parser.add_argument(
        "--policy-path",
        default="",
        help="Required for `--backend act`: local or Hub ACT checkpoint path. A matching local dataset folder is still required for preprocessing stats.",
    )
    competition_parser.add_argument(
        "--dataset-name",
        default="",
        help="Local dataset folder used for ACT feature names and normalization stats. Defaults to `<profile>_<primitive>`.",
    )
    competition_parser.add_argument(
        "--policy-device",
        default="",
        help="Optional ACT device override such as `cpu`, `mps`, or `cuda`.",
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
