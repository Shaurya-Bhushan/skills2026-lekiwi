from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from skills2026.paths import LOGS_DIR, ensure_workspace_dirs

MANIFEST_FILENAME = "skills2026_dataset_manifest.json"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _stable_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def _camera_snapshot(camera) -> dict[str, Any]:
    calibration_payload = {
        "calibrated": camera.calibration.calibrated,
        "homography": camera.calibration.homography,
        "roi": camera.calibration.roi,
    }
    return {
        "role": camera.role,
        "source_id": str(camera.source_id),
        "width": camera.width,
        "height": camera.height,
        "fps": camera.fps,
        "enabled": camera.enabled,
        "calibration": calibration_payload,
        "calibration_signature": _stable_hash(calibration_payload),
    }


def profile_snapshot(profile) -> dict[str, Any]:
    cameras = {
        role: _camera_snapshot(camera)
        for role, camera in sorted(profile.cameras.items())
    }
    return {
        "profile_name": profile.profile_name,
        "mode": profile.mode,
        "robot_id": profile.robot_id,
        "cameras": cameras,
    }


def profile_signature(profile) -> str:
    return _stable_hash(profile_snapshot(profile))


def pickup_setup_signature(profile) -> str:
    servo_snapshot = {
        name: {
            "x_gains": servo.x_gains,
            "y_gains": servo.y_gains,
            "tolerance_px": servo.tolerance_px,
            "max_step": servo.max_step,
        }
        for name, servo in sorted(profile.servo.items())
    }
    payload = {
        "profile": profile_snapshot(profile),
        "service_poses": profile.service_poses,
        "servo": servo_snapshot,
    }
    return _stable_hash(payload)


@dataclass
class ReplayApproval:
    episode_index: int
    status: str
    reviewed_at: str
    profile_name: str
    profile_signature: str
    notes: str = ""
    report_path: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ReplayApproval":
        return cls(
            episode_index=int(raw["episode_index"]),
            status=str(raw["status"]),
            reviewed_at=str(raw["reviewed_at"]),
            profile_name=str(raw["profile_name"]),
            profile_signature=str(raw["profile_signature"]),
            notes=str(raw.get("notes", "")),
            report_path=str(raw.get("report_path", "")),
        )


@dataclass
class PickupGateStamp:
    primitive_name: str
    suite_name: str
    scenario_name: str
    report_path: str
    report_created_at: str
    stamped_at: str
    passed: bool

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PickupGateStamp":
        return cls(
            primitive_name=str(raw["primitive_name"]),
            suite_name=str(raw["suite_name"]),
            scenario_name=str(raw["scenario_name"]),
            report_path=str(raw["report_path"]),
            report_created_at=str(raw["report_created_at"]),
            stamped_at=str(raw["stamped_at"]),
            passed=bool(raw["passed"]),
        )


@dataclass
class DatasetManifest:
    schema_version: int
    dataset_name: str
    primitive_name: str
    profile_name: str
    profile_signature: str
    profile_snapshot: dict[str, Any]
    created_at: str
    updated_at: str
    recorded_episode_count: int = 0
    replay_approvals: dict[str, ReplayApproval] = field(default_factory=dict)
    pickup_validation: PickupGateStamp | None = None
    training_runs: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def create(cls, profile, dataset_name: str, primitive_name: str) -> "DatasetManifest":
        created_at = _now_iso()
        return cls(
            schema_version=1,
            dataset_name=dataset_name,
            primitive_name=primitive_name,
            profile_name=profile.profile_name,
            profile_signature=profile_signature(profile),
            profile_snapshot=profile_snapshot(profile),
            created_at=created_at,
            updated_at=created_at,
        )

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "DatasetManifest":
        approvals = {
            str(key): ReplayApproval.from_dict(value)
            for key, value in raw.get("replay_approvals", {}).items()
        }
        pickup_raw = raw.get("pickup_validation")
        pickup_validation = (
            PickupGateStamp.from_dict(pickup_raw)
            if isinstance(pickup_raw, dict)
            else None
        )
        return cls(
            schema_version=int(raw.get("schema_version", 1)),
            dataset_name=str(raw["dataset_name"]),
            primitive_name=str(raw["primitive_name"]),
            profile_name=str(raw["profile_name"]),
            profile_signature=str(raw["profile_signature"]),
            profile_snapshot=dict(raw.get("profile_snapshot", {})),
            created_at=str(raw.get("created_at", _now_iso())),
            updated_at=str(raw.get("updated_at", _now_iso())),
            recorded_episode_count=int(raw.get("recorded_episode_count", 0)),
            replay_approvals=approvals,
            pickup_validation=pickup_validation,
            training_runs=list(raw.get("training_runs", [])),
        )

    @property
    def approved_episode_indices(self) -> list[int]:
        approved = [
            approval.episode_index
            for approval in self.replay_approvals.values()
            if approval.status == "pass"
        ]
        return sorted(set(approved))

    @property
    def failed_episode_indices(self) -> list[int]:
        failed = [
            approval.episode_index
            for approval in self.replay_approvals.values()
            if approval.status == "fail"
        ]
        return sorted(set(failed))

    @property
    def missing_review_episode_indices(self) -> list[int]:
        reviewed = set(self.approved_episode_indices + self.failed_episode_indices)
        return [index for index in range(self.recorded_episode_count) if index not in reviewed]

    @property
    def all_recorded_episodes_approved(self) -> bool:
        return (
            self.recorded_episode_count > 0
            and not self.failed_episode_indices
            and not self.missing_review_episode_indices
            and len(self.approved_episode_indices) == self.recorded_episode_count
        )

    @property
    def act_ready(self) -> bool:
        return bool(
            self.all_recorded_episodes_approved
            and self.pickup_validation is not None
            and self.pickup_validation.passed
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "dataset_name": self.dataset_name,
            "primitive_name": self.primitive_name,
            "profile_name": self.profile_name,
            "profile_signature": self.profile_signature,
            "profile_snapshot": self.profile_snapshot,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "recorded_episode_count": self.recorded_episode_count,
            "replay_approvals": {
                key: asdict(value)
                for key, value in sorted(self.replay_approvals.items(), key=lambda item: int(item[0]))
            },
            "pickup_validation": asdict(self.pickup_validation) if self.pickup_validation else None,
            "training_runs": self.training_runs,
            "act_ready": self.act_ready,
            "approved_episode_indices": self.approved_episode_indices,
            "failed_episode_indices": self.failed_episode_indices,
            "missing_review_episode_indices": self.missing_review_episode_indices,
        }

    def sync_episode_count(self, episode_count: int) -> None:
        self.recorded_episode_count = max(int(episode_count), 0)
        self.updated_at = _now_iso()

    def mark_replay_approval(
        self,
        *,
        episode_index: int,
        status: str,
        profile,
        notes: str = "",
        report_path: str = "",
    ) -> None:
        normalized_status = status.strip().lower()
        if normalized_status not in {"pass", "fail"}:
            raise ValueError(f"Unsupported replay approval status '{status}'.")
        self.replay_approvals[str(int(episode_index))] = ReplayApproval(
            episode_index=int(episode_index),
            status=normalized_status,
            reviewed_at=_now_iso(),
            profile_name=profile.profile_name,
            profile_signature=profile_signature(profile),
            notes=notes,
            report_path=report_path,
        )
        self.updated_at = _now_iso()

    def mark_pickup_validation(self, stamp: PickupGateStamp) -> None:
        self.pickup_validation = stamp
        self.updated_at = _now_iso()

    def record_training_run(self, details: dict[str, Any]) -> None:
        self.training_runs.append(details)
        self.updated_at = _now_iso()


def dataset_manifest_path(dataset_root: Path) -> Path:
    return dataset_root / MANIFEST_FILENAME


def load_dataset_manifest(dataset_root: Path) -> DatasetManifest | None:
    manifest_path = dataset_manifest_path(dataset_root)
    if not manifest_path.exists():
        return None
    return DatasetManifest.from_dict(json.loads(manifest_path.read_text()))


def save_dataset_manifest(dataset_root: Path, manifest: DatasetManifest) -> Path:
    ensure_workspace_dirs()
    dataset_root.mkdir(parents=True, exist_ok=True)
    manifest.updated_at = _now_iso()
    target = dataset_manifest_path(dataset_root)
    target.write_text(json.dumps(manifest.to_dict(), indent=2, sort_keys=True))
    return target


def dataset_has_existing_content(dataset_root: Path) -> bool:
    if not dataset_root.exists():
        return False
    for child in dataset_root.iterdir():
        if child.name == MANIFEST_FILENAME:
            continue
        return True
    return False


def dataset_total_episodes(dataset_root: Path) -> int:
    info_path = dataset_root / "meta" / "info.json"
    if not info_path.exists():
        return 0
    raw = json.loads(info_path.read_text())
    return int(raw.get("total_episodes", 0))


def sync_manifest_from_dataset(dataset_root: Path, manifest: DatasetManifest) -> DatasetManifest:
    manifest.sync_episode_count(dataset_total_episodes(dataset_root))
    return manifest


def ensure_manifest_matches_profile(
    manifest: DatasetManifest,
    profile,
    *,
    dataset_name: str | None = None,
    primitive_name: str | None = None,
) -> None:
    expected_signature = profile_signature(profile)
    if dataset_name and manifest.dataset_name != dataset_name:
        raise ValueError(
            f"Dataset manifest belongs to '{manifest.dataset_name}', not '{dataset_name}'."
        )
    if primitive_name and manifest.primitive_name != primitive_name:
        raise ValueError(
            f"Dataset manifest was recorded for '{manifest.primitive_name}', not '{primitive_name}'."
        )
    if manifest.profile_name != profile.profile_name:
        raise ValueError(
            f"Dataset manifest belongs to profile '{manifest.profile_name}', not '{profile.profile_name}'."
        )
    if manifest.profile_signature != expected_signature:
        raise ValueError(
            "Dataset manifest does not match the active profile's camera IDs/calibration. "
            "Use the original profile or re-record the dataset under the current setup."
        )


@dataclass
class ReplayValidationReport:
    dataset_name: str
    primitive_name: str
    profile_name: str
    profile_signature: str
    episode_index: int
    created_at: str
    result: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_replay_report_path(dataset_name: str, episode_index: int) -> Path:
    ensure_workspace_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = dataset_name.replace("/", "_")
    return LOGS_DIR / f"replay_validation_{safe_name}_ep{episode_index:03d}_{timestamp}.json"


def save_replay_validation_report(report: ReplayValidationReport, target: Path) -> Path:
    ensure_workspace_dirs()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return target


def pickup_gate_primitive_for_training(primitive_name: str) -> str | None:
    if "fuse" in primitive_name:
        return "pick_fuse"
    if "board" in primitive_name:
        return "pick_board"
    if "transformer" in primitive_name:
        return "pick_transformer"
    if "steve" in primitive_name:
        return "pick_steve"
    if "debris" in primitive_name:
        return "pick_debris"
    return None


def latest_passing_pickup_stamp(profile, primitive_name: str) -> PickupGateStamp | None:
    required_pickup_primitive = pickup_gate_primitive_for_training(primitive_name)
    if required_pickup_primitive is None:
        return None

    expected_signature = pickup_setup_signature(profile)
    candidates = sorted(LOGS_DIR.glob("pickup_validation_*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    for candidate in candidates:
        try:
            report = json.loads(candidate.read_text())
        except json.JSONDecodeError:
            continue
        if report.get("profile_name") != profile.profile_name:
            continue
        if report.get("profile_signature") != expected_signature:
            continue
        for summary in report.get("scenarios", []):
            scenario = summary.get("scenario", {})
            if scenario.get("primitive_name") != required_pickup_primitive:
                continue
            attempts = int(summary.get("attempts", 0))
            successes = int(summary.get("successes", 0))
            if attempts <= 0:
                return None
            if successes != attempts:
                return None
            return PickupGateStamp(
                primitive_name=required_pickup_primitive,
                suite_name=str(report.get("suite_name", "")),
                scenario_name=str(scenario.get("name", "")),
                report_path=str(candidate),
                report_created_at=str(report.get("created_at", "")),
                stamped_at=_now_iso(),
                passed=True,
            )
    return None


def describe_replay_gate_failure(manifest: DatasetManifest) -> str:
    details: list[str] = []
    if manifest.failed_episode_indices:
        details.append(
            "failed episodes: " + ", ".join(str(index) for index in manifest.failed_episode_indices)
        )
    if manifest.missing_review_episode_indices:
        details.append(
            "missing replay review: " + ", ".join(str(index) for index in manifest.missing_review_episode_indices)
        )
    if not details:
        details.append("dataset has no approved replay episodes yet")
    return "; ".join(details)
