from __future__ import annotations

import os
import sys
from pathlib import Path


def _normalize_src_path(candidate: Path) -> Path:
    if candidate.name == "src":
        return candidate
    if (candidate / "src" / "lerobot").exists():
        return candidate / "src"
    return candidate


def _candidate_lerobot_src_paths() -> list[Path]:
    here = Path(__file__).resolve()
    candidates: list[Path] = []

    for env_name in ("LEROBOT_SRC", "LEROBOT_PATH", "LEROBOT_REPO"):
        raw = os.environ.get(env_name, "").strip()
        if raw:
            candidates.append(_normalize_src_path(Path(raw).expanduser()))

    for parent in here.parents:
        candidates.append(parent / "lerobot" / "src")
        candidates.append(parent / "LeRobot" / "src")
        if parent.name == "lerobot":
            candidates.append(parent / "src")

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        resolved = str(candidate.resolve(strict=False))
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(candidate)
    return unique


def ensure_lerobot_on_path() -> Path:
    try:
        import lerobot  # noqa: F401
        return Path(lerobot.__file__).resolve().parents[1]
    except ModuleNotFoundError:
        pass

    for candidate in _candidate_lerobot_src_paths():
        if not (candidate / "lerobot").exists():
            continue
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)
        try:
            import lerobot  # noqa: F401
            return candidate
        except ModuleNotFoundError:
            continue

    searched = ", ".join(str(path) for path in _candidate_lerobot_src_paths()[:4])
    raise ModuleNotFoundError(
        "Could not import 'lerobot'. Install LeRobot in this environment, set `LEROBOT_SRC=/path/to/lerobot/src`, "
        f"or place this repo beside a sibling lerobot checkout. Looked in: {searched}"
    ) from None
