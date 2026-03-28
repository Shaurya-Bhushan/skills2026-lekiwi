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

    def test_legacy_policy_backend_falls_back_to_opencv(self):
        restored = Skills2026Profile.from_dict(
            {
                "profile_name": "legacy",
                "policy": {
                    "default_backend": "smolvla",
                    "smolvla": {"enabled": True},
                },
            }
        )
        self.assertEqual(restored.policy.default_backend, "opencv_fsm")

    def test_default_wrist_servo_keeps_wrist_roll_out_of_visual_servo(self):
        profile = Skills2026Profile.defaults("servo")
        self.assertNotIn("arm_wrist_roll.pos", profile.servo["wrist"].x_gains)

    def test_legacy_wrist_servo_defaults_are_migrated(self):
        restored = Skills2026Profile.from_dict(
            {
                "profile_name": "legacy-servo",
                "servo": {
                    "wrist": {
                        "x_gains": {
                            "arm_shoulder_pan.pos": -2.5,
                            "arm_wrist_roll.pos": 1.5,
                        },
                        "y_gains": {
                            "arm_shoulder_lift.pos": 2.5,
                            "arm_elbow_flex.pos": -1.0,
                        },
                    }
                },
            }
        )
        self.assertEqual(restored.servo["wrist"].x_gains, {"arm_shoulder_pan.pos": -3.0})


if __name__ == "__main__":
    unittest.main()
