from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zotero_organiser.config import PersonalizationConfig, RankingConfig
from zotero_organiser.personalization import PersonalizationRanker, build_profile
from zotero_organiser.ranking import TaxonomyRanker
from zotero_organiser.state import StateStore
from zotero_organiser.taxonomy import Taxonomy


class FakeBackend:
    def embed(self, texts):
        return [[1.0, 0.0] if "screening" in text else [0.0, 1.0] for text in texts]


class FakeZotero:
    def top_items(self):
        return iter(
            [
                {
                    "key": "A",
                    "version": 1,
                    "data": {"title": "screening", "tags": [{"tag": "legacy-screen"}]},
                },
                {
                    "key": "B",
                    "version": 1,
                    "data": {"title": "screening", "tags": [{"tag": "topic/screening"}]},
                },
            ]
        )

    def library_version(self):
        return 2


def taxonomy() -> Taxonomy:
    return Taxonomy.model_validate(
        {
            "version": "test",
            "classifier": {"semantic_namespaces": ["topic"]},
            "namespaces": {"topic": {"max_tags": 2, "values": {"screening": {}, "solvation": {}}}},
        }
    )


class PersonalizationTests(unittest.TestCase):
    def test_profile_build_preserves_raw_vocabulary_and_uses_only_approved_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            state = StateStore(Path(directory) / "state.sqlite")
            ranker = TaxonomyRanker(
                RankingConfig(cache_dir=Path(directory)), taxonomy(), backend=FakeBackend()
            )
            try:
                built = build_profile(state, FakeZotero(), ranker)
                vocabulary = state.profile_vocabulary()
                scorer = PersonalizationRanker(PersonalizationConfig(), taxonomy(), state, ranker)
                before = scorer.scores({"data": {"title": "screening"}})
                state.set_profile_mapping("legacy-screen", "topic/screening")
                after = scorer.scores({"data": {"title": "screening"}})
            finally:
                state.close()

        self.assertEqual((built.item_count, built.tag_count), (2, 2))
        self.assertEqual(
            {entry["raw_tag"] for entry in vocabulary}, {"legacy-screen", "topic/screening"}
        )
        self.assertIn("topic/screening", before)
        self.assertGreater(after["topic/screening"], before["topic/screening"])
        self.assertNotIn("legacy-screen", after)
