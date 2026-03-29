import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skills2026.perception.front import FrontPerception
from skills2026.perception.models import TargetSelector
from skills2026.perception.wrist import WristPerception


class TargetSelectorTests(unittest.TestCase):
    def test_selector_prefers_larger_apparent_object_when_centers_match(self):
        selector = TargetSelector()
        bbox, _ = selector.select_bbox(
            candidates=[
                (90, 90, 10, 10),
                (85, 85, 20, 20),
            ],
            desired_center=(100.0, 100.0),
            track_key="wood_piece",
        )
        self.assertEqual(bbox, (85, 85, 20, 20))

    def test_selector_keeps_tracking_same_object(self):
        selector = TargetSelector()
        first, _ = selector.select_bbox(
            candidates=[
                (20, 80, 20, 20),
                (140, 80, 20, 20),
            ],
            desired_center=(30.0, 90.0),
            track_key="wood_piece",
        )
        second, _ = selector.select_bbox(
            candidates=[
                (18, 82, 20, 20),
                (132, 78, 28, 28),
            ],
            desired_center=(100.0, 90.0),
            track_key="wood_piece",
        )
        self.assertEqual(first, (20, 80, 20, 20))
        self.assertEqual(second, (18, 82, 20, 20))

    def test_selector_prefers_closer_candidate_for_pickup_when_both_are_valid(self):
        selector = TargetSelector()
        bbox, meta = selector.select_bbox(
            candidates=[
                (90, 90, 18, 18),
                (82, 82, 36, 36),
            ],
            desired_center=(100.0, 100.0),
            track_key="wood_piece_pick",
            prefer_closer=True,
            desired_slack_px=25.0,
            tracking_slack_px=20.0,
        )
        self.assertEqual(bbox, (82, 82, 36, 36))
        self.assertTrue(meta["prefer_closer"])

    def test_selector_ignores_far_large_distractor_when_pickup_prefers_closer(self):
        selector = TargetSelector()
        bbox, _ = selector.select_bbox(
            candidates=[
                (92, 92, 18, 18),
                (10, 10, 60, 60),
            ],
            desired_center=(100.0, 100.0),
            track_key="wood_piece_pick",
            prefer_closer=True,
            desired_slack_px=22.0,
            tracking_slack_px=20.0,
        )
        self.assertEqual(bbox, (92, 92, 18, 18))


class PerceptionTests(unittest.TestCase):
    def test_front_uses_bgr_color_space_for_real_lekiwi_frames(self):
        frame = np.zeros((220, 220, 3), dtype=np.uint8)
        frame[80:140, 80:140] = (255, 0, 0)

        target = FrontPerception(canonical_size=(220, 220)).analyze(
            frame,
            "pick_fuse",
            target_color="blue",
            target_slot="fuse_supply",
        )

        self.assertTrue(target.found)
        self.assertEqual(target.label, "blue_fuse")

    def test_front_pick_debris_defaults_to_centered_candidate(self):
        frame = np.full((200, 200, 3), 255, dtype=np.uint8)
        frame[80:120, 85:115] = 0
        frame[20:60, 10:40] = 0

        target = FrontPerception(canonical_size=(200, 200)).analyze(frame, "pick_debris")

        self.assertTrue(target.found)
        self.assertIsNotNone(target.center_px)
        self.assertAlmostEqual(target.center_px[0], 100.0, delta=20.0)

    def test_front_uses_actual_frame_size_when_uncalibrated(self):
        frame = np.full((200, 200, 3), 255, dtype=np.uint8)
        frame[80:120, 85:115] = 0

        target = FrontPerception(canonical_size=(800, 600)).analyze(frame, "pick_debris")

        self.assertTrue(target.found)
        self.assertAlmostEqual(target.metadata["desired_center"][0], 100.0, delta=1.0)
        self.assertAlmostEqual(target.metadata["desired_center"][1], 100.0, delta=1.0)

    def test_front_transformer_requires_real_detection(self):
        frame = np.full((220, 220, 3), 255, dtype=np.uint8)

        target = FrontPerception(canonical_size=(220, 220)).analyze(frame, "replace_transformer", target_slot="left")

        self.assertFalse(target.found)

    def test_wrist_generic_pick_prefers_center_candidate(self):
        frame = np.full((200, 200, 3), 255, dtype=np.uint8)
        frame[85:125, 88:118] = 0
        frame[10:50, 150:180] = 0

        target = WristPerception().analyze(frame, "pick_debris")

        self.assertTrue(target.found)
        self.assertIsNotNone(target.center_px)
        self.assertAlmostEqual(target.center_px[0], 103.0, delta=20.0)

    def test_wrist_uses_bgr_color_space_for_real_lekiwi_frames(self):
        frame = np.zeros((220, 220, 3), dtype=np.uint8)
        frame[80:140, 80:140] = (255, 0, 0)

        target = WristPerception().analyze(frame, "pick_fuse", target_color="blue")

        self.assertTrue(target.found)
        self.assertEqual(target.label, "blue_fuse_precision")

    def test_wrist_low_contrast_object_is_still_detected(self):
        frame = np.full((240, 240, 3), 170, dtype=np.uint8)
        frame[90:150, 95:145] = 140

        target = WristPerception().analyze(frame, "pick_debris")

        self.assertTrue(target.found)
        self.assertIsNotNone(target.center_px)
        self.assertAlmostEqual(target.center_px[0], 120.0, delta=25.0)
        self.assertAlmostEqual(target.center_px[1], 120.0, delta=25.0)


if __name__ == "__main__":
    unittest.main()
