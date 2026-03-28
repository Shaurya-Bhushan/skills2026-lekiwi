from __future__ import annotations

import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .bootstrap import ensure_lerobot_on_path


@dataclass
class SerialPortInfo:
    device: str
    description: str


def discover_cameras() -> list[dict[str, Any]]:
    ensure_lerobot_on_path()
    from lerobot.cameras.opencv.camera_opencv import OpenCVCamera

    return OpenCVCamera.find_cameras()


def discover_serial_ports() -> list[SerialPortInfo]:
    try:
        from serial.tools import list_ports

        return [
            SerialPortInfo(device=port.device, description=port.description)
            for port in list_ports.comports()
        ]
    except Exception:
        fallback = []
        for pattern in ("/dev/tty.*", "/dev/ttyUSB*", "/dev/ttyACM*", "/dev/cu.*"):
            for path in sorted(Path("/").glob(pattern.lstrip("/"))):
                fallback.append(SerialPortInfo(device=str(path), description="serial device"))
        return fallback


def camera_exists(source_id: str | int) -> bool:
    for camera in discover_cameras():
        if camera["id"] == source_id or str(camera["id"]) == str(source_id):
            return True
    return False


def read_single_camera_frame(source_id: str | int, width: int, height: int, fps: int) -> tuple[bool, str]:
    ensure_lerobot_on_path()
    try:
        from lerobot.cameras.configs import ColorMode
        from lerobot.cameras.opencv.camera_opencv import OpenCVCamera
        from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig

        camera = OpenCVCamera(
            OpenCVCameraConfig(
                index_or_path=source_id,
                width=width,
                height=height,
                fps=fps,
                color_mode=ColorMode.RGB,
                warmup_s=0.2,
            )
        )
        camera.connect()
        frame = camera.read_latest()
        camera.disconnect()
        if frame is None:
            return False, "camera opened but no frame was returned"
        return True, f"frame shape={frame.shape}"
    except Exception as exc:
        return False, str(exc)


def tcp_port_open(host: str, port: int, timeout_s: float = 0.75) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True, "reachable"
    except Exception as exc:
        return False, str(exc)

