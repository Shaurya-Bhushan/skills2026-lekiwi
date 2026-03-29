import sys
import types
import unittest
from importlib.machinery import ModuleSpec
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

if "lerobot.cameras.opencv.configuration_opencv" not in sys.modules:
    lerobot = types.ModuleType("lerobot")
    cameras = types.ModuleType("lerobot.cameras")
    opencv = types.ModuleType("lerobot.cameras.opencv")
    configuration_opencv = types.ModuleType("lerobot.cameras.opencv.configuration_opencv")
    robots = types.ModuleType("lerobot.robots")
    lekiwi = types.ModuleType("lerobot.robots.lekiwi")

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

    configuration_opencv.OpenCVCameraConfig = _DummyOpenCVCameraConfig
    lekiwi.LeKiwiClient = _DummyLeKiwiClient
    lekiwi.LeKiwiClientConfig = _DummyLeKiwiClientConfig
    lerobot.__spec__ = ModuleSpec("lerobot", loader=None)
    lerobot.__path__ = []
    cameras.__spec__ = ModuleSpec("lerobot.cameras", loader=None)
    cameras.__path__ = []
    opencv.__spec__ = ModuleSpec("lerobot.cameras.opencv", loader=None)
    opencv.__path__ = []
    configuration_opencv.__spec__ = ModuleSpec("lerobot.cameras.opencv.configuration_opencv", loader=None)
    robots.__spec__ = ModuleSpec("lerobot.robots", loader=None)
    robots.__path__ = []
    lekiwi.__spec__ = ModuleSpec("lerobot.robots.lekiwi", loader=None)

    sys.modules["lerobot"] = lerobot
    sys.modules["lerobot.cameras"] = cameras
    sys.modules["lerobot.cameras.opencv"] = opencv
    sys.modules["lerobot.cameras.opencv.configuration_opencv"] = configuration_opencv
    sys.modules["lerobot.robots"] = robots
    sys.modules["lerobot.robots.lekiwi"] = lekiwi

from skills2026.control.competition import CompetitionRunner
from skills2026.control.fsm import PrimitiveState


class _FakeIO:
    def __init__(self):
        self.profile = type("Profile", (), {"budget": type("Budget", (), {"loop_hz": 10.0})()})()
        self.stop_args = []

    def connect(self):
        return None

    def disconnect(self):
        return None

    def get_observation(self):
        return {
            "arm_shoulder_pan.pos": 1.0,
            "arm_shoulder_lift.pos": 2.0,
            "arm_elbow_flex.pos": 3.0,
            "arm_wrist_flex.pos": 4.0,
            "arm_wrist_roll.pos": 5.0,
            "arm_gripper.pos": 6.0,
            "front": None,
            "wrist": None,
        }

    def arm_pose_from_observation(self, observation):
        return {key: float(value) for key, value in observation.items() if key.endswith(".pos")}

    def merge_action(self, action, base_vel=None):
        return dict(action)

    def send_action(self, action):
        return action

    def stop_base(self, observation=None):
        self.stop_args.append(observation)


class _FakeController:
    def __init__(self):
        self.spec = type("Spec", (), {"name": "pick_debris", "camera_role": "wrist"})()
        self.fsm = type("FSM", (), {"state": PrimitiveState.DETECT_GLOBAL})()

    def step(self, current_pose, detections, wrist_allowed):
        return type(
            "Decision",
            (),
            {
                "action": current_pose,
                "message": "continue",
                "done": False,
                "failed": False,
            },
        )()


class _ExplodingController(_FakeController):
    def step(self, current_pose, detections, wrist_allowed):
        raise RuntimeError("boom")


class _FakePerception:
    def analyze(self, *args, **kwargs):
        return None


class _FakeScheduler:
    def __init__(self):
        self.front_fps_scale = 1.0

    def request_precision(self, enabled):
        self.enabled = enabled

    def should_use_wrist(self):
        return False

    def observe_loop_duration(self, dt_s):
        self.last_dt_s = dt_s


class _FakeSafety:
    def apply(self, action, current_pose):
        return action


class CompetitionTests(unittest.TestCase):
    def test_timeout_stop_uses_last_observation(self):
        io = _FakeIO()
        runner = CompetitionRunner(
            io=io,
            controller=_FakeController(),
            front=_FakePerception(),
            wrist=_FakePerception(),
            scheduler=_FakeScheduler(),
            safety=_FakeSafety(),
        )

        exit_code = runner.run(max_cycles=1)

        self.assertEqual(exit_code, 1)
        self.assertEqual(len(io.stop_args), 1)
        self.assertIsNotNone(io.stop_args[0])
        self.assertEqual(io.stop_args[0]["arm_wrist_roll.pos"], 5.0)

    def test_exception_still_stops_base(self):
        io = _FakeIO()
        runner = CompetitionRunner(
            io=io,
            controller=_ExplodingController(),
            front=_FakePerception(),
            wrist=_FakePerception(),
            scheduler=_FakeScheduler(),
            safety=_FakeSafety(),
        )

        with self.assertRaises(RuntimeError):
            runner.run(max_cycles=1)

        self.assertEqual(len(io.stop_args), 1)
        self.assertIsNotNone(io.stop_args[0])

    def test_wrist_precision_request_is_not_skipped_when_wrist_frame_is_missing(self):
        class _PrecisionScheduler:
            def __init__(self):
                self.front_fps_scale = 1.0
                self.enabled = False

            def request_precision(self, enabled):
                self.enabled = enabled

            def should_use_wrist(self):
                return self.enabled

            def observe_loop_duration(self, dt_s):
                self.last_dt_s = dt_s

        class _DoneController(_FakeController):
            def __init__(self):
                super().__init__()
                self.fsm.state = PrimitiveState.SWITCH_TO_WRIST_PRECISION
                self.last_wrist_allowed = None

            def step(self, current_pose, detections, wrist_allowed):
                self.last_wrist_allowed = wrist_allowed
                return type(
                    "Decision",
                    (),
                    {
                        "action": current_pose,
                        "message": "done",
                        "done": True,
                        "failed": False,
                    },
                )()

        io = _FakeIO()
        controller = _DoneController()
        scheduler = _PrecisionScheduler()
        runner = CompetitionRunner(
            io=io,
            controller=controller,
            front=_FakePerception(),
            wrist=_FakePerception(),
            scheduler=scheduler,
            safety=_FakeSafety(),
        )

        exit_code = runner.run(max_cycles=1)

        self.assertEqual(exit_code, 0)
        self.assertTrue(scheduler.enabled)
        self.assertTrue(controller.last_wrist_allowed)


if __name__ == "__main__":
    unittest.main()
