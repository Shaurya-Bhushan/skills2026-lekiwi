import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skills2026.control.pickup_validation import (
    PickupValidationRunner,
    default_pickup_report_path,
    get_pickup_validation_scenarios,
    missing_pickup_validation_poses,
    save_pickup_validation_report,
)
from skills2026.control.primitives import PRIMITIVES
from skills2026.profile import Skills2026Profile


class PickupValidationTests(unittest.TestCase):
    def test_suite_selection_returns_expected_scenarios(self):
        core = get_pickup_validation_scenarios("core")
        ecu = get_pickup_validation_scenarios("ecu")
        all_scenarios = get_pickup_validation_scenarios("all")

        self.assertGreaterEqual(len(core), 5)
        self.assertGreaterEqual(len(ecu), 4)
        self.assertEqual(len(all_scenarios), len(core) + len(ecu))

    def test_missing_service_poses_are_reported(self):
        profile = Skills2026Profile.defaults("validation")
        scenarios = get_pickup_validation_scenarios("ecu")

        missing = missing_pickup_validation_poses(profile, scenarios)

        self.assertIn("tray_hover", missing)
        self.assertIn("steve_pick_pose", missing)

    def test_runner_collects_results_and_summary(self):
        profile = Skills2026Profile.defaults("validation")
        for spec in PRIMITIVES.values():
            profile.service_poses[spec.coarse_pose] = {"arm_shoulder_pan.pos": 0.0}
            profile.service_poses[spec.action_pose] = {"arm_shoulder_pan.pos": 1.0}
            profile.service_poses[spec.retract_pose] = {"arm_shoulder_pan.pos": 0.0}

        scenarios = get_pickup_validation_scenarios("core")[:2]
        exit_codes = iter([0, 1, 0, 0])

        class _FakePrimitiveRunner:
            def __init__(self, code):
                self.code = code

            def run(self, max_cycles=500):
                return self.code

        output = io.StringIO()
        runner = PickupValidationRunner(
            profile=profile,
            suite_name="core",
            scenarios=scenarios,
            trials_per_scenario=2,
            build_runner=lambda scenario: _FakePrimitiveRunner(next(exit_codes)),
            output=output,
            input_stream=io.StringIO(),
        )

        report = runner.run(max_cycles=20, pause_between_trials=False, fail_fast=False)

        self.assertEqual(report.total_attempts, 4)
        self.assertEqual(report.total_successes, 3)
        self.assertAlmostEqual(report.overall_success_rate, 0.75)
        self.assertFalse(report.all_passed)
        rendered = output.getvalue()
        self.assertIn("Single Target Debris Pickup", rendered)
        self.assertIn("Scenario success: 1/2", rendered)

    def test_report_can_be_saved(self):
        profile = Skills2026Profile.defaults("validation")
        scenarios = get_pickup_validation_scenarios("core")[:1]

        class _AlwaysPassRunner:
            def run(self, max_cycles=500):
                return 0

        runner = PickupValidationRunner(
            profile=profile,
            suite_name="core",
            scenarios=scenarios,
            trials_per_scenario=1,
            build_runner=lambda scenario: _AlwaysPassRunner(),
            output=io.StringIO(),
            input_stream=io.StringIO(),
        )
        report = runner.run(max_cycles=10, pause_between_trials=False)

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "report.json"
            saved = save_pickup_validation_report(report, target)
            raw = json.loads(saved.read_text())

        self.assertEqual(saved.name, "report.json")
        self.assertTrue(raw["all_passed"])
        self.assertEqual(raw["total_successes"], 1)

    def test_default_report_path_uses_logs_directory(self):
        target = default_pickup_report_path("default", "core")
        self.assertIn("pickup_validation_default_core_", target.name)
        self.assertEqual(target.suffix, ".json")


if __name__ == "__main__":
    unittest.main()
