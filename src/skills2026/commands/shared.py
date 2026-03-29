from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from skills2026.bootstrap import ensure_lerobot_on_path
from skills2026.hardware import tcp_port_open


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
        f"--host.port_zmq_cmd={profile.host.cmd_port}",
        f"--host.port_zmq_observations={profile.host.observation_port}",
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
    deadline = time.time() + max(float(profile.host.connect_timeout_s), 3.0)
    cmd_detail = "unreachable"
    obs_detail = "unreachable"
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"LeKiwi host exited early with code {process.returncode}. "
                "Check the robot port, permissions, and host logs."
            )
        cmd_ok, cmd_detail = tcp_port_open(profile.host.remote_ip, profile.host.cmd_port)
        obs_ok, obs_detail = tcp_port_open(profile.host.remote_ip, profile.host.observation_port)
        if cmd_ok and obs_ok:
            return process
        time.sleep(0.2)

    process.terminate()
    try:
        process.wait(timeout=2)
    except Exception:
        try:
            process.kill()
            process.wait(timeout=2)
        except Exception:
            pass
    raise RuntimeError(
        "LeKiwi host did not come online on the configured ports. "
        f"cmd={cmd_detail}; obs={obs_detail}"
    )
