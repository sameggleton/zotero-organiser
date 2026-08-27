from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from zotero_organiser.backup import repository_status
from zotero_organiser.config import BackupConfig


class BackupTests(unittest.TestCase):
    def config(self, **overrides) -> BackupConfig:
        values = {
            "source": "/tmp/source",
            "repository": "/tmp/restic",
            "prewrite_dir": "/tmp/prewrite",
        }
        values.update(overrides)
        return BackupConfig.model_validate(values)

    @patch("zotero_organiser.backup.shutil.which", return_value=None)
    def test_missing_restic_is_unavailable(self, _which):
        status = repository_status(self.config())
        self.assertFalse(status.available)
        self.assertIn("not installed", status.detail)

    @patch("zotero_organiser.backup.subprocess.run")
    @patch("zotero_organiser.backup.shutil.which", return_value="/opt/homebrew/bin/restic")
    def test_local_and_remote_repositories_use_restic_preflight(self, _which, run):
        run.return_value = subprocess.CompletedProcess([], 0, "[]", "")
        for repository in ("/tmp/restic", "sftp:user@example:/backups/zotero"):
            status = repository_status(self.config(repository=repository))
            self.assertTrue(status.available)
        self.assertEqual(run.call_count, 2)

    @patch("zotero_organiser.backup.shutil.which", return_value="/usr/bin/restic")
    def test_missing_required_mount_blocks_external_repository(self, _which):
        with tempfile.TemporaryDirectory() as directory:
            mount = Path(directory) / "external"
            status = repository_status(
                self.config(
                    repository=str(mount / "restic"),
                    required_mount=mount,
                )
            )
        self.assertFalse(status.available)
        self.assertIn("required mount", status.detail)

    @patch("zotero_organiser.backup.subprocess.run")
    @patch("zotero_organiser.backup.os_access_writable", return_value=True)
    @patch("zotero_organiser.backup.Path.is_mount", return_value=True)
    @patch("zotero_organiser.backup.shutil.which", return_value="/usr/bin/restic")
    def test_mounted_external_repository_is_checked(self, _which, _is_mount, _writable, run):
        run.return_value = subprocess.CompletedProcess([], 0, "[]", "")
        with tempfile.TemporaryDirectory() as directory:
            mount = Path(directory)
            status = repository_status(
                self.config(
                    repository=str(mount / "restic"),
                    required_mount=mount,
                )
            )
        self.assertTrue(status.available)

    @patch("zotero_organiser.backup.subprocess.run")
    @patch("zotero_organiser.backup.shutil.which", return_value="/usr/bin/restic")
    def test_restic_error_is_reported(self, _which, run):
        run.return_value = subprocess.CompletedProcess([], 1, "", "repository does not exist\n")
        status = repository_status(self.config())
        self.assertFalse(status.available)
        self.assertEqual(status.detail, "repository does not exist")


if __name__ == "__main__":
    unittest.main()
