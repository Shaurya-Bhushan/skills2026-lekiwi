import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skills2026.hardware import assess_camera_framing


class HardwareFramingTests(unittest.TestCase):
    def test_camera_framing_accepts_textured_scene(self):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        frame[40:200, 40:280] = (90, 120, 160)
        frame[80:120, 80:240] = (20, 20, 20)
        frame[140:180, 120:240] = (240, 240, 240)
        ok, detail = assess_camera_framing(frame, "front")

        self.assertTrue(ok)
        self.assertIn("framing looks usable", detail)

    def test_camera_framing_rejects_blank_scene(self):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        ok, detail = assess_camera_framing(frame, "wrist")

        self.assertFalse(ok)
        self.assertIn("framing looks weak", detail)


if __name__ == "__main__":
    unittest.main()
