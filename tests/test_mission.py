import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skills2026.control.primitives import PRIMITIVES
from skills2026.control.tasks import MISSION_PRESETS, TASKS


class MissionCatalogTests(unittest.TestCase):
    def test_full_match_covers_all_major_task_families(self):
        full_match = set(MISSION_PRESETS["full_match"])
        self.assertIn("clear_debris", full_match)
        self.assertIn("move_fallen_beams", full_match)
        self.assertIn("deliver_supply_item", full_match)
        self.assertIn("repair_fuse_circuit", full_match)
        self.assertIn("repair_board_circuit", full_match)
        self.assertIn("repair_transformer", full_match)
        self.assertIn("install_ecu_fan", full_match)
        self.assertIn("protect_workers", full_match)
        self.assertIn("deliver_steve", full_match)
        self.assertIn("flip_breaker", full_match)
        self.assertIn("final_position", full_match)

    def test_every_task_uses_known_primitives(self):
        for task in TASKS.values():
            for step in task.primitive_sequence:
                self.assertIn(step.primitive_name, PRIMITIVES)


if __name__ == "__main__":
    unittest.main()
