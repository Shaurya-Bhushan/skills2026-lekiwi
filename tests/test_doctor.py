import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skills2026.commands.doctor import collect_checks
from skills2026.profile import Skills2026Profile


class DoctorTests(unittest.TestCase):
    @patch("skills2026.commands.doctor.checklist_ready", return_value=(True, []))
    @patch("skills2026.commands.doctor.tcp_port_open", return_value=(True, "reachable"))
    @patch("skills2026.commands.doctor.read_single_camera_frame", return_value=(True, "frame shape=(480, 640, 3)"))
    @patch("skills2026.commands.doctor.camera_exists", return_value=True)
    @patch("skills2026.commands.doctor.discover_serial_ports", return_value=[])
    def test_doctor_flags_duplicate_camera_sources(
        self,
        _discover_serial_ports,
        _camera_exists,
        _read_single_camera_frame,
        _tcp_port_open,
        _checklist_ready,
    ):
        profile = Skills2026Profile.defaults("doctor")
        profile.cameras["front"].source_id = 0
        profile.cameras["wrist"].source_id = 0

        results = collect_checks(profile)
        collision = next(result for result in results if result.name == "camera_source_collision")

        self.assertFalse(collision.ok)
        self.assertIn("front=0", collision.detail)
        self.assertIn("wrist=0", collision.detail)


if __name__ == "__main__":
    unittest.main()
