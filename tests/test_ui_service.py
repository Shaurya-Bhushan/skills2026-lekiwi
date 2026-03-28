import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skills2026.ui.service import SetupFormData, ensure_profile_name


class UIServiceTests(unittest.TestCase):
    def test_profile_name_normalization(self):
        self.assertEqual(ensure_profile_name("  demo.json "), "demo")
        self.assertEqual(ensure_profile_name(""), "default")

    def test_form_roundtrip_sets_backend_and_rename_map(self):
        form = SetupFormData(
            profile_name="demo",
            mode="dev_remote",
            default_backend="smolvla",
            remote_ip="127.0.0.1",
            robot_id="skills2026_lekiwi",
            leader_port="/dev/tty.usbmodem1",
            robot_serial_port="/dev/tty.usbmodem2",
            start_local_host=True,
            front_camera_id="0",
            front_width=640,
            front_height=480,
            front_fps=15,
            front_enabled=True,
            wrist_camera_id="1",
            wrist_width=640,
            wrist_height=480,
            wrist_fps=12,
            wrist_enabled=True,
            kill_switch_ready=True,
            wiring_diagram_ready=True,
            tabletop_stand_ready=True,
            local_only_mode_confirmed=True,
            smolvla_enabled=True,
            smolvla_model_id="user/lekiwi-smolvla",
            smolvla_device="cpu",
            smolvla_require_finetuned=True,
            smolvla_rename_map_json='{"observation.images.front": "observation.images.image"}',
        )
        profile = form.to_profile()
        self.assertEqual(profile.policy.default_backend, "smolvla")
        self.assertEqual(profile.policy.smolvla.model_id, "user/lekiwi-smolvla")
        self.assertEqual(
            profile.policy.smolvla.rename_map,
            {"observation.images.front": "observation.images.image"},
        )


if __name__ == "__main__":
    unittest.main()
