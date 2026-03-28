from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from skills2026.bootstrap import ensure_lerobot_on_path
from skills2026.paths import DATASETS_DIR
from skills2026.robot.lekiwi_io import LeKiwiIO
from skills2026.robot.safety import SafetyController

ensure_lerobot_on_path()

try:  # pragma: no cover - depends on active lerobot runtime
    import torch
    from lerobot.datasets.dataset_metadata import LeRobotDatasetMetadata
    from lerobot.policies.act.configuration_act import ACTConfig
    from lerobot.policies.act.modeling_act import ACTPolicy
    from lerobot.policies.factory import make_pre_post_processors
    from lerobot.policies.utils import build_inference_frame, make_robot_action
except ModuleNotFoundError as exc:  # pragma: no cover - runtime only
    ACT_IMPORT_ERROR = exc
else:  # pragma: no cover - runtime only
    ACT_IMPORT_ERROR = None


def _require_act_runtime() -> None:
    if ACT_IMPORT_ERROR is None:
        return
    missing = ACT_IMPORT_ERROR.name or "unknown dependency"
    raise RuntimeError(
        "ACT support needs the full LeRobot runtime in your active environment "
        f"(missing dependency: {missing}). Activate the LeRobot env, ensure ACT dependencies are installed, "
        "and reinstall this repo in that same environment."
    ) from ACT_IMPORT_ERROR


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
    io: LeKiwiIO
    safety: SafetyController
    policy: object
    preprocess: object
    postprocess: object
    dataset_meta: object
    device: object
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
        try:
            for _ in range(max_cycles):
                loop_start = time.perf_counter()
                observation = self.io.get_observation()
                current_pose = self.io.arm_pose_from_observation(observation)

                try:
                    obs_frame = build_inference_frame(
                        observation=observation,
                        device=self.device,
                        ds_features=self.dataset_meta.features,
                        task=self.task,
                        robot_type=self.dataset_meta.robot_type,
                    )
                except Exception as exc:
                    raise RuntimeError(
                        "ACT could not build an inference frame from the current LeKiwi observation. "
                        "Make sure the checkpoint and dataset were recorded with the same front/wrist camera keys "
                        "and the same action layout."
                    ) from exc

                obs_frame = self.preprocess(obs_frame)
                action_tensor = self.policy.select_action(obs_frame)
                action_tensor = self.postprocess(action_tensor)
                robot_action = make_robot_action(action_tensor, self.dataset_meta.features)
                safe_action = self.safety.apply(robot_action, current_pose)
                self.io.send_action(safe_action)

                dt_s = time.perf_counter() - loop_start
                sleep_s = max((1.0 / self.io.profile.budget.loop_hz) - dt_s, 0.0)
                time.sleep(sleep_s)
            self.io.stop_base()
            return 0
        finally:
            self.io.disconnect()
