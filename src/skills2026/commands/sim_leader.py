from __future__ import annotations

import os
import subprocess
from pathlib import Path


SIM_REPO_ENV = "SKILLS2026_LEKIWI_SIM_REPO"
SIM_LAUNCHER = "run_local_leader_arm.command"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_sim_repo() -> Path:
    repo_root = _repo_root()
    candidates = [
        Path(os.environ.get(SIM_REPO_ENV, "")).expanduser(),
        repo_root.parent / "skills2026-lekiwi-sim",
        repo_root.parent / "local-lekiwi-sim",
        repo_root.parent / "ekumen-lekiwi",
        repo_root.parent / "lekiwi-sim",
        repo_root.parent / "LeKiwi",
    ]
    for candidate in candidates:
        if not str(candidate):
            continue
        if (candidate / SIM_LAUNCHER).exists():
            return candidate
    return repo_root.parent / "skills2026-lekiwi-sim"


def _resolve_sim_repo(raw_path: str) -> Path:
    if raw_path:
        return Path(raw_path).expanduser().resolve(strict=False)
    return _default_sim_repo().resolve(strict=False)


def run(args) -> int:
    sim_repo = _resolve_sim_repo(args.sim_repo)
    launcher = sim_repo / SIM_LAUNCHER
    if not launcher.exists():
        raise FileNotFoundError(
            "Could not find the local LeKiwi simulator launcher. "
            f"Expected {launcher}. Use --sim-repo or set {SIM_REPO_ENV}."
        )
    if not os.access(launcher, os.X_OK):
        raise RuntimeError(f"The simulator launcher is not executable: {launcher}")

    cmd = [str(launcher), args.leader_arm_port]
    return subprocess.call(cmd, cwd=str(sim_repo))
