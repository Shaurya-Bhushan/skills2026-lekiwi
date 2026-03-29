from __future__ import annotations

import os
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from skills2026.bootstrap import ensure_lerobot_on_path
from skills2026.paths import DATASETS_DIR, PROJECT_ROOT
from skills2026.profile import load_profile
from skills2026.training import (
    describe_replay_gate_failure,
    ensure_manifest_matches_profile,
    latest_passing_pickup_stamp,
    load_dataset_manifest,
    save_dataset_manifest,
    sync_manifest_from_dataset,
)


def _default_output_dir(dataset_name: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return PROJECT_ROOT / "outputs" / "train" / f"act_{dataset_name}_{stamp}"


def _training_command(
    *,
    dataset_name: str,
    dataset_root: Path,
    output_dir: Path,
    job_name: str,
    device: str,
    steps: int,
    batch_size: int,
    push_to_hub: bool,
    policy_repo_id: str,
    wandb_enabled: bool,
) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "lerobot.scripts.lerobot_train",
        f"--dataset.repo_id=skills2026/{dataset_name}",
        f"--dataset.root={dataset_root}",
        "--policy.type=act",
        f"--output_dir={output_dir}",
        f"--job_name={job_name}",
        f"--policy.device={device}",
        f"--steps={steps}",
        f"--batch_size={batch_size}",
        f"--wandb.enable={'true' if wandb_enabled else 'false'}",
        f"--policy.push_to_hub={'true' if push_to_hub else 'false'}",
    ]
    if push_to_hub:
        command.append(f"--policy.repo_id={policy_repo_id}")
    return command


def run(args) -> int:
    profile = load_profile(args.profile)
    dataset_name = args.dataset_name or f"{profile.profile_name}_{args.primitive}"
    dataset_root = DATASETS_DIR / dataset_name
    manifest = load_dataset_manifest(dataset_root)
    if manifest is None:
        raise FileNotFoundError(
            f"No dataset manifest found at {dataset_root}. Record the dataset with `skills2026 record` first."
        )

    manifest = sync_manifest_from_dataset(dataset_root, manifest)
    ensure_manifest_matches_profile(
        manifest,
        profile,
        dataset_name=dataset_name,
        primitive_name=args.primitive,
    )
    if not manifest.all_recorded_episodes_approved:
        raise RuntimeError(
            "ACT training is blocked until every recorded episode in this dataset has passed replay validation: "
            + describe_replay_gate_failure(manifest)
            + ". Run `skills2026 replay <dataset> <episode> --validate --validation-result pass|fail` for each episode."
        )

    if args.push_to_hub and not args.policy_repo_id:
        raise ValueError("`--policy-repo-id` is required when `--push-to-hub` is enabled.")

    pickup_stamp = latest_passing_pickup_stamp(profile, args.primitive)
    if pickup_stamp is None:
        raise RuntimeError(
            f"ACT training is blocked until there is a passing pickup_validation report for the current {args.primitive} setup. "
            "Run `skills2026 pickup_validation` again after any camera, calibration, servo, or service-pose change."
        )

    output_dir = Path(args.output_dir) if args.output_dir else _default_output_dir(dataset_name)
    job_name = args.job_name or f"act_{dataset_name}"
    command = _training_command(
        dataset_name=dataset_name,
        dataset_root=dataset_root,
        output_dir=output_dir,
        job_name=job_name,
        device=args.policy_device,
        steps=args.steps,
        batch_size=args.batch_size,
        push_to_hub=args.push_to_hub,
        policy_repo_id=args.policy_repo_id,
        wandb_enabled=args.wandb,
    )

    print("Running ACT training with replay-gated data:")
    print(shlex.join(command))

    if args.dry_run:
        return 0

    lerobot_src = ensure_lerobot_on_path()
    env = os.environ.copy()
    current_pythonpath = env.get("PYTHONPATH", "")
    pythonpath_parts = [str(lerobot_src)]
    if current_pythonpath:
        pythonpath_parts.append(current_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

    result = subprocess.run(command, cwd=str(PROJECT_ROOT), env=env, check=False)
    manifest.mark_pickup_validation(pickup_stamp)
    manifest.record_training_run(
        {
            "command": command,
            "dataset_name": dataset_name,
            "job_name": job_name,
            "output_dir": str(output_dir),
            "device": args.policy_device,
            "steps": args.steps,
            "batch_size": args.batch_size,
            "push_to_hub": args.push_to_hub,
            "policy_repo_id": args.policy_repo_id,
            "wandb": args.wandb,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "exit_code": int(result.returncode),
        }
    )
    save_dataset_manifest(dataset_root, manifest)
    if result.returncode != 0:
        raise RuntimeError(
            f"ACT training exited with code {result.returncode}. "
            "Fix the training error above before using the checkpoint in competition mode."
        )
    print(f"ACT training finished. Checkpoints should be under {output_dir}.")
    return 0
