from __future__ import annotations

import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

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


def capture_single_camera_frame(
    source_id: str | int,
    width: int,
    height: int,
    fps: int,
) -> tuple[bool, np.ndarray | None, str]:
    ensure_lerobot_on_path()
    camera = None
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
        if frame is None:
            return False, None, "camera opened but no frame was returned"
        return True, frame, f"frame shape={frame.shape}"
    except Exception as exc:
        return False, None, str(exc)
    finally:
        if camera is not None:
            try:
                camera.disconnect()
            except Exception:
                pass


def read_single_camera_frame(source_id: str | int, width: int, height: int, fps: int) -> tuple[bool, str]:
    ok, _, detail = capture_single_camera_frame(source_id, width, height, fps)
    return ok, detail


def assess_camera_framing(frame: np.ndarray, camera_role: str) -> tuple[bool, str]:
    if frame is None or frame.size == 0:
        return False, f"{camera_role} camera framing looks empty"

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mean = float(gray.mean())
    std = float(gray.std())
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    edges = cv2.Canny(gray, 60, 140)
    edge_density = float(np.count_nonzero(edges)) / float(edges.size or 1)
    dark_ratio = float(np.mean(gray < 14))
    bright_ratio = float(np.mean(gray > 242))

    if camera_role == "front":
        min_mean, max_mean = 18.0, 238.0
        min_std = 18.0
        min_blur = 50.0
        min_edge_density = 0.012
    else:
        min_mean, max_mean = 18.0, 238.0
        min_std = 14.0
        min_blur = 30.0
        min_edge_density = 0.008

    issues: list[str] = []
    if mean < min_mean:
        issues.append(f"too dark (mean={mean:.1f})")
    elif mean > max_mean:
        issues.append(f"too bright (mean={mean:.1f})")
    if std < min_std:
        issues.append(f"too flat (std={std:.1f})")
    if blur < min_blur:
        issues.append(f"too blurry (lap_var={blur:.1f})")
    if edge_density < min_edge_density:
        issues.append(f"too little structure (edge_density={edge_density:.3f})")
    if dark_ratio > 0.78:
        issues.append(f"mostly dark ({dark_ratio:.0%})")
    if bright_ratio > 0.78:
        issues.append(f"mostly overexposed ({bright_ratio:.0%})")

    detail = (
        f"mean={mean:.1f}, std={std:.1f}, lap_var={blur:.1f}, "
        f"edge_density={edge_density:.3f}, dark={dark_ratio:.0%}, bright={bright_ratio:.0%}"
    )
    if issues:
        return False, f"{camera_role} camera framing looks weak: {', '.join(issues)} ({detail})"
    return True, f"{camera_role} camera framing looks usable ({detail})"


def tcp_port_open(host: str, port: int, timeout_s: float = 0.75) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True, "reachable"
    except Exception as exc:
        return False, str(exc)
