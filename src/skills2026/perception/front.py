from __future__ import annotations

from dataclasses import dataclass, field
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
from skills2026.perception.models import TargetSelector, VisionTarget


HSV_RANGES = {
    "orange": ((5, 80, 80), (20, 255, 255)),
    "green": ((35, 50, 50), (95, 255, 255)),
    "blue": ((95, 50, 50), (135, 255, 255)),
    "black": ((0, 0, 0), (180, 255, 80)),
}


@dataclass
class FrontPerception:
    canonical_size: tuple[int, int] = DEFAULT_CANONICAL_SIZE
    selector: TargetSelector = field(default_factory=TargetSelector)

    def _maybe_warp(self, frame: np.ndarray, calibration: dict[str, Any] | None) -> np.ndarray:
        if calibration and calibration.get("calibrated") and calibration.get("homography"):
            return warp_frame(frame, calibration["homography"], self.canonical_size)
        return frame

    def _mask_bboxes(
        self,
        hsv: np.ndarray,
        color_name: str,
        min_area: int = 250,
    ) -> list[tuple[int, int, int, int]]:
        lower, upper = HSV_RANGES[color_name]
        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes: list[tuple[int, int, int, int]] = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area:
                continue
            boxes.append(cv2.boundingRect(contour))
        return boxes

    def _bbox_center(self, bbox: tuple[int, int, int, int]) -> tuple[float, float]:
        x, y, w, h = bbox
        return (x + w / 2.0, y + h / 2.0)

    def _foreground_mask(self, frame: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
        blur = cv2.GaussianBlur(clahe, (5, 5), 0)
        _, otsu_mask = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        adaptive_mask = cv2.adaptiveThreshold(
            clahe,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            31,
            6,
        )
        edge_mask = cv2.Canny(clahe, 45, 120)
        edge_mask = cv2.dilate(edge_mask, np.ones((3, 3), dtype=np.uint8), iterations=1)
        mask = cv2.bitwise_or(otsu_mask, adaptive_mask)
        mask = cv2.bitwise_or(mask, edge_mask)
        kernel = np.ones((5, 5), dtype=np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        return mask

    def _foreground_bboxes(self, frame: np.ndarray, min_area: int = 350) -> list[tuple[int, int, int, int]]:
        mask = self._foreground_mask(frame)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes: list[tuple[int, int, int, int]] = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area:
                continue
            boxes.append(cv2.boundingRect(contour))
        return boxes

    def analyze(
        self,
        frame: np.ndarray,
        primitive_name: str,
        calibration: dict[str, Any] | None = None,
        target_color: str | None = None,
        target_slot: str | None = None,
    ) -> VisionTarget:
        warped = self._maybe_warp(frame, calibration)
        frame_h, frame_w = warped.shape[:2]
        hsv = cv2.cvtColor(warped, cv2.COLOR_BGR2HSV)
        width, height = frame_w, frame_h
        desired_slack_px = max(frame_w, frame_h) * 0.12
        tracking_slack_px = max(frame_w, frame_h) * 0.10

        if "fuse" in primitive_name:
            search_color = target_color or "black"
            if primitive_name == "pick_fuse":
                desired = MISSION_ZONE_CENTERS.get(target_slot or "fuse_supply", MISSION_ZONE_CENTERS["fuse_supply"])
            else:
                desired = FUSE_SLOT_CENTERS.get(target_slot or target_color or search_color, FUSE_SLOT_CENTERS["green"])
            desired_center = (desired[0] * width, desired[1] * height)
            candidates = self._mask_bboxes(hsv, search_color, min_area=180)
            bbox, selection = self.selector.select_bbox(
                candidates,
                desired_center,
                f"{primitive_name}:{search_color}",
                prefer_closer=primitive_name.startswith(("pick_", "remove_")),
                desired_slack_px=desired_slack_px,
                tracking_slack_px=tracking_slack_px,
            )
            if bbox is None:
                return VisionTarget(found=False, camera_role="front", label="fuse")
            center = self._bbox_center(bbox)
            return VisionTarget(
                found=True,
                camera_role="front",
                confidence=0.75,
                center_px=center,
                error_px=(desired_center[0] - center[0], desired_center[1] - center[1]),
                bbox_xywh=bbox,
                label=f"{search_color}_fuse",
                metadata={"desired_center": desired_center, "warped_shape": warped.shape[:2], **selection},
            )

        if "board" in primitive_name:
            if primitive_name == "pick_board":
                desired = MISSION_ZONE_CENTERS.get(target_slot or "board_supply", MISSION_ZONE_CENTERS["board_supply"])
            else:
                desired = BOARD_SLOT_CENTERS.get(target_slot or "center", BOARD_SLOT_CENTERS["center"])
            desired_center = (desired[0] * width, desired[1] * height)
            green_candidates = self._mask_bboxes(hsv, "green", min_area=500)
            green_bbox, green_selection = self.selector.select_bbox(
                green_candidates,
                desired_center,
                f"{primitive_name}:board_green",
                prefer_closer=primitive_name.startswith(("pick_", "remove_")),
                desired_slack_px=desired_slack_px,
                tracking_slack_px=tracking_slack_px,
            )
            generic_candidates = self._foreground_bboxes(warped, min_area=300)
            generic_bbox, generic_selection = self.selector.select_bbox(
                generic_candidates,
                desired_center,
                f"{primitive_name}:board_foreground",
                prefer_closer=primitive_name.startswith(("pick_", "remove_")),
                desired_slack_px=desired_slack_px,
                tracking_slack_px=tracking_slack_px,
            )
            bbox = green_bbox or generic_bbox
            if bbox is not None:
                center = self._bbox_center(bbox)
                selection = green_selection if green_bbox is not None else generic_selection
                return VisionTarget(
                    found=True,
                    camera_role="front",
                    confidence=0.70 if green_bbox is not None else 0.58,
                    center_px=center,
                    error_px=(desired_center[0] - center[0], desired_center[1] - center[1]),
                    bbox_xywh=bbox,
                    label="board_green_strip" if green_bbox is not None else "board_foreground",
                    metadata={"desired_center": desired_center, **selection},
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
            candidates = self._foreground_bboxes(warped, min_area=320)
            bbox, selection = self.selector.select_bbox(
                candidates,
                desired_center,
                f"{primitive_name}:transformer",
                prefer_closer=primitive_name.startswith(("pick_", "remove_")),
                desired_slack_px=desired_slack_px,
                tracking_slack_px=tracking_slack_px,
            )
            if bbox is None:
                return VisionTarget(found=False, camera_role="front", label="transformer_region")
            center = self._bbox_center(bbox)
            return VisionTarget(
                found=True,
                camera_role="front",
                confidence=0.60,
                center_px=center,
                error_px=(desired_center[0] - center[0], desired_center[1] - center[1]),
                bbox_xywh=bbox,
                label="transformer_region",
                metadata={"desired_center": desired_center, **selection},
            )

        generic_slot = PRIMITIVE_DEFAULT_TARGETS.get(primitive_name)
        if generic_slot or primitive_name.startswith("pick_"):
            desired_key = target_slot or generic_slot
            if primitive_name == "pick_debris" or desired_key is None:
                desired_center = (width / 2.0, height / 2.0)
            else:
                fallback_key = generic_slot or desired_key
                desired = MISSION_ZONE_CENTERS.get(desired_key, MISSION_ZONE_CENTERS[fallback_key])
                desired_center = (desired[0] * width, desired[1] * height)
            candidates = self._foreground_bboxes(warped, min_area=220)
            bbox, selection = self.selector.select_bbox(
                candidates,
                desired_center,
                f"{primitive_name}:generic",
                prefer_closer=primitive_name.startswith(("pick_", "remove_")),
                desired_slack_px=desired_slack_px,
                tracking_slack_px=tracking_slack_px,
            )
            if bbox is None:
                return VisionTarget(found=False, camera_role="front", label=primitive_name)
            center = self._bbox_center(bbox)
            return VisionTarget(
                found=True,
                camera_role="front",
                confidence=0.68,
                center_px=center,
                error_px=(desired_center[0] - center[0], desired_center[1] - center[1]),
                bbox_xywh=bbox,
                label=primitive_name,
                metadata={"desired_center": desired_center, **selection},
            )

        return VisionTarget(found=False, camera_role="front", label=primitive_name)
