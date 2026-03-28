from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from skills2026.bootstrap import ensure_lerobot_on_path


def maybe_start_local_host(profile) -> subprocess.Popen[str] | None:
    if not profile.host.start_local_host:
        return None

    lerobot_src = ensure_lerobot_on_path()
    cmd = [
        sys.executable,
        "-m",
        "lerobot.robots.lekiwi.lekiwi_host",
        f"--robot.id={profile.robot_id}",
        f"--host.connection_time_s={profile.host.connection_time_s}",
    ]
    if profile.robot_serial_port:
        cmd.append(f"--robot.port={profile.robot_serial_port}")

    env = os.environ.copy()
    current_pythonpath = env.get("PYTHONPATH", "")
    path_parts = [str(lerobot_src)]
    if current_pythonpath:
        path_parts.append(current_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(path_parts)

    process = subprocess.Popen(cmd, cwd=str(Path(__file__).resolve().parents[4]), env=env)
    time.sleep(1.5)
    return process
