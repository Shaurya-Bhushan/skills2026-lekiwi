from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from skills2026.perception.front import HSV_RANGES
from skills2026.perception.models import VisionTarget


@dataclass
class WristPerception:
    def _mask_color(self, hsv: np.ndarray, color_name: str) -> np.ndarray:
        lower, upper = HSV_RANGES[color_name]
        return cv2.inRange(hsv, np.array(lower), np.array(upper))

    def _largest_bbox(self, mask: np.ndarray, min_area: int = 120) -> tuple[int, int, int, int] | None:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best = None
        best_area = 0.0
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area or area <= best_area:
                continue
            best = cv2.boundingRect(contour)
            best_area = area
        return best

    def analyze(
        self,
        frame: np.ndarray,
        primitive_name: str,
        target_color: str | None = None,
    ) -> VisionTarget:
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        frame_h, frame_w = frame.shape[:2]
        desired_center = (frame_w / 2.0, frame_h / 2.0)

        if "fuse" in primitive_name:
            color_name = target_color or "green"
            bbox = self._largest_bbox(self._mask_color(hsv, color_name))
            if bbox is None:
                return VisionTarget(found=False, camera_role="wrist", label="fuse_precision")
            x, y, w, h = bbox
            center = (x + w / 2.0, y + h / 2.0)
            low_sat = cv2.inRange(hsv, np.array((0, 0, 80)), np.array((180, 70, 255)))
            low_sat_roi = low_sat[max(y - 4, 0) : min(y + h + 4, frame_h), max(x - 4, 0) : min(x + w + 4, frame_w)]
            bare_ratio = float(low_sat_roi.mean() / 255.0) if low_sat_roi.size else 1.0
            verified = bare_ratio < 0.18
            return VisionTarget(
                found=True,
                camera_role="wrist",
                confidence=0.85,
                center_px=center,
                error_px=(desired_center[0] - center[0], desired_center[1] - center[1]),
                bbox_xywh=bbox,
                label=f"{color_name}_fuse_precision",
                metadata={
                    "verified": verified,
                    "bare_ratio": bare_ratio,
                },
            )

        if "board" in primitive_name:
            green_mask = self._mask_color(hsv, "green")
            bbox = self._largest_bbox(green_mask, min_area=240)
            if bbox is None:
                return VisionTarget(found=False, camera_role="wrist", label="board_precision")
            x, y, w, h = bbox
            center = (x + w / 2.0, y + h / 2.0)
            verified = h < frame_h * 0.28
            return VisionTarget(
                found=True,
                camera_role="wrist",
                confidence=0.75,
                center_px=center,
                error_px=(desired_center[0] - center[0], desired_center[1] - center[1]),
                bbox_xywh=bbox,
                label="board_green_strip",
                metadata={"verified": verified},
            )

        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 60, 120)
        points = cv2.findNonZero(edges)
        if points is None:
            return VisionTarget(found=False, camera_role="wrist", label="transformer_precision")
        x, y, w, h = cv2.boundingRect(points)
        center = (x + w / 2.0, y + h / 2.0)
        return VisionTarget(
            found=True,
            camera_role="wrist",
            confidence=0.55,
            center_px=center,
            error_px=(desired_center[0] - center[0], desired_center[1] - center[1]),
            bbox_xywh=(x, y, w, h),
            label="transformer_bolt_region",
            metadata={"verified": False},
        )

