from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .config import BackupConfig


@dataclass(frozen=True)
class RepositoryStatus:
    available: bool
    detail: str


def repository_status(config: BackupConfig, *, timeout: int = 30) -> RepositoryStatus:
    executable = shutil.which("restic")
    if executable is None:
        return RepositoryStatus(False, "restic is not installed or not on PATH")

    if config.required_mount is not None:
        mount = config.required_mount
        repository = Path(config.repository).expanduser()
        try:
            repository.relative_to(mount)
        except ValueError:
            return RepositoryStatus(False, f"repository is not beneath required mount {mount}")
        try:
            if not mount.exists() or not mount.is_mount():
                return RepositoryStatus(False, f"required mount is unavailable: {mount}")
            if not os_access_writable(mount):
                return RepositoryStatus(False, f"required mount is not writable: {mount}")
        except OSError as exc:
            return RepositoryStatus(False, f"cannot inspect required mount: {exc}")

    try:
        result = subprocess.run(
            [executable, "--repo", config.repository, "snapshots", "--json", "--latest", "1"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return RepositoryStatus(False, f"restic repository check failed: {exc}")
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()
        return RepositoryStatus(
            False, detail[-1] if detail else "restic could not open the repository"
        )
    return RepositoryStatus(True, "repository is accessible")


def os_access_writable(path: Path) -> bool:
    import os

    return os.access(path, os.W_OK)


def restic_backup(repository: str, source: Path) -> str:
    result = subprocess.run(
        ["restic", "--repo", str(repository), "backup", "--json", str(source)],
        capture_output=True,
        text=True,
        check=True,
    )
    snapshots = re.findall(r'"snapshot_id"\s*:\s*"([0-9a-f]+)"', result.stdout)
    if not snapshots:
        raise RuntimeError("restic completed without returning a snapshot id")
    return snapshots[-1]


def save_prewrite(root: Path, item: dict) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S-%fZ")
    path = root / item["key"] / f"{timestamp}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(item, indent=2, sort_keys=True))
    return path
