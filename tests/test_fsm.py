import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skills2026.control.primitives import PrimitiveController, PRIMITIVES
from skills2026.perception.models import DetectionBundle, VisionTarget
from skills2026.profile import Skills2026Profile


def _pose(value: float):
    return {
        "arm_shoulder_pan.pos": value,
        "arm_shoulder_lift.pos": value,
        "arm_elbow_flex.pos": value,
        "arm_wrist_flex.pos": value,
        "arm_wrist_roll.pos": value,
        "arm_gripper.pos": value,
    }


class FSMTests(unittest.TestCase):
    def test_fsm_moves_from_detect_to_approach(self):
        profile = Skills2026Profile.defaults("fsm")
        profile.service_poses["tray_hover"] = _pose(10.0)
        profile.service_poses["tray_grasp"] = _pose(12.0)
        profile.service_poses["safe_retract"] = _pose(0.0)
        controller = PrimitiveController(PRIMITIVES["pick_fuse"], profile)
        coarse = VisionTarget(found=True, camera_role="front", confidence=0.8)
        current = _pose(0.0)
        decision = controller.step(current, DetectionBundle(coarse_target=coarse), wrist_allowed=True)
        self.assertEqual(controller.fsm.state.value, "approach_coarse")
        self.assertFalse(decision.done)


if __name__ == "__main__":
    unittest.main()
