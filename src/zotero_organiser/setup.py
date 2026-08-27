"""Guided safe configuration used by scripts/setup."""

from __future__ import annotations

import json
import os
import platform
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

import yaml

from .config import Config, default_config_path, default_environment_path, load_environment
from .models import (
    EMBEDDING_MODELS,
    NLI_MODELS,
    AcceleratorInfo,
    Runtime,
    active_spec,
    compatible_runtimes,
    detect_accelerator,
    download_models,
    format_bytes,
    recommended_embedding_size,
    recommended_nli_size,
)
from .taxonomy import install_user_taxonomy
from .terminal import Terminal


def _project_root() -> Path:
    """Repo root for `uv tool install`: launcher export, else this checkout."""
    override = os.environ.get("ZOTERO_ORGANISER_PROJECT_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def _default_paths() -> tuple[Path, Path, Path, Path]:
    home = Path.home()
    # Local Zotero storage on macOS and Linux. WebDAV (/srv/zotero-webdav) is an example, not a default.
    attachments = home / "Zotero/storage"
    state = home / ".local/state/zotero-organiser/state.sqlite"
    share = home / ".local/share/zotero-organiser"
    return attachments, state, share / "restic", share / "prewrite"


def _ask_path(ui: Terminal, label: str, default: Path) -> Path:
    return Path(ui.ask(label, str(default))).expanduser()


def _write_atomic(path: Path, content: str, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    if mode is not None:
        temporary.chmod(mode)
    temporary.replace(path)


def _dump_config(raw: dict) -> str:
    dumped = yaml.safe_dump(raw, sort_keys=False)
    return dumped.replace(
        "attachments:\n",
        "attachments:\n  # Local Zotero storage. WebDAV example: /srv/zotero-webdav\n",
        1,
    )


def _yaml_section_enabled(raw: object, name: str) -> bool:
    if not isinstance(raw, dict):
        return False
    section = raw.get(name)
    return isinstance(section, dict) and bool(section.get("enabled"))


def _run(ui: Terminal, command: list[str]) -> bool:
    ui.write("Running: " + " ".join(command))
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        ui.write(f"Command failed ({exc.returncode}).")
        return False
    except FileNotFoundError:
        ui.write(f"Command not found: {command[0]}.")
        return False
    return True


def _tool_python() -> Path | None:
    try:
        completed = subprocess.run(
            ["uv", "tool", "dir"], check=True, capture_output=True, text=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    python = Path(completed.stdout.strip()) / "zotero-organiser" / "bin" / "python"
    return python if python.exists() else None


def _tool_command(*args: str) -> list[str]:
    """Use the uv-tool interpreter so ranker/classifier extras are importable."""
    python = _tool_python()
    if python is not None:
        return [str(python), "-m", "zotero_organiser.cli", *args]
    return ["zotero-organiser", *args]


_PREFETCH_SCRIPT = (
    "import json, sys\n"
    "from pathlib import Path\n"
    f"from {download_models.__module__} import download_models\n"
    "data = json.loads(sys.argv[1])\n"
    "download_models([(m, Path(p), g) for m, p, g in data['embeddings']], data['nli_models'])\n"
)


def _prefetch_selected_models(
    ui: Terminal,
    embeddings: list[tuple[str, Path, bool]],
    nli_models: list[str],
) -> bool:
    python = _tool_python()
    if python is None:
        ui.write("Could not locate the uv tool environment to download models.")
        return False
    payload = json.dumps(
        {
            "embeddings": [[model, str(cache_dir), gpu] for model, cache_dir, gpu in embeddings],
            "nli_models": nli_models,
        }
    )
    return _run(ui, [str(python), "-c", _PREFETCH_SCRIPT, payload])


def _pin_torch(ui: Terminal, runtime: Runtime) -> bool:
    if runtime.torch_backend is None:
        return True
    python = _tool_python()
    if python is None:
        ui.write("Could not locate the uv tool environment to pin torch.")
        return False
    return _run(
        ui,
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            "torch",
            "--torch-backend",
            runtime.torch_backend,
        ],
    )


def _model_choice_labels(models, recommended_size: str) -> list[str]:
    labels = []
    for spec in models:
        mark = " (recommended)" if spec.size == recommended_size else ""
        labels.append(f"{spec.size}  {spec.model}  (~{format_bytes(spec.typical_bytes)}){mark}")
    return labels


def _select_local_models(
    ui: Terminal, info: AcceleratorInfo, system: str
) -> tuple[Runtime, list, list]:
    ui.write(f"Detected accelerator: {info.detail}")
    runtimes = compatible_runtimes(info, system=system)
    runtime = runtimes[ui.choose("Runtime", [item.label for item in runtimes], default=0)]
    embedding_default = recommended_embedding_size(runtime.kind)
    nli_default = recommended_nli_size(runtime.kind)
    embedding_indexes = ui.choose_many(
        "Embedding model sizes to download",
        _model_choice_labels(EMBEDDING_MODELS, embedding_default),
        defaults=[
            index for index, spec in enumerate(EMBEDDING_MODELS) if spec.size == embedding_default
        ],
    )
    nli_indexes = ui.choose_many(
        "Reranker / NLI model sizes to download",
        _model_choice_labels(NLI_MODELS, nli_default),
        defaults=[index for index, spec in enumerate(NLI_MODELS) if spec.size == nli_default],
    )
    embeddings = [EMBEDDING_MODELS[index] for index in embedding_indexes]
    nli_models = [NLI_MODELS[index] for index in nli_indexes]
    total = sum(spec.typical_bytes for spec in (*embeddings, *nli_models))
    ui.write(f"Selected models will use about {format_bytes(total)} of disk once downloaded.")
    return runtime, embeddings, nli_models


def _classifier_config(
    method: int, runtime: Runtime | None, embeddings: list, nli_models: list
) -> tuple[dict, dict, dict]:
    classification: dict = {"enabled": False}
    ranking: dict = {"enabled": False}
    local_classifier: dict = {"enabled": False}
    if method in {0, 2}:
        assert runtime is not None
        ranking = {
            "enabled": True,
            "mode": "shortlist",
            "backend": runtime.ranking_backend,
            "model": active_spec(embeddings, recommended_embedding_size(runtime.kind)).model,
        }
        local_classifier = {
            "enabled": True,
            "mode": "primary",
            "backend": "transformers-nli",
            "model": active_spec(nli_models, recommended_nli_size(runtime.kind)).model,
            "device": runtime.device,
            "fallback_to_remote": method == 2,
        }
    if method in {1, 2}:
        classification["enabled"] = True
    return classification, ranking, local_classifier


def main() -> int:
    ui = Terminal()
    system = platform.system()
    if system not in {"Darwin", "Linux"} or (
        system == "Linux" and "ubuntu" not in platform.platform().lower()
    ):
        ui.write(
            "Guided defaults support macOS and Ubuntu. You can still enter POSIX paths manually."
        )
    if not shutil.which("uv"):
        ui.write(
            "uv is required. Install it from https://docs.astral.sh/uv/ and re-run scripts/setup."
        )
        return 1
    ui.heading("zotero-organiser setup")
    config_path = Path(ui.ask("Configuration path", str(default_config_path()))).expanduser()
    if config_path.exists():
        action = ui.choose(
            "A configuration already exists", ["Reuse it", "Back up and replace it", "Exit"]
        )
        if action == 0:
            ui.write(f"Reusing {config_path}; no configuration changed.")
            raw = yaml.safe_load(config_path.read_text()) or {}
            if _yaml_section_enabled(raw, "ranking") or _yaml_section_enabled(
                raw, "local_classifier"
            ):
                ui.write("To download local models later, run: zotero-organiser models download")
            return 0
        if action == 2:
            return 0
        backup_path = config_path.with_suffix(config_path.suffix + ".bak")
        _write_atomic(backup_path, config_path.read_text())
        ui.write(f"Backed up existing configuration to {backup_path}")
    attachments, state, repository, prewrite = _default_paths()
    attachments = _ask_path(ui, "Attachment storage path", attachments)
    state = _ask_path(ui, "State database path", state)
    repository = Path(ui.ask("Restic repository path", str(repository))).expanduser()
    prewrite = _ask_path(ui, "Pre-write JSON directory", prewrite)
    method = ui.choose(
        "Classifier method",
        [
            "Local models (recommended)",
            "Remote OpenAI-compatible API",
            "Local models with remote API fallback",
            "Disabled/manual triage",
        ],
        default=0,
    )
    runtime: Runtime | None = None
    embeddings: list = []
    nli_models: list = []
    classification: dict
    ranking: dict
    local_classifier: dict
    if method in {0, 2}:
        runtime, embeddings, nli_models = _select_local_models(ui, detect_accelerator(), system)
    classification, ranking, local_classifier = _classifier_config(
        method, runtime, embeddings, nli_models
    )
    if method in {1, 2}:
        env_name = ui.ask("API-key environment variable", "OPENAI_API_KEY")
        classification["api_key_env"] = env_name
        ui.write(
            f"Add {env_name}=... to the environment file; the secret will not be requested or displayed."
        )
    raw = {
        "zotero": {
            "mode": "local",
            "base_url": "http://127.0.0.1:23119/api",
            "app_name": "zotero-organiser",
        },
        "attachments": {"path": str(attachments)},
        "backup": {
            "source": str(attachments),
            "repository": str(repository),
            "prewrite_dir": str(prewrite),
        },
        "state": {"database": str(state)},
        "taxonomy": {"path": str(config_path.with_name("taxonomy.yml"))},
        "classification": classification,
        "ranking": ranking,
        "local_classifier": local_classifier,
        "safety": {
            "write_enabled": False,
            "require_backup": True,
            "only_new_items": True,
            "allow_tag_removal": False,
            "max_items_per_cycle": 5,
        },
    }
    try:
        Config.model_validate(raw)
    except Exception as exc:
        ui.write(f"Generated configuration is invalid: {exc}")
        return 1
    taxonomy_path = config_path.with_name("taxonomy.yml")
    try:
        install_user_taxonomy(taxonomy_path)
        ui.write(f"Wrote starter taxonomy to {taxonomy_path}; edit this file.")
    except FileExistsError:
        ui.write(f"Keeping existing taxonomy at {taxonomy_path}")
    except (FileNotFoundError, ValueError) as exc:
        ui.write(f"Could not install a user taxonomy: {exc}")
        return 1
    _write_atomic(config_path, _dump_config(raw))
    ui.write(f"Wrote safe, write-disabled configuration to {config_path}")
    default_env = (
        default_environment_path()
        if config_path == default_config_path()
        else config_path.with_name("environment")
    )
    env_path = Path(ui.ask("Environment file path", str(default_env))).expanduser()
    if not env_path.exists() and ui.confirm(
        f"Create owner-only environment file at {env_path}", default=True
    ):
        _write_atomic(env_path, "# Secrets for zotero-organiser\n", stat.S_IRUSR | stat.S_IWUSR)
    root = _project_root()
    installed = False
    if ui.confirm("Install editable command with uv", default=True):
        target = str(root)
        if runtime is not None:
            target = f"{root}[{runtime.extras}]"
        if not _run(ui, ["uv", "tool", "install", "--editable", target]):
            ui.write("Install failed; setup cannot continue.")
            return 1
        if runtime is not None and not _pin_torch(ui, runtime):
            ui.write("Could not pin a hardware-compatible PyTorch wheel; setup cannot continue.")
            return 1
        installed = True
    if runtime is not None and ui.confirm("Download selected models now", default=True):
        if not installed:
            ui.write("Install the command first, then run: zotero-organiser models download")
        else:
            cache_dir = Path.home() / ".cache/zotero-organiser/ranker"
            gpu = runtime.ranking_backend == "fastembed-gpu"
            if not _prefetch_selected_models(
                ui,
                [(spec.model, cache_dir, gpu) for spec in embeddings],
                [spec.model for spec in nli_models],
            ):
                ui.write("Model download failed.")
                ui.write("Setup cannot continue.")
                return 1
            ui.write("Downloaded selected local models.")
    if ui.confirm("Initialize the Restic repository now", default=False):
        try:
            load_environment(env_path)
        except ValueError as exc:
            ui.write(f"Could not load environment file: {exc}; Restic may ask for credentials.")
        if not _run(ui, ["restic", "--repo", str(repository), "init"]):
            ui.write("Restic initialization failed; setup cannot continue.")
            return 1
    failed = False
    if ui.confirm("Run doctor", default=False):
        if _run(ui, _tool_command("--config", str(config_path), "doctor")):
            ui.write("Doctor completed.")
        else:
            ui.write("Doctor failed.")
            failed = True
    if ui.confirm("Build the local preference profile", default=False):
        if not _run(ui, _tool_command("--config", str(config_path), "profile", "build")):
            ui.write("Profile build failed.")
            failed = True
    if ui.confirm("Start the read-only test assistant", default=False):
        if _run(ui, _tool_command("--config", str(config_path), "test")):
            ui.write("Test assistant completed.")
        else:
            ui.write("Test assistant failed.")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
