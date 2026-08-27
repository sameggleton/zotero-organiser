from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Protocol

from .config import LocalClassifierConfig
from .taxonomy import Taxonomy


class LocalClassifierUnavailable(RuntimeError):
    """The optional local NLI classifier cannot be used."""


class NLIBackend(Protocol):
    def score(self, premises: Iterable[str], hypotheses: Iterable[str]) -> list[float]: ...


class TransformersNLIBackend:
    """Lazy Transformers adapter for an entailment-based local tag scorer."""

    def __init__(self, config: LocalClassifierConfig, *, local_files_only: bool = True):
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:
            raise LocalClassifierUnavailable(
                "local classification requires the optional dependency; "
                "install zotero-organiser[local-classifier]"
            ) from exc
        self.torch = torch
        self.device = _resolve_device(torch, config.device)
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                config.model, local_files_only=local_files_only
            )
            self.model = AutoModelForSequenceClassification.from_pretrained(
                config.model, local_files_only=local_files_only
            )
            self.model.to(self.device)
            self.model.eval()
            self.entailment_index = _entailment_index(self.model.config)
        except LocalClassifierUnavailable:
            raise
        except Exception as exc:
            if local_files_only and _is_missing_cache(exc):
                raise LocalClassifierUnavailable(
                    f"local NLI model {config.model} is not cached; "
                    "run zotero-organiser models download"
                ) from exc
            raise LocalClassifierUnavailable(
                f"could not load local NLI model {config.model}: {exc}"
            ) from exc
        self.batch_size = config.batch_size

    def score(self, premises: Iterable[str], hypotheses: Iterable[str]) -> list[float]:
        pairs = list(zip(premises, hypotheses, strict=True))
        scores: list[float] = []
        try:
            for start in range(0, len(pairs), self.batch_size):
                batch = pairs[start : start + self.batch_size]
                encoded = self.tokenizer(
                    [premise for premise, _hypothesis in batch],
                    [hypothesis for _premise, hypothesis in batch],
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt",
                )
                encoded = {name: value.to(self.device) for name, value in encoded.items()}
                with self.torch.inference_mode():
                    logits = self.model(**encoded).logits
                    probabilities = self.torch.softmax(logits, dim=-1)[:, self.entailment_index]
                scores.extend(float(value) for value in probabilities.detach().cpu().tolist())
        except Exception as exc:
            raise LocalClassifierUnavailable(f"local NLI inference failed: {exc}") from exc
        return scores


@dataclass
class LocalNLIClassifier:
    config: LocalClassifierConfig
    taxonomy: Taxonomy
    backend: NLIBackend | None = None

    def score(self, item: dict[str, Any], candidate_tags: Iterable[str]) -> dict[str, float]:
        definitions = self.taxonomy.local_classifier_hypotheses()
        tags = [tag for tag in candidate_tags if tag in definitions]
        if not tags:
            return {}
        document = _document_text(item)
        if not document:
            return {}
        backend = self._backend()
        positives = [definitions[tag][0] for tag in tags]
        positive_scores = backend.score([document] * len(tags), positives)
        if len(positive_scores) != len(tags):
            raise LocalClassifierUnavailable(
                "local NLI backend returned an invalid number of scores"
            )
        scores = dict(zip(tags, positive_scores, strict=True))

        excluded_tags: list[str] = []
        exclusions: list[str] = []
        for tag in tags:
            for hypothesis in definitions[tag][1]:
                excluded_tags.append(tag)
                exclusions.append(hypothesis)
        if exclusions:
            exclusion_scores = backend.score([document] * len(exclusions), exclusions)
            if len(exclusion_scores) != len(exclusions):
                raise LocalClassifierUnavailable(
                    "local NLI backend returned an invalid number of exclusion scores"
                )
            for tag, excluded in zip(excluded_tags, exclusion_scores, strict=True):
                scores[tag] *= 1 - excluded
        return scores

    def _backend(self) -> NLIBackend:
        if self.backend is None:
            self.backend = TransformersNLIBackend(self.config)
        return self.backend


def _is_missing_cache(exc: BaseException) -> bool:
    # Hugging Face cache misses are OSError/LocalEntryNotFoundError; do not treat
    # device, provider, or parse failures as a missing snapshot.
    if isinstance(exc, OSError) or type(exc).__name__ == "LocalEntryNotFoundError":
        return True
    text = str(exc).lower()
    return "local_files_only" in text or "from any source" in text or "disk cache" in text


def _resolve_device(torch: Any, configured: str) -> str:
    if configured != "auto":
        return configured
    if torch.cuda.is_available():
        return "cuda"
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return "mps"
    return "cpu"


def _entailment_index(model_config: Any) -> int:
    labels = getattr(model_config, "id2label", {})
    for index, label in labels.items():
        if str(label).lower() == "entailment":
            return int(index)
    raise LocalClassifierUnavailable("local NLI model does not expose an entailment label")


def _document_text(item: dict[str, Any]) -> str:
    data = item["data"]
    return "\n".join(
        part
        for part in (
            data.get("title", ""),
            data.get("abstractNote", ""),
            data.get("itemType", ""),
            data.get("publicationTitle", ""),
        )
        if part
    )
