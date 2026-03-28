from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from skills2026.calibration import warp_frame
from skills2026.constants import (
    BOARD_SLOT_CENTERS,
    DEFAULT_CANONICAL_SIZE,
    FUSE_SLOT_CENTERS,
    TRANSFORMER_SLOT_CENTERS,
)
from skills2026.perception.models import VisionTarget


HSV_RANGES = {
    "orange": ((5, 80, 80), (20, 255, 255)),
    "green": ((35, 50, 50), (95, 255, 255)),
    "blue": ((95, 50, 50), (135, 255, 255)),
    "black": ((0, 0, 0), (180, 255, 80)),
}


@dataclass
class FrontPerception:
    canonical_size: tuple[int, int] = DEFAULT_CANONICAL_SIZE

    def _maybe_warp(self, frame: np.ndarray, calibration: dict[str, Any] | None) -> np.ndarray:
        if calibration and calibration.get("calibrated") and calibration.get("homography"):
            return warp_frame(frame, calibration["homography"], self.canonical_size)
        return frame

    def _largest_mask_contour(
        self,
        hsv: np.ndarray,
        color_name: str,
        min_area: int = 250,
    ) -> tuple[np.ndarray | None, tuple[int, int, int, int] | None]:
        lower, upper = HSV_RANGES[color_name]
        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best = None
        best_bbox = None
        best_area = 0.0
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area or area <= best_area:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            best = contour
            best_bbox = (x, y, w, h)
            best_area = area
        return best, best_bbox

    def _bbox_center(self, bbox: tuple[int, int, int, int]) -> tuple[float, float]:
        x, y, w, h = bbox
        return (x + w / 2.0, y + h / 2.0)

    def analyze(
        self,
        frame: np.ndarray,
        primitive_name: str,
        calibration: dict[str, Any] | None = None,
        target_color: str | None = None,
        target_slot: str | None = None,
    ) -> VisionTarget:
        warped = self._maybe_warp(frame, calibration)
        hsv = cv2.cvtColor(warped, cv2.COLOR_RGB2HSV)
        width, height = self.canonical_size

        if "fuse" in primitive_name:
            search_color = target_color or "black"
            contour, bbox = self._largest_mask_contour(hsv, search_color, min_area=180)
            if bbox is None:
                return VisionTarget(found=False, camera_role="front", label="fuse")
            desired = FUSE_SLOT_CENTERS.get(target_color or search_color, FUSE_SLOT_CENTERS["green"])
            desired_center = (desired[0] * width, desired[1] * height)
            center = self._bbox_center(bbox)
            return VisionTarget(
                found=True,
                camera_role="front",
                confidence=0.75,
                center_px=center,
                error_px=(desired_center[0] - center[0], desired_center[1] - center[1]),
                bbox_xywh=bbox,
                label=f"{search_color}_fuse",
                metadata={"desired_center": desired_center, "warped_shape": warped.shape[:2]},
            )

        if "board" in primitive_name:
            green_contour, green_bbox = self._largest_mask_contour(hsv, "green", min_area=500)
            if green_bbox is not None:
                desired = BOARD_SLOT_CENTERS.get(target_slot or "center", BOARD_SLOT_CENTERS["center"])
                desired_center = (desired[0] * width, desired[1] * height)
                center = self._bbox_center(green_bbox)
                return VisionTarget(
                    found=True,
                    camera_role="front",
                    confidence=0.70,
                    center_px=center,
                    error_px=(desired_center[0] - center[0], desired_center[1] - center[1]),
                    bbox_xywh=green_bbox,
                    label="board_green_strip",
                    metadata={"desired_center": desired_center},
                )
            return VisionTarget(found=False, camera_role="front", label="board")

        desired = TRANSFORMER_SLOT_CENTERS.get(target_slot or "left", TRANSFORMER_SLOT_CENTERS["left"])
        desired_center = (desired[0] * width, desired[1] * height)
        return VisionTarget(
            found=True,
            camera_role="front",
            confidence=0.55,
            center_px=desired_center,
            error_px=(0.0, 0.0),
            label="transformer_region",
            metadata={"desired_center": desired_center},
        )

