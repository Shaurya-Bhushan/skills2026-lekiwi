from __future__ import annotations

import time

from skills2026.bootstrap import ensure_lerobot_on_path
from skills2026.commands.shared import maybe_start_local_host
from skills2026.profile import load_profile
from skills2026.robot.lekiwi_io import LeKiwiIO

ensure_lerobot_on_path()

from lerobot.teleoperators.keyboard.teleop_keyboard import KeyboardTeleop, KeyboardTeleopConfig  # noqa: E402
from lerobot.teleoperators.so_leader import SO100Leader, SO100LeaderConfig  # noqa: E402


def run(args) -> int:
    profile = load_profile(args.profile)
    host_process = maybe_start_local_host(profile)
    io = LeKiwiIO(profile)
    leader = SO100Leader(SO100LeaderConfig(port=profile.leader_port))
    keyboard = KeyboardTeleop(KeyboardTeleopConfig())

    try:
        io.connect()
        leader.connect()
        keyboard.connect()

        print("Starting teleop loop. Press Ctrl+C to exit.")
        while True:
            observation = io.get_observation()
            arm_action = leader.get_action()
            arm_action = {f"arm_{key}": value for key, value in arm_action.items()}
            base_action = io.robot._from_keyboard_to_base_action(keyboard.get_action())
            current_pose = io.arm_pose_from_observation(observation)
            merged = io.merge_action({**current_pose, **arm_action}, base_action)
            io.send_action(merged)
            time.sleep(1.0 / 15.0)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            io.stop_base()
        except Exception:
            pass
        io.disconnect()
        if leader.is_connected:
            leader.disconnect()
        if keyboard.is_connected:
            keyboard.disconnect()
        if host_process is not None:
            host_process.terminate()
    return 0

