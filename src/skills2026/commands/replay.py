from __future__ import annotations

import time

from skills2026.bootstrap import ensure_lerobot_on_path
from skills2026.commands.shared import maybe_start_local_host
from skills2026.paths import DATASETS_DIR
from skills2026.profile import load_profile

ensure_lerobot_on_path()

from lerobot.datasets.lerobot_dataset import LeRobotDataset  # noqa: E402
from lerobot.robots.lekiwi import LeKiwiClient, LeKiwiClientConfig  # noqa: E402
from lerobot.utils.constants import ACTION  # noqa: E402


def run(args) -> int:
    profile = load_profile(args.profile)
    host_process = maybe_start_local_host(profile)
    dataset_root = DATASETS_DIR / args.dataset_name
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
    return 0

