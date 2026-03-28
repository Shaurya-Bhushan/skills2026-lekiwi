from __future__ import annotations

import logging

from skills2026.calibration import interactive_pick_homography
from skills2026.hardware import discover_cameras, discover_serial_ports
from skills2026.profile import Skills2026Profile, load_profile, save_profile

logger = logging.getLogger(__name__)


def _prompt(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def _parse_camera_id(raw: str) -> str | int:
    try:
        return int(raw)
    except ValueError:
        return raw


def run(args) -> int:
    try:
        profile = load_profile(args.profile)
    except FileNotFoundError:
        profile = Skills2026Profile.defaults(args.profile or "default")

    cameras = discover_cameras()
    ports = discover_serial_ports()

    print("\nDetected cameras:")
    for idx, camera in enumerate(cameras):
        print(f"  {idx}: id={camera['id']} name={camera['name']}")

    print("\nDetected serial ports:")
    for idx, port in enumerate(ports):
        print(f"  {idx}: {port.device} ({port.description})")

    front_default = str(profile.cameras["front"].source_id)
    wrist_default = str(profile.cameras["wrist"].source_id)
    leader_default = profile.leader_port or (ports[0].device if ports else "")
    robot_default = profile.robot_serial_port or ""

    profile.mode = _prompt("Runtime mode (dev_remote or competition_local)", profile.mode)
    profile.host.remote_ip = _prompt("LeKiwi host IP", profile.host.remote_ip)
    profile.leader_port = _prompt("Leader arm port", leader_default)
    profile.robot_serial_port = _prompt("Robot serial port (optional)", robot_default)
    profile.cameras["front"].source_id = _parse_camera_id(_prompt("Front camera ID", front_default))
    profile.cameras["wrist"].source_id = _parse_camera_id(_prompt("Wrist camera ID", wrist_default))
    profile.host.start_local_host = _prompt(
        "Start local host automatically? (y/n)",
        "y" if profile.host.start_local_host else "n",
    ).lower().startswith("y")

    path = save_profile(profile)
    print(f"\nSaved profile to {path}")

    if args.skip_live:
        return 0

    live = _prompt("Capture live poses and camera calibration now? (y/n)", "y")
    if not live.lower().startswith("y"):
        return 0

    from skills2026.robot.lekiwi_io import LeKiwiIO

    io = LeKiwiIO(profile)
    try:
        io.connect()
        observation = io.get_observation()
        for camera_role in ("front", "wrist"):
            frame = observation.get(camera_role)
            if frame is None:
                continue
            calibrate = _prompt(f"Calibrate {camera_role} camera with 4 corner clicks? (y/n)", "y")
            if calibrate.lower().startswith("y"):
                homography = interactive_pick_homography(frame, f"skills2026_{camera_role}_calibration")
                profile.cameras[camera_role].calibration.homography = homography
                profile.cameras[camera_role].calibration.calibrated = True

        for pose_name in profile.service_poses:
            capture = _prompt(f"Capture live pose '{pose_name}'? (y/n)", "y")
            if not capture.lower().startswith("y"):
                continue
            input(f"Move the robot to '{pose_name}' and press Enter to capture.")
            pose_obs = io.get_observation()
            profile.service_poses[pose_name] = io.arm_pose_from_observation(pose_obs)
            print(f"Captured pose '{pose_name}'.")
    finally:
        io.disconnect()

    save_profile(profile, path)
    print(f"Updated profile saved to {path}")
    return 0
