from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zotero_organiser.webdav import attachment_ready, storage_available


class StorageTests(unittest.TestCase):
    def test_mac_storage_key_layout_is_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            item_dir = root / "ABCD1234"
            item_dir.mkdir()
            (item_dir / "paper.pdf").write_bytes(b"pdf")
            attachments = [
                {
                    "key": "ABCD1234",
                    "data": {
                        "itemType": "attachment",
                        "linkMode": "imported_file",
                        "filename": "paper.pdf",
                    },
                }
            ]
            self.assertTrue(storage_available(root))
            self.assertTrue(attachment_ready(root, attachments))

    def test_missing_stored_attachment_is_not_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            attachments = [
                {
                    "key": "MISSING1",
                    "data": {
                        "itemType": "attachment",
                        "linkMode": "imported_file",
                        "filename": "paper.pdf",
                    },
                }
            ]
            self.assertFalse(attachment_ready(Path(directory), attachments))

    def test_linked_files_do_not_block_readiness(self):
        with tempfile.TemporaryDirectory() as directory:
            attachments = [
                {
                    "key": "LINKED01",
                    "data": {
                        "itemType": "attachment",
                        "linkMode": "linked_file",
                        "filename": "elsewhere.pdf",
                    },
                }
            ]
            self.assertTrue(attachment_ready(Path(directory), attachments))


if __name__ == "__main__":
    unittest.main()
