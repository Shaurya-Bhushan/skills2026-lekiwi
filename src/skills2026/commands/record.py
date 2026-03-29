from __future__ import annotations

from pathlib import Path

from skills2026.bootstrap import ensure_lerobot_on_path
from skills2026.commands.doctor import collect_camera_checks
from skills2026.commands.shared import maybe_start_local_host
from skills2026.hardware import discover_serial_ports, tcp_port_open
from skills2026.paths import DATASETS_DIR
from skills2026.profile import load_profile
from skills2026.training import (
    DatasetManifest,
    dataset_has_existing_content,
    load_dataset_manifest,
    save_dataset_manifest,
    sync_manifest_from_dataset,
    ensure_manifest_matches_profile,
)

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


def _dataset_repo_id(dataset_name: str) -> str:
    return f"skills2026/{dataset_name}"


def _record_preflight_failures(profile) -> list[str]:
    serial_ports = {port.device for port in discover_serial_ports()}
    failures: list[str] = []

    if not profile.leader_port:
        failures.append("leader arm port is not configured")
    elif profile.leader_port not in serial_ports:
        failures.append(f"leader arm port not found: {profile.leader_port}")

    if profile.robot_serial_port and profile.robot_serial_port not in serial_ports:
        failures.append(f"robot serial port not found: {profile.robot_serial_port}")

    for label, port in (
        ("host command port", profile.host.cmd_port),
        ("host observation port", profile.host.observation_port),
    ):
        ok, detail = tcp_port_open(profile.host.remote_ip, port)
        if not ok:
            failures.append(f"{label} unavailable: {detail}")

    camera_failures = [
        result
        for result in collect_camera_checks(profile)
        if not result.ok
        and (
            result.name == "camera_enabled"
            or result.name.endswith(("_camera_present", "_camera_frame", "_camera_framing", "_camera_calibration"))
        )
    ]
    failures.extend(f"{result.name}: {result.detail}" for result in camera_failures)
    return failures


def run(args) -> int:
    profile = load_profile(args.profile)
    host_process = maybe_start_local_host(profile)
    dataset_name = args.dataset_name or f"{profile.profile_name}_{args.primitive}"
    dataset_root = DATASETS_DIR / dataset_name

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

    listener = None
    dataset = None
    try:
        preflight_failures = _record_preflight_failures(profile)
        if preflight_failures:
            raise ValueError(
                "Recording cannot start until the live setup passes its readiness checks:\n- "
                + "\n- ".join(preflight_failures)
            )

        existing_manifest = load_dataset_manifest(dataset_root)
        if existing_manifest is not None:
            ensure_manifest_matches_profile(
                existing_manifest,
                profile,
                dataset_name=dataset_name,
                primitive_name=args.primitive,
            )
            if not args.append:
                raise ValueError(
                    f"Dataset root {dataset_root} already has a saved manifest and recorded data. "
                    "Use `--append` to resume it intentionally or choose a new `--dataset-name`."
                )
        elif args.append:
            raise ValueError(
                f"Cannot append to {dataset_root} because it has no dataset manifest. "
                "Re-record into a fresh dataset or repair the dataset manually first."
            )
        elif dataset_has_existing_content(dataset_root):
            raise ValueError(
                f"Dataset root {dataset_root} already contains recorded data. "
                "Use a new `--dataset-name` or pass `--append` to resume this exact dataset intentionally."
            )
        elif dataset_root.exists():
            raise ValueError(
                f"Dataset root {dataset_root} already exists. Remove or rename the empty directory before recording."
            )

        robot.connect()
        leader_arm.connect()
        keyboard.connect()

        action_features = hw_to_dataset_features(robot.action_features, ACTION)
        obs_features = hw_to_dataset_features(robot.observation_features, OBS_STR)
        if args.append:
            dataset = LeRobotDataset.resume(
                repo_id=_dataset_repo_id(dataset_name),
                root=dataset_root,
                image_writer_threads=2,
                streaming_encoding=False,
            )
            manifest = existing_manifest
        else:
            dataset = LeRobotDataset.create(
                repo_id=_dataset_repo_id(dataset_name),
                root=dataset_root,
                fps=args.fps,
                features={**action_features, **obs_features},
                robot_type=robot.name,
                use_videos=True,
                image_writer_threads=2,
                streaming_encoding=False,
            )
            manifest = DatasetManifest.create(profile, dataset_name, args.primitive)
            save_dataset_manifest(dataset_root, manifest)

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
        if dataset is not None:
            dataset.finalize()
            manifest = load_dataset_manifest(dataset_root)
            if manifest is not None:
                save_dataset_manifest(dataset_root, sync_manifest_from_dataset(dataset_root, manifest))
        if host_process is not None:
            host_process.terminate()

    print(f"Saved dataset at {dataset_root}")
    return 0
