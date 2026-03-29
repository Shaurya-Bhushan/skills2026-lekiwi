from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from skills2026.perception.front import HSV_RANGES
from skills2026.perception.models import TargetSelector, VisionTarget


@dataclass
class WristPerception:
    selector: TargetSelector = field(default_factory=TargetSelector)

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

    def _mask_color(self, hsv: np.ndarray, color_name: str) -> np.ndarray:
        lower, upper = HSV_RANGES[color_name]
        return cv2.inRange(hsv, np.array(lower), np.array(upper))

    def _bboxes(self, mask: np.ndarray, min_area: int = 120) -> list[tuple[int, int, int, int]]:
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
        target_color: str | None = None,
    ) -> VisionTarget:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        frame_h, frame_w = frame.shape[:2]
        desired_center = (frame_w / 2.0, frame_h / 2.0)
        desired_slack_px = max(frame_w, frame_h) * 0.10
        tracking_slack_px = max(frame_w, frame_h) * 0.08
        prefer_closer = primitive_name.startswith(("pick_", "remove_"))

        if "fuse" in primitive_name:
            color_name = target_color or "green"
            candidates = self._bboxes(self._mask_color(hsv, color_name))
            bbox, selection = self.selector.select_bbox(
                candidates,
                desired_center,
                f"{primitive_name}:{color_name}:wrist",
                prefer_closer=prefer_closer,
                desired_slack_px=desired_slack_px,
                tracking_slack_px=tracking_slack_px,
            )
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
                    **selection,
                    "verified": verified,
                    "bare_ratio": bare_ratio,
                },
            )

        if "board" in primitive_name:
            green_mask = self._mask_color(hsv, "green")
            candidates = self._bboxes(green_mask, min_area=240)
            bbox, selection = self.selector.select_bbox(
                candidates,
                desired_center,
                f"{primitive_name}:board:wrist",
                prefer_closer=prefer_closer,
                desired_slack_px=desired_slack_px,
                tracking_slack_px=tracking_slack_px,
            )
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
                metadata={**selection, "verified": verified},
            )

        if any(
            token in primitive_name
            for token in ("debris", "supply", "worker", "steve", "fan", "autonomous_bot", "beam", "breaker", "final_robot", "transformer")
        ):
            mask = self._foreground_mask(frame)
            candidates = self._bboxes(mask, min_area=180)
            bbox, selection = self.selector.select_bbox(
                candidates,
                desired_center,
                f"{primitive_name}:generic:wrist",
                prefer_closer=prefer_closer,
                desired_slack_px=desired_slack_px,
                tracking_slack_px=tracking_slack_px,
            )
            if bbox is None:
                return VisionTarget(found=False, camera_role="wrist", label=f"{primitive_name}_precision")
            x, y, w, h = bbox
            center = (x + w / 2.0, y + h / 2.0)
            error_px = (desired_center[0] - center[0], desired_center[1] - center[1])
            verified = abs(error_px[0]) <= 18 and abs(error_px[1]) <= 18
            return VisionTarget(
                found=True,
                camera_role="wrist",
                confidence=0.70,
                center_px=center,
                error_px=error_px,
                bbox_xywh=bbox,
                label=f"{primitive_name}_precision",
                metadata={**selection, "verified": verified},
            )

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
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
