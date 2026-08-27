from __future__ import annotations

import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import httpx

from zotero_organiser.classify import Classification, Classifier
from zotero_organiser.config import ClassificationConfig
from zotero_organiser.taxonomy import Taxonomy, load_taxonomy, AVAILABLE_PROFILES

PROFILES_DIR = Path(__file__).resolve().parents[1] / "examples" / "taxonomies" / "profiles"

ALL_PROFILES = [f"{pid}.yml" for pid in AVAILABLE_PROFILES]

DOMAIN_SAMPLE_PAPERS: dict[str, dict[str, any]] = {
    "physics-astronomy.yml": {
        "item": {
            "key": "PHYS001",
            "data": {
                "title": "Quantum entanglement and topological states in superconducting circuits",
                "abstractNote": (
                    "We experimentally investigate robust quantum entanglement and topological states "
                    "in superconducting qubit circuits using microwave spectroscopy and simulations."
                ),
                "tags": [],
                "collections": [],
            },
        },
        "sample_tags": [
            "role/empirical",
            "topic/quantum-physics",
            "topic/condensed-matter",
            "system/quantum-devices",
            "method/laboratory-experiment",
        ],
    },
    "biological-sciences.yml": {
        "item": {
            "key": "BIO001",
            "data": {
                "title": "CRISPR-Cas9 mediated gene editing reveals essential mechanisms in cell division",
                "abstractNote": (
                    "Using targeted CRISPR-Cas9 genome editing and fluorescence microscopy, we investigate "
                    "cell cycle regulation, cytoskeleton dynamics, and genetics in model organisms."
                ),
                "tags": [],
                "collections": [],
            },
        },
        "sample_tags": [
            "role/empirical",
            "topic/cell-biology",
            "topic/genetics",
            "system/cellular-systems",
            "method/gene-editing",
        ],
    },
    "chemistry-molecular-sciences.yml": {
        "item": {
            "key": "CHEM001",
            "data": {
                "title": "Total organic synthesis and electrocatalytic characterization of porous frameworks",
                "abstractNote": (
                    "We report the multi-step organic synthesis of crystalline frameworks exhibiting "
                    "high electrocatalytic activity, confirmed via NMR spectroscopy and cyclic voltammetry."
                ),
                "tags": [],
                "collections": [],
            },
        },
        "sample_tags": [
            "role/empirical",
            "topic/organic-chemistry",
            "topic/electrochemistry",
            "system/molecular-compounds",
            "method/chemical-synthesis",
        ],
    },
    "computer-information-sciences.yml": {
        "item": {
            "key": "CS001",
            "data": {
                "title": "Transformer-based machine learning algorithms for distributed systems optimization",
                "abstractNote": (
                    "We propose a deep neural network architecture and reinforcement learning algorithm "
                    "for automated scheduling in large-scale distributed cloud infrastructure."
                ),
                "tags": [],
                "collections": [],
            },
        },
        "sample_tags": [
            "role/methodological",
            "topic/machine-learning",
            "topic/distributed-systems",
            "system/software-systems",
            "method/algorithmic-design",
        ],
    },
    "economics.yml": {
        "item": {
            "key": "ECON001",
            "data": {
                "title": "Econometric analysis of monetary policy transmission on household income inequality",
                "abstractNote": (
                    "Using difference-in-differences econometrics and macroeconomic panel data, we estimate "
                    "the distributional impact of central bank interest rate shocks on microeconomic consumer choice."
                ),
                "tags": [],
                "collections": [],
            },
        },
        "sample_tags": [
            "role/empirical",
            "topic/econometrics",
            "topic/macroeconomics",
            "system/national-economies",
            "method/quasi-experimental-econometrics",
        ],
    },
    "indigenous-studies.yml": {
        "item": {
            "key": "IND001",
            "data": {
                "title": "Traditional ecological knowledge and Indigenous governance in Caring for Country",
                "abstractNote": (
                    "Through yarning methodologies and participatory research with First Nations communities, "
                    "we examine cultural burning practices, self-determination, and land stewardship."
                ),
                "tags": [],
                "collections": [],
            },
        },
        "sample_tags": [
            "role/empirical",
            "topic/indigenous-knowledge",
            "topic/indigenous-governance",
            "system/indigenous-communities",
            "method/yarning-and-oral-storywork",
        ],
    },
}


class DomainProfilesE2ETests(unittest.TestCase):
    def test_all_25_profiles_load_and_validate(self):
        self.assertEqual(len(ALL_PROFILES), 25)
        for profile_filename in ALL_PROFILES:
            profile_path = PROFILES_DIR / profile_filename
            with self.subTest(profile=profile_filename):
                self.assertTrue(profile_path.is_file(), f"Profile {profile_filename} missing")
                tax = load_taxonomy(profile_path)
                self.assertIsInstance(tax, Taxonomy)
                self.assertGreaterEqual(len(tax.classifier_tags()), 20)

    def test_sample_papers_classification_e2e(self):
        for profile_name, sample in DOMAIN_SAMPLE_PAPERS.items():
            profile_path = PROFILES_DIR / profile_name
            with self.subTest(domain=profile_name):
                tax = load_taxonomy(profile_path)

                item = sample["item"]
                expected_tags = sample["sample_tags"]

                # Ensure expected tags exist in the profile
                for tag in expected_tags:
                    self.assertIn(
                        tag,
                        tax.classifier_tags(),
                        f"Expected tag {tag} not in {profile_name}",
                    )

                # Test prompt construction
                prompt_def = tax.prompt_definitions()
                self.assertIn("role", prompt_def)
                self.assertIn("topic", prompt_def)
                self.assertIn("system", prompt_def)
                self.assertIn("method", prompt_def)

                # Mock LLM response
                mock_payload = {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "tags": [
                                            {"tag": t, "confidence": 0.95} for t in expected_tags
                                        ]
                                    }
                                )
                            }
                        }
                    ]
                }
                mock_response = httpx.Response(
                    200,
                    request=httpx.Request("POST", "http://localhost:8000/v1/chat/completions"),
                    json=mock_payload,
                )

                config = ClassificationConfig(
                    enabled=True,
                    provider="openai_compatible",
                    model="test-model",
                    base_url="http://localhost:8000/v1",
                    api_key="mock",
                )
                classifier = Classifier(config, tax)

                with patch.dict(os.environ, {"OPENAI_API_KEY": "mock-key"}):
                    with patch.object(classifier, "_post", return_value=mock_response):
                        result = classifier.classify(item)
                        self.assertIsInstance(result, Classification)
                        result_tags = {label.tag for label in result.tags}
                        self.assertEqual(result_tags, set(expected_tags))
                        self.assertEqual(len(result.tags), len(expected_tags))
