import unittest

from zotero_organiser.reconcile import reconcile


class ReconciliationTests(unittest.TestCase):
    def test_human_tag_is_never_claimed(self):
        plan = reconcile({"topic/solvation"}, set(), {"topic/solvation"})
        self.assertIn("topic/solvation", plan.tags)
        self.assertNotIn("topic/solvation", plan.auto_tags)

    def test_removed_owned_semantic_tag_is_suppressed(self):
        plan = reconcile(set(), {"topic/solvation"}, {"topic/solvation"})
        self.assertIn("topic/solvation", plan.suppressed_tags)
        self.assertNotIn("topic/solvation", plan.tags)

    def test_existing_status_is_preserved_but_never_owned(self):
        plan = reconcile(
            {"status/reading"},
            {"status/reading"},
            {"topic/solvation"},
            allow_tag_removal=True,
        )
        self.assertEqual(plan.tags, {"status/reading", "topic/solvation"})
        self.assertEqual(plan.auto_tags, {"topic/solvation"})

    def test_classifier_status_output_is_ignored(self):
        plan = reconcile(set(), set(), {"status/to-read", "topic/solvation"})
        self.assertEqual(plan.tags, {"topic/solvation"})
        self.assertEqual(plan.auto_tags, {"topic/solvation"})

    def test_deleted_legacy_auto_status_is_not_suppressed(self):
        plan = reconcile(set(), {"status/needs-triage"}, set())
        self.assertEqual(plan.tags, set())
        self.assertEqual(plan.auto_tags, set())
        self.assertEqual(plan.suppressed_tags, set())

    def test_no_status_is_added_when_no_semantic_tag_is_accepted(self):
        plan = reconcile(set(), set(), set())
        self.assertEqual(plan.tags, set())
        self.assertEqual(plan.auto_tags, set())

    def test_no_removal_preserves_owned_semantic_tag(self):
        plan = reconcile(
            {"topic/solvation"},
            {"topic/solvation"},
            set(),
            allow_tag_removal=False,
        )
        self.assertEqual(plan.tags, {"topic/solvation"})
        self.assertEqual(plan.auto_tags, {"topic/solvation"})


if __name__ == "__main__":
    unittest.main()
