from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
PROFILES_DIR = PROJECT_ROOT / "profiles"
DATA_DIR = PROJECT_ROOT / "data"
DATASETS_DIR = DATA_DIR / "datasets"
LOGS_DIR = DATA_DIR / "logs"
DEFAULT_PROFILE_PATH = PROFILES_DIR / "default.json"


def ensure_workspace_dirs() -> None:
    for directory in (PROFILES_DIR, DATA_DIR, DATASETS_DIR, LOGS_DIR):
        directory.mkdir(parents=True, exist_ok=True)

