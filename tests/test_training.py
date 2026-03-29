import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skills2026.profile import Skills2026Profile
from skills2026.training import (
    DatasetManifest,
    PickupGateStamp,
    describe_replay_gate_failure,
    ensure_manifest_matches_profile,
    latest_passing_pickup_stamp,
    pickup_setup_signature,
    save_dataset_manifest,
    sync_manifest_from_dataset,
)


class TrainingManifestTests(unittest.TestCase):
    def test_manifest_requires_all_reviews_and_pickup_gate(self):
        profile = Skills2026Profile.defaults("test")
        manifest = DatasetManifest.create(profile, "test_insert_fuse", "insert_fuse")
        manifest.sync_episode_count(2)
        manifest.mark_replay_approval(episode_index=0, status="pass", profile=profile)
        self.assertFalse(manifest.act_ready)
        self.assertIn("missing replay review: 1", describe_replay_gate_failure(manifest))

        manifest.mark_replay_approval(episode_index=1, status="pass", profile=profile)
        self.assertFalse(manifest.act_ready)
        manifest.mark_pickup_validation(
            PickupGateStamp(
                primitive_name="pick_fuse",
                suite_name="ecu",
                scenario_name="fuse_supply_pickup",
                report_path="/tmp/report.json",
                report_created_at="2026-03-29T10:00:00",
                stamped_at="2026-03-29T10:05:00",
                passed=True,
            )
        )
        self.assertTrue(manifest.act_ready)

    def test_manifest_rejects_profile_signature_mismatch(self):
        profile = Skills2026Profile.defaults("test")
        manifest = DatasetManifest.create(profile, "test_insert_fuse", "insert_fuse")
        other_profile = Skills2026Profile.defaults("test")
        other_profile.cameras["front"].source_id = 99
        with self.assertRaises(ValueError):
            ensure_manifest_matches_profile(manifest, other_profile, dataset_name="test_insert_fuse")

    def test_sync_manifest_from_dataset_reads_info_json(self):
        profile = Skills2026Profile.defaults("test")
        manifest = DatasetManifest.create(profile, "test_insert_fuse", "insert_fuse")
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset_root = Path(temp_dir)
            meta_dir = dataset_root / "meta"
            meta_dir.mkdir(parents=True, exist_ok=True)
            (meta_dir / "info.json").write_text(json.dumps({"total_episodes": 3}))
            save_dataset_manifest(dataset_root, manifest)
            synced = sync_manifest_from_dataset(dataset_root, manifest)
            self.assertEqual(synced.recorded_episode_count, 3)

    def test_latest_passing_pickup_stamp_uses_matching_profile_and_scenario(self):
        report = {
            "profile_name": "alpha",
            "profile_signature": pickup_setup_signature(Skills2026Profile.defaults("alpha")),
            "suite_name": "ecu",
            "created_at": "2026-03-29T12:00:00",
            "scenarios": [
                {
                    "scenario": {
                        "name": "fuse_supply_pickup",
                        "primitive_name": "pick_fuse",
                    },
                    "successes": 2,
                    "attempts": 2,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = Path(temp_dir)
            (logs_dir / "pickup_validation_alpha_ecu_20260329_120000.json").write_text(
                json.dumps(report)
            )
            with patch("skills2026.training.LOGS_DIR", logs_dir):
                stamp = latest_passing_pickup_stamp(Skills2026Profile.defaults("alpha"), "insert_fuse")
            self.assertIsNotNone(stamp)
            assert stamp is not None
            self.assertEqual(stamp.primitive_name, "pick_fuse")
            self.assertEqual(stamp.suite_name, "ecu")

    def test_latest_passing_pickup_stamp_rejects_stale_setup_signature(self):
        profile = Skills2026Profile.defaults("alpha")
        stale_profile = Skills2026Profile.defaults("alpha")
        stale_profile.service_poses["tray_grasp"] = {"arm_shoulder_pan.pos": 9.0}
        report = {
            "profile_name": "alpha",
            "profile_signature": pickup_setup_signature(stale_profile),
            "suite_name": "ecu",
            "created_at": "2026-03-29T12:00:00",
            "scenarios": [
                {
                    "scenario": {
                        "name": "fuse_supply_pickup",
                        "primitive_name": "pick_fuse",
                    },
                    "successes": 2,
                    "attempts": 2,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = Path(temp_dir)
            (logs_dir / "pickup_validation_alpha_ecu_20260329_120000.json").write_text(
                json.dumps(report)
            )
            with patch("skills2026.training.LOGS_DIR", logs_dir):
                stamp = latest_passing_pickup_stamp(profile, "insert_fuse")
            self.assertIsNone(stamp)

    def test_latest_passing_pickup_stamp_rejects_older_pass_when_newer_report_failed(self):
        profile = Skills2026Profile.defaults("alpha")
        signature = pickup_setup_signature(profile)
        passing_report = {
            "profile_name": "alpha",
            "profile_signature": signature,
            "suite_name": "ecu",
            "created_at": "2026-03-29T11:00:00",
            "scenarios": [
                {
                    "scenario": {"name": "fuse_supply_pickup", "primitive_name": "pick_fuse"},
                    "successes": 2,
                    "attempts": 2,
                }
            ],
        }
        failing_report = {
            "profile_name": "alpha",
            "profile_signature": signature,
            "suite_name": "ecu",
            "created_at": "2026-03-29T12:00:00",
            "scenarios": [
                {
                    "scenario": {"name": "fuse_supply_pickup", "primitive_name": "pick_fuse"},
                    "successes": 1,
                    "attempts": 2,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = Path(temp_dir)
            older = logs_dir / "pickup_validation_alpha_ecu_older.json"
            newer = logs_dir / "pickup_validation_alpha_ecu_newer.json"
            older.write_text(json.dumps(passing_report))
            newer.write_text(json.dumps(failing_report))
            os.utime(older, (1, 1))
            os.utime(newer, (2, 2))
            with patch("skills2026.training.LOGS_DIR", logs_dir):
                stamp = latest_passing_pickup_stamp(profile, "insert_fuse")
            self.assertIsNone(stamp)


if __name__ == "__main__":
    unittest.main()
