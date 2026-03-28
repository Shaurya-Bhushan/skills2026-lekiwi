from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from skills2026.bootstrap import ensure_lerobot_on_path


def maybe_start_local_host(profile) -> subprocess.Popen[str] | None:
    if not profile.host.start_local_host:
        return None

    ensure_lerobot_on_path()
    cmd = [
        sys.executable,
        "-m",
        "lerobot.robots.lekiwi.lekiwi_host",
        f"--robot.id={profile.robot_id}",
        f"--host.connection_time_s={profile.host.connection_time_s}",
    ]
    if profile.robot_serial_port:
        cmd.append(f"--robot.port={profile.robot_serial_port}")

    process = subprocess.Popen(cmd, cwd=str(Path(__file__).resolve().parents[4]))
    time.sleep(1.5)
    return process

