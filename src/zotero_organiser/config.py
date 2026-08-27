from __future__ import annotations

import os
import shlex
import warnings
from typing import Any, Literal
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator


def _expand(value: object) -> object:
    if isinstance(value, str):
        return os.path.expanduser(os.path.expandvars(value))
    if isinstance(value, dict):
        return {key: _expand(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand(item) for item in value]
    return value


class ZoteroConfig(BaseModel):
    mode: Literal["local"] = "local"
    base_url: str = "http://127.0.0.1:23119/api"
    app_name: str = "zotero-organiser"


class AttachmentStorageConfig(BaseModel):
    path: Path


class WebDAVConfig(AttachmentStorageConfig):
    """Compatibility model for configurations written before 0.2."""


class BackupConfig(BaseModel):
    source: Path
    repository: str
    required_mount: Path | None = None
    prewrite_dir: Path


class StateConfig(BaseModel):
    database: Path


class ClassificationConfig(BaseModel):
    """Remote OpenAI-compatible classifier. Off by default so omitted keys do not send metadata."""

    enabled: bool = False
    provider: str = "openai_compatible"
    endpoint: str = "https://api.openai.com/v1/chat/completions"
    api_key_env: str = "OPENAI_API_KEY"
    model: str = "gpt-4.1-mini"
    auto_accept_threshold: float = Field(default=0.92, ge=0, le=1)
    triage_threshold: float = Field(default=0.70, ge=0, le=1)


class RankingConfig(BaseModel):
    """Local candidate ranker."""

    enabled: bool = False
    mode: Literal["shadow", "shortlist"] = "shadow"
    backend: Literal["fastembed-cpu", "fastembed-gpu"] = "fastembed-cpu"
    model: str = "BAAI/bge-small-en-v1.5"
    cache_dir: Path = Field(default_factory=lambda: Path.home() / ".cache/zotero-organiser/ranker")
    dense_top_k: int = Field(default=24, gt=0)
    lexical_top_k: int = Field(default=12, gt=0)
    per_namespace_k: int = Field(default=3, gt=0)


class LocalClassifierConfig(BaseModel):
    """Local NLI scorer."""

    enabled: bool = False
    mode: Literal["shadow", "primary"] = "shadow"
    backend: Literal["transformers-nli"] = "transformers-nli"
    model: str = "tasksource/ModernBERT-large-nli"
    device: Literal["auto", "cpu", "mps", "cuda"] = "auto"
    batch_size: int = Field(default=8, gt=0)
    fallback_to_remote: bool = True


class PersonalizationConfig(BaseModel):
    """Local, user-approved tag preference profile for candidate retrieval."""

    enabled: bool = False
    mode: Literal["shadow", "rerank"] = "shadow"
    min_examples: int = Field(default=3, gt=0)
    weight: float = Field(default=0.12, ge=0, le=0.5)


class TaxonomyConfig(BaseModel):
    """Optional path to a user taxonomy; CLI --taxonomy overrides this."""

    path: Path | None = None


class SafetyConfig(BaseModel):
    # Deliberately opt in to externally visible changes.
    write_enabled: bool = False
    require_backup: bool = True
    only_new_items: bool = True
    allow_tag_removal: bool = False
    max_items_per_cycle: int = Field(default=5, gt=0)


class DaemonConfig(BaseModel):
    poll_interval_seconds: int = Field(default=60, gt=0)
    settle_seconds: int = Field(default=120, ge=0)
    max_attachment_wait_seconds: int = Field(default=1800, ge=0)
    allowed_item_types: set[str] = {
        "journalArticle",
        "conferencePaper",
        "preprint",
        "book",
        "bookSection",
        "thesis",
        "report",
    }


class Config(BaseModel):
    zotero: ZoteroConfig
    attachments: AttachmentStorageConfig
    webdav: WebDAVConfig | None = None
    backup: BackupConfig
    state: StateConfig
    taxonomy: TaxonomyConfig = Field(default_factory=TaxonomyConfig)
    classification: ClassificationConfig = ClassificationConfig()
    ranking: RankingConfig = RankingConfig()
    local_classifier: LocalClassifierConfig = LocalClassifierConfig()
    personalization: PersonalizationConfig = PersonalizationConfig()
    safety: SafetyConfig = SafetyConfig()
    daemon: DaemonConfig = DaemonConfig()

    @model_validator(mode="before")
    @classmethod
    def resolve_legacy_paths(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        raw = dict(value)
        if raw.get("attachments") is None:
            if raw.get("webdav") is None:
                return raw
            warnings.warn(
                "webdav.path is deprecated; use attachments.path",
                FutureWarning,
                stacklevel=2,
            )
            raw["attachments"] = raw["webdav"]
        backup = dict(raw.get("backup") or {})
        if backup.get("source") is None:
            backup["source"] = raw["attachments"]["path"]
        raw["backup"] = backup
        return raw

    @model_validator(mode="after")
    def validate_local_classifier(self) -> "Config":
        if self.local_classifier.enabled and not self.ranking.enabled:
            raise ValueError(
                "local_classifier requires ranking.enabled: true for candidate retrieval"
            )
        if self.personalization.enabled and not self.ranking.enabled:
            raise ValueError("personalization requires ranking.enabled: true for local embeddings")
        return self


def default_config_path() -> Path:
    root = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser()
    return root / "zotero-organiser/config.yml"


def default_environment_path() -> Path:
    return default_config_path().with_name("environment")


def default_user_taxonomy_path(config_path: Path | None = None) -> Path:
    """User-owned taxonomy next to the config file, not the packaged seed."""
    return (config_path or default_config_path()).with_name("taxonomy.yml")


def load_environment(path: Path | None) -> bool:
    """Load a small KEY=VALUE file without overriding the caller's environment."""
    if path is None or not path.exists():
        return False
    for line_number, raw_line in enumerate(path.read_text().splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ValueError(f"{path}:{line_number}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or not key.replace("_", "a").isalnum() or key[0].isdigit():
            raise ValueError(f"{path}:{line_number}: invalid environment variable name")
        try:
            parts = shlex.split(value, comments=True, posix=True)
        except ValueError as exc:
            raise ValueError(f"{path}:{line_number}: {exc}") from exc
        if len(parts) > 1:
            raise ValueError(f"{path}:{line_number}: quote values containing spaces")
        os.environ.setdefault(key, parts[0] if parts else "")
    return True


def load_config(path: Path | None = None) -> Config:
    path = path or default_config_path()
    with path.open() as handle:
        raw = yaml.safe_load(handle) or {}
    return Config.model_validate(_expand(raw))
