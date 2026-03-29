from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .constants import DEFAULT_FRONT_FPS, DEFAULT_LOOP_HZ, DEFAULT_WRIST_FPS
from .paths import DEFAULT_PROFILE_PATH, PROFILES_DIR, ensure_workspace_dirs


def _identity_homography() -> list[list[float]]:
    return [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ]


def _migrate_legacy_wrist_x_gains(raw: dict[str, Any]) -> dict[str, Any]:
    merged = dict(raw)
    x_gains = {str(k): float(v) for k, v in merged.get("x_gains", {}).items()}
    legacy_defaults = {
        "arm_shoulder_pan.pos": -2.5,
        "arm_wrist_roll.pos": 1.5,
    }
    if x_gains == legacy_defaults:
        merged["x_gains"] = {
            "arm_shoulder_pan.pos": -3.0,
        }
    return merged


@dataclass
class CameraCalibration:
    calibrated: bool = False
    homography: list[list[float]] = field(default_factory=_identity_homography)
    roi: list[int] | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "CameraCalibration":
        return cls(
            calibrated=bool(raw.get("calibrated", False)),
            homography=raw.get("homography", _identity_homography()),
            roi=raw.get("roi"),
        )


@dataclass
class CameraProfile:
    role: str
    source_id: str | int
    width: int
    height: int
    fps: int
    enabled: bool = True
    calibration: CameraCalibration = field(default_factory=CameraCalibration)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "CameraProfile":
        return cls(
            role=str(raw["role"]),
            source_id=raw["source_id"],
            width=int(raw.get("width", 640)),
            height=int(raw.get("height", 480)),
            fps=int(raw.get("fps", DEFAULT_FRONT_FPS)),
            enabled=bool(raw.get("enabled", True)),
            calibration=CameraCalibration.from_dict(raw.get("calibration", {})),
        )


@dataclass
class HostProfile:
    remote_ip: str = "127.0.0.1"
    cmd_port: int = 5555
    observation_port: int = 5556
    connect_timeout_s: int = 5
    start_local_host: bool = False
    connection_time_s: int = 7200

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "HostProfile":
        return cls(
            remote_ip=str(raw.get("remote_ip", "127.0.0.1")),
            cmd_port=int(raw.get("cmd_port", 5555)),
            observation_port=int(raw.get("observation_port", 5556)),
            connect_timeout_s=int(raw.get("connect_timeout_s", 5)),
            start_local_host=bool(raw.get("start_local_host", False)),
            connection_time_s=int(raw.get("connection_time_s", 7200)),
        )


@dataclass
class ServoProfile:
    x_gains: dict[str, float] = field(default_factory=dict)
    y_gains: dict[str, float] = field(default_factory=dict)
    tolerance_px: float = 32.0
    max_step: float = 2.5

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ServoProfile":
        return cls(
            x_gains={str(k): float(v) for k, v in raw.get("x_gains", {}).items()},
            y_gains={str(k): float(v) for k, v in raw.get("y_gains", {}).items()},
            tolerance_px=float(raw.get("tolerance_px", 32.0)),
            max_step=float(raw.get("max_step", 2.5)),
        )


@dataclass
class RuntimeBudget:
    loop_hz: float = DEFAULT_LOOP_HZ
    overload_ratio: float = 1.35
    overload_strikes_before_disabling_wrist: int = 2
    overload_strikes_before_throttling_front: int = 4
    front_fps_min: int = 10

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "RuntimeBudget":
        return cls(
            loop_hz=float(raw.get("loop_hz", DEFAULT_LOOP_HZ)),
            overload_ratio=float(raw.get("overload_ratio", 1.35)),
            overload_strikes_before_disabling_wrist=int(
                raw.get("overload_strikes_before_disabling_wrist", 2)
            ),
            overload_strikes_before_throttling_front=int(
                raw.get("overload_strikes_before_throttling_front", 4)
            ),
            front_fps_min=int(raw.get("front_fps_min", 10)),
        )


@dataclass
class CompetitionChecklist:
    kill_switch_ready: bool = False
    wiring_diagram_ready: bool = False
    tabletop_stand_ready: bool = False
    local_only_mode_confirmed: bool = False

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "CompetitionChecklist":
        return cls(
            kill_switch_ready=bool(raw.get("kill_switch_ready", False)),
            wiring_diagram_ready=bool(raw.get("wiring_diagram_ready", False)),
            tabletop_stand_ready=bool(raw.get("tabletop_stand_ready", False)),
            local_only_mode_confirmed=bool(raw.get("local_only_mode_confirmed", False)),
        )


@dataclass
class PolicyProfile:
    default_backend: str = "opencv_fsm"

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PolicyProfile":
        backend = str(raw.get("default_backend", "opencv_fsm")).strip() or "opencv_fsm"
        if backend != "opencv_fsm":
            backend = "opencv_fsm"
        return cls(default_backend=backend)


@dataclass
class Skills2026Profile:
    profile_name: str
    mode: str = "dev_remote"
    robot_id: str = "skills2026_lekiwi"
    leader_port: str = ""
    robot_serial_port: str = ""
    cameras: dict[str, CameraProfile] = field(default_factory=dict)
    host: HostProfile = field(default_factory=HostProfile)
    service_poses: dict[str, dict[str, float]] = field(default_factory=dict)
    servo: dict[str, ServoProfile] = field(default_factory=dict)
    budget: RuntimeBudget = field(default_factory=RuntimeBudget)
    checklist: CompetitionChecklist = field(default_factory=CompetitionChecklist)
    policy: PolicyProfile = field(default_factory=PolicyProfile)
    data_root: str = "data/datasets"

    @classmethod
    def defaults(cls, profile_name: str = "default") -> "Skills2026Profile":
        return cls(
            profile_name=profile_name,
            cameras={
                "front": CameraProfile(
                    role="front",
                    source_id=0,
                    width=640,
                    height=480,
                    fps=DEFAULT_FRONT_FPS,
                ),
                "wrist": CameraProfile(
                    role="wrist",
                    source_id=1,
                    width=640,
                    height=480,
                    fps=DEFAULT_WRIST_FPS,
                ),
            },
            servo={
                "front": ServoProfile(
                    x_gains={"arm_shoulder_pan.pos": -6.0},
                    y_gains={"arm_shoulder_lift.pos": 5.0},
                    tolerance_px=48.0,
                    max_step=3.0,
                ),
                "wrist": ServoProfile(
                    x_gains={
                        "arm_shoulder_pan.pos": -3.0,
                    },
                    y_gains={
                        "arm_shoulder_lift.pos": 2.5,
                        "arm_elbow_flex.pos": -1.0,
                    },
                    tolerance_px=20.0,
                    max_step=1.5,
                ),
            },
            service_poses={
                "stow": {},
                "safe_retract": {},
                "tray_hover": {},
                "tray_grasp": {},
                "fuse_remove_hover": {},
                "fuse_remove_pose": {},
                "board_remove_hover": {},
                "board_remove_pose": {},
                "transformer_supply_hover": {},
                "transformer_supply_pick_pose": {},
                "transformer_remove_hover": {},
                "transformer_remove_pose": {},
                "debris_hover": {},
                "debris_pick_pose": {},
                "debris_zone_hover": {},
                "debris_zone_drop_pose": {},
                "beam_hover": {},
                "beam_push_pose": {},
                "fuse_insert_hover": {},
                "fuse_insert_pose": {},
                "board_insert_hover": {},
                "board_insert_pose": {},
                "supply_hover": {},
                "supply_pick_pose": {},
                "safe_room_hover": {},
                "safe_room_place_pose": {},
                "safe_room_orient_pose": {},
                "worker_hover": {},
                "worker_pick_pose": {},
                "worker_zone_hover": {},
                "worker_place_pose": {},
                "steve_hover": {},
                "steve_pick_pose": {},
                "lobby_hover": {},
                "lobby_place_pose": {},
                "fan_hover": {},
                "fan_pick_pose": {},
                "fan_mount_hover": {},
                "fan_mount_pose": {},
                "breaker_hover": {},
                "breaker_flip_pose": {},
                "bot_hover": {},
                "bot_pick_pose": {},
                "bot_zone_hover": {},
                "bot_zone_place_pose": {},
                "final_zone_hover": {},
                "final_zone_pose": {},
                "transformer_bolt_hover": {},
                "transformer_bolt_pose": {},
                "transformer_bolt_lock_pose": {},
                "transformer_insert_hover": {},
                "transformer_insert_pose": {},
            },
        )

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Skills2026Profile":
        profile = cls.defaults(str(raw.get("profile_name", "default")))
        profile.mode = str(raw.get("mode", profile.mode))
        profile.robot_id = str(raw.get("robot_id", profile.robot_id))
        profile.leader_port = str(raw.get("leader_port", profile.leader_port))
        profile.robot_serial_port = str(raw.get("robot_serial_port", profile.robot_serial_port))
        profile.host = HostProfile.from_dict(raw.get("host", {}))
        profile.budget = RuntimeBudget.from_dict(raw.get("budget", {}))
        profile.checklist = CompetitionChecklist.from_dict(raw.get("checklist", {}))
        profile.policy = PolicyProfile.from_dict(raw.get("policy", {}))
        profile.data_root = str(raw.get("data_root", profile.data_root))

        cameras = raw.get("cameras", {})
        merged_cameras: dict[str, CameraProfile] = {}
        for role, camera in profile.cameras.items():
            merged_cameras[role] = CameraProfile.from_dict(
                {**asdict(camera), **cameras.get(role, {})}
            )
        for role, camera_raw in cameras.items():
            if role not in merged_cameras:
                merged_cameras[role] = CameraProfile.from_dict(camera_raw)
        profile.cameras = merged_cameras

        servo = raw.get("servo", {})
        merged_servo: dict[str, ServoProfile] = {}
        for role, servo_profile in profile.servo.items():
            merged_raw = {**asdict(servo_profile), **servo.get(role, {})}
            if role == "wrist":
                merged_raw = _migrate_legacy_wrist_x_gains(merged_raw)
            merged_servo[role] = ServoProfile.from_dict(merged_raw)
        for role, servo_raw in servo.items():
            if role not in merged_servo:
                migrated = _migrate_legacy_wrist_x_gains(servo_raw) if role == "wrist" else servo_raw
                merged_servo[role] = ServoProfile.from_dict(migrated)
        profile.servo = merged_servo

        incoming_poses = raw.get("service_poses", {})
        merged_poses: dict[str, dict[str, float]] = {}
        for name, pose in profile.service_poses.items():
            merged_poses[name] = {str(k): float(v) for k, v in incoming_poses.get(name, pose).items()}
        for name, pose in incoming_poses.items():
            if name not in merged_poses:
                merged_poses[name] = {str(k): float(v) for k, v in pose.items()}
        profile.service_poses = merged_poses
        return profile


def resolve_profile_path(profile_name: str | None) -> Path:
    ensure_workspace_dirs()
    if not profile_name or profile_name == "default":
        return DEFAULT_PROFILE_PATH
    return PROFILES_DIR / f"{profile_name}.json"


def load_profile(profile_name: str | None = None) -> Skills2026Profile:
    path = resolve_profile_path(profile_name)
    if not path.exists():
        raise FileNotFoundError(
            f"No profile found at {path}. Run `skills2026 setup` first."
        )
    return Skills2026Profile.from_dict(json.loads(path.read_text()))


def save_profile(profile: Skills2026Profile, path: Path | None = None) -> Path:
    ensure_workspace_dirs()
    target = path or resolve_profile_path(profile.profile_name)
    target.write_text(json.dumps(asdict(profile), indent=2, sort_keys=True))
    return target
