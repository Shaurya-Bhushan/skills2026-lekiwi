import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skills2026.cli import build_parser


class CLITests(unittest.TestCase):
    def test_competition_backend_argument(self):
        parser = build_parser()
        args = parser.parse_args(
            [
                "competition",
                "ecu",
                "--backend",
                "smolvla",
                "--primitive",
                "insert_fuse",
            ]
        )
        self.assertEqual(args.backend, "smolvla")
        self.assertEqual(args.primitive, "insert_fuse")

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
                "full_match",
            ]
        )
        self.assertEqual(args.mode_name, "mission")
        self.assertEqual(args.mission_name, "full_match")


if __name__ == "__main__":
    unittest.main()
