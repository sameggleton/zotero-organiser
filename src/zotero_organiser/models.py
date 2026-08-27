"""Local embedding and NLI model catalog, hardware detection, and prefetch."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .config import Config
from .local_classifier import LocalClassifierUnavailable, TransformersNLIBackend
from .ranking import FastEmbedBackend, RankerUnavailable


Accelerator = Literal["cpu", "mps", "cuda", "rocm"]
SIZE_ORDER = {"small": 0, "medium": 1, "large": 2}


@dataclass(frozen=True)
class ModelSpec:
    size: str
    model: str
    typical_bytes: int
    license: str
    entailment: bool = False


@dataclass(frozen=True)
class AcceleratorInfo:
    kind: Accelerator
    detail: str
    cuda_backend: str | None = None


@dataclass(frozen=True)
class Runtime:
    kind: Accelerator
    label: str
    extras: str
    ranking_backend: Literal["fastembed-cpu", "fastembed-gpu"]
    device: Literal["auto", "cpu", "mps", "cuda"]
    torch_backend: str | None


@dataclass(frozen=True)
class ModelStatus:
    name: str
    model: str
    cached: bool
    detail: str


EMBEDDING_MODELS: tuple[ModelSpec, ...] = (
    ModelSpec("small", "BAAI/bge-small-en-v1.5", 130 * 1024 * 1024, "MIT"),
    ModelSpec("medium", "BAAI/bge-base-en-v1.5", 210 * 1024 * 1024, "MIT"),
    ModelSpec("large", "BAAI/bge-large-en-v1.5", 1200 * 1024 * 1024, "MIT"),
)

NLI_MODELS: tuple[ModelSpec, ...] = (
    ModelSpec(
        "small",
        "tasksource/ModernBERT-base-nli",
        500 * 1024 * 1024,
        "Apache-2.0",
        entailment=True,
    ),
    ModelSpec(
        "large",
        "tasksource/ModernBERT-large-nli",
        1600 * 1024 * 1024,
        "Apache-2.0",
        entailment=True,
    ),
)

_RUNTIME_LABELS = {
    "cpu": "CPU",
    "mps": "Apple GPU (MPS)",
    "cuda": "NVIDIA GPU (CUDA)",
    "rocm": "AMD GPU (ROCm)",
}


def embedding_spec(size: str) -> ModelSpec:
    return _spec_by_size(EMBEDDING_MODELS, size)


def nli_spec(size: str) -> ModelSpec:
    return _spec_by_size(NLI_MODELS, size)


def spec_for_model(models: tuple[ModelSpec, ...], model: str) -> ModelSpec | None:
    for spec in models:
        if spec.model == model:
            return spec
    return None


def format_bytes(size: int) -> str:
    if size >= 1024 * 1024 * 1024:
        value = size / (1024 * 1024 * 1024)
        return f"{value:.1f} GB".replace(".0 ", " ")
    megabytes = max(1, round(size / (1024 * 1024)))
    return f"{megabytes} MB"


def recommended_embedding_size(accelerator: Accelerator) -> str:
    if accelerator == "cpu":
        return "small"
    return "medium"


def recommended_nli_size(accelerator: Accelerator) -> str:
    if accelerator in {"cuda", "rocm"}:
        return "large"
    return "small"


def active_spec(selected: list[ModelSpec], recommended_size: str) -> ModelSpec:
    if not selected:
        raise ValueError("at least one model size is required")
    for spec in selected:
        if spec.size == recommended_size:
            return spec
    return max(selected, key=lambda spec: SIZE_ORDER[spec.size])


def detect_accelerator(
    *,
    system: str | None = None,
    machine: str | None = None,
    which=shutil.which,
    nvidia_smi_output: str | None = None,
) -> AcceleratorInfo:
    system = system if system is not None else platform.system()
    machine = (machine if machine is not None else platform.machine()).lower()
    if system == "Darwin":
        if machine in {"arm64", "aarch64"}:
            return AcceleratorInfo("mps", "Apple Silicon")
        return AcceleratorInfo("cpu", "macOS without Apple Silicon")
    nvidia = which("nvidia-smi")
    if nvidia:
        output = nvidia_smi_output
        if output is None:
            output = _command_output([nvidia])
        backend = _cuda_backend(output or "")
        detail = "NVIDIA GPU"
        if backend and backend != "auto":
            detail = f"NVIDIA GPU ({backend})"
        return AcceleratorInfo("cuda", detail, cuda_backend=backend or "auto")
    if which("rocminfo") or which("rocm-smi"):
        return AcceleratorInfo("rocm", "AMD GPU with ROCm")
    return AcceleratorInfo("cpu", "CPU")


def compatible_runtimes(info: AcceleratorInfo, *, system: str | None = None) -> list[Runtime]:
    system = system if system is not None else platform.system()
    runtimes = [_runtime("cpu", system, info)]
    if info.kind == "mps" and system == "Darwin":
        runtimes.append(_runtime("mps", system, info))
    if info.kind == "cuda" and system != "Darwin":
        runtimes.append(_runtime("cuda", system, info))
    if info.kind == "rocm" and system == "Linux":
        runtimes.append(_runtime("rocm", system, info))
    recommended = next((item for item in runtimes if item.kind == info.kind), runtimes[0])
    return [recommended, *[item for item in runtimes if item is not recommended]]


def huggingface_hub_dir() -> Path:
    for key in ("HF_HUB_CACHE", "HUGGINGFACE_HUB_CACHE"):
        override = os.environ.get(key)
        if override:
            return Path(override).expanduser()
    home = os.environ.get("HF_HOME")
    if home:
        return Path(home).expanduser() / "hub"
    return Path.home() / ".cache/huggingface/hub"


def embedding_cached(model: str, cache_dir: Path) -> bool:
    return _cache_dir_has_model(cache_dir, model)


def nli_cached(model: str, hub_dir: Path | None = None) -> bool:
    return _cache_dir_has_model(hub_dir or huggingface_hub_dir(), model)


def model_status(config: Config) -> list[ModelStatus]:
    statuses: list[ModelStatus] = []
    if config.ranking.enabled:
        cached = embedding_cached(config.ranking.model, config.ranking.cache_dir)
        statuses.append(
            ModelStatus(
                "Embedding",
                config.ranking.model,
                cached,
                "cached" if cached else "not cached; run zotero-organiser models download",
            )
        )
    if config.local_classifier.enabled:
        cached = nli_cached(config.local_classifier.model)
        statuses.append(
            ModelStatus(
                "NLI reranker",
                config.local_classifier.model,
                cached,
                "cached" if cached else "not cached; run zotero-organiser models download",
            )
        )
    return statuses


def download_embedding(model: str, cache_dir: Path, *, gpu: bool = False) -> None:
    backend = FastEmbedBackend(model, cache_dir, gpu=gpu, local_files_only=False)
    backend.embed(["warmup"])


def download_nli(model: str) -> None:
    from .config import LocalClassifierConfig

    TransformersNLIBackend(LocalClassifierConfig(model=model, device="cpu"), local_files_only=False)


def download_models(
    embeddings: list[tuple[str, Path, bool]],
    nli_models: list[str],
) -> None:
    for model, cache_dir, gpu in embeddings:
        download_embedding(model, cache_dir, gpu=gpu)
    for model in nli_models:
        download_nli(model)


def download_active_models(config: Config) -> None:
    embeddings: list[tuple[str, Path, bool]] = []
    nli_models: list[str] = []
    if config.ranking.enabled:
        embeddings.append(
            (
                config.ranking.model,
                config.ranking.cache_dir,
                config.ranking.backend == "fastembed-gpu",
            )
        )
    if config.local_classifier.enabled:
        nli_models.append(config.local_classifier.model)
    if not embeddings and not nli_models:
        raise RuntimeError("no local models are enabled in the configuration")
    try:
        download_models(embeddings, nli_models)
    except (RankerUnavailable, LocalClassifierUnavailable) as exc:
        raise RuntimeError(str(exc)) from exc


def _spec_by_size(models: tuple[ModelSpec, ...], size: str) -> ModelSpec:
    for spec in models:
        if spec.size == size:
            return spec
    raise KeyError(f"unknown model size: {size}")


def _runtime(kind: Accelerator, system: str, info: AcceleratorInfo) -> Runtime:
    ranking_backend: Literal["fastembed-cpu", "fastembed-gpu"] = (
        "fastembed-gpu" if kind == "cuda" else "fastembed-cpu"
    )
    extras = "ranker-gpu,local-classifier" if kind == "cuda" else "ranker,local-classifier"
    if kind == "cpu":
        device: Literal["auto", "cpu", "mps", "cuda"] = "cpu"
        torch_backend = "cpu" if system == "Linux" else None
    elif kind == "mps":
        device = "mps"
        torch_backend = None
    elif kind == "cuda":
        device = "cuda"
        torch_backend = info.cuda_backend or "auto"
    else:
        device = "auto"
        torch_backend = "rocm"
    return Runtime(
        kind=kind,
        label=_RUNTIME_LABELS[kind],
        extras=extras,
        ranking_backend=ranking_backend,
        device=device,
        torch_backend=torch_backend,
    )


def _cuda_backend(nvidia_smi_output: str) -> str | None:
    marker = "CUDA Version:"
    if marker not in nvidia_smi_output:
        return "auto"
    try:
        version = nvidia_smi_output.split(marker, 1)[1].split()[0]
        major, minor, *_ = (int(part) for part in version.split("."))
    except (ValueError, IndexError):
        return "auto"
    if (major, minor) >= (13, 0):
        return "cu130"
    if (major, minor) >= (12, 8):
        return "cu128"
    if (major, minor) >= (12, 6):
        return "cu126"
    return "auto"


def _command_output(command: list[str]) -> str:
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
    except OSError:
        return ""
    return completed.stdout + completed.stderr


def _cache_dir_has_model(root: Path, model: str) -> bool:
    repo_dir = root / f"models--{model.replace('/', '--')}"
    if not repo_dir.is_dir():
        return False
    snapshots = repo_dir / "snapshots"
    if snapshots.is_dir():
        for snapshot in snapshots.iterdir():
            if not snapshot.is_dir():
                continue
            config = snapshot / "config.json"
            if _nonempty_file(config) or _has_onnx_weight(snapshot):
                return True
    # FastEmbed may store ONNX at the repo root rather than under snapshots/.
    return _has_onnx_weight(repo_dir)


def _nonempty_file(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0 and not path.name.endswith(".lock")


def _has_onnx_weight(directory: Path) -> bool:
    for path in (*directory.glob("*.onnx"), *directory.glob("onnx/*.onnx")):
        if _nonempty_file(path):
            return True
    return False
