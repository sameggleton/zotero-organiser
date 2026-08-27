from __future__ import annotations

import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from zotero_organiser.config import RankingConfig
from zotero_organiser.ranking import FastEmbedBackend, RankerUnavailable, TaxonomyRanker
from zotero_organiser.taxonomy import Taxonomy


class FakeBackend:
    def __init__(self):
        self.calls: list[list[str]] = []

    def embed(self, texts):
        texts = list(texts)
        self.calls.append(texts)
        vectors = []
        for text in texts:
            if "paper" in text:
                vectors.append([1.0, 0.0])
            elif "screening" in text:
                vectors.append([1.0, 0.0])
            else:
                vectors.append([0.0, 1.0])
        return vectors


def taxonomy() -> Taxonomy:
    return Taxonomy.model_validate(
        {
            "version": "test",
            "classifier": {"semantic_namespaces": ["topic"]},
            "namespaces": {
                "topic": {
                    "max_tags": 2,
                    "values": {
                        "screening": {"description": "mineral screening"},
                        "electrochemistry": {"description": "electrochemical method"},
                    },
                }
            },
        }
    )


class RankingTests(unittest.TestCase):
    def config(self, directory: str) -> RankingConfig:
        return RankingConfig(
            cache_dir=Path(directory), dense_top_k=1, lexical_top_k=1, per_namespace_k=1
        )

    def item(self) -> dict:
        return {
            "data": {
                "title": "A paper about screening",
                "abstractNote": "An electrochemical method is evaluated.",
                "itemType": "journalArticle",
            }
        }

    def test_hybrid_ranking_unions_dense_and_lexical_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            ranking = TaxonomyRanker(
                self.config(directory), taxonomy(), backend=FakeBackend()
            ).rank(self.item())
        by_tag = {candidate.tag: candidate for candidate in ranking.candidates}
        self.assertEqual(set(by_tag), {"topic/screening", "topic/electrochemistry"})
        self.assertIn("dense", by_tag["topic/screening"].sources)
        self.assertIn("lexical", by_tag["topic/electrochemistry"].sources)

    def test_taxonomy_vectors_are_reused_from_disk_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            first = FakeBackend()
            TaxonomyRanker(self.config(directory), taxonomy(), backend=first).rank(self.item())
            self.assertEqual(len(first.calls), 2)

            second = FakeBackend()
            TaxonomyRanker(self.config(directory), taxonomy(), backend=second).rank(self.item())
            self.assertEqual(len(second.calls), 1)

    def test_fastembed_backend_normalizes_numeric_scalars_to_python_floats(self):
        module = ModuleType("fastembed")

        class TextEmbedding:
            def __init__(self, **_kwargs):
                pass

            def embed(self, _texts):
                return iter([[Decimal("0.25"), Decimal("0.75")]])

        module.TextEmbedding = TextEmbedding
        with patch.dict("sys.modules", {"fastembed": module}):
            backend = FastEmbedBackend("test-model", Path("/tmp/ranker-test"))
            vectors = backend.embed(["test document"])

        self.assertEqual(vectors, [[0.25, 0.75]])
        self.assertTrue(all(type(value) is float for value in vectors[0]))

    def test_gpu_backend_passes_cuda_provider(self):
        captured = {}

        class TextEmbedding:
            def __init__(self, **kwargs):
                captured.update(kwargs)

            def embed(self, _texts):
                return iter([[0.1, 0.2]])

        module = ModuleType("fastembed")
        module.TextEmbedding = TextEmbedding
        with patch.dict("sys.modules", {"fastembed": module}):
            FastEmbedBackend("BAAI/bge-small-en-v1.5", Path("/tmp/ranker-test"), gpu=True)
        self.assertEqual(captured["providers"], ["CUDAExecutionProvider", "CPUExecutionProvider"])
        self.assertTrue(captured["local_files_only"])

    def test_missing_cache_explains_how_to_download(self):
        class TextEmbedding:
            def __init__(self, **_kwargs):
                raise OSError("not in cache")

        module = ModuleType("fastembed")
        module.TextEmbedding = TextEmbedding
        with (
            patch.dict("sys.modules", {"fastembed": module}),
            self.assertRaisesRegex(RankerUnavailable, "models download"),
        ):
            FastEmbedBackend("test-model", Path("/tmp/ranker-test"))

    def test_fastembed_value_error_cache_miss_explains_how_to_download(self):
        class TextEmbedding:
            def __init__(self, **_kwargs):
                raise ValueError("Could not load model test-model from any source.")

        module = ModuleType("fastembed")
        module.TextEmbedding = TextEmbedding
        with (
            patch.dict("sys.modules", {"fastembed": module}),
            self.assertRaisesRegex(RankerUnavailable, "models download"),
        ):
            FastEmbedBackend("test-model", Path("/tmp/ranker-test"))

    def test_provider_errors_are_not_reported_as_missing_cache(self):
        class TextEmbedding:
            def __init__(self, **_kwargs):
                raise RuntimeError("CUDAExecutionProvider is not available")

        module = ModuleType("fastembed")
        module.TextEmbedding = TextEmbedding
        with (
            patch.dict("sys.modules", {"fastembed": module}),
            self.assertRaises(RankerUnavailable) as raised,
        ):
            FastEmbedBackend("test-model", Path("/tmp/ranker-test"), gpu=True)
        self.assertIn("CUDAExecutionProvider", str(raised.exception))
        self.assertNotIn("models download", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
