from __future__ import annotations

import unittest

from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

from zotero_organiser.config import LocalClassifierConfig
from zotero_organiser.local_classifier import (
    LocalClassifierUnavailable,
    LocalNLIClassifier,
    TransformersNLIBackend,
)
from zotero_organiser.taxonomy import Taxonomy


class FakeBackend:
    def __init__(self):
        self.calls: list[tuple[list[str], list[str]]] = []

    def score(self, premises, hypotheses):
        premises, hypotheses = list(premises), list(hypotheses)
        self.calls.append((premises, hypotheses))
        if len(self.calls) == 1:
            return [0.9, 0.8]
        return [0.25]


class LocalNLIClassifierTests(unittest.TestCase):
    def taxonomy(self) -> Taxonomy:
        return Taxonomy.model_validate(
            {
                "version": "test",
                "classifier": {"semantic_namespaces": ["topic"]},
                "namespaces": {
                    "topic": {
                        "max_tags": 2,
                        "values": {
                            "solvation": {
                                "description": "Solvation is central.",
                                "exclude": ["only a passing mention"],
                            },
                            "screening": {"description": "Screening is central."},
                        },
                    }
                },
            }
        )

    def test_scores_candidates_and_penalizes_entailing_exclusions(self):
        backend = FakeBackend()
        classifier = LocalNLIClassifier(LocalClassifierConfig(), self.taxonomy(), backend=backend)
        item = {"data": {"title": "A paper", "abstractNote": "Solvation and screening"}}

        scores = classifier.score(item, ["topic/solvation", "topic/screening"])

        self.assertEqual(scores, {"topic/solvation": 0.675, "topic/screening": 0.8})
        self.assertEqual(len(backend.calls), 2)
        self.assertEqual(len(backend.calls[0][0]), 2)
        self.assertIn("excluded scope", backend.calls[1][1][0])

    def test_ignores_candidates_outside_the_taxonomy(self):
        classifier = LocalNLIClassifier(
            LocalClassifierConfig(), self.taxonomy(), backend=FakeBackend()
        )
        item = {"data": {"title": "A paper"}}
        self.assertEqual(classifier.score(item, ["status/read"]), {})

    def test_primary_load_uses_local_files_only(self):
        captured = {}

        class Tokenizer:
            @classmethod
            def from_pretrained(cls, model, **kwargs):
                captured["tokenizer"] = kwargs
                return MagicMock()

        class Model:
            @classmethod
            def from_pretrained(cls, model, **kwargs):
                captured["model"] = kwargs
                loaded = MagicMock()
                loaded.config = SimpleNamespace(id2label={0: "entailment"})
                loaded.to.return_value = loaded
                return loaded

        torch = ModuleType("torch")
        torch.cuda = SimpleNamespace(is_available=lambda: False)
        torch.backends = SimpleNamespace(mps=SimpleNamespace(is_available=lambda: False))
        transformers = ModuleType("transformers")
        transformers.AutoTokenizer = Tokenizer
        transformers.AutoModelForSequenceClassification = Model
        with patch.dict("sys.modules", {"torch": torch, "transformers": transformers}):
            TransformersNLIBackend(LocalClassifierConfig(model="tasksource/ModernBERT-base-nli"))
        self.assertTrue(captured["tokenizer"]["local_files_only"])
        self.assertTrue(captured["model"]["local_files_only"])

    def test_missing_cache_explains_how_to_download(self):
        torch = ModuleType("torch")
        torch.cuda = SimpleNamespace(is_available=lambda: False)
        torch.backends = SimpleNamespace(mps=SimpleNamespace(is_available=lambda: False))
        transformers = ModuleType("transformers")

        class Tokenizer:
            @classmethod
            def from_pretrained(cls, model, **kwargs):
                raise OSError("not in cache")

        transformers.AutoTokenizer = Tokenizer
        transformers.AutoModelForSequenceClassification = MagicMock()
        with (
            patch.dict("sys.modules", {"torch": torch, "transformers": transformers}),
            self.assertRaisesRegex(LocalClassifierUnavailable, "models download"),
        ):
            TransformersNLIBackend(LocalClassifierConfig())

    def test_device_errors_are_not_reported_as_missing_cache(self):
        torch = ModuleType("torch")
        torch.cuda = SimpleNamespace(is_available=lambda: False)
        torch.backends = SimpleNamespace(mps=SimpleNamespace(is_available=lambda: False))
        transformers = ModuleType("transformers")

        class Tokenizer:
            @classmethod
            def from_pretrained(cls, model, **kwargs):
                return MagicMock()

        class Model:
            @classmethod
            def from_pretrained(cls, model, **kwargs):
                loaded = MagicMock()
                loaded.to.side_effect = RuntimeError("CUDA out of memory")
                return loaded

        transformers.AutoTokenizer = Tokenizer
        transformers.AutoModelForSequenceClassification = Model
        with (
            patch.dict("sys.modules", {"torch": torch, "transformers": transformers}),
            self.assertRaises(LocalClassifierUnavailable) as raised,
        ):
            TransformersNLIBackend(LocalClassifierConfig())
        self.assertIn("CUDA out of memory", str(raised.exception))
        self.assertNotIn("models download", str(raised.exception))

    def test_missing_entailment_label_is_not_reported_as_missing_cache(self):
        torch = ModuleType("torch")
        torch.cuda = SimpleNamespace(is_available=lambda: False)
        torch.backends = SimpleNamespace(mps=SimpleNamespace(is_available=lambda: False))
        transformers = ModuleType("transformers")

        class Tokenizer:
            @classmethod
            def from_pretrained(cls, model, **kwargs):
                return MagicMock()

        class Model:
            @classmethod
            def from_pretrained(cls, model, **kwargs):
                loaded = MagicMock()
                loaded.config = SimpleNamespace(id2label={0: "contradiction", 1: "neutral"})
                loaded.to.return_value = loaded
                return loaded

        transformers.AutoTokenizer = Tokenizer
        transformers.AutoModelForSequenceClassification = Model
        with (
            patch.dict("sys.modules", {"torch": torch, "transformers": transformers}),
            self.assertRaises(LocalClassifierUnavailable) as raised,
        ):
            TransformersNLIBackend(LocalClassifierConfig())
        self.assertIn("entailment", str(raised.exception))
        self.assertNotIn("models download", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
