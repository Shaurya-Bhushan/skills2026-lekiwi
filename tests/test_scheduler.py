import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skills2026.profile import RuntimeBudget
from skills2026.runtime.camera_scheduler import CameraScheduler


class SchedulerTests(unittest.TestCase):
    def test_scheduler_disables_wrist_before_front_throttle(self):
        scheduler = CameraScheduler(RuntimeBudget(loop_hz=10.0))
        scheduler.request_precision(True)
        scheduler.observe_loop_duration(0.2)
        self.assertTrue(scheduler.wrist_enabled)
        scheduler.observe_loop_duration(0.2)
        self.assertFalse(scheduler.wrist_enabled)
        self.assertEqual(scheduler.front_fps_scale, 1.0)
        scheduler.observe_loop_duration(0.2)
        scheduler.observe_loop_duration(0.2)
        self.assertEqual(scheduler.front_fps_scale, 0.75)


if __name__ == "__main__":
    unittest.main()
