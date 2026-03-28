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
    MISSION_ZONE_CENTERS,
    PRIMITIVE_DEFAULT_TARGETS,
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

    def _largest_foreground_bbox(self, frame: np.ndarray, min_area: int = 350) -> tuple[int, int, int, int] | None:
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, mask = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        kernel = np.ones((5, 5), dtype=np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best_bbox = None
        best_area = 0.0
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area or area <= best_area:
                continue
            best_bbox = cv2.boundingRect(contour)
            best_area = area
        return best_bbox

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
            if primitive_name == "pick_fuse":
                desired = MISSION_ZONE_CENTERS.get(target_slot or "fuse_supply", MISSION_ZONE_CENTERS["fuse_supply"])
            else:
                desired = FUSE_SLOT_CENTERS.get(target_slot or target_color or search_color, FUSE_SLOT_CENTERS["green"])
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
            generic_bbox = self._largest_foreground_bbox(warped, min_area=300)
            bbox = green_bbox or generic_bbox
            if bbox is not None:
                if primitive_name == "pick_board":
                    desired = MISSION_ZONE_CENTERS.get(target_slot or "board_supply", MISSION_ZONE_CENTERS["board_supply"])
                else:
                    desired = BOARD_SLOT_CENTERS.get(target_slot or "center", BOARD_SLOT_CENTERS["center"])
                desired_center = (desired[0] * width, desired[1] * height)
                center = self._bbox_center(bbox)
                return VisionTarget(
                    found=True,
                    camera_role="front",
                    confidence=0.70 if green_bbox is not None else 0.58,
                    center_px=center,
                    error_px=(desired_center[0] - center[0], desired_center[1] - center[1]),
                    bbox_xywh=bbox,
                    label="board_green_strip" if green_bbox is not None else "board_foreground",
                    metadata={"desired_center": desired_center},
                )
            return VisionTarget(found=False, camera_role="front", label="board")

        if "transformer" in primitive_name:
            if primitive_name == "pick_transformer":
                desired = MISSION_ZONE_CENTERS.get(
                    target_slot or "transformer_supply",
                    MISSION_ZONE_CENTERS["transformer_supply"],
                )
            else:
                desired = TRANSFORMER_SLOT_CENTERS.get(target_slot or "left", TRANSFORMER_SLOT_CENTERS["left"])
            desired_center = (desired[0] * width, desired[1] * height)
            bbox = self._largest_foreground_bbox(warped, min_area=320)
            center = self._bbox_center(bbox) if bbox is not None else desired_center
            return VisionTarget(
                found=True,
                camera_role="front",
                confidence=0.60,
                center_px=center,
                error_px=(desired_center[0] - center[0], desired_center[1] - center[1]),
                bbox_xywh=bbox,
                label="transformer_region",
                metadata={"desired_center": desired_center},
            )

        generic_slot = PRIMITIVE_DEFAULT_TARGETS.get(primitive_name)
        if generic_slot:
            bbox = self._largest_foreground_bbox(warped, min_area=220)
            if bbox is None:
                return VisionTarget(found=False, camera_role="front", label=primitive_name)
            desired = MISSION_ZONE_CENTERS.get(target_slot or generic_slot, MISSION_ZONE_CENTERS[generic_slot])
            desired_center = (desired[0] * width, desired[1] * height)
            center = self._bbox_center(bbox)
            return VisionTarget(
                found=True,
                camera_role="front",
                confidence=0.68,
                center_px=center,
                error_px=(desired_center[0] - center[0], desired_center[1] - center[1]),
                bbox_xywh=bbox,
                label=primitive_name,
                metadata={"desired_center": desired_center},
            )

        return VisionTarget(found=False, camera_role="front", label=primitive_name)
