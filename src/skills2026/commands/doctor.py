from __future__ import annotations

from dataclasses import dataclass

from skills2026.hardware import camera_exists, discover_serial_ports, read_single_camera_frame, tcp_port_open
from skills2026.policy.smolvla import inspect_smolvla_runtime
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
            profile.policy.default_backend in {"opencv_fsm", "smolvla"},
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

    for role, camera in profile.cameras.items():
        exists = camera_exists(camera.source_id)
        results.append(CheckResult(f"{role}_camera_present", exists, str(camera.source_id)))
        if exists:
            ok, detail = read_single_camera_frame(camera.source_id, camera.width, camera.height, camera.fps)
            results.append(CheckResult(f"{role}_camera_frame", ok, detail))
        results.append(
            CheckResult(
                f"{role}_camera_calibration",
                camera.calibration.calibrated,
                "ready" if camera.calibration.calibrated else "not calibrated",
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

    smolvla_status = inspect_smolvla_runtime()
    smolvla_required = profile.policy.default_backend == "smolvla"
    results.append(
        CheckResult(
            "smolvla_backend",
            smolvla_status.ready if smolvla_required else True,
            smolvla_status.detail if smolvla_status.ready else f"optional backend: {smolvla_status.detail}",
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
