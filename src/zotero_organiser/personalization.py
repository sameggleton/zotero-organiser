"""Local preference-profile scoring for taxonomy candidate retrieval."""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import islice
from typing import Iterable

from .config import PersonalizationConfig
from .ranking import TaxonomyRanker, document_text
from .state import StateStore
from .taxonomy import Taxonomy
from .zotero import ZoteroClient, tags


@dataclass(frozen=True)
class ProfileBuild:
    item_count: int
    tag_count: int


def build_profile(state: StateStore, zotero: ZoteroClient, ranker: TaxonomyRanker) -> ProfileBuild:
    """Embed current top-level items and retain their pre-existing tag vocabulary locally."""
    records: list[tuple[str, int, str, set[str]]] = []
    for item in zotero.top_items():
        text = document_text(item)
        item_tags = tags(item)
        if text and item_tags:
            records.append((item["key"], item["version"], text, item_tags))
    embedded: list[tuple[str, int, list[float], set[str]]] = []
    for batch in _batches(records, 64):
        vectors = ranker.embed_documents(record[2] for record in batch)
        embedded.extend(
            (record[0], record[1], vector, record[3])
            for record, vector in zip(batch, vectors, strict=True)
        )
    if server_id := getattr(zotero, "server_id", None):
        state.set_zotero_server_id(server_id)
    state.replace_profile(
        embedding_model=ranker.config.model,
        library_version=zotero.library_version(),
        items=embedded,
    )
    return ProfileBuild(
        len(embedded), len({tag for *_rest, item_tags in embedded for tag in item_tags})
    )


class PersonalizationRanker:
    """Use approved historic tags as a bounded local ranking signal."""

    def __init__(
        self,
        config: PersonalizationConfig,
        taxonomy: Taxonomy,
        state: StateStore,
        ranker: TaxonomyRanker,
    ):
        self.config = config
        self.taxonomy = taxonomy
        self.state = state
        self.ranker = ranker

    def scores(self, item: dict) -> dict[str, float]:
        centroids = self.state.profile_centroids(
            model=self.ranker.config.model, canonical_tags=self.taxonomy.classifier_tags()
        )
        if not centroids:
            return {}
        query = self.ranker.embed_documents([document_text(item)])[0]
        scores: dict[str, float] = {}
        for tag, (centroid, examples) in centroids.items():
            similarity = _cosine(query, centroid)
            reliability = min(1.0, examples / self.config.min_examples)
            scores[tag] = self.config.weight * reliability * max(0.0, similarity)
        return scores


def _cosine(left: list[float], right: list[float]) -> float:
    numerator = math.fsum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(math.fsum(value * value for value in left))
    right_norm = math.sqrt(math.fsum(value * value for value in right))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


def _batches(
    values: list[tuple[str, int, str, set[str]]], size: int
) -> Iterable[list[tuple[str, int, str, set[str]]]]:
    iterator = iter(values)
    while batch := list(islice(iterator, size)):
        yield batch
