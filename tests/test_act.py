import sys
import tempfile
import types
import unittest
from importlib.machinery import ModuleSpec
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

if "lerobot.cameras.opencv.configuration_opencv" not in sys.modules:
    lerobot = types.ModuleType("lerobot")
    cameras = types.ModuleType("lerobot.cameras")
    camera_configs = types.ModuleType("lerobot.cameras.configs")
    opencv = types.ModuleType("lerobot.cameras.opencv")
    configuration_opencv = types.ModuleType("lerobot.cameras.opencv.configuration_opencv")
    robots = types.ModuleType("lerobot.robots")
    lekiwi = types.ModuleType("lerobot.robots.lekiwi")
    datasets = types.ModuleType("lerobot.datasets")
    dataset_metadata = types.ModuleType("lerobot.datasets.dataset_metadata")
    policies = types.ModuleType("lerobot.policies")
    policies_act = types.ModuleType("lerobot.policies.act")
    act_config = types.ModuleType("lerobot.policies.act.configuration_act")
    act_model = types.ModuleType("lerobot.policies.act.modeling_act")
    policies_factory = types.ModuleType("lerobot.policies.factory")
    policies_utils = types.ModuleType("lerobot.policies.utils")

    class _DummyOpenCVCameraConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class _DummyLeKiwiClientConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class _DummyLeKiwiClient:
        def __init__(self, config):
            self.config = config
            self.is_connected = False

        def connect(self):
            self.is_connected = True

        def disconnect(self):
            self.is_connected = False

        def get_observation(self):
            return {}

        def send_action(self, action):
            return action

    class _DummyColorMode:
        RGB = "RGB"

    class _DummyDatasetMeta:
        def __init__(self, **kwargs):
            self.repo_id = kwargs.get("repo_id", "")
            self.root = kwargs.get("root")
            self.stats = {"dummy": 1}
            self.features = {"dummy": 1}
            self.robot_type = "lekiwi"

    class _DummyACTConfig:
        device = "cpu"

        @classmethod
        def from_pretrained(cls, pretrained_name_or_path):
            return cls()

    class _DummyACTPolicy:
        def __init__(self, config):
            self.config = config

        @classmethod
        def from_pretrained(cls, policy_path, config=None):
            return cls(config or _DummyACTConfig())

        def reset(self):
            return None

        def select_action(self, obs_frame):
            return {"action": "dummy"}

    def _dummy_pre_post_processors(**kwargs):
        return (lambda value: value, lambda value: value)

    def _dummy_build_inference_frame(**kwargs):
        raise RuntimeError("boom")

    def _dummy_make_robot_action(action_tensor, features):
        return {"arm_shoulder_pan.pos": 0.0, "x.vel": 0.0, "y.vel": 0.0, "theta.vel": 0.0}

    camera_configs.ColorMode = _DummyColorMode
    configuration_opencv.OpenCVCameraConfig = _DummyOpenCVCameraConfig
    lekiwi.LeKiwiClient = _DummyLeKiwiClient
    lekiwi.LeKiwiClientConfig = _DummyLeKiwiClientConfig
    dataset_metadata.LeRobotDatasetMetadata = _DummyDatasetMeta
    act_config.ACTConfig = _DummyACTConfig
    act_model.ACTPolicy = _DummyACTPolicy
    policies_factory.make_pre_post_processors = _dummy_pre_post_processors
    policies_utils.build_inference_frame = _dummy_build_inference_frame
    policies_utils.make_robot_action = _dummy_make_robot_action

    lerobot.__spec__ = ModuleSpec("lerobot", loader=None)
    lerobot.__path__ = []
    cameras.__spec__ = ModuleSpec("lerobot.cameras", loader=None)
    cameras.__path__ = []
    camera_configs.__spec__ = ModuleSpec("lerobot.cameras.configs", loader=None)
    opencv.__spec__ = ModuleSpec("lerobot.cameras.opencv", loader=None)
    opencv.__path__ = []
    configuration_opencv.__spec__ = ModuleSpec("lerobot.cameras.opencv.configuration_opencv", loader=None)
    robots.__spec__ = ModuleSpec("lerobot.robots", loader=None)
    robots.__path__ = []
    lekiwi.__spec__ = ModuleSpec("lerobot.robots.lekiwi", loader=None)
    datasets.__spec__ = ModuleSpec("lerobot.datasets", loader=None)
    datasets.__path__ = []
    dataset_metadata.__spec__ = ModuleSpec("lerobot.datasets.dataset_metadata", loader=None)
    policies.__spec__ = ModuleSpec("lerobot.policies", loader=None)
    policies.__path__ = []
    policies_act.__spec__ = ModuleSpec("lerobot.policies.act", loader=None)
    policies_act.__path__ = []
    act_config.__spec__ = ModuleSpec("lerobot.policies.act.configuration_act", loader=None)
    act_model.__spec__ = ModuleSpec("lerobot.policies.act.modeling_act", loader=None)
    policies_factory.__spec__ = ModuleSpec("lerobot.policies.factory", loader=None)
    policies_utils.__spec__ = ModuleSpec("lerobot.policies.utils", loader=None)

    sys.modules["lerobot"] = lerobot
    sys.modules["lerobot.cameras"] = cameras
    sys.modules["lerobot.cameras.configs"] = camera_configs
    sys.modules["lerobot.cameras.opencv"] = opencv
    sys.modules["lerobot.cameras.opencv.configuration_opencv"] = configuration_opencv
    sys.modules["lerobot.robots"] = robots
    sys.modules["lerobot.robots.lekiwi"] = lekiwi
    sys.modules["lerobot.datasets"] = datasets
    sys.modules["lerobot.datasets.dataset_metadata"] = dataset_metadata
    sys.modules["lerobot.policies"] = policies
    sys.modules["lerobot.policies.act"] = policies_act
    sys.modules["lerobot.policies.act.configuration_act"] = act_config
    sys.modules["lerobot.policies.act.modeling_act"] = act_model
    sys.modules["lerobot.policies.factory"] = policies_factory
    sys.modules["lerobot.policies.utils"] = policies_utils

from skills2026.policy import act as act_module
from skills2026.profile import Skills2026Profile
from skills2026.training import DatasetManifest, PickupGateStamp, save_dataset_manifest


class _DummyIO:
    def __init__(self, profile):
        self.profile = profile
        self.stop_args = []
        self.connected = False

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.connected = False

    def get_observation(self):
        return {
            "arm_shoulder_pan.pos": 0.0,
            "arm_shoulder_lift.pos": 0.0,
            "arm_elbow_flex.pos": 0.0,
            "arm_wrist_flex.pos": 0.0,
            "arm_wrist_roll.pos": 0.0,
            "arm_gripper.pos": 0.0,
            "front": None,
            "wrist": None,
        }

    def arm_pose_from_observation(self, observation):
        return {key: float(value) for key, value in observation.items() if key.endswith(".pos")}

    def stop_base(self, observation=None):
        self.stop_args.append(observation)

    def send_action(self, action):
        return action


class _DummyTorch:
    device = staticmethod(lambda name: name)
    cuda = types.SimpleNamespace(is_available=lambda: False)
    backends = types.SimpleNamespace(mps=types.SimpleNamespace(is_available=lambda: False))


class _DummyDatasetMetadata:
    def __init__(self, **kwargs):
        self.repo_id = kwargs.get("repo_id", "")
        self.root = kwargs.get("root")
        self.stats = {"dummy": 1}
        self.features = {"dummy": 1}
        self.robot_type = "lekiwi"


class _DummyACTConfig:
    device = "cpu"

    @classmethod
    def from_pretrained(cls, pretrained_name_or_path):
        return cls()


class _DummyACTPolicy:
    def __init__(self, config):
        self.config = config

    @classmethod
    def from_pretrained(cls, policy_path, config=None):
        return cls(config or _DummyACTConfig())

    def reset(self):
        return None

    def select_action(self, obs_frame):
        return {"action": "dummy"}


def _dummy_pre_post_processors(**kwargs):
    return (lambda value: value, lambda value: value)


def _boom_build_inference_frame(**kwargs):
    raise RuntimeError("boom")


def _dummy_make_robot_action(action_tensor, features):
    return {"arm_shoulder_pan.pos": 0.0, "x.vel": 0.0, "y.vel": 0.0, "theta.vel": 0.0}


class ActRunnerTests(unittest.TestCase):
    def test_act_runner_refuses_unreviewed_dataset(self):
        profile = Skills2026Profile.defaults("act")
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset_root = Path(temp_dir) / "default_insert_fuse"
            meta_dir = dataset_root / "meta"
            meta_dir.mkdir(parents=True, exist_ok=True)
            (meta_dir / "info.json").write_text('{"total_episodes": 1}')
            manifest = DatasetManifest.create(profile, "default_insert_fuse", "insert_fuse")
            manifest.sync_episode_count(1)
            save_dataset_manifest(dataset_root, manifest)
            with patch.object(act_module, "ACT_IMPORT_ERROR", None), \
                patch.object(act_module, "torch", _DummyTorch, create=True), \
                patch.object(act_module, "DATASETS_DIR", Path(temp_dir)), \
                patch.object(act_module, "LeRobotDatasetMetadata", _DummyDatasetMetadata, create=True), \
                patch.object(act_module, "ACTConfig", _DummyACTConfig, create=True), \
                patch.object(act_module, "ACTPolicy", _DummyACTPolicy, create=True), \
                patch.object(act_module, "make_pre_post_processors", _dummy_pre_post_processors, create=True), \
                patch.object(act_module, "build_inference_frame", _boom_build_inference_frame, create=True), \
                patch.object(act_module, "make_robot_action", _dummy_make_robot_action, create=True):
                with self.assertRaises(RuntimeError):
                    act_module.ACTRunner.from_profile(
                        profile=profile,
                        primitive_name="insert_fuse",
                        policy_path="dummy/checkpoint",
                        dataset_name="default_insert_fuse",
                        device_name="cpu",
                    )

    def test_act_runner_stops_base_on_inference_error(self):
        profile = Skills2026Profile.defaults("act")
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset_root = Path(temp_dir) / "default_insert_fuse"
            meta_dir = dataset_root / "meta"
            meta_dir.mkdir(parents=True, exist_ok=True)
            (meta_dir / "info.json").write_text('{"total_episodes": 1}')
            manifest = DatasetManifest.create(profile, "default_insert_fuse", "insert_fuse")
            manifest.sync_episode_count(1)
            manifest.mark_replay_approval(episode_index=0, status="pass", profile=profile)
            manifest.mark_pickup_validation(
                PickupGateStamp(
                    primitive_name="pick_fuse",
                    suite_name="ecu",
                    scenario_name="fuse_supply_pickup",
                    report_path="/tmp/report.json",
                    report_created_at="2026-03-29T12:00:00",
                    stamped_at="2026-03-29T12:05:00",
                    passed=True,
                )
            )
            save_dataset_manifest(dataset_root, manifest)
            with patch.object(act_module, "ACT_IMPORT_ERROR", None), \
                patch.object(act_module, "torch", _DummyTorch, create=True), \
                patch.object(act_module, "DATASETS_DIR", Path(temp_dir)), \
                patch.object(act_module, "LeRobotDatasetMetadata", _DummyDatasetMetadata, create=True), \
                patch.object(act_module, "ACTConfig", _DummyACTConfig, create=True), \
                patch.object(act_module, "ACTPolicy", _DummyACTPolicy, create=True), \
                patch.object(act_module, "make_pre_post_processors", _dummy_pre_post_processors, create=True), \
                patch.object(act_module, "build_inference_frame", _boom_build_inference_frame, create=True), \
                patch.object(act_module, "make_robot_action", _dummy_make_robot_action, create=True):
                runner = act_module.ACTRunner.from_profile(
                    profile=profile,
                    primitive_name="insert_fuse",
                    policy_path="dummy/checkpoint",
                    dataset_name="default_insert_fuse",
                    device_name="cpu",
                )
                runner.io = _DummyIO(profile)

                with self.assertRaises(RuntimeError):
                    runner.run(max_cycles=1)

                self.assertEqual(len(runner.io.stop_args), 1)
                self.assertIsNotNone(runner.io.stop_args[0])


if __name__ == "__main__":
    unittest.main()
