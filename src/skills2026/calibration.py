from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from .constants import DEFAULT_CANONICAL_SIZE


def interactive_pick_homography(
    frame: np.ndarray,
    window_name: str,
    canonical_size: tuple[int, int] = DEFAULT_CANONICAL_SIZE,
) -> list[list[float]]:
    points: list[tuple[int, int]] = []
    clone = frame.copy()

    def on_mouse(event: int, x: int, y: int, _flags: int, _param: Any) -> None:
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
            points.append((x, y))
            cv2.circle(clone, (x, y), 6, (0, 255, 0), -1)
            cv2.imshow(window_name, clone)

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.imshow(window_name, clone)
    cv2.setMouseCallback(window_name, on_mouse)

    while len(points) < 4:
        key = cv2.waitKey(20) & 0xFF
        if key == 27:
            cv2.destroyWindow(window_name)
            raise RuntimeError("Calibration cancelled.")

    cv2.destroyWindow(window_name)
    src = np.array(points, dtype=np.float32)
    width, height = canonical_size
    dst = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )
    homography = cv2.getPerspectiveTransform(src, dst)
    return homography.tolist()


def warp_frame(
    frame: np.ndarray,
    homography: list[list[float]],
    canonical_size: tuple[int, int] = DEFAULT_CANONICAL_SIZE,
) -> np.ndarray:
    width, height = canonical_size
    return cv2.warpPerspective(frame, np.array(homography, dtype=np.float32), (width, height))

