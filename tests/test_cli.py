import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skills2026.cli import build_parser


class CLITests(unittest.TestCase):
    def test_competition_ecu_primitive_argument(self):
        parser = build_parser()
        args = parser.parse_args(
            [
                "competition",
                "ecu",
                "--primitive",
                "remove_transformer",
            ]
        )
        self.assertEqual(args.primitive, "remove_transformer")

    def test_competition_act_backend_argument(self):
        parser = build_parser()
        args = parser.parse_args(
            [
                "competition",
                "ecu",
                "--backend",
                "act",
                "--primitive",
                "insert_fuse",
                "--policy-path",
                "user/act_insert_fuse",
                "--dataset-name",
                "default_insert_fuse",
                "--policy-device",
                "cpu",
            ]
        )
        self.assertEqual(args.backend, "act")
        self.assertEqual(args.policy_path, "user/act_insert_fuse")
        self.assertEqual(args.dataset_name, "default_insert_fuse")
        self.assertEqual(args.policy_device, "cpu")

    def test_ui_command_exists(self):
        parser = build_parser()
        args = parser.parse_args(["ui", "--host", "0.0.0.0", "--port", "9999", "--no-browser"])
        self.assertEqual(args.command, "ui")
        self.assertEqual(args.host, "0.0.0.0")
        self.assertEqual(args.port, 9999)
        self.assertTrue(args.no_browser)

    def test_competition_mission_argument(self):
        parser = build_parser()
        args = parser.parse_args(
            [
                "competition",
                "mission",
                "--mission-name",
                "ecu_steve_priority",
            ]
        )
        self.assertEqual(args.mode_name, "mission")
        self.assertEqual(args.mission_name, "ecu_steve_priority")


if __name__ == "__main__":
    unittest.main()
