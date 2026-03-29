from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from skills2026.commands.doctor import CheckResult, collect_checks
from skills2026.hardware import discover_cameras, discover_serial_ports
from skills2026.paths import PROFILES_DIR, ensure_workspace_dirs
from skills2026.profile import Skills2026Profile, load_profile, save_profile


def _parse_camera_id(raw: str) -> str | int:
    value = str(raw).strip()
    if not value:
        return ""
    try:
        return int(value)
    except ValueError:
        return value


def _safe_int(raw: str | int | float, default: int) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def list_profiles() -> list[str]:
    ensure_workspace_dirs()
    profiles = ["default"]
    for path in sorted(PROFILES_DIR.glob("*.json")):
        name = path.stem
        if name not in profiles:
            profiles.append(name)
    return profiles


def load_or_default_profile(profile_name: str) -> Skills2026Profile:
    try:
        return load_profile(profile_name)
    except FileNotFoundError:
        return Skills2026Profile.defaults(profile_name or "default")


@dataclass
class SetupFormData:
    profile_name: str
    mode: str
    default_backend: str
    remote_ip: str
    robot_id: str
    leader_port: str
    robot_serial_port: str
    start_local_host: bool
    front_camera_id: str
    front_width: int
    front_height: int
    front_fps: int
    front_enabled: bool
    wrist_camera_id: str
    wrist_width: int
    wrist_height: int
    wrist_fps: int
    wrist_enabled: bool
    kill_switch_ready: bool
    wiring_diagram_ready: bool
    tabletop_stand_ready: bool
    local_only_mode_confirmed: bool

    @classmethod
    def from_profile(cls, profile: Skills2026Profile) -> "SetupFormData":
        return cls(
            profile_name=profile.profile_name,
            mode=profile.mode,
            default_backend=profile.policy.default_backend,
            remote_ip=profile.host.remote_ip,
            robot_id=profile.robot_id,
            leader_port=profile.leader_port,
            robot_serial_port=profile.robot_serial_port,
            start_local_host=profile.host.start_local_host,
            front_camera_id=str(profile.cameras["front"].source_id),
            front_width=profile.cameras["front"].width,
            front_height=profile.cameras["front"].height,
            front_fps=profile.cameras["front"].fps,
            front_enabled=profile.cameras["front"].enabled,
            wrist_camera_id=str(profile.cameras["wrist"].source_id),
            wrist_width=profile.cameras["wrist"].width,
            wrist_height=profile.cameras["wrist"].height,
            wrist_fps=profile.cameras["wrist"].fps,
            wrist_enabled=profile.cameras["wrist"].enabled,
            kill_switch_ready=profile.checklist.kill_switch_ready,
            wiring_diagram_ready=profile.checklist.wiring_diagram_ready,
            tabletop_stand_ready=profile.checklist.tabletop_stand_ready,
            local_only_mode_confirmed=profile.checklist.local_only_mode_confirmed,
        )

    def to_profile(self) -> Skills2026Profile:
        profile = load_or_default_profile(self.profile_name or "default")
        profile.profile_name = self.profile_name or "default"
        profile.mode = self.mode
        profile.policy.default_backend = self.default_backend
        profile.host.remote_ip = self.remote_ip.strip() or profile.host.remote_ip
        profile.robot_id = self.robot_id.strip() or profile.robot_id
        profile.leader_port = self.leader_port.strip()
        profile.robot_serial_port = self.robot_serial_port.strip()
        profile.host.start_local_host = bool(self.start_local_host)

        profile.cameras["front"].source_id = _parse_camera_id(self.front_camera_id)
        profile.cameras["front"].width = _safe_int(self.front_width, profile.cameras["front"].width)
        profile.cameras["front"].height = _safe_int(self.front_height, profile.cameras["front"].height)
        profile.cameras["front"].fps = _safe_int(self.front_fps, profile.cameras["front"].fps)
        profile.cameras["front"].enabled = bool(self.front_enabled)

        profile.cameras["wrist"].source_id = _parse_camera_id(self.wrist_camera_id)
        profile.cameras["wrist"].width = _safe_int(self.wrist_width, profile.cameras["wrist"].width)
        profile.cameras["wrist"].height = _safe_int(self.wrist_height, profile.cameras["wrist"].height)
        profile.cameras["wrist"].fps = _safe_int(self.wrist_fps, profile.cameras["wrist"].fps)
        profile.cameras["wrist"].enabled = bool(self.wrist_enabled)

        profile.checklist.kill_switch_ready = bool(self.kill_switch_ready)
        profile.checklist.wiring_diagram_ready = bool(self.wiring_diagram_ready)
        profile.checklist.tabletop_stand_ready = bool(self.tabletop_stand_ready)
        profile.checklist.local_only_mode_confirmed = bool(self.local_only_mode_confirmed)
        return profile


def form_values_from_profile(profile_name: str) -> tuple:
    form = SetupFormData.from_profile(load_or_default_profile(profile_name or "default"))
    return (
        form.profile_name,
        form.mode,
        form.default_backend,
        form.remote_ip,
        form.robot_id,
        form.leader_port,
        form.robot_serial_port,
        form.start_local_host,
        form.front_camera_id,
        form.front_width,
        form.front_height,
        form.front_fps,
        form.front_enabled,
        form.wrist_camera_id,
        form.wrist_width,
        form.wrist_height,
        form.wrist_fps,
        form.wrist_enabled,
        form.kill_switch_ready,
        form.wiring_diagram_ready,
        form.tabletop_stand_ready,
        form.local_only_mode_confirmed,
        build_profile_summary(form.to_profile()),
        build_next_steps(form.to_profile()),
    )


def save_form_data(form: SetupFormData) -> tuple[str, str, str]:
    profile = form.to_profile()
    path = save_profile(profile)
    message = f"Saved profile to `{path}`."
    return (
        message,
        build_profile_summary(profile),
        build_next_steps(profile),
    )


def build_profile_summary(profile: Skills2026Profile) -> str:
    pose_count = sum(1 for pose in profile.service_poses.values() if pose)
    total_poses = len(profile.service_poses)
    return "\n".join(
        [
            f"### Profile `{profile.profile_name}`",
            f"- Runtime mode: `{profile.mode}`",
            f"- Default backend: `{profile.policy.default_backend}`",
            f"- Front camera: `{profile.cameras['front'].source_id}` at {profile.cameras['front'].width}x{profile.cameras['front'].height} @ {profile.cameras['front'].fps} FPS",
            f"- Wrist camera: `{profile.cameras['wrist'].source_id}` at {profile.cameras['wrist'].width}x{profile.cameras['wrist'].height} @ {profile.cameras['wrist'].fps} FPS",
            f"- Leader port: `{profile.leader_port or 'not set'}`",
            f"- Service poses captured: `{pose_count}/{total_poses}`",
            f"- Camera calibration: front=`{profile.cameras['front'].calibration.calibrated}`, wrist=`{profile.cameras['wrist'].calibration.calibrated}`",
        ]
    )


def build_next_steps(profile: Skills2026Profile) -> str:
    steps = [
        f"1. Save this profile as `{profile.profile_name}`.",
        f"2. Run `skills2026 --profile {profile.profile_name} doctor` to confirm hardware and checklist readiness.",
        f"3. When the robot is powered and the cameras are live, run `skills2026 --profile {profile.profile_name} setup` to capture camera calibration and service poses.",
        f"4. Start with `skills2026 --profile {profile.profile_name} teleop` before trying `record` or `competition`.",
        f"5. Run `skills2026 --profile {profile.profile_name} pickup_validation --suite core --trials 3` once pickup is stable.",
        f"6. Start with `skills2026 --profile {profile.profile_name} competition mission --mission-name ecu_steve_priority` once your ECU service poses are captured.",
        "7. Keep the default OpenCV/FSM stack until fuse, board, transformer, and Steve tasks are repeatable.",
        "8. If you still need learning later, record clean demonstrations and train ACT for insertion or contact refinement.",
    ]
    return "### Beginner Next Steps\n" + "\n".join(f"- {step}" for step in steps)


def discover_hardware_snapshot() -> tuple[list[list[str]], list[list[str]], str]:
    try:
        cameras = discover_cameras()
    except Exception as exc:
        cameras = []
        camera_error = f"Camera discovery failed: {exc}"
    else:
        camera_error = ""

    try:
        ports = discover_serial_ports()
    except Exception as exc:
        ports = []
        port_error = f"Serial discovery failed: {exc}"
    else:
        port_error = ""

    camera_rows = [[str(camera["id"]), str(camera["name"])] for camera in cameras]
    port_rows = [[port.device, port.description] for port in ports]

    suggestions = []
    if camera_error:
        suggestions.append(camera_error)
    if port_error:
        suggestions.append(port_error)
    if cameras:
        suggestions.append(f"Front camera suggestion: `{cameras[0]['id']}`")
        if len(cameras) > 1:
            suggestions.append(f"Wrist camera suggestion: `{cameras[1]['id']}`")
    else:
        suggestions.append("No cameras detected yet.")

    if ports:
        suggestions.append(f"Leader port suggestion: `{ports[0].device}`")
        if len(ports) > 1:
            suggestions.append(f"Robot serial suggestion: `{ports[1].device}`")
    else:
        suggestions.append("No serial ports detected yet.")

    return camera_rows, port_rows, "\n".join(f"- {item}" for item in suggestions)


def apply_detected_defaults(profile_name: str) -> tuple:
    profile = load_or_default_profile(profile_name or "default")
    try:
        cameras = discover_cameras()
    except Exception:
        cameras = []
    try:
        ports = discover_serial_ports()
    except Exception:
        ports = []

    if cameras:
        profile.cameras["front"].source_id = cameras[0]["id"]
        profile.cameras["wrist"].source_id = cameras[1]["id"] if len(cameras) > 1 else cameras[0]["id"]
    if ports:
        profile.leader_port = ports[0].device
        profile.robot_serial_port = ports[1].device if len(ports) > 1 else profile.robot_serial_port

    return form_values_from_profile(profile.profile_name)


def run_doctor_for_form(form: SetupFormData) -> tuple[list[list[str]], str]:
    try:
        profile = form.to_profile()
        results = collect_checks(profile)
    except Exception as exc:
        return [["FAIL", "doctor_runtime", str(exc)]], "### Readiness Result\n- The check could not finish. Fix the error shown in the table first."

    rows = [["PASS" if result.ok else "FAIL", result.name, result.detail] for result in results]
    failures = [result.name for result in results if not result.ok]
    if failures:
        summary = "### Readiness Result\n- Some setup items still need attention.\n- Failing checks: " + ", ".join(
            f"`{name}`" for name in failures
        )
    else:
        summary = "### Readiness Result\n- Everything in the current form passed."
    return rows, summary


def profile_name_choices() -> list[str]:
    return list_profiles()


def ensure_profile_name(raw: str) -> str:
    name = raw.strip() or "default"
    if name.endswith(".json"):
        name = Path(name).stem
    return name
