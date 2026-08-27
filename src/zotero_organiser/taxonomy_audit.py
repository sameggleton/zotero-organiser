"""Embedding-assisted, reporting-only review of potentially overlapping tags."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

from .ranking import TaxonomyRanker
from .taxonomy import TagRelationship, Taxonomy


@dataclass(frozen=True)
class AuditFinding:
    first_tag: str
    second_tag: str
    similarity: float
    relationship: TagRelationship | None = None

    @property
    def status(self) -> str:
        return "declared" if self.relationship is not None else "pending"


@dataclass(frozen=True)
class TaxonomyAudit:
    taxonomy_digest: str
    embedding_model: str
    threshold: float
    findings: tuple[AuditFinding, ...]


def audit_taxonomy(
    taxonomy: Taxonomy, ranker: TaxonomyRanker, *, threshold: float
) -> TaxonomyAudit:
    """Find high-similarity, same-namespace pairs without changing any tags.

    Restricting the first audit to a namespace avoids flagging legitimately
    related concepts that answer different questions about a paper.
    """
    tags, vectors = ranker.taxonomy_vectors()
    findings: list[AuditFinding] = []
    for index, first_tag in enumerate(tags):
        first_namespace, _, _ = first_tag.partition("/")
        for second_tag, second_vector in zip(tags[index + 1 :], vectors[index + 1 :], strict=True):
            second_namespace, _, _ = second_tag.partition("/")
            if first_namespace != second_namespace:
                continue
            similarity = _cosine(vectors[index], second_vector)
            relationship = taxonomy.relationship_for(first_tag, second_tag)
            if similarity >= threshold or relationship is not None:
                findings.append(AuditFinding(first_tag, second_tag, similarity, relationship))
    findings.sort(key=lambda finding: (-finding.similarity, finding.first_tag, finding.second_tag))
    content = json.dumps(taxonomy.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return TaxonomyAudit(
        taxonomy_digest=hashlib.sha256(content.encode()).hexdigest(),
        embedding_model=ranker.config.model,
        threshold=threshold,
        findings=tuple(findings),
    )


def _cosine(first: list[float], second: list[float]) -> float:
    numerator = math.fsum(a * b for a, b in zip(first, second, strict=True))
    first_norm = math.sqrt(math.fsum(value * value for value in first))
    second_norm = math.sqrt(math.fsum(value * value for value in second))
    if first_norm == 0 or second_norm == 0:
        return 0.0
    return numerator / (first_norm * second_norm)
