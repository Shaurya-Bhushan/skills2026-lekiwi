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
    for candidate in _candidate_lerobot_src_paths():
        if not (candidate / "lerobot").exists():
            continue
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)
        existing = sys.modules.get("lerobot")
        if existing is not None:
            existing_file = getattr(existing, "__file__", "") or ""
            existing_paths = list(getattr(existing, "__path__", []) or [])
            if (existing_file or existing_paths) and candidate_str not in existing_file and not any(
                candidate_str in str(path) for path in existing_paths
            ):
                for module_name in list(sys.modules):
                    if module_name == "lerobot" or module_name.startswith("lerobot."):
                        del sys.modules[module_name]
        try:
            import lerobot  # noqa: F401
            return candidate
        except ModuleNotFoundError:
            continue

    try:
        import lerobot  # noqa: F401

        lerobot_file = getattr(lerobot, "__file__", None)
        if lerobot_file:
            return Path(lerobot_file).resolve().parents[1]
        lerobot_path = getattr(lerobot, "__path__", None)
        if lerobot_path:
            location = next(iter(lerobot_path), None)
            if location:
                candidate = Path(location).resolve()
                return candidate.parent if candidate.name == "lerobot" else _normalize_src_path(candidate)
        spec = getattr(lerobot, "__spec__", None)
        if spec and spec.submodule_search_locations:
            candidate = Path(next(iter(spec.submodule_search_locations))).resolve()
            return candidate.parent if candidate.name == "lerobot" else _normalize_src_path(candidate)
        return Path.cwd()
    except ModuleNotFoundError:
        pass

    searched = ", ".join(str(path) for path in _candidate_lerobot_src_paths()[:4])
    raise ModuleNotFoundError(
        "Could not import 'lerobot'. Install LeRobot in this environment, set `LEROBOT_SRC=/path/to/lerobot/src`, "
        f"or place this repo beside a sibling lerobot checkout. Looked in: {searched}"
    ) from None
