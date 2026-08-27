from __future__ import annotations

from pathlib import Path


def storage_available(storage_root: Path) -> bool:
    """Return false when Zotero's configured attachment tree cannot be inspected."""
    try:
        return storage_root.is_dir() and storage_root.exists()
    except OSError:
        return False


def attachment_ready(storage_root: Path, attachments: list[dict]) -> bool:
    """Check Zotero's conventional storage-key/filename layout, not metadata."""
    if not storage_available(storage_root):
        return False
    for attachment in attachments:
        data = attachment.get("data", {})
        if data.get("itemType") != "attachment" or data.get("linkMode") == "linked_file":
            continue
        filename = data.get("filename")
        if filename and not (storage_root / attachment["key"] / filename).is_file():
            return False
    return True


# Retained for callers importing the pre-0.2 name.
webdav_available = storage_available
