from __future__ import annotations

import os
import platform
from importlib.util import find_spec
from dataclasses import dataclass
from pathlib import Path

import httpx

from .backup import repository_status
from .config import Config
from .models import model_status
from .taxonomy import is_packaged_taxonomy, load_taxonomy, packaged_taxonomy_path
from .webdav import storage_available
from .zotero import ZoteroClient


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


def _writable_parent(path: Path) -> bool:
    candidate = path.expanduser()
    if candidate.exists():
        return candidate.is_file() and os.access(candidate, os.W_OK)
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate.is_dir() and os.access(candidate, os.W_OK)


def run_checks(config: Config) -> list[Check]:
    checks: list[Check] = []
    client = ZoteroClient(config.zotero)
    try:
        version = client.library_version()
        app_version = f"Zotero {client.zotero_version}; " if client.zotero_version else ""
        checks.append(
            Check("Zotero Local API", True, f"available; {app_version}library version {version}")
        )
        try:
            client.require_local_write_support()
            checks.append(Check("Zotero Local API writes", True, "available"))
        except RuntimeError as exc:
            checks.append(Check("Zotero Local API writes", False, str(exc)))
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 403:
            detail = "disabled; enable 'Allow other applications' in Zotero Settings > Advanced"
        else:
            detail = f"HTTP {exc.response.status_code}"
        checks.append(Check("Zotero Local API", False, detail))
    except httpx.HTTPError as exc:
        checks.append(Check("Zotero Local API", False, f"unavailable: {exc}"))
    except (KeyError, ValueError) as exc:
        checks.append(Check("Zotero Local API", False, f"invalid response: {exc}"))
    finally:
        client.close()

    attachment_path = config.attachments.path
    checks.append(
        Check(
            "Attachment storage",
            storage_available(attachment_path),
            str(attachment_path),
        )
    )
    backup_source = config.backup.source
    checks.append(
        Check(
            "Backup source",
            storage_available(backup_source),
            str(backup_source),
        )
    )
    checks.append(
        Check(
            "State location",
            _writable_parent(config.state.database),
            str(config.state.database),
        )
    )
    taxonomy_path = config.taxonomy.path or packaged_taxonomy_path()
    if not taxonomy_path.expanduser().is_file():
        checks.append(
            Check(
                "Taxonomy",
                False,
                f"missing: {taxonomy_path}; run zotero-organiser taxonomy init",
            )
        )
    else:
        try:
            taxonomy = load_taxonomy(taxonomy_path)
            packaged = is_packaged_taxonomy(taxonomy_path)
            if packaged and config.safety.write_enabled:
                checks.append(
                    Check(
                        "Taxonomy",
                        False,
                        f"packaged starter at {taxonomy_path}; copy with taxonomy init before enabling writes",
                    )
                )
            elif packaged:
                checks.append(
                    Check(
                        "Taxonomy",
                        True,
                        f"packaged starter at {taxonomy_path}; run taxonomy init before enabling writes",
                    )
                )
            else:
                checks.append(
                    Check(
                        "Taxonomy",
                        True,
                        f"{taxonomy_path}; v{taxonomy.version}; {len(taxonomy.tags())} tags",
                    )
                )
        except Exception as exc:
            checks.append(Check("Taxonomy", False, str(exc)))
    backup = repository_status(config.backup)
    checks.append(Check("Restic repository", backup.available, backup.detail))

    local = config.local_classifier
    if local.enabled:
        required = ("fastembed", "torch", "transformers")
        local_ready = all(find_spec(package) is not None for package in required)
        local_detail = (
            f"{local.model}; runtime available"
            if local_ready
            else "install zotero-organiser[ranker] (or [ranker-gpu]) and [local-classifier]"
        )
        checks.append(Check("Local NLI classifier", local_ready, local_detail))
        checks.append(_device_check(config))
    for status in model_status(config):
        checks.append(
            Check(f"{status.name} model", status.cached, f"{status.model}; {status.detail}")
        )

    key_name = config.classification.api_key_env
    if local.enabled and local.mode == "primary" and not local.fallback_to_remote:
        classifier_ready = True
        classifier_detail = "not required; local primary classifier has no remote fallback"
    elif not config.classification.enabled:
        classifier_ready = True
        classifier_detail = "disabled"
    else:
        classifier_ready = bool(os.environ.get(key_name))
        classifier_detail = f"{key_name} is {'set' if classifier_ready else 'missing'}"
    checks.append(Check("Classifier credentials", classifier_ready, classifier_detail))
    return checks


def _device_check(config: Config) -> Check:
    device = config.local_classifier.device
    if device == "auto":
        return Check("Local NLI device", True, "auto")
    try:
        import torch
    except ImportError:
        return Check("Local NLI device", False, "torch is not installed")
    if device == "cuda" and not torch.cuda.is_available():
        return Check(
            "Local NLI device",
            False,
            "cuda requested but torch.cuda.is_available() is false",
        )
    if device == "mps":
        mps = getattr(torch.backends, "mps", None)
        available = platform.system() == "Darwin" and mps is not None and mps.is_available()
        if not available:
            return Check("Local NLI device", False, "mps requested but is not available")
    return Check("Local NLI device", True, device)
