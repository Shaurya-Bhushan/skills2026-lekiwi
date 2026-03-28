from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TargetSelector:
    tracking_weight: float = 0.35
    apparent_area_bonus_weight: float = 1.5
    memory_expiry_frames: int = 5
    tracked_centers: dict[str, tuple[float, float]] = field(default_factory=dict)
    missing_counts: dict[str, int] = field(default_factory=dict)

    def _bbox_center(self, bbox: tuple[int, int, int, int]) -> tuple[float, float]:
        x, y, w, h = bbox
        return (x + w / 2.0, y + h / 2.0)

    def _bbox_area(self, bbox: tuple[int, int, int, int]) -> float:
        return float(bbox[2] * bbox[3])

    def _distance(self, a: tuple[float, float], b: tuple[float, float]) -> float:
        return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5

    def select_bbox(
        self,
        candidates: list[tuple[int, int, int, int]],
        desired_center: tuple[float, float],
        track_key: str,
        *,
        prefer_closer: bool = False,
        desired_slack_px: float = 80.0,
        tracking_slack_px: float = 60.0,
    ) -> tuple[tuple[int, int, int, int] | None, dict[str, Any]]:
        if not candidates:
            misses = self.missing_counts.get(track_key, 0) + 1
            self.missing_counts[track_key] = misses
            if misses >= self.memory_expiry_frames:
                self.tracked_centers.pop(track_key, None)
            return None, {
                "candidate_count": 0,
                "selected_via": "none",
                "track_key": track_key,
            }

        last_center = self.tracked_centers.get(track_key)
        candidate_info = []
        for bbox in candidates:
            center = self._bbox_center(bbox)
            candidate_info.append(
                {
                    "bbox": bbox,
                    "center": center,
                    "area": self._bbox_area(bbox),
                    "desired_distance": self._distance(center, desired_center),
                    "tracking_distance": self._distance(center, last_center) if last_center is not None else 0.0,
                }
            )

        min_desired_distance = min(info["desired_distance"] for info in candidate_info)
        desired_filtered = [
            info for info in candidate_info if info["desired_distance"] <= min_desired_distance + desired_slack_px
        ]
        selected_pool = desired_filtered

        selected_via = "desired_center"
        if last_center is not None and desired_filtered:
            min_tracking_distance = min(info["tracking_distance"] for info in desired_filtered)
            tracked_filtered = [
                info
                for info in desired_filtered
                if info["tracking_distance"] <= min_tracking_distance + tracking_slack_px
            ]
            if tracked_filtered:
                selected_pool = tracked_filtered
                selected_via = "tracked"

        if prefer_closer:
            best = max(
                selected_pool,
                key=lambda info: (
                    info["area"],
                    -info["desired_distance"],
                    -info["tracking_distance"],
                ),
            )
            selected_via = "closer_apparent" if selected_via == "desired_center" else f"{selected_via}+closer_apparent"
        else:
            def weighted_score(info: dict[str, Any]) -> tuple[float, float]:
                return (
                    info["desired_distance"] + (info["tracking_distance"] * self.tracking_weight),
                    -info["area"] * self.apparent_area_bonus_weight,
                )

            best = min(selected_pool, key=weighted_score)

        best_bbox = best["bbox"]
        best_center = best["center"]
        best_area = best["area"]
        best_tracking_distance = best["tracking_distance"]
        best_desired_distance = best["desired_distance"]

        self.tracked_centers[track_key] = best_center
        self.missing_counts[track_key] = 0

        return best_bbox, {
            "candidate_count": len(candidates),
            "selected_via": selected_via,
            "track_key": track_key,
            "desired_distance_px": best_desired_distance,
            "tracking_distance_px": best_tracking_distance,
            "apparent_area_px": best_area,
            "prefer_closer": prefer_closer,
        }


@dataclass
class VisionTarget:
    found: bool
    camera_role: str
    confidence: float = 0.0
    center_px: tuple[float, float] | None = None
    error_px: tuple[float, float] | None = None
    bbox_xywh: tuple[int, int, int, int] | None = None
    label: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DetectionBundle:
    coarse_target: VisionTarget | None = None
    fine_target: VisionTarget | None = None
    verified: bool = False
    message: str = ""
