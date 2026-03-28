from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from skills2026.bootstrap import ensure_lerobot_on_path
from skills2026.robot.safety import SafetyController

if TYPE_CHECKING:
    from skills2026.robot.lekiwi_io import LeKiwiIO

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SmolVLAAvailability:
    ready: bool
    detail: str


def inspect_smolvla_runtime() -> SmolVLAAvailability:
    try:
        ensure_lerobot_on_path()
        import torch  # noqa: F401
        from lerobot.datasets.feature_utils import hw_to_dataset_features  # noqa: F401
        from lerobot.policies.factory import make_pre_post_processors  # noqa: F401
        from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy  # noqa: F401
        from lerobot.policies.utils import build_inference_frame, make_robot_action  # noqa: F401

        return SmolVLAAvailability(True, "runtime ready")
    except ModuleNotFoundError as exc:
        return SmolVLAAvailability(False, f"missing dependency: {exc.name}")
    except Exception as exc:  # pragma: no cover - advisory path
        return SmolVLAAvailability(False, f"runtime import failed: {exc}")


def _resolve_device(torch_module, requested: str) -> str:
    if requested != "auto":
        return requested
    if torch_module.cuda.is_available():
        return "cuda"
    if hasattr(torch_module.backends, "mps") and torch_module.backends.mps.is_available():
        return "mps"
    return "cpu"


@dataclass
class SmolVLARunner:
    io: Any
    safety: SafetyController
    primitive_name: str
    task: str
    model_id: str
    device_name: str
    rename_map: dict[str, str]
    policy: Any
    preprocess: Any
    postprocess: Any
    dataset_features: dict[str, dict]
    torch: Any

    @classmethod
    def from_profile(
        cls,
        profile,
        primitive_name: str,
        task: str | None = None,
        model_id: str | None = None,
        device_name: str | None = None,
        allow_base_model: bool = False,
    ) -> "SmolVLARunner":
        status = inspect_smolvla_runtime()
        if not status.ready:
            raise RuntimeError(
                f"SmolVLA backend is unavailable: {status.detail}. "
                'Activate the LeRobot env and install `pip install -e ".[smolvla]"` in the lerobot repo.'
            )

        ensure_lerobot_on_path()
        import torch
        from lerobot.configs.types import FeatureType
        from lerobot.datasets.feature_utils import hw_to_dataset_features
        from lerobot.policies.factory import make_pre_post_processors
        from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy

        settings = profile.policy.smolvla
        selected_model = model_id or settings.model_id
        selected_device = _resolve_device(torch, device_name or settings.device)
        selected_task = task or settings.task_prompts.get(primitive_name, primitive_name.replace("_", " "))

        if settings.require_finetuned_checkpoint and selected_model == "lerobot/smolvla_base" and not allow_base_model:
            raise ValueError(
                "SmolVLA is wired up for LeKiwi, but the base checkpoint is not a LeKiwi-ready policy. "
                "Use a fine-tuned checkpoint for your robot/cameras, or pass --allow-base-model only for bring-up experiments."
            )

        from skills2026.robot.lekiwi_io import LeKiwiIO

        io = LeKiwiIO(profile)
        policy = SmolVLAPolicy.from_pretrained(selected_model)
        preprocessor_overrides = {
            "device_processor": {"device": selected_device},
        }
        if settings.rename_map:
            preprocessor_overrides["rename_observations_processor"] = {"rename_map": settings.rename_map}

        preprocess, postprocess = make_pre_post_processors(
            policy.config,
            selected_model,
            preprocessor_overrides=preprocessor_overrides,
        )

        action_features = hw_to_dataset_features(io.robot.action_features, "action")
        obs_features = hw_to_dataset_features(io.robot.observation_features, "observation")
        dataset_features = {**action_features, **obs_features}

        expected_action_dim = None
        if getattr(policy.config, "output_features", None) and "action" in policy.config.output_features:
            expected_action_dim = policy.config.output_features["action"].shape[0]
        robot_action_dim = len(io.robot.action_features)
        if expected_action_dim is not None and expected_action_dim != robot_action_dim:
            raise ValueError(
                f"SmolVLA checkpoint action dimension ({expected_action_dim}) does not match LeKiwi ({robot_action_dim}). "
                "Use a LeKiwi fine-tuned SmolVLA checkpoint."
            )

        expected_visuals = {
            key for key, feature in getattr(policy.config, "input_features", {}).items() if feature.type == FeatureType.VISUAL
        }
        provided_visuals = {
            settings.rename_map.get(key, key)
            for key in dataset_features
            if key.startswith("observation.images.")
        }
        if expected_visuals and not (
            expected_visuals.issubset(provided_visuals) or provided_visuals.issubset(expected_visuals)
        ):
            raise ValueError(
                "SmolVLA camera keys do not match this LeKiwi profile. "
                "Update profile.policy.smolvla.rename_map so your front/wrist images map to the checkpoint's expected keys."
            )

        return cls(
            io=io,
            safety=SafetyController(),
            primitive_name=primitive_name,
            task=selected_task,
            model_id=selected_model,
            device_name=selected_device,
            rename_map=settings.rename_map,
            policy=policy,
            preprocess=preprocess,
            postprocess=postprocess,
            dataset_features=dataset_features,
            torch=torch,
        )

    def run(self, max_cycles: int = 500) -> int:
        from lerobot.policies.utils import build_inference_frame, make_robot_action

        self.io.connect()
        self.policy.reset()
        try:
            for cycle_idx in range(max_cycles):
                started = time.perf_counter()
                observation = self.io.get_observation()
                current_pose = self.io.arm_pose_from_observation(observation)
                obs_frame = build_inference_frame(
                    observation=observation,
                    device=self.torch.device(self.device_name),
                    ds_features=self.dataset_features,
                    task=self.task,
                    robot_type=self.io.robot.name,
                )
                obs_frame = self.preprocess(obs_frame)
                with self.torch.inference_mode():
                    action = self.policy.select_action(obs_frame)
                action = self.postprocess(action)
                robot_action = make_robot_action(action, self.dataset_features)
                safe_action = self.safety.apply(robot_action, current_pose)
                self.io.send_action(safe_action)

                if cycle_idx % 10 == 0:
                    logger.info(
                        "smolvla cycle=%s model=%s device=%s task=%s",
                        cycle_idx,
                        self.model_id,
                        self.device_name,
                        self.task,
                    )

                dt_s = time.perf_counter() - started
                time.sleep(max((1.0 / self.io.profile.budget.loop_hz) - dt_s, 0.0))

            logger.warning("SmolVLA run timed out.")
            self.io.stop_base()
            return 1
        finally:
            self.io.disconnect()
