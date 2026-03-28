from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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

