from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from zotero_organiser.backup import RepositoryStatus
from zotero_organiser.config import Config
from zotero_organiser.doctor import _writable_parent, run_checks


class DoctorTests(unittest.TestCase):
    def test_existing_writable_state_database_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "state.sqlite"
            database.touch()
            self.assertTrue(_writable_parent(database))

    def config(self, root: Path) -> Config:
        storage = root / "storage"
        storage.mkdir()
        return Config.model_validate(
            {
                "zotero": {},
                "attachments": {"path": storage},
                "backup": {
                    "source": storage,
                    "repository": str(root / "restic"),
                    "prewrite_dir": root / "prewrite",
                },
                "state": {"database": root / "state" / "state.sqlite"},
            }
        )

    @patch(
        "zotero_organiser.doctor.repository_status",
        return_value=RepositoryStatus(True, "repository is accessible"),
    )
    @patch("zotero_organiser.doctor.ZoteroClient")
    def test_ready_environment(self, client_type, _repository):
        client_type.return_value.library_version.return_value = 42
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(os.environ, {"OPENAI_API_KEY": "set"}),
        ):
            checks = run_checks(self.config(Path(directory)))
        self.assertTrue(all(check.ok for check in checks))

    @patch(
        "zotero_organiser.doctor.repository_status",
        return_value=RepositoryStatus(False, "restic missing"),
    )
    @patch("zotero_organiser.doctor.ZoteroClient")
    def test_disabled_local_api_and_missing_services_are_reported(self, client_type, _repository):
        request = httpx.Request("GET", "http://127.0.0.1:23119/api/users/0/items")
        response = httpx.Response(403, request=request)
        client_type.return_value.library_version.side_effect = httpx.HTTPStatusError(
            "forbidden", request=request, response=response
        )
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            raw = self.config(Path(directory)).model_dump(mode="json")
            raw["classification"] = {"enabled": True}
            checks = run_checks(Config.model_validate(raw))
        by_name = {check.name: check for check in checks}
        self.assertFalse(by_name["Zotero Local API"].ok)
        self.assertIn("Allow other applications", by_name["Zotero Local API"].detail)
        self.assertFalse(by_name["Restic repository"].ok)
        self.assertFalse(by_name["Classifier credentials"].ok)

    @patch(
        "zotero_organiser.doctor.repository_status",
        return_value=RepositoryStatus(True, "repository is accessible"),
    )
    @patch("zotero_organiser.doctor.ZoteroClient")
    def test_local_primary_without_fallback_does_not_require_remote_credentials(
        self, client_type, _repository
    ):
        client_type.return_value.library_version.return_value = 42
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            raw = self.config(Path(directory)).model_dump(mode="json")
            raw["ranking"] = {"enabled": True}
            raw["local_classifier"] = {
                "enabled": True,
                "mode": "primary",
                "fallback_to_remote": False,
            }
            checks = run_checks(Config.model_validate(raw))
        by_name = {check.name: check for check in checks}
        self.assertTrue(by_name["Classifier credentials"].ok)
        self.assertIn("not required", by_name["Classifier credentials"].detail)

    @patch(
        "zotero_organiser.doctor.repository_status",
        return_value=RepositoryStatus(True, "repository is accessible"),
    )
    @patch("zotero_organiser.doctor.ZoteroClient")
    def test_local_models_fail_when_weights_are_not_cached(self, client_type, _repository):
        client_type.return_value.library_version.return_value = 42
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            raw = self.config(Path(directory)).model_dump(mode="json")
            raw["ranking"] = {
                "enabled": True,
                "cache_dir": str(Path(directory) / "empty-ranker"),
            }
            raw["local_classifier"] = {
                "enabled": True,
                "mode": "primary",
                "fallback_to_remote": False,
            }
            with patch(
                "zotero_organiser.models.huggingface_hub_dir",
                return_value=Path(directory) / "hub",
            ):
                checks = run_checks(Config.model_validate(raw))
        by_name = {check.name: check for check in checks}
        self.assertFalse(by_name["Embedding model"].ok)
        self.assertFalse(by_name["NLI reranker model"].ok)
        self.assertIn("models download", by_name["Embedding model"].detail)

    @patch(
        "zotero_organiser.doctor.repository_status",
        return_value=RepositoryStatus(True, "repository is accessible"),
    )
    @patch("zotero_organiser.doctor.ZoteroClient")
    def test_packaged_taxonomy_fails_when_writes_are_enabled(self, client_type, _repository):
        client_type.return_value.library_version.return_value = 42
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(os.environ, {"OPENAI_API_KEY": "set"}),
        ):
            raw = self.config(Path(directory)).model_dump(mode="json")
            raw["safety"] = {"write_enabled": True}
            checks = run_checks(Config.model_validate(raw))
        by_name = {check.name: check for check in checks}
        self.assertFalse(by_name["Taxonomy"].ok)
        self.assertIn("packaged starter", by_name["Taxonomy"].detail)

    @patch(
        "zotero_organiser.doctor.repository_status",
        return_value=RepositoryStatus(True, "repository is accessible"),
    )
    @patch("zotero_organiser.doctor.ZoteroClient")
    def test_user_taxonomy_copy_is_ok_with_writes_enabled(self, client_type, _repository):
        client_type.return_value.library_version.return_value = 42
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(os.environ, {"OPENAI_API_KEY": "set"}),
        ):
            from zotero_organiser.taxonomy import install_user_taxonomy

            root = Path(directory)
            user_taxonomy = root / "taxonomy.yml"
            install_user_taxonomy(user_taxonomy)
            raw = self.config(root).model_dump(mode="json")
            raw["safety"] = {"write_enabled": True}
            raw["taxonomy"] = {"path": str(user_taxonomy)}
            checks = run_checks(Config.model_validate(raw))
        by_name = {check.name: check for check in checks}
        self.assertTrue(by_name["Taxonomy"].ok)
        self.assertIn(str(user_taxonomy), by_name["Taxonomy"].detail)


if __name__ == "__main__":
    unittest.main()
