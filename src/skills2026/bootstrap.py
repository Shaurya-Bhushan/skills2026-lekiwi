from __future__ import annotations

import sys
from pathlib import Path


def ensure_lerobot_on_path() -> Path:
    candidate = Path(__file__).resolve().parents[3] / "lerobot" / "src"
    if candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

    try:
        import lerobot  # noqa: F401
    except ModuleNotFoundError:
        raise ModuleNotFoundError(
            "Could not import 'lerobot'. Install LeRobot in this environment or place this repo "
            f"beside a sibling lerobot checkout so it can be found at {candidate}."
        ) from None

    return candidate
