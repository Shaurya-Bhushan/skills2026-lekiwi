import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skills2026.commands import train_act as train_act_command
from skills2026.profile import Skills2026Profile
from skills2026.training import DatasetManifest, PickupGateStamp, load_dataset_manifest, save_dataset_manifest


class TrainActCommandTests(unittest.TestCase):
    def _ready_manifest(self, profile: Skills2026Profile) -> DatasetManifest:
        manifest = DatasetManifest.create(profile, "alpha_insert_fuse", "insert_fuse")
        manifest.sync_episode_count(2)
        manifest.mark_replay_approval(episode_index=0, status="pass", profile=profile)
        manifest.mark_replay_approval(episode_index=1, status="pass", profile=profile)
        return manifest

    def test_train_act_blocks_when_replay_reviews_missing(self):
        profile = Skills2026Profile.defaults("alpha")
        manifest = DatasetManifest.create(profile, "alpha_insert_fuse", "insert_fuse")
        manifest.sync_episode_count(2)
        manifest.mark_replay_approval(episode_index=0, status="pass", profile=profile)
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset_root = Path(temp_dir) / "alpha_insert_fuse"
            meta_dir = dataset_root / "meta"
            meta_dir.mkdir(parents=True, exist_ok=True)
            (meta_dir / "info.json").write_text(json.dumps({"total_episodes": 2}))
            save_dataset_manifest(dataset_root, manifest)
            args = Namespace(
                profile="alpha",
                primitive="insert_fuse",
                dataset_name="alpha_insert_fuse",
                policy_device="cpu",
                steps=20000,
                batch_size=8,
                output_dir="",
                job_name="",
                wandb=False,
                push_to_hub=False,
                policy_repo_id="",
                dry_run=True,
            )
            with patch.object(train_act_command, "load_profile", return_value=profile), patch.object(
                train_act_command, "DATASETS_DIR", Path(temp_dir)
            ):
                with self.assertRaises(RuntimeError):
                    train_act_command.run(args)

    def test_train_act_dry_run_succeeds_with_reviewed_dataset(self):
        profile = Skills2026Profile.defaults("alpha")
        manifest = self._ready_manifest(profile)
        pickup_stamp = PickupGateStamp(
            primitive_name="pick_fuse",
            suite_name="ecu",
            scenario_name="fuse_supply_pickup",
            report_path="/tmp/pickup_report.json",
            report_created_at="2026-03-29T12:00:00",
            stamped_at="2026-03-29T12:05:00",
            passed=True,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset_root = Path(temp_dir) / "alpha_insert_fuse"
            meta_dir = dataset_root / "meta"
            meta_dir.mkdir(parents=True, exist_ok=True)
            (meta_dir / "info.json").write_text(json.dumps({"total_episodes": 2}))
            save_dataset_manifest(dataset_root, manifest)
            args = Namespace(
                profile="alpha",
                primitive="insert_fuse",
                dataset_name="alpha_insert_fuse",
                policy_device="cpu",
                steps=20000,
                batch_size=8,
                output_dir="",
                job_name="",
                wandb=False,
                push_to_hub=False,
                policy_repo_id="",
                dry_run=True,
            )
            with patch.object(train_act_command, "load_profile", return_value=profile), patch.object(
                train_act_command, "DATASETS_DIR", Path(temp_dir)
            ), patch.object(
                train_act_command,
                "latest_passing_pickup_stamp",
                return_value=pickup_stamp,
            ):
                exit_code = train_act_command.run(args)

            self.assertEqual(exit_code, 0)
            saved = load_dataset_manifest(dataset_root)
            self.assertIsNotNone(saved)
            assert saved is not None
            self.assertIsNone(saved.pickup_validation)


if __name__ == "__main__":
    unittest.main()
