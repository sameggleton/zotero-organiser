import unittest
from pathlib import Path

try:
    from pydantic import ValidationError
    from zotero_organiser.taxonomy import Taxonomy, load_taxonomy
except ModuleNotFoundError:  # Allows the stdlib-only local smoke suite to run.
    Taxonomy = None
    load_taxonomy = None
    ValidationError = None

ROOT = Path(__file__).resolve().parents[1]
GENERIC_TAXONOMY = ROOT / "src" / "zotero_organiser" / "taxonomy.yml"
MOLECULAR_SIMULATION_TAXONOMY = ROOT / "examples" / "taxonomies" / "molecular-simulation.yml"


@unittest.skipIf(Taxonomy is None, "project dependencies are not installed")
class TaxonomyTests(unittest.TestCase):
    def taxonomy(self) -> Taxonomy:
        return Taxonomy.model_validate(
            {
                "version": "1",
                "classifier": {"semantic_namespaces": ["topic"]},
                "namespaces": {
                    "status": {
                        "kind": "workflow",
                        "classifier_eligible": False,
                        "max_tags": 1,
                        "values": {"read": {}},
                    },
                    "topic": {
                        "max_tags": 1,
                        "values": {"solvation": {}, "legacy": {"classifier_eligible": False}},
                    },
                },
            }
        )

    def test_repo_root_does_not_duplicate_the_packaged_taxonomy(self):
        self.assertTrue(GENERIC_TAXONOMY.is_file())
        self.assertFalse((ROOT / "taxonomy.yml").exists())

    def test_install_user_taxonomy_copies_seed_and_refuses_packaged_overwrite(self):
        import tempfile

        from zotero_organiser.taxonomy import (
            install_user_taxonomy,
            is_packaged_taxonomy,
            packaged_taxonomy_path,
        )

        self.assertTrue(is_packaged_taxonomy(packaged_taxonomy_path()))
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / "taxonomy.yml"
            written = install_user_taxonomy(dest)
            self.assertEqual(written, dest)
            self.assertEqual(dest.read_text(), packaged_taxonomy_path().read_text())
            self.assertFalse(is_packaged_taxonomy(dest))
            with self.assertRaises(FileExistsError):
                install_user_taxonomy(dest)
            dest.write_text("stale\n")
            install_user_taxonomy(dest, force=True)
            self.assertEqual(dest.read_text(), packaged_taxonomy_path().read_text())
        with self.assertRaises(ValueError):
            install_user_taxonomy(packaged_taxonomy_path(), force=True)

    def test_generic_packaged_taxonomy_validates(self):
        taxonomy = load_taxonomy(GENERIC_TAXONOMY)
        eligible = taxonomy.classifier_tags()
        self.assertGreaterEqual(len(eligible), 10)
        self.assertLessEqual(len(eligible), 20)
        self.assertLess(len(taxonomy.tags()), 40)
        self.assertTrue(eligible <= taxonomy.tags())
        for namespace in ("field", "model", "software"):
            self.assertNotIn(namespace, taxonomy.namespaces)
            self.assertFalse(any(tag.startswith(f"{namespace}/") for tag in eligible))
        taxonomy.validate_tags(sorted(eligible)[:1])

    def test_status_tags_remain_classifier_ineligible(self):
        taxonomy = load_taxonomy(GENERIC_TAXONOMY)
        status = taxonomy.namespaces["status"]
        self.assertEqual(status.kind, "workflow")
        self.assertFalse(status.classifier_eligible)
        self.assertNotIn("status", taxonomy.classifier.semantic_namespaces)
        self.assertFalse(any(tag.startswith("status/") for tag in taxonomy.classifier_tags()))
        with self.assertRaises(ValueError):
            taxonomy.validate_tags(["status/to-read"])

    def test_priority_remains_human_owned(self):
        taxonomy = load_taxonomy(GENERIC_TAXONOMY)
        self.assertFalse(taxonomy.namespaces["priority"].classifier_eligible)
        self.assertNotIn("priority", taxonomy.classifier.semantic_namespaces)
        self.assertFalse(any(tag.startswith("priority/") for tag in taxonomy.classifier_tags()))

    def test_molecular_simulation_profile_validates(self):
        taxonomy = load_taxonomy(MOLECULAR_SIMULATION_TAXONOMY)
        eligible = taxonomy.classifier_tags()
        self.assertGreater(len(taxonomy.tags()), 100)
        self.assertEqual(
            taxonomy.classifier.semantic_namespaces,
            {"role", "topic", "system", "method"},
        )
        for namespace in ("field", "model", "software"):
            self.assertFalse(taxonomy.namespaces[namespace].classifier_eligible)
            self.assertNotIn(namespace, taxonomy.classifier.semantic_namespaces)
            self.assertFalse(any(tag.startswith(f"{namespace}/") for tag in eligible))
        self.assertFalse(any(tag.startswith("status/") for tag in eligible))
        taxonomy.validate_tags(["topic/screening"])

    def test_organiser_may_set_is_rejected(self):
        with self.assertRaises(ValidationError):
            Taxonomy.model_validate(
                {
                    "version": "1",
                    "namespaces": {
                        "status": {
                            "kind": "workflow",
                            "classifier_eligible": False,
                            "max_tags": 1,
                            "organiser_may_set": ["read"],
                            "values": {"read": {}},
                        }
                    },
                }
            )

    def test_only_eligible_canonical_tags_are_allowed(self):
        taxonomy = self.taxonomy()
        self.assertEqual(taxonomy.classifier_tags(), {"topic/solvation"})
        taxonomy.validate_tags(["topic/solvation"])
        with self.assertRaises(ValueError):
            taxonomy.validate_tags(["status/read"])
        with self.assertRaises(ValueError):
            taxonomy.validate_tags(["topic/legacy"])

    def test_prompt_definitions_can_be_limited_to_ranked_candidates(self):
        taxonomy = self.taxonomy()
        self.assertIn("topic/solvation", taxonomy.prompt_definitions({"topic/solvation"}))
        self.assertNotIn("topic/legacy", taxonomy.prompt_definitions({"topic/legacy"}))

    def test_local_classifier_hypotheses_include_positive_scope_and_exclusions(self):
        taxonomy = Taxonomy.model_validate(
            {
                "version": "1",
                "classifier": {"semantic_namespaces": ["topic"]},
                "namespaces": {
                    "topic": {
                        "max_tags": 1,
                        "values": {
                            "solvation": {
                                "description": "Solvation is central.",
                                "include": ["hydration"],
                                "exclude": ["only a passing mention"],
                            }
                        },
                    }
                },
            }
        )
        positive, exclusions = taxonomy.local_classifier_hypotheses()["topic/solvation"]
        self.assertIn("Solvation is central", positive)
        self.assertIn("hydration", positive)
        self.assertEqual(
            exclusions,
            (
                "For tag topic/solvation, this paper is in an excluded scope: only a passing mention.",
            ),
        )

    def test_relationships_must_reference_distinct_defined_tags(self):
        taxonomy = Taxonomy.model_validate(
            {
                "version": "1",
                "namespaces": {"topic": {"max_tags": 2, "values": {"a": {}, "b": {}}}},
                "relationships": [
                    {
                        "tags": ["topic/a", "topic/b"],
                        "kind": "near_duplicate",
                        "resolution": "keep_both",
                    }
                ],
            }
        )
        self.assertEqual(taxonomy.relationship_for("topic/b", "topic/a").kind, "near_duplicate")
        with self.assertRaises(ValueError):
            Taxonomy.model_validate(
                {
                    "version": "1",
                    "namespaces": {"topic": {"max_tags": 2, "values": {"a": {}, "b": {}}}},
                    "relationships": [{"tags": ["topic/a", "topic/a"], "kind": "near_duplicate"}],
                }
            )


if __name__ == "__main__":
    unittest.main()
