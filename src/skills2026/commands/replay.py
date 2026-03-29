from __future__ import annotations

import time
from pathlib import Path
import sys

from skills2026.bootstrap import ensure_lerobot_on_path
from skills2026.commands.shared import maybe_start_local_host
from skills2026.paths import DATASETS_DIR
from skills2026.profile import load_profile
from skills2026.training import (
    ReplayValidationReport,
    default_replay_report_path,
    ensure_manifest_matches_profile,
    load_dataset_manifest,
    save_dataset_manifest,
    save_replay_validation_report,
    sync_manifest_from_dataset,
)

ensure_lerobot_on_path()

from lerobot.datasets.lerobot_dataset import LeRobotDataset  # noqa: E402
from lerobot.robots.lekiwi import LeKiwiClient, LeKiwiClientConfig  # noqa: E402
from lerobot.utils.constants import ACTION  # noqa: E402


def _resolve_validation_result(args) -> tuple[str, str]:
    if args.validation_result:
        return args.validation_result, args.notes
    if not args.validate:
        return "", args.notes
    if not sys.stdin.isatty():
        raise RuntimeError("Replay validation requires `--validation-result pass|fail` in non-interactive mode.")
    try:
        response = input(
            "Replay finished. Did it match the intended demo closely enough to train on? [p/f]: "
        ).strip().lower()
    except EOFError as exc:
        raise RuntimeError(
            "Replay validation requires `--validation-result pass|fail` when stdin is not interactive."
        ) from exc
    if response in {"p", "pass"}:
        return "pass", args.notes
    if response in {"f", "fail"}:
        return "fail", args.notes
    raise RuntimeError("Replay validation expects `p`/`pass` or `f`/`fail`.")


def run(args) -> int:
    profile = load_profile(args.profile)
    dataset_root = DATASETS_DIR / args.dataset_name
    manifest = load_dataset_manifest(dataset_root)
    primitive_name = getattr(args, "primitive", "")
    if args.validation_result and not args.validate:
        raise ValueError("`--validation-result` only makes sense together with `--validate`.")
    if manifest is not None:
        ensure_manifest_matches_profile(manifest, profile, dataset_name=args.dataset_name)
        primitive_name = primitive_name or manifest.primitive_name
    elif args.validate:
        raise ValueError(
            "Replay validation requires a dataset manifest. Re-record this dataset with the current workflow first."
        )

    host_process = maybe_start_local_host(profile)
    dataset = LeRobotDataset(
        repo_id=f"skills2026/{args.dataset_name}",
        root=dataset_root,
        episodes=[args.episode],
    )

    robot = LeKiwiClient(
        LeKiwiClientConfig(
            remote_ip=profile.host.remote_ip,
            port_zmq_cmd=profile.host.cmd_port,
            port_zmq_observations=profile.host.observation_port,
            id=profile.robot_id,
        )
    )
    actions = dataset.select_columns(ACTION)
    try:
        robot.connect()
        for idx in range(dataset.num_frames):
            action = {
                name: float(actions[idx][ACTION][i])
                for i, name in enumerate(dataset.features[ACTION]["names"])
            }
            robot.send_action(action)
            time.sleep(1.0 / dataset.fps)
    finally:
        if robot.is_connected:
            robot.disconnect()
        if host_process is not None:
            host_process.terminate()

    if not args.validate:
        return 0

    result, notes = _resolve_validation_result(args)
    report = ReplayValidationReport(
        dataset_name=args.dataset_name,
        primitive_name=primitive_name or manifest.primitive_name,
        profile_name=profile.profile_name,
        profile_signature=manifest.profile_signature,
        episode_index=args.episode,
        created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        result=result,
        notes=notes,
    )
    report_path = Path(args.report_path) if args.report_path else default_replay_report_path(
        args.dataset_name,
        args.episode,
    )
    save_replay_validation_report(report, report_path)
    manifest.mark_replay_approval(
        episode_index=args.episode,
        status=result,
        profile=profile,
        notes=notes,
        report_path=str(report_path),
    )
    save_dataset_manifest(dataset_root, sync_manifest_from_dataset(dataset_root, manifest))
    print(f"Replay validation report saved to {report_path}")
    if result == "pass":
        print(f"Episode {args.episode} approved for ACT gating.")
        return 0

    print(f"Episode {args.episode} marked as failed for ACT gating.")
    return 1
