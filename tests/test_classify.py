from __future__ import annotations

import json
import os
import unittest
from unittest.mock import MagicMock, patch

import httpx

from zotero_organiser.classify import Classification, Classifier, ClassifierRequestError, input_hash
from zotero_organiser.config import ClassificationConfig, LocalClassifierConfig
from zotero_organiser.ranking import Candidate, RankerUnavailable, Ranking


class ClassifierTests(unittest.TestCase):
    def classifier(self) -> Classifier:
        taxonomy = MagicMock()
        taxonomy.classifier.rules = []
        taxonomy.classifier_tags.return_value = {"topic/screening"}
        taxonomy.prompt_definitions.return_value = "topic/screening"
        return Classifier(ClassificationConfig(enabled=True), taxonomy)

    @patch("zotero_organiser.classify.time.sleep")
    @patch("zotero_organiser.classify.httpx.post")
    def test_http_400_and_409_are_terminal(self, post, sleep):
        request = httpx.Request("POST", "https://classifier.example/v1/chat/completions")
        item = {"data": {"title": "Paper", "tags": [], "collections": []}}
        for status in (400, 409):
            with self.subTest(status=status):
                post.reset_mock()
                sleep.reset_mock()
                post.return_value = httpx.Response(
                    status, request=request, json={"error": {"message": "permanent client error"}}
                )
                with patch.dict(os.environ, {"OPENAI_API_KEY": "secret"}):
                    with self.assertRaisesRegex(
                        ClassifierRequestError, f"HTTP {status}.*permanent client error"
                    ):
                        self.classifier().classify(item)
                self.assertEqual(post.call_count, 1)
                sleep.assert_not_called()

    @patch("zotero_organiser.classify.time.sleep")
    @patch("zotero_organiser.classify.httpx.post")
    def test_transient_429_and_5xx_are_retried(self, post, sleep):
        request = httpx.Request("POST", "https://classifier.example/v1/chat/completions")
        item = {"data": {"title": "Paper", "tags": [], "collections": []}}
        for status in (408, 429, 503):
            with self.subTest(status=status):
                post.reset_mock()
                sleep.reset_mock()
                post.side_effect = [
                    httpx.Response(
                        status,
                        request=request,
                        json={"error": {"message": "temporary gateway failure"}},
                    ),
                    httpx.Response(
                        200,
                        request=request,
                        json={"choices": [{"message": {"content": '{"tags": []}'}}]},
                    ),
                ]
                with patch.dict(os.environ, {"OPENAI_API_KEY": "secret"}):
                    result = self.classifier().classify(item)
                self.assertEqual(result.tags, [])
                self.assertEqual(post.call_count, 2)
                sleep.assert_called_once_with(1)

    @patch("zotero_organiser.classify.time.sleep")
    @patch("zotero_organiser.classify.httpx.post")
    def test_final_error_includes_provider_detail(self, post, _sleep):
        request = httpx.Request("POST", "https://classifier.example/v1/chat/completions")
        post.return_value = httpx.Response(
            400, request=request, json={"error": {"message": "unsupported response format"}}
        )
        item = {"data": {"title": "Paper", "tags": [], "collections": []}}
        with patch.dict(os.environ, {"OPENAI_API_KEY": "secret"}):
            with self.assertRaisesRegex(
                ClassifierRequestError, "HTTP 400.*unsupported response format"
            ):
                self.classifier().classify(item)
        self.assertEqual(post.call_count, 1)

    @patch("zotero_organiser.classify.httpx.post")
    def test_shortlist_mode_limits_prompt_and_schema_to_ranker_candidates(self, post):
        post.return_value = httpx.Response(
            200, json={"choices": [{"message": {"content": '{"tags": []}'}}]}
        )
        taxonomy = MagicMock()
        taxonomy.classifier.rules = []
        taxonomy.classifier_tags.return_value = {"topic/screening", "topic/other"}
        taxonomy.prompt_definitions.return_value = "topic/screening"
        ranker = MagicMock()
        ranker.config.mode = "shortlist"
        ranker.rank.return_value = Ranking(
            (Candidate("topic/screening", 0.9, 0.4, frozenset({"dense"})),)
        )
        item = {"key": "ABC", "data": {"title": "Paper", "tags": [], "collections": []}}

        with patch.dict(os.environ, {"OPENAI_API_KEY": "secret"}):
            Classifier(ClassificationConfig(enabled=True), taxonomy, ranker).classify(item)

        taxonomy.prompt_definitions.assert_called_once_with({"topic/screening"})
        schema = post.call_args.kwargs["json"]["response_format"]["json_schema"]["schema"]
        self.assertEqual(
            schema["properties"]["tags"]["items"]["properties"]["tag"]["enum"], ["topic/screening"]
        )

    @patch("zotero_organiser.classify.httpx.post")
    def test_unavailable_ranker_falls_back_to_full_taxonomy(self, post):
        post.return_value = httpx.Response(
            200, json={"choices": [{"message": {"content": '{"tags": []}'}}]}
        )
        taxonomy = MagicMock()
        taxonomy.classifier.rules = []
        taxonomy.classifier_tags.return_value = {"topic/screening"}
        taxonomy.prompt_definitions.return_value = "topic/screening"
        ranker = MagicMock()
        ranker.rank.side_effect = RankerUnavailable("not installed")
        item = {"key": "ABC", "data": {"title": "Paper", "tags": [], "collections": []}}

        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "secret"}),
            self.assertLogs("zotero_organiser.classify", "WARNING"),
        ):
            Classifier(ClassificationConfig(enabled=True), taxonomy, ranker).classify(item)

        taxonomy.prompt_definitions.assert_called_once_with(None)

    @patch("zotero_organiser.classify.httpx.post")
    def test_logs_classifier_request_timing(self, post):
        post.return_value = httpx.Response(
            200, json={"choices": [{"message": {"content": '{"tags": []}'}}]}
        )
        taxonomy = MagicMock()
        taxonomy.classifier.rules = []
        taxonomy.classifier_tags.return_value = {"topic/screening"}
        taxonomy.prompt_definitions.return_value = "topic/screening"
        item = {"key": "ABC", "data": {"title": "Paper", "tags": [], "collections": []}}

        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "secret"}),
            self.assertLogs("zotero_organiser.classify", "INFO") as logs,
        ):
            Classifier(ClassificationConfig(enabled=True), taxonomy).classify(item)

        self.assertTrue(
            any("timing item=ABC phase=classifier_request seconds=" in line for line in logs.output)
        )

    @patch("zotero_organiser.classify.httpx.post")
    def test_primary_local_classifier_bypasses_remote_request(self, post):
        taxonomy = MagicMock()
        taxonomy.classifier.rules = []
        taxonomy.namespaces = {}
        ranker = MagicMock()
        ranker.config.mode = "shadow"
        ranker.rank.return_value = Ranking(
            (Candidate("topic/screening", 0.9, 0.4, frozenset({"dense"})),)
        )
        local = MagicMock()
        local.config = LocalClassifierConfig(enabled=True, mode="primary")
        local.score.return_value = {"topic/screening": 0.95}
        classifier = Classifier(ClassificationConfig(), taxonomy, ranker, local)
        expected = Classification.model_validate(
            {"tags": [{"tag": "topic/screening", "confidence": 0.95}]}
        )
        classifier._local_classification = MagicMock(return_value=expected)

        result = classifier.classify(
            {"key": "ABC", "data": {"title": "Paper", "tags": [], "collections": []}}
        )

        self.assertEqual(result, expected)
        post.assert_not_called()
        local.score.assert_called_once_with(
            {"key": "ABC", "data": {"title": "Paper", "tags": [], "collections": []}},
            {"topic/screening"},
        )

    @patch("zotero_organiser.classify.httpx.post")
    def test_prompt_puts_rules_in_system_and_document_fields_in_json_user(self, post):
        post.return_value = httpx.Response(
            200, json={"choices": [{"message": {"content": '{"tags": []}'}}]}
        )
        item = {
            "data": {
                "title": "Paper",
                "abstractNote": "An abstract",
                "itemType": "journalArticle",
                "publicationTitle": "Journal",
                "tags": [{"tag": "role/review"}],
                "collections": ["COLLID"],
            }
        }
        with patch.dict(os.environ, {"OPENAI_API_KEY": "secret"}):
            self.classifier().classify(item)

        messages = post.call_args.kwargs["json"]["messages"]
        self.assertEqual([message["role"] for message in messages], ["system", "user"])
        system, user = messages
        combined = f"{system['content']}\n{user['content']}".lower()
        self.assertNotIn("scientific document", combined)
        self.assertNotIn("collid", combined)
        document = json.loads(user["content"])
        self.assertEqual(
            document,
            {
                "abstract": "An abstract",
                "existing_tags": ["role/review"],
                "itemType": "journalArticle",
                "publication": "Journal",
                "title": "Paper",
            },
        )
        self.assertNotIn("collections", document)
        self.assertIn("Taxonomy rules:", system["content"])
        self.assertIn("topic/screening", system["content"])
        self.assertNotIn("Classify", user["content"])

    def test_input_hash_matches_sent_fields_and_omits_collections(self):
        base = {
            "data": {
                "title": "Paper",
                "abstractNote": "Abs",
                "itemType": "journalArticle",
                "publicationTitle": "J",
                "tags": [{"tag": "role/review"}],
                "collections": ["AAAA"],
            }
        }
        other_collections = {"data": {**base["data"], "collections": ["BBBB"]}}
        other_title = {"data": {**base["data"], "title": "Other"}}
        digest = input_hash(base, "tax-1", "cls-1", {"role/review"})
        self.assertEqual(digest, input_hash(other_collections, "tax-1", "cls-1", {"role/review"}))
        self.assertNotEqual(digest, input_hash(other_title, "tax-1", "cls-1", {"role/review"}))
        self.assertNotEqual(digest, input_hash(base, "tax-1", "cls-1", set()))


if __name__ == "__main__":
    unittest.main()
