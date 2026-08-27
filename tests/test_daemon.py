"""Mocked write-path coverage for Organiser.

Live Restic/Zotero smoke (manual, not automated):
1. restic snapshots --latest 1 against the configured repository
2. zotero-organiser doctor
3. zotero-organiser dry-run <item>  (isolated SQLite; production state unchanged)
4. enable writes only on a disposable library copy
5. zotero-organiser once  (confirm snapshot id, prewrite JSON, If-Unmodified-Since-Version PUT)
6. confirm status/* and collections were not rewritten
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx

from zotero_organiser.backup import RepositoryStatus
from zotero_organiser.classify import Classification, Label
from zotero_organiser.config import Config, ZoteroConfig
from zotero_organiser.daemon import Organiser
from zotero_organiser.state import ItemState, SCHEMA_VERSION, StateStore
from zotero_organiser.taxonomy import Taxonomy
from zotero_organiser.test_assistant import isolated_config
from zotero_organiser.zotero import LocalWriteDenied, VersionConflict, ZoteroClient


def sample_taxonomy() -> Taxonomy:
    return Taxonomy.model_validate(
        {
            "version": "1",
            "classifier": {"semantic_namespaces": ["topic"]},
            "namespaces": {
                "topic": {"max_tags": 2, "values": {"solvation": {}, "screening": {}}},
            },
        }
    )


def sample_item(key: str = "ABCD1234", version: int = 3, item_tags: tuple[str, ...] = ()) -> dict:
    return {
        "key": key,
        "version": version,
        "data": {
            "key": key,
            "version": version,
            "itemType": "journalArticle",
            "title": "Solvation of ions",
            "abstractNote": "We study water.",
            "publicationTitle": "Journal",
            "dateAdded": "2024-06-01T00:00:00Z",
            "tags": [{"tag": tag} for tag in item_tags],
            "collections": ["C1"],
        },
    }


def make_config(root: Path, **safety) -> Config:
    storage = root / "storage"
    storage.mkdir()
    values = {
        "write_enabled": False,
        "require_backup": True,
        "only_new_items": True,
        "allow_tag_removal": False,
        "max_items_per_cycle": 5,
    }
    values.update(safety)
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
            "safety": values,
            "daemon": {
                "settle_seconds": 0,
                "poll_interval_seconds": 1,
                "max_attachment_wait_seconds": 0,
            },
        }
    )


class DaemonTests(unittest.TestCase):
    def organiser(self, root: Path, **safety) -> Organiser:
        config = make_config(root, **safety)
        organiser = Organiser(config, sample_taxonomy())
        organiser.zotero.close()
        zotero = MagicMock()
        zotero.server_id = "server"
        zotero.local_api_key = "local-key"
        zotero.zotero_version = "10.0.0"
        zotero.children.return_value = []
        zotero.get_item.return_value = sample_item()
        written = sample_item(version=4, item_tags=("topic/solvation",))
        zotero.update_tags.return_value = written
        organiser.zotero = zotero
        organiser.classifier = MagicMock()
        organiser.classifier.version = "test-classifier"
        organiser.classifier.ranker = None
        organiser.classifier.classify.return_value = Classification(
            tags=[Label(tag="topic/solvation", confidence=0.99)]
        )
        organiser.state.establish_baseline(1, baseline_at="2020-01-01T00:00:00+00:00")
        organiser.state.set_zotero_server_id("server")
        return organiser

    def test_schema_version_is_recorded_in_meta(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state" / "state.sqlite"
            store = StateStore(path)
            try:
                row = store.db.execute(
                    "SELECT value FROM meta WHERE key='schema_version'"
                ).fetchone()
                self.assertEqual(row["value"], str(SCHEMA_VERSION))
            finally:
                store.close()

    def test_existing_database_without_schema_version_is_stamped(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.sqlite"
            db = sqlite3.connect(path)
            db.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.commit()
            db.close()
            store = StateStore(path)
            try:
                row = store.db.execute(
                    "SELECT value FROM meta WHERE key='schema_version'"
                ).fetchone()
                self.assertEqual(row["value"], str(SCHEMA_VERSION))
            finally:
                store.close()

    def test_existing_state_directory_is_chmod_0700(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory) / "state-dir"
            parent.mkdir(mode=0o755)
            os.chmod(parent, 0o755)
            store = StateStore(parent / "state.sqlite")
            store.close()
            self.assertEqual(parent.stat().st_mode & 0o777, 0o700)

    def test_write_disabled_process_does_not_classify_or_upsert_pending(self):
        with tempfile.TemporaryDirectory() as directory:
            organiser = self.organiser(Path(directory), write_enabled=False)
            try:
                result = organiser.process("ABCD1234")
                self.assertEqual(result, {"skipped": "writes disabled"})
                organiser.classifier.classify.assert_not_called()
                organiser.zotero.update_tags.assert_not_called()
                self.assertIsNone(organiser.state.get("ABCD1234"))
            finally:
                organiser.close()

    def test_write_disabled_sync_discovers_without_reclassifying(self):
        with tempfile.TemporaryDirectory() as directory:
            organiser = self.organiser(Path(directory), write_enabled=False)
            try:
                organiser.zotero.changed_items.return_value = ([sample_item()], 6)
                organiser.sync()
                organiser.sync()
                organiser.classifier.classify.assert_not_called()
                stored = organiser.state.get("ABCD1234")
                self.assertIsNotNone(stored)
                self.assertEqual(stored.state, "discovered")
                self.assertNotEqual(stored.state, "classifying")
            finally:
                organiser.close()

    def test_max_items_per_cycle_follows_pending_discovery_order(self):
        with tempfile.TemporaryDirectory() as directory:
            organiser = self.organiser(Path(directory), write_enabled=True, max_items_per_cycle=1)
            try:
                organiser.state.upsert(
                    ItemState("ZZZ99999", 1, "discovered"),
                    discovered_at="2020-01-01T00:00:00+00:00",
                )
                organiser.state.upsert(
                    ItemState("AAA00000", 1, "discovered"),
                    discovered_at="2020-01-02T00:00:00+00:00",
                )
                organiser.zotero.changed_items.return_value = ([], 1)
                organiser.process = MagicMock(return_value={"skipped": "unchanged"})
                organiser.sync()
                organiser.process.assert_called_once()
                self.assertEqual(organiser.process.call_args.args[0], "ZZZ99999")
            finally:
                organiser.close()

    @patch("zotero_organiser.daemon.restic_backup", return_value="snapdeadbeef")
    @patch("zotero_organiser.daemon.repository_status", return_value=RepositoryStatus(True, "ok"))
    def test_write_path_records_snapshot_prewrite_and_conditional_put(self, _status, _backup):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = make_config(root, write_enabled=True)
            item = sample_item()
            current = dict(item)
            puts: list[httpx.Request] = []

            def handler(request: httpx.Request) -> httpx.Response:
                headers = {
                    "Zotero-Server-ID": "local-server",
                    "Last-Modified-Version": str(current["version"]),
                }
                if request.method == "PUT":
                    puts.append(request)
                    payload = json.loads(request.content)
                    current["version"] = item["version"] + 1
                    current["data"] = payload
                    return httpx.Response(
                        200, headers=headers, json={"successful": {"0": item["key"]}}
                    )
                if str(request.url.path).endswith("/children"):
                    return httpx.Response(200, headers=headers, json=[])
                return httpx.Response(200, headers=headers, json=current)

            organiser = Organiser(config, sample_taxonomy())
            organiser.zotero.close()
            client = ZoteroClient(
                ZoteroConfig(),
                server_id="local-server",
                local_api_key="local-key",
                client=httpx.Client(transport=httpx.MockTransport(handler)),
            )
            client.zotero_version = "10.0.0"
            organiser.zotero = client
            organiser.classifier = MagicMock()
            organiser.classifier.version = "test-classifier"
            organiser.classifier.ranker = None
            organiser.classifier.classify.return_value = Classification(
                tags=[Label(tag="topic/solvation", confidence=0.99)]
            )
            organiser.state.establish_baseline(1, baseline_at="2020-01-01T00:00:00+00:00")
            organiser.state.set_zotero_server_id("local-server")
            try:
                result = organiser.process(item["key"])
                self.assertIn("topic/solvation", result["tags"])
                self.assertEqual(len(puts), 1)
                self.assertEqual(
                    puts[0].headers["If-Unmodified-Since-Version"], str(item["version"])
                )
                payload = json.loads(puts[0].content)
                self.assertEqual(payload["tags"], [{"tag": "topic/solvation"}])
                row = organiser.state.db.execute(
                    "SELECT backup_snapshot, prewrite_path, state FROM items WHERE item_key=?",
                    (item["key"],),
                ).fetchone()
                self.assertEqual(row["backup_snapshot"], "snapdeadbeef")
                self.assertEqual(row["state"], "organised")
                prewrite = Path(row["prewrite_path"])
                self.assertTrue(prewrite.is_file())
                self.assertEqual(json.loads(prewrite.read_text())["key"], item["key"])
            finally:
                organiser.close()

    @patch("zotero_organiser.daemon.restic_backup", return_value="snapdeadbeef")
    @patch("zotero_organiser.daemon.repository_status", return_value=RepositoryStatus(True, "ok"))
    def test_removed_auto_tag_is_suppressed_and_not_put(self, _status, _backup):
        with tempfile.TemporaryDirectory() as directory:
            organiser = self.organiser(Path(directory), write_enabled=True)
            try:
                stored = organiser.state.discover("ABCD1234", 3)
                stored.auto_tags = {"topic/solvation"}
                organiser.state.upsert(stored)
                organiser.zotero.get_item.return_value = sample_item(
                    "ABCD1234", 3, item_tags=("status/reading",)
                )
                organiser.zotero.update_tags.return_value = sample_item(
                    "ABCD1234", 4, item_tags=("status/reading",)
                )
                organiser.process("ABCD1234")
                desired = organiser.zotero.update_tags.call_args.args[1]
                self.assertNotIn("topic/solvation", desired)
                self.assertIn("status/reading", desired)
                after = organiser.state.get("ABCD1234")
                self.assertIn("topic/solvation", after.suppressed_tags)
            finally:
                organiser.close()

    @patch("zotero_organiser.daemon.restic_backup", return_value="snapdeadbeef")
    @patch("zotero_organiser.daemon.repository_status", return_value=RepositoryStatus(True, "ok"))
    def test_version_conflict_retries_put(self, _status, _backup):
        with tempfile.TemporaryDirectory() as directory:
            organiser = self.organiser(Path(directory), write_enabled=True)
            try:
                v1 = sample_item(version=3)
                v2 = sample_item(version=4)
                organiser.zotero.get_item.side_effect = [v1, v1, v2]
                organiser.zotero.update_tags.side_effect = [
                    VersionConflict("ABCD1234"),
                    sample_item(version=5, item_tags=("topic/solvation",)),
                ]
                organiser.process("ABCD1234")
                self.assertEqual(organiser.zotero.update_tags.call_count, 2)
            finally:
                organiser.close()

    @patch("zotero_organiser.daemon.restic_backup", return_value="snapdeadbeef")
    @patch("zotero_organiser.daemon.repository_status", return_value=RepositoryStatus(True, "ok"))
    def test_expired_authorization_reauths_and_retries_put(self, _status, _backup):
        with tempfile.TemporaryDirectory() as directory:
            organiser = self.organiser(Path(directory), write_enabled=True)
            try:
                organiser.zotero.local_api_key = "expired"
                organiser.zotero.authorize_write.return_value = "fresh-key"
                organiser.zotero.update_tags.side_effect = [
                    LocalWriteDenied("expired"),
                    sample_item(version=4, item_tags=("topic/solvation",)),
                ]
                organiser.process("ABCD1234")
                organiser.zotero.authorize_write.assert_called_once()
                self.assertEqual(organiser.zotero.update_tags.call_count, 2)
                self.assertEqual(organiser.state.get_local_api_key(), "fresh-key")
            finally:
                organiser.close()

    def test_dry_run_isolated_config_does_not_touch_production_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            production = make_config(root)
            production_store = StateStore(production.state.database)
            production_store.establish_baseline(1, baseline_at="2020-01-01T00:00:00+00:00")
            production_store.close()
            workspace = root / "preview"
            workspace.mkdir()
            organiser = Organiser(isolated_config(production, workspace), sample_taxonomy())
            organiser.zotero.close()
            organiser.zotero = MagicMock()
            organiser.zotero.children.return_value = []
            organiser.zotero.get_item.return_value = sample_item()
            organiser.classifier = MagicMock()
            organiser.classifier.version = "test-classifier"
            organiser.classifier.ranker = None
            organiser.classifier.classify.return_value = Classification(
                tags=[Label(tag="topic/solvation", confidence=0.99)]
            )
            try:
                result = organiser.process("ABCD1234", dry_run=True, force=True)
                self.assertIn("scores", result)
                organiser.classifier.classify.assert_called_once()
                organiser.zotero.update_tags.assert_not_called()
            finally:
                organiser.close()
            replay = StateStore(production.state.database)
            try:
                self.assertIsNone(replay.get("ABCD1234"))
                self.assertEqual(replay.pending_keys(), [])
            finally:
                replay.close()

    def test_run_does_not_swallow_keyboard_interrupt(self):
        with tempfile.TemporaryDirectory() as directory:
            organiser = self.organiser(Path(directory))
            organiser.sync = MagicMock(side_effect=KeyboardInterrupt)
            try:
                with self.assertRaises(KeyboardInterrupt):
                    organiser.run()
            finally:
                organiser.close()
            organiser.sync.assert_called_once()


if __name__ == "__main__":
    unittest.main()
