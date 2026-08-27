from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zotero_organiser.config import RankingConfig
from zotero_organiser.ranking import TaxonomyRanker
from zotero_organiser.state import StateStore
from zotero_organiser.taxonomy import Taxonomy
from zotero_organiser.taxonomy_audit import audit_taxonomy


class FakeBackend:
    def embed(self, texts):
        vectors = []
        for text in texts:
            vectors.append([1.0, 0.0] if "peptide" in text else [0.0, 1.0])
        return vectors


def taxonomy() -> Taxonomy:
    return Taxonomy.model_validate(
        {
            "version": "test",
            "classifier": {"semantic_namespaces": ["system"]},
            "relationships": [
                {
                    "tags": ["system/peptide", "system/polypeptide"],
                    "kind": "near_duplicate",
                    "resolution": "keep_both",
                }
            ],
            "namespaces": {
                "system": {
                    "max_tags": 3,
                    "values": {
                        "peptide": {"description": "a peptide system"},
                        "polypeptide": {"description": "a polypeptide system"},
                        "electrolyte": {"description": "an electrolyte system"},
                    },
                }
            },
        }
    )


class TaxonomyAuditTests(unittest.TestCase):
    def test_audit_reports_similar_pairs_and_declared_relationships(self):
        with tempfile.TemporaryDirectory() as directory:
            ranker = TaxonomyRanker(
                RankingConfig(cache_dir=Path(directory)), taxonomy(), backend=FakeBackend()
            )
            audit = audit_taxonomy(taxonomy(), ranker, threshold=0.88)

        self.assertEqual(len(audit.findings), 1)
        finding = audit.findings[0]
        self.assertEqual(
            (finding.first_tag, finding.second_tag), ("system/peptide", "system/polypeptide")
        )
        self.assertEqual(finding.similarity, 1.0)
        self.assertEqual(finding.status, "declared")
        self.assertEqual(finding.relationship.resolution, "keep_both")

    def test_audit_history_persists_findings(self):
        with tempfile.TemporaryDirectory() as directory:
            state = StateStore(Path(directory) / "state.sqlite")
            try:
                audit_id = state.record_taxonomy_audit(
                    taxonomy_version="test",
                    taxonomy_digest="digest",
                    embedding_model="model",
                    threshold=0.88,
                    findings=[
                        (
                            "system/peptide",
                            "system/polypeptide",
                            0.91,
                            "near_duplicate",
                            "keep_both",
                            "declared",
                        )
                    ],
                )
                history = state.taxonomy_audit_history()
            finally:
                state.close()

        self.assertEqual(audit_id, 1)
        self.assertEqual(history[0]["findings_count"], 1)
        self.assertEqual(history[0]["embedding_model"], "model")
