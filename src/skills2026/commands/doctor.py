from __future__ import annotations

from dataclasses import dataclass

from skills2026.hardware import (
    assess_camera_framing,
    camera_exists,
    capture_single_camera_frame,
    discover_serial_ports,
    tcp_port_open,
)
from skills2026.profile import load_profile
from skills2026.robot.safety import checklist_ready


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def collect_checks(profile) -> list[CheckResult]:
    serial_ports = {port.device for port in discover_serial_ports()}
    results: list[CheckResult] = []
    results.append(
        CheckResult(
            "default_backend",
            profile.policy.default_backend == "opencv_fsm",
            profile.policy.default_backend,
        )
    )

    results.append(
        CheckResult(
            "leader_arm_port",
            bool(profile.leader_port and profile.leader_port in serial_ports),
            profile.leader_port or "not configured",
        )
    )
    if profile.robot_serial_port:
        results.append(
            CheckResult(
                "robot_serial_port",
                profile.robot_serial_port in serial_ports,
                profile.robot_serial_port,
            )
    )

    results.extend(collect_camera_checks(profile))

    enabled_sources = {
        role: str(camera.source_id)
        for role, camera in profile.cameras.items()
        if camera.enabled
    }
    duplicate_sources = len(set(enabled_sources.values())) != len(enabled_sources)
    results.append(
        CheckResult(
            "camera_source_collision",
            not duplicate_sources,
            ", ".join(f"{role}={source}" for role, source in enabled_sources.items()) or "no cameras enabled",
        )
    )

    for port_name, port in (("host_cmd_port", profile.host.cmd_port), ("host_observation_port", profile.host.observation_port)):
        ok, detail = tcp_port_open(profile.host.remote_ip, port)
        results.append(CheckResult(port_name, ok, detail))

    poses_ready = all(bool(pose) for pose in profile.service_poses.values())
    results.append(
        CheckResult(
            "service_poses",
            poses_ready,
            f"{sum(1 for pose in profile.service_poses.values() if pose)}/{len(profile.service_poses)} captured",
        )
    )

    checklist_ok, missing = checklist_ready(profile.checklist)
    results.append(
        CheckResult(
            "competition_checklist",
            checklist_ok,
            "ready" if checklist_ok else f"missing {', '.join(missing)}",
        )
    )
    return results


def collect_camera_checks(profile) -> list[CheckResult]:
    results: list[CheckResult] = []
    enabled_roles = [role for role, camera in profile.cameras.items() if camera.enabled]
    results.append(
        CheckResult(
            "camera_enabled",
            bool(enabled_roles),
            ", ".join(enabled_roles) if enabled_roles else "no cameras enabled",
        )
    )
    for role, camera in profile.cameras.items():
        if not camera.enabled:
            results.extend(
                [
                    CheckResult(f"{role}_camera_present", True, "disabled in profile"),
                    CheckResult(f"{role}_camera_frame", True, "disabled in profile"),
                    CheckResult(f"{role}_camera_framing", True, "disabled in profile"),
                    CheckResult(f"{role}_camera_calibration", True, "disabled in profile"),
                ]
            )
            continue
        exists = camera_exists(camera.source_id)
        results.append(CheckResult(f"{role}_camera_present", exists, str(camera.source_id)))
        if exists:
            ok, frame, detail = capture_single_camera_frame(camera.source_id, camera.width, camera.height, camera.fps)
            results.append(CheckResult(f"{role}_camera_frame", ok, detail))
            if ok and frame is not None:
                framing_ok, framing_detail = assess_camera_framing(frame, role)
                results.append(CheckResult(f"{role}_camera_framing", framing_ok, framing_detail))
        results.append(
            CheckResult(
                f"{role}_camera_calibration",
                camera.calibration.calibrated,
                "ready" if camera.calibration.calibrated else "not calibrated",
            )
        )
    return results


def run(args) -> int:
    profile = load_profile(args.profile)
    results = collect_checks(profile)

    failed = 0
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"{status:>4} | {result.name:<28} | {result.detail}")
        failed += 0 if result.ok else 1

    return 0 if failed == 0 else 1
