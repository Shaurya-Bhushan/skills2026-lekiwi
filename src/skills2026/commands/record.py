from __future__ import annotations

from pathlib import Path

from skills2026.bootstrap import ensure_lerobot_on_path
from skills2026.commands.shared import maybe_start_local_host
from skills2026.paths import DATASETS_DIR
from skills2026.profile import load_profile

ensure_lerobot_on_path()

from lerobot.datasets.feature_utils import hw_to_dataset_features  # noqa: E402
from lerobot.datasets.lerobot_dataset import LeRobotDataset  # noqa: E402
from lerobot.processor import make_default_processors  # noqa: E402
from lerobot.robots.lekiwi import LeKiwiClient, LeKiwiClientConfig  # noqa: E402
from lerobot.scripts.lerobot_record import record_loop  # noqa: E402
from lerobot.teleoperators.keyboard import KeyboardTeleop, KeyboardTeleopConfig  # noqa: E402
from lerobot.teleoperators.so_leader import SO100Leader, SO100LeaderConfig  # noqa: E402
from lerobot.utils.constants import ACTION, OBS_STR  # noqa: E402
from lerobot.utils.control_utils import init_keyboard_listener  # noqa: E402


def _dataset_repo_id(profile_name: str, primitive: str) -> str:
    return f"skills2026/{profile_name}_{primitive}"


def run(args) -> int:
    profile = load_profile(args.profile)
    host_process = maybe_start_local_host(profile)
    dataset_name = args.dataset_name or f"{profile.profile_name}_{args.primitive}"
    dataset_root = DATASETS_DIR / dataset_name
    dataset_root.mkdir(parents=True, exist_ok=True)

    camera_configs = {}
    for role, camera in profile.cameras.items():
        if not camera.enabled:
            continue
        from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig

        camera_configs[role] = OpenCVCameraConfig(
            index_or_path=camera.source_id,
            width=camera.width,
            height=camera.height,
            fps=camera.fps,
        )

    robot = LeKiwiClient(
        LeKiwiClientConfig(
            remote_ip=profile.host.remote_ip,
            port_zmq_cmd=profile.host.cmd_port,
            port_zmq_observations=profile.host.observation_port,
            id=profile.robot_id,
            cameras=camera_configs,
        )
    )
    leader_arm = SO100Leader(SO100LeaderConfig(port=profile.leader_port))
    keyboard = KeyboardTeleop(KeyboardTeleopConfig())
    teleop_action_processor, robot_action_processor, robot_observation_processor = make_default_processors()

    action_features = hw_to_dataset_features(robot.action_features, ACTION)
    obs_features = hw_to_dataset_features(robot.observation_features, OBS_STR)
    dataset = LeRobotDataset.create(
        repo_id=_dataset_repo_id(profile.profile_name, args.primitive),
        root=dataset_root,
        fps=args.fps,
        features={**action_features, **obs_features},
        robot_type=robot.name,
        use_videos=True,
        image_writer_threads=2,
        streaming_encoding=False,
    )

    listener = None
    try:
        robot.connect()
        leader_arm.connect()
        keyboard.connect()
        listener, events = init_keyboard_listener()
        recorded = 0
        while recorded < args.episodes and not events["stop_recording"]:
            record_loop(
                robot=robot,
                events=events,
                fps=args.fps,
                dataset=dataset,
                teleop=[leader_arm, keyboard],
                control_time_s=args.episode_time_s,
                single_task=args.primitive,
                display_data=False,
                teleop_action_processor=teleop_action_processor,
                robot_action_processor=robot_action_processor,
                robot_observation_processor=robot_observation_processor,
            )
            if events["rerecord_episode"]:
                events["rerecord_episode"] = False
                events["exit_early"] = False
                dataset.clear_episode_buffer()
                continue
            dataset.save_episode()
            recorded += 1
    finally:
        if listener is not None:
            listener.stop()
        if keyboard.is_connected:
            keyboard.disconnect()
        if leader_arm.is_connected:
            leader_arm.disconnect()
        if robot.is_connected:
            robot.disconnect()
        dataset.finalize()
        if host_process is not None:
            host_process.terminate()

    print(f"Saved dataset at {dataset_root}")
    return 0
