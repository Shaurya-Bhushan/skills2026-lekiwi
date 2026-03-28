import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skills2026.profile import Skills2026Profile


class ProfileTests(unittest.TestCase):
    def test_profile_roundtrip_defaults(self):
        profile = Skills2026Profile.defaults("test")
        raw = profile.__dict__.copy()
        restored = Skills2026Profile.from_dict(
            {
                "profile_name": "test",
                "mode": profile.mode,
                "robot_id": profile.robot_id,
                "leader_port": profile.leader_port,
                "robot_serial_port": profile.robot_serial_port,
                "cameras": {
                    role: {
                        "role": camera.role,
                        "source_id": camera.source_id,
                        "width": camera.width,
                        "height": camera.height,
                        "fps": camera.fps,
                        "enabled": camera.enabled,
                        "calibration": {
                            "calibrated": camera.calibration.calibrated,
                            "homography": camera.calibration.homography,
                        },
                    }
                    for role, camera in profile.cameras.items()
                },
                "service_poses": profile.service_poses,
            }
        )
        self.assertEqual(restored.profile_name, "test")
        self.assertEqual(set(restored.cameras), {"front", "wrist"})
        self.assertEqual(restored.service_poses.keys(), raw["service_poses"].keys())
        self.assertEqual(restored.policy.default_backend, "opencv_fsm")
        self.assertIn("insert_fuse", restored.policy.smolvla.task_prompts)


class PolicyDefaultsTests(unittest.TestCase):
    def test_smolvla_defaults_are_present(self):
        profile = Skills2026Profile.defaults("policy")
        self.assertTrue(profile.policy.smolvla.enabled)
        self.assertEqual(profile.policy.smolvla.device, "auto")


if __name__ == "__main__":
    unittest.main()
