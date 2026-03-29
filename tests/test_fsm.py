import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skills2026.control.primitives import PrimitiveController, PRIMITIVES
from skills2026.control.fsm import PrimitiveState
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

    def test_align_fine_tolerates_camera_settle_and_transient_target_loss(self):
        profile = Skills2026Profile.defaults("fsm")
        controller = PrimitiveController(PRIMITIVES["pick_debris"], profile)
        controller.fsm.state = PrimitiveState.ALIGN_FINE
        current = _pose(0.0)
        fine = VisionTarget(
            found=True,
            camera_role="wrist",
            confidence=0.8,
            error_px=(48.0, 0.0),
            metadata={},
        )

        decision = controller.step(current, DetectionBundle(fine_target=fine), wrist_allowed=True)
        self.assertEqual(decision.message, "fine-aligning with wrist camera")
        self.assertEqual(controller.fsm.state, PrimitiveState.ALIGN_FINE)
        self.assertGreater(controller.wrist_settle_cycles_remaining, 0)

        for _ in range(3):
            decision = controller.step(current, DetectionBundle(), wrist_allowed=True)
            self.assertEqual(controller.fsm.state, PrimitiveState.ALIGN_FINE)
            self.assertFalse(decision.failed)

        self.assertIn("wrist", decision.message)

    def test_align_fine_only_fails_after_grace_cycles(self):
        profile = Skills2026Profile.defaults("fsm")
        controller = PrimitiveController(PRIMITIVES["pick_debris"], profile)
        controller.fsm.state = PrimitiveState.ALIGN_FINE
        current = _pose(0.0)

        for _ in range(controller.wrist_target_miss_grace_cycles):
            decision = controller.step(current, DetectionBundle(), wrist_allowed=True)
            self.assertEqual(controller.fsm.state, PrimitiveState.ALIGN_FINE)
            self.assertFalse(decision.failed)

        decision = controller.step(current, DetectionBundle(), wrist_allowed=True)
        self.assertEqual(controller.fsm.state, PrimitiveState.RETRY_OR_ABORT)
        self.assertEqual(decision.message, "lost wrist target")

    def test_verify_waits_for_post_action_settle(self):
        profile = Skills2026Profile.defaults("fsm")
        controller = PrimitiveController(PRIMITIVES["insert_fuse"], profile)
        controller.fsm.state = PrimitiveState.VERIFY
        controller.wrist_settle_cycles_remaining = 2
        current = _pose(0.0)

        first = controller.step(current, DetectionBundle(), wrist_allowed=True)
        second = controller.step(current, DetectionBundle(), wrist_allowed=True)

        self.assertEqual(first.message, "waiting for post-action settle")
        self.assertEqual(second.message, "waiting for post-action settle")
        self.assertEqual(controller.fsm.state, PrimitiveState.VERIFY)

    def test_front_only_primitive_skips_wrist_precision_even_when_available(self):
        profile = Skills2026Profile.defaults("fsm")
        controller = PrimitiveController(PRIMITIVES["push_fallen_beam"], profile)
        controller.fsm.state = PrimitiveState.SWITCH_TO_WRIST_PRECISION
        current = _pose(0.0)

        decision = controller.step(current, DetectionBundle(), wrist_allowed=True)

        self.assertEqual(controller.fsm.state, PrimitiveState.GRASP_OR_INSERT)
        self.assertEqual(decision.message, "continuing without wrist precision")
        self.assertFalse(decision.use_wrist)

    def test_coarse_alignment_uses_front_error_before_switching_to_wrist(self):
        profile = Skills2026Profile.defaults("fsm")
        profile.service_poses["tray_hover"] = _pose(0.0)
        profile.service_poses["tray_grasp"] = _pose(5.0)
        profile.service_poses["safe_retract"] = _pose(0.0)
        controller = PrimitiveController(PRIMITIVES["pick_fuse"], profile)
        controller.fsm.state = PrimitiveState.APPROACH_COARSE
        current = _pose(0.0)
        coarse = VisionTarget(found=True, camera_role="front", error_px=(80.0, 0.0))

        decision = controller.step(current, DetectionBundle(coarse_target=coarse), wrist_allowed=True)

        self.assertEqual(controller.fsm.state, PrimitiveState.APPROACH_COARSE)
        self.assertEqual(decision.message, "coarse-aligning with front camera")

    def test_grasp_holds_action_pose_before_verifying(self):
        profile = Skills2026Profile.defaults("fsm")
        profile.service_poses["debris_pick_pose"] = _pose(5.0)
        controller = PrimitiveController(PRIMITIVES["pick_debris"], profile)
        controller.fsm.state = PrimitiveState.GRASP_OR_INSERT
        current = _pose(5.0)

        first = controller.step(current, DetectionBundle(), wrist_allowed=True)
        second = controller.step(current, DetectionBundle(), wrist_allowed=True)
        third = controller.step(current, DetectionBundle(), wrist_allowed=True)

        self.assertEqual(first.message, "holding action pose to secure grasp")
        self.assertEqual(second.message, "holding action pose to secure grasp")
        self.assertEqual(third.message, "grasp pose reached, retracting to verify pickup")
        self.assertEqual(controller.fsm.state, PrimitiveState.RETRACT)

    def test_pickup_verifies_after_retract_with_fresh_wrist_target(self):
        profile = Skills2026Profile.defaults("fsm")
        profile.service_poses["debris_pick_pose"] = _pose(5.0)
        profile.service_poses["safe_retract"] = _pose(10.0)
        controller = PrimitiveController(PRIMITIVES["pick_debris"], profile)
        controller.fsm.state = PrimitiveState.GRASP_OR_INSERT
        action_pose = _pose(5.0)
        retract_pose = _pose(10.0)
        carried = VisionTarget(
            found=True,
            camera_role="wrist",
            confidence=0.9,
            error_px=(0.0, 0.0),
            bbox_xywh=(88, 88, 30, 30),
            metadata={},
        )

        controller.step(action_pose, DetectionBundle(fine_target=carried), wrist_allowed=True)
        controller.step(action_pose, DetectionBundle(fine_target=carried), wrist_allowed=True)
        controller.step(action_pose, DetectionBundle(fine_target=carried), wrist_allowed=True)
        self.assertEqual(controller.fsm.state, PrimitiveState.RETRACT)

        decision = controller.step(retract_pose, DetectionBundle(), wrist_allowed=True)
        self.assertEqual(decision.message, "retracted and verifying pickup")
        self.assertEqual(controller.fsm.state, PrimitiveState.VERIFY)

        settle_one = controller.step(retract_pose, DetectionBundle(), wrist_allowed=True)
        settle_two = controller.step(retract_pose, DetectionBundle(), wrist_allowed=True)
        self.assertEqual(settle_one.message, "waiting for post-action settle")
        self.assertEqual(settle_two.message, "waiting for post-action settle")

        first_verify = controller.step(retract_pose, DetectionBundle(fine_target=carried), wrist_allowed=True)
        second_verify = controller.step(retract_pose, DetectionBundle(fine_target=carried), wrist_allowed=True)

        self.assertEqual(first_verify.message, "pickup verification confirming carried object")
        self.assertTrue(second_verify.done)
        self.assertEqual(second_verify.message, "pickup verification passed")

    def test_pickup_retries_when_wrist_target_never_returns_after_retract(self):
        profile = Skills2026Profile.defaults("fsm")
        controller = PrimitiveController(PRIMITIVES["pick_debris"], profile)
        controller.fsm.state = PrimitiveState.VERIFY

        for _ in range(controller.wrist_target_miss_grace_cycles):
            decision = controller.step(_pose(0.0), DetectionBundle(), wrist_allowed=True)
            self.assertEqual(controller.fsm.state, PrimitiveState.VERIFY)
            self.assertEqual(decision.message, "pickup verification waiting for fresh wrist target")

        decision = controller.step(_pose(0.0), DetectionBundle(), wrist_allowed=True)
        self.assertEqual(controller.fsm.state, PrimitiveState.RETRY_OR_ABORT)
        self.assertEqual(decision.message, "pickup verification failed: wrist target missing after retract")

    def test_pickup_can_confirm_from_front_tracking_when_wrist_is_occluded(self):
        profile = Skills2026Profile.defaults("fsm")
        controller = PrimitiveController(PRIMITIVES["pick_debris"], profile)
        controller.fsm.state = PrimitiveState.VERIFY
        controller.pre_action_bbox_area = 400.0
        controller.pre_action_coarse_bbox_area = 400.0
        controller.pre_action_coarse_center = (70.0, 70.0)
        coarse = VisionTarget(
            found=True,
            camera_role="front",
            center_px=(130.0, 70.0),
            bbox_xywh=(110, 50, 24, 24),
            metadata={},
        )

        first = controller.step(_pose(0.0), DetectionBundle(coarse_target=coarse), wrist_allowed=True)
        second = controller.step(_pose(0.0), DetectionBundle(coarse_target=coarse), wrist_allowed=True)

        self.assertEqual(first.message, "pickup verification confirming carried object in front view")
        self.assertTrue(second.done)
        self.assertEqual(second.message, "pickup verification passed from front-camera carry tracking")


if __name__ == "__main__":
    unittest.main()
