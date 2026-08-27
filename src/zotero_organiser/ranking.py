from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .config import RankingConfig
from .taxonomy import Taxonomy


class RankerUnavailable(RuntimeError):
    """The optional local embedding backend cannot be used."""


class EmbeddingBackend(Protocol):
    def embed(self, texts: Iterable[str]) -> list[list[float]]: ...


class FastEmbedBackend:
    """Lazy FastEmbed adapter so the core installation has no ML dependency."""

    def __init__(
        self,
        model: str,
        cache_dir: Path,
        *,
        gpu: bool = False,
        local_files_only: bool = True,
    ):
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:
            extra = "ranker-gpu" if gpu else "ranker"
            raise RankerUnavailable(
                f"ranking requires the optional dependency; install zotero-organiser[{extra}]"
            ) from exc
        kwargs: dict = {"model_name": model, "cache_dir": str(cache_dir)}
        if gpu:
            kwargs["providers"] = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        if local_files_only:
            kwargs["local_files_only"] = True
        try:
            self.model = TextEmbedding(**kwargs)
        except Exception as exc:
            if local_files_only and _is_missing_cache(exc):
                raise RankerUnavailable(
                    f"embedding model {model} is not cached; run zotero-organiser models download"
                ) from exc
            raise RankerUnavailable(f"could not load embedding model {model}: {exc}") from exc

    def embed(self, texts: Iterable[str]) -> list[list[float]]:
        # FastEmbed yields NumPy scalar values. Convert them here so validation,
        # arithmetic, and JSON persistence use only portable Python floats.
        return [[float(value) for value in vector] for vector in self.model.embed(list(texts))]


@dataclass(frozen=True)
class Candidate:
    tag: str
    dense_score: float
    lexical_score: float
    sources: frozenset[str]
    profile_score: float = 0.0


@dataclass(frozen=True)
class Ranking:
    candidates: tuple[Candidate, ...]

    @property
    def tags(self) -> set[str]:
        return {candidate.tag for candidate in self.candidates}


class TaxonomyRanker:
    """Hybrid local candidate ranker for a small, fixed taxonomy."""

    def __init__(
        self,
        config: RankingConfig,
        taxonomy: Taxonomy,
        *,
        backend: EmbeddingBackend | None = None,
        local_files_only: bool = True,
    ):
        self.config = config
        self.taxonomy = taxonomy
        self.backend = backend
        self.local_files_only = local_files_only
        self._taxonomy_vectors: tuple[list[str], list[list[float]]] | None = None

    def rank(self, item: dict, *, profile_scores: dict[str, float] | None = None) -> Ranking:
        texts = self.taxonomy.ranking_texts()
        tags, vectors = self.taxonomy_vectors()
        document = document_text(item)
        query_vector = self._backend().embed([document])[0]
        if len(query_vector) != len(vectors[0]):
            raise RankerUnavailable("embedding model returned inconsistent vector dimensions")

        dense = {tag: _dot(query_vector, vector) for tag, vector in zip(tags, vectors, strict=True)}
        profile_scores = profile_scores or {}
        combined = {tag: dense[tag] + profile_scores.get(tag, 0.0) for tag in tags}
        lexical = _lexical_scores(document, texts)
        selected: dict[str, set[str]] = {}

        def add(tag: str, source: str) -> None:
            selected.setdefault(tag, set()).add(source)

        for tag in _top(combined, self.config.dense_top_k):
            add(tag, "dense")
        for tag in _top(
            {tag: score for tag, score in lexical.items() if score > 0}, self.config.lexical_top_k
        ):
            add(tag, "lexical")
        namespaces = self.taxonomy.classifier.semantic_namespaces or {
            tag.partition("/")[0] for tag in tags
        }
        for namespace in namespaces:
            namespace_scores = {
                tag: score for tag, score in combined.items() if tag.startswith(namespace + "/")
            }
            for tag in _top(namespace_scores, self.config.per_namespace_k):
                add(tag, "namespace")

        candidates = tuple(
            Candidate(
                tag,
                dense[tag],
                lexical[tag],
                frozenset(sources | ({"profile"} if profile_scores.get(tag, 0.0) else set())),
                profile_scores.get(tag, 0.0),
            )
            for tag, sources in sorted(
                selected.items(),
                key=lambda entry: (-combined[entry[0]], -lexical[entry[0]], entry[0]),
            )
        )
        return Ranking(candidates)

    def taxonomy_vectors(self) -> tuple[list[str], list[list[float]]]:
        """Return cached embedding vectors for eligible taxonomy definitions."""
        return self._vectors(self.taxonomy.ranking_texts())

    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        """Embed local profile documents with the configured ranker model."""
        return self._backend().embed(texts)

    def _backend(self) -> EmbeddingBackend:
        if self.backend is None:
            self.backend = FastEmbedBackend(
                self.config.model,
                self.config.cache_dir,
                gpu=self.config.backend == "fastembed-gpu",
                local_files_only=self.local_files_only,
            )
        return self.backend

    def _vectors(self, texts: dict[str, str]) -> tuple[list[str], list[list[float]]]:
        if self._taxonomy_vectors is not None:
            return self._taxonomy_vectors
        tags = sorted(texts)
        cache_path = self._cache_path(tags, texts)
        try:
            cached = json.loads(cache_path.read_text())
            vectors = cached["vectors"]
            if cached["tags"] == tags and _valid_vectors(vectors):
                self._taxonomy_vectors = tags, vectors
                return self._taxonomy_vectors
        except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            pass

        vectors = self._backend().embed(texts[tag] for tag in tags)
        if len(vectors) != len(tags) or not _valid_vectors(vectors):
            raise RankerUnavailable("embedding backend returned invalid taxonomy vectors")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = cache_path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"tags": tags, "vectors": vectors}, separators=(",", ":")))
        temporary.replace(cache_path)
        self._taxonomy_vectors = tags, vectors
        return self._taxonomy_vectors

    def _cache_path(self, tags: list[str], texts: dict[str, str]) -> Path:
        content = json.dumps(
            {"model": self.config.model, "tags": [(tag, texts[tag]) for tag in tags]},
            separators=(",", ":"),
            sort_keys=True,
        )
        digest = hashlib.sha256(content.encode()).hexdigest()
        return self.config.cache_dir / f"taxonomy-{digest}.json"


def _is_missing_cache(exc: BaseException) -> bool:
    # Hugging Face cache misses are OSError/LocalEntryNotFoundError; FastEmbed
    # wraps the same failure as ValueError after trying HF + GCS.
    if isinstance(exc, OSError) or type(exc).__name__ == "LocalEntryNotFoundError":
        return True
    text = str(exc).lower()
    return "local_files_only" in text or "from any source" in text or "disk cache" in text


def document_text(item: dict) -> str:
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


def _dot(left: list[float], right: list[float]) -> float:
    return math.fsum(a * b for a, b in zip(left, right, strict=True))


def _top(scores: dict[str, float], count: int) -> list[str]:
    return [
        tag
        for tag, _score in sorted(scores.items(), key=lambda entry: (-entry[1], entry[0]))[:count]
    ]


def _lexical_scores(document: str, texts: dict[str, str]) -> dict[str, float]:
    query = set(_tokens(document))
    documents = {tag: set(_tokens(text)) for tag, text in texts.items()}
    frequencies = Counter(token for terms in documents.values() for token in terms)
    total = len(documents)
    return {
        tag: math.fsum(
            math.log((total + 1) / (frequencies[token] + 1)) + 1 for token in query & terms
        )
        for tag, terms in documents.items()
    }


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9+.-]*", text.lower())


def _valid_vectors(vectors: object) -> bool:
    return (
        isinstance(vectors, list)
        and bool(vectors)
        and all(isinstance(vector, list) and vector for vector in vectors)
        and len({len(vector) for vector in vectors}) == 1
        and all(
            isinstance(value, (int, float)) and math.isfinite(value)
            for vector in vectors
            for value in vector
        )
    )
