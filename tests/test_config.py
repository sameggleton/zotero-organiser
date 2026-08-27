from __future__ import annotations

import os
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch

import yaml

from zotero_organiser.cli import default_taxonomy_path, resolve_taxonomy_path
from zotero_organiser.config import (
    Config,
    SafetyConfig,
    default_config_path,
    default_environment_path,
    default_user_taxonomy_path,
    load_config,
    load_environment,
)


class ConfigTests(unittest.TestCase):
    def base_config(self) -> dict:
        return {
            "zotero": {},
            "attachments": {"path": "/tmp/storage"},
            "backup": {"repository": "/tmp/restic", "prewrite_dir": "/tmp/prewrite"},
            "state": {"database": "/tmp/state.sqlite"},
        }

    def test_backup_source_defaults_to_attachment_storage(self):
        config = Config.model_validate(self.base_config())
        self.assertEqual(config.backup.source, Path("/tmp/storage"))

    def test_legacy_webdav_path_remains_supported(self):
        raw = self.base_config()
        raw["webdav"] = {"path": "/srv/zotero-webdav"}
        del raw["attachments"]
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            config = Config.model_validate(raw)
        self.assertEqual(config.attachments.path, Path("/srv/zotero-webdav"))
        self.assertTrue(any("deprecated" in str(item.message) for item in caught))

    def test_platform_profiles_validate(self):
        root = Path(__file__).parents[1]
        for name in ("config.macos.example.yml", "config.ubuntu.example.yml"):
            raw = yaml.safe_load((root / name).read_text())
            config = Config.model_validate(raw)
            self.assertIsNotNone(config.attachments)
            self.assertIsNotNone(config.backup.source)

    def test_default_config_path_uses_home_config_directory(self):
        with patch.dict(os.environ, {"HOME": "/Users/test"}, clear=True):
            self.assertEqual(
                default_config_path(), Path("/Users/test/.config/zotero-organiser/config.yml")
            )
            self.assertEqual(
                default_environment_path(), Path("/Users/test/.config/zotero-organiser/environment")
            )
            self.assertEqual(
                default_user_taxonomy_path(),
                Path("/Users/test/.config/zotero-organiser/taxonomy.yml"),
            )
            self.assertEqual(
                default_user_taxonomy_path(Path("/tmp/custom/config.yml")),
                Path("/tmp/custom/taxonomy.yml"),
            )

    def test_default_config_path_honours_xdg_override(self):
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": "/tmp/config"}, clear=False):
            self.assertEqual(default_config_path(), Path("/tmp/config/zotero-organiser/config.yml"))

    def test_environment_file_preserves_existing_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "environment"
            path.write_text('EXISTING="from file"\nNEW_VALUE="with spaces"\nEMPTY=\n')
            with patch.dict(os.environ, {"EXISTING": "from shell"}, clear=False):
                self.assertTrue(load_environment(path))
                self.assertEqual(os.environ["EXISTING"], "from shell")
                self.assertEqual(os.environ["NEW_VALUE"], "with spaces")
                self.assertEqual(os.environ["EMPTY"], "")
                os.environ.pop("NEW_VALUE", None)
                os.environ.pop("EMPTY", None)

    def test_conservative_safety_defaults(self):
        config = Config.model_validate(self.base_config())
        self.assertFalse(config.safety.write_enabled)
        self.assertTrue(config.safety.require_backup)
        self.assertTrue(config.safety.only_new_items)
        self.assertFalse(config.safety.allow_tag_removal)
        self.assertEqual(config.safety.max_items_per_cycle, 5)
        self.assertNotIn("allow_collection_changes", SafetyConfig.model_fields)
        self.assertFalse(hasattr(config.safety, "allow_collection_changes"))

    def test_allow_collection_changes_in_yaml_is_ignored(self):
        raw = self.base_config()
        raw["safety"] = {"allow_collection_changes": True, "write_enabled": False}
        config = Config.model_validate(raw)
        self.assertFalse(config.safety.write_enabled)
        self.assertFalse(hasattr(config.safety, "allow_collection_changes"))

    def test_taxonomy_path_is_read_from_config(self):
        with tempfile.TemporaryDirectory() as directory:
            custom = Path(directory) / "custom.yml"
            path = Path(directory) / "config.yml"
            raw = self.base_config()
            raw["taxonomy"] = {"path": str(custom)}
            path.write_text(yaml.safe_dump(raw))
            config = load_config(path)
            self.assertEqual(config.taxonomy.path, custom)

    def test_taxonomy_cli_flag_overrides_config_path(self):
        raw = self.base_config()
        raw["taxonomy"] = {"path": "/tmp/from-config.yml"}
        config = Config.model_validate(raw)
        self.assertEqual(
            resolve_taxonomy_path(Path("/tmp/from-cli.yml"), config),
            Path("/tmp/from-cli.yml"),
        )
        self.assertEqual(resolve_taxonomy_path(None, config), Path("/tmp/from-config.yml"))
        self.assertEqual(resolve_taxonomy_path(None, None), default_taxonomy_path())

    def test_default_taxonomy_path_from_real_cli_is_a_file(self):
        from zotero_organiser import cli as real_cli

        path = default_taxonomy_path()
        self.assertEqual(path, Path(real_cli.__file__).with_name("taxonomy.yml"))
        self.assertTrue(path.is_file())

    def test_packaged_taxonomy_is_module_adjacent(self):
        with tempfile.TemporaryDirectory() as directory:
            packaged = Path(directory) / "site-packages" / "zotero_organiser"
            packaged.mkdir(parents=True)
            (packaged / "taxonomy.yml").write_text("packaged\n")
            (packaged / "cli.py").write_text("")
            path = default_taxonomy_path(packaged / "cli.py")
            self.assertEqual(path, packaged / "taxonomy.yml")
            self.assertTrue(path.is_file())

    def test_editable_layout_does_not_walk_repo_root_taxonomy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            module = root / "src" / "zotero_organiser" / "cli.py"
            module.parent.mkdir(parents=True)
            module.write_text("")
            (root / "taxonomy.yml").write_text("repo-root\n")
            path = default_taxonomy_path(module)
            self.assertEqual(path, module.with_name("taxonomy.yml"))
            self.assertFalse(path.exists())
            self.assertNotEqual(path, root / "taxonomy.yml")

    def test_omitted_classification_does_not_enable_remote(self):
        config = Config.model_validate(self.base_config())
        self.assertFalse(config.classification.enabled)
        self.assertFalse(config.ranking.enabled)
        self.assertFalse(config.local_classifier.enabled)

    def test_omitted_local_classifier_model_defaults_to_large_nli(self):
        raw = self.base_config()
        raw["ranking"] = {"enabled": True}
        raw["local_classifier"] = {
            "enabled": True,
            "mode": "primary",
            "fallback_to_remote": True,
        }
        config = Config.model_validate(raw)
        self.assertEqual(config.local_classifier.model, "tasksource/ModernBERT-large-nli")

    def test_fastembed_gpu_backend_is_accepted(self):
        raw = self.base_config()
        raw["ranking"] = {"enabled": True, "backend": "fastembed-gpu"}
        config = Config.model_validate(raw)
        self.assertEqual(config.ranking.backend, "fastembed-gpu")

    def test_local_classifier_requires_candidate_ranking(self):
        raw = self.base_config()
        raw["local_classifier"] = {"enabled": True}
        with self.assertRaisesRegex(ValueError, "requires ranking.enabled"):
            Config.model_validate(raw)

    def test_personalization_requires_candidate_ranking(self):
        raw = self.base_config()
        raw["personalization"] = {"enabled": True}
        with self.assertRaisesRegex(ValueError, "requires ranking.enabled"):
            Config.model_validate(raw)


if __name__ == "__main__":
    unittest.main()
