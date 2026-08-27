from pathlib import Path
import unittest

from zotero_organiser.taxonomy import Taxonomy, load_taxonomy, AVAILABLE_PROFILES

PROFILES_DIR = Path(__file__).resolve().parents[1] / "examples" / "taxonomies" / "profiles"

REQUIRED_PROFILES = [f"{pid}.yml" for pid in AVAILABLE_PROFILES]


class TaxonomyProfilesTests(unittest.TestCase):
    def test_all_profile_files_exist(self):
        self.assertTrue(PROFILES_DIR.is_dir(), f"Directory not found: {PROFILES_DIR}")
        self.assertEqual(len(REQUIRED_PROFILES), 25)
        for filename in REQUIRED_PROFILES:
            profile_path = PROFILES_DIR / filename
            self.assertTrue(profile_path.is_file(), f"Profile file missing: {profile_path}")

    def test_all_profiles_validate_cleanly(self):
        for filename in REQUIRED_PROFILES:
            profile_path = PROFILES_DIR / filename
            with self.subTest(profile=filename):
                tax = load_taxonomy(profile_path)
                self.assertIsInstance(tax, Taxonomy)
                self.assertEqual(tax.schema_version, 1)
                self.assertEqual(tax.version, "1.0.0")

                # Verify required namespaces
                for ns in ["status", "priority", "role", "topic", "system", "method"]:
                    self.assertIn(ns, tax.namespaces, f"Namespace '{ns}' missing in {filename}")

                # Status is workflow & ineligible
                status_ns = tax.namespaces["status"]
                self.assertEqual(status_ns.kind, "workflow")
                self.assertFalse(status_ns.classifier_eligible)
                self.assertEqual(status_ns.max_tags, 1)
                self.assertTrue(status_ns.mutually_exclusive)

                # Priority is judgement & ineligible
                priority_ns = tax.namespaces["priority"]
                self.assertEqual(priority_ns.kind, "judgement")
                self.assertFalse(priority_ns.classifier_eligible)

                # Semantic namespaces
                for sem_ns in ["role", "topic", "system", "method"]:
                    ns_obj = tax.namespaces[sem_ns]
                    self.assertEqual(ns_obj.kind, "semantic")
                    self.assertTrue(ns_obj.classifier_eligible)
                    self.assertGreater(len(ns_obj.values), 0)

                # Check tags and classifier tags
                all_tags = tax.tags()
                classifier_tags = tax.classifier_tags()

                self.assertGreaterEqual(len(classifier_tags), 20)
                self.assertTrue(classifier_tags.issubset(all_tags))
                self.assertFalse(any(t.startswith("status/") for t in classifier_tags))
                self.assertFalse(any(t.startswith("priority/") for t in classifier_tags))

                # Verify prompt definitions and hypotheses work
                prompt = tax.prompt_definitions()
                self.assertIn("role (at most", prompt)
                self.assertIn("topic (at most", prompt)
                self.assertNotIn("status (at most", prompt)

                hypotheses = tax.local_classifier_hypotheses()
                self.assertGreater(len(hypotheses), 0)
