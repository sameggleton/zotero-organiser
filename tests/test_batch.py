from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from zotero_organiser.daemon import Organiser
from zotero_organiser.policy import Decision


def item(key: str, item_type: str = "journalArticle", *item_tags: str) -> dict:
    return {
        "key": key,
        "data": {
            "itemType": item_type,
            "tags": [{"tag": tag} for tag in item_tags],
        },
    }


class BatchTests(unittest.TestCase):
    def organiser(self, *, write_enabled: bool = True) -> Organiser:
        organiser = Organiser.__new__(Organiser)
        organiser.config = SimpleNamespace(
            safety=SimpleNamespace(write_enabled=write_enabled),
            daemon=SimpleNamespace(allowed_item_types={"journalArticle"}),
            classification=SimpleNamespace(
                enabled=False, endpoint="https://api.openai.com/v1/chat/completions"
            ),
        )
        organiser.taxonomy = MagicMock()
        organiser.taxonomy.classifier_tags.return_value = {"topic/solvation", "method/simulation"}
        organiser.zotero = MagicMock()
        organiser.state = MagicMock()
        organiser._cycle_snapshot = "old-snapshot"
        return organiser

    def test_batch_includes_status_only_items_and_stops_at_requested_count(self):
        organiser = self.organiser()
        organiser.zotero.top_items.return_value = iter(
            [
                item("DONE0001"),
                item("STATUS01", "journalArticle", "status/reading"),
                item("TAGGED01", "journalArticle", "topic/solvation"),
                item("NOTE0001", "note"),
                item("EMPTY001"),
                item("EMPTY002"),
            ]
        )
        organiser.state.get.side_effect = lambda key: (
            SimpleNamespace(state="needs_triage") if key == "DONE0001" else None
        )
        organiser.process = MagicMock(
            side_effect=[
                {
                    "scores": {"method/simulation": 0.97},
                    "decision": Decision({"method/simulation"}, set(), set()),
                    "tags": {"status/reading", "method/simulation"},
                },
                {
                    "scores": {"topic/solvation": 0.81, "method/simulation": 0.71},
                    "decision": Decision(set(), set(), set()),
                    "tags": set(),
                },
            ]
        )

        with self.assertLogs("zotero_organiser.daemon", "INFO") as logs:
            summary = organiser.tag_untagged(2)

        self.assertEqual(summary.selected, 2)
        self.assertEqual(summary.classified, 2)
        self.assertEqual(summary.tagged, 1)
        self.assertEqual(summary.unchanged, 1)
        self.assertEqual(summary.failed, 0)
        self.assertIn(
            "INFO:zotero_organiser.daemon:classified item EMPTY001; no taxonomy tags met "
            "the acceptance threshold; top candidates: topic/solvation=0.81, method/simulation=0.71",
            logs.output,
        )
        self.assertEqual(
            [call.args[0] for call in organiser.process.call_args_list],
            ["STATUS01", "EMPTY001"],
        )
        for call in organiser.process.call_args_list:
            self.assertTrue(call.kwargs["allow_prebaseline"])
            self.assertTrue(call.kwargs["require_semantically_untagged"])

    def test_batch_requires_writes_to_be_enabled(self):
        organiser = self.organiser(write_enabled=False)
        with self.assertRaisesRegex(RuntimeError, "write_enabled"):
            organiser.tag_untagged(1)

    def test_batch_checks_local_write_support_before_scanning(self):
        organiser = self.organiser()
        organiser.zotero.require_local_write_support.side_effect = RuntimeError(
            "Zotero 10 required"
        )
        with self.assertRaisesRegex(RuntimeError, "Zotero 10"):
            organiser.tag_untagged(1)
        organiser.zotero.top_items.assert_not_called()


if __name__ == "__main__":
    unittest.main()
