from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from skills2026.bootstrap import ensure_lerobot_on_path
from skills2026.paths import DATASETS_DIR

try:  # pragma: no cover - depends on the active runtime
    import torch
except ModuleNotFoundError as exc:  # pragma: no cover - runtime only
    torch = None
    ACT_IMPORT_ERROR = exc
else:  # pragma: no cover - runtime only
    ACT_IMPORT_ERROR = None


# Lazy-loaded LeRobot runtime symbols. Keep this module importable even when the
# user only wants the OpenCV + FSM path.
LeRobotDatasetMetadata: Any = None
ACTConfig: Any = None
ACTPolicy: Any = None
make_pre_post_processors: Any = None
build_inference_frame: Any = None
make_robot_action: Any = None
LeKiwiIO: Any = None
SafetyController: Any = None


def _load_lerobot_runtime() -> None:
    global LeRobotDatasetMetadata
    global ACTConfig
    global ACTPolicy
    global make_pre_post_processors
    global build_inference_frame
    global make_robot_action
    global LeKiwiIO
    global SafetyController

    needs_lerobot = any(
        value is None
        for value in (
            LeRobotDatasetMetadata,
            ACTConfig,
            ACTPolicy,
            make_pre_post_processors,
            build_inference_frame,
            make_robot_action,
            LeKiwiIO,
            SafetyController,
        )
    )
    if not needs_lerobot:
        return

    ensure_lerobot_on_path()

    if LeKiwiIO is None:
        from skills2026.robot.lekiwi_io import LeKiwiIO as _LeKiwiIO

        LeKiwiIO = _LeKiwiIO
    if SafetyController is None:
        from skills2026.robot.safety import SafetyController as _SafetyController

        SafetyController = _SafetyController
    if LeRobotDatasetMetadata is None:
        from lerobot.datasets.dataset_metadata import LeRobotDatasetMetadata as _LeRobotDatasetMetadata

        LeRobotDatasetMetadata = _LeRobotDatasetMetadata
    if ACTConfig is None:
        from lerobot.policies.act.configuration_act import ACTConfig as _ACTConfig

        ACTConfig = _ACTConfig
    if ACTPolicy is None:
        from lerobot.policies.act.modeling_act import ACTPolicy as _ACTPolicy

        ACTPolicy = _ACTPolicy
    if make_pre_post_processors is None:
        from lerobot.policies.factory import make_pre_post_processors as _make_pre_post_processors

        make_pre_post_processors = _make_pre_post_processors
    if build_inference_frame is None:
        from lerobot.policies.utils import build_inference_frame as _build_inference_frame

        build_inference_frame = _build_inference_frame
    if make_robot_action is None:
        from lerobot.policies.utils import make_robot_action as _make_robot_action

        make_robot_action = _make_robot_action


def _require_act_runtime() -> None:
    if ACT_IMPORT_ERROR is not None:
        missing = ACT_IMPORT_ERROR.name or "unknown dependency"
        raise RuntimeError(
            "ACT support needs the full LeRobot runtime in your active environment "
            f"(missing dependency: {missing}). Activate the LeRobot env, ensure ACT dependencies are installed, "
            "and reinstall this repo in that same environment."
        ) from ACT_IMPORT_ERROR

    try:
        _load_lerobot_runtime()
    except ModuleNotFoundError as exc:  # pragma: no cover - runtime only
        missing = exc.name or "unknown dependency"
        raise RuntimeError(
            "ACT support needs the full LeRobot runtime in your active environment "
            f"(missing dependency: {missing}). Activate the LeRobot env, ensure ACT dependencies are installed, "
            "and reinstall this repo in that same environment."
        ) from exc


def _select_device(device_name: str | None) -> "torch.device":
    if device_name:
        return torch.device(device_name)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


@dataclass
class ACTRunner:
    io: Any
    safety: Any
    policy: Any
    preprocess: Any
    postprocess: Any
    dataset_meta: Any
    device: Any
    task: str

    @classmethod
    def from_profile(
        cls,
        profile,
        primitive_name: str,
        policy_path: str,
        dataset_name: str | None = None,
        task: str | None = None,
        device_name: str | None = None,
    ) -> "ACTRunner":
        _require_act_runtime()

        if not policy_path:
            raise ValueError(
                "ACT backend requires `--policy-path` pointing to a trained ACT checkpoint or Hub repo."
            )

        resolved_dataset_name = dataset_name or f"{profile.profile_name}_{primitive_name}"
        dataset_root = DATASETS_DIR / resolved_dataset_name
        if not dataset_root.exists():
            raise FileNotFoundError(
                f"No local dataset metadata found at {dataset_root}. "
                "Record data for this primitive first or pass `--dataset-name`."
            )

        device = _select_device(device_name)
        config = ACTConfig.from_pretrained(pretrained_name_or_path=policy_path)
        config.device = str(device)
        policy = ACTPolicy.from_pretrained(policy_path, config=config)

        dataset_meta = LeRobotDatasetMetadata(
            repo_id=f"skills2026/{resolved_dataset_name}",
            root=dataset_root,
        )

        preprocess, postprocess = make_pre_post_processors(
            policy_cfg=policy.config,
            pretrained_path=policy_path,
            dataset_stats=dataset_meta.stats,
            preprocessor_overrides={"device_processor": {"device": str(device)}},
        )

        return cls(
            io=LeKiwiIO(profile),
            safety=SafetyController(),
            policy=policy,
            preprocess=preprocess,
            postprocess=postprocess,
            dataset_meta=dataset_meta,
            device=device,
            task=task or primitive_name,
        )

    def run(self, max_cycles: int = 500) -> int:
        _require_act_runtime()

        self.policy.reset()
        self.io.connect()
        last_observation = None
        try:
            for _ in range(max_cycles):
                loop_start = time.perf_counter()
                observation = self.io.get_observation()
                last_observation = observation
                current_pose = self.io.arm_pose_from_observation(observation)

                try:
                    obs_frame = build_inference_frame(
                        observation=observation,
                        device=self.device,
                        ds_features=self.dataset_meta.features,
                        task=self.task,
                        robot_type=self.dataset_meta.robot_type,
                    )
                    obs_frame = self.preprocess(obs_frame)
                    action_tensor = self.policy.select_action(obs_frame)
                    action_tensor = self.postprocess(action_tensor)
                    robot_action = make_robot_action(action_tensor, self.dataset_meta.features)
                    safe_action = self.safety.apply(robot_action, current_pose)
                except Exception as exc:
                    raise RuntimeError(
                        "ACT failed while converting a LeKiwi observation into an action. "
                        "Verify the checkpoint, dataset stats, camera keys, and action layout."
                    ) from exc

                self.io.send_action(safe_action)

                dt_s = time.perf_counter() - loop_start
                sleep_s = max((1.0 / self.io.profile.budget.loop_hz) - dt_s, 0.0)
                time.sleep(sleep_s)
            self.io.stop_base(last_observation)
            return 0
        except Exception:
            self.io.stop_base(last_observation)
            raise
        finally:
            self.io.disconnect()
