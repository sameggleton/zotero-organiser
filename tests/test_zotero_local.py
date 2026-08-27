import json
import unittest

import httpx

from zotero_organiser.config import ZoteroConfig
from zotero_organiser.zotero import LocalWriteUnsupported, ZoteroClient


class LocalApiTests(unittest.TestCase):
    def test_top_items_are_requested_oldest_first(self):
        requests = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json=[{"key": "ABC12345", "data": {}}])

        client = ZoteroClient(
            ZoteroConfig(), client=httpx.Client(transport=httpx.MockTransport(handler))
        )
        self.assertEqual([item["key"] for item in client.top_items()], ["ABC12345"])
        self.assertEqual(requests[0].url.path, "/api/users/0/items/top")
        self.assertEqual(requests[0].url.params["sort"], "dateAdded")
        self.assertEqual(requests[0].url.params["direction"], "asc")
        client.close()

    def test_children_are_paginated_past_one_hundred(self):
        requests = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            start = int(request.url.params["start"])
            payload = [{"key": str(start + i), "data": {}} for i in range(100 if start == 0 else 1)]
            return httpx.Response(200, json=payload)

        client = ZoteroClient(
            ZoteroConfig(), client=httpx.Client(transport=httpx.MockTransport(handler))
        )
        children = client.children("PARENTKEY")
        self.assertEqual(len(children), 101)
        child_requests = [
            request
            for request in requests
            if request.url.path.endswith("/items/PARENTKEY/children")
        ]
        self.assertEqual(len(child_requests), 2)
        client.close()

    def test_collections_and_collection_items_are_paginated(self):
        requests = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            start = int(request.url.params["start"])
            if request.url.path.endswith("/collections"):
                payload = [
                    {"key": str(start + i), "data": {"name": f"C{start + i}"}}
                    for i in range(100 if start == 0 else 1)
                ]
            else:
                payload = [
                    {"key": str(start + i), "data": {}} for i in range(100 if start == 0 else 1)
                ]
            return httpx.Response(200, json=payload)

        client = ZoteroClient(
            ZoteroConfig(), client=httpx.Client(transport=httpx.MockTransport(handler))
        )
        self.assertEqual(len(list(client.collections())), 101)
        self.assertEqual(len(list(client.collection_items("COLLECTION"))), 101)
        self.assertTrue(
            any(r.url.path.endswith("/collections/COLLECTION/items/top") for r in requests)
        )
        client.close()

    def test_reads_learn_server_identity_and_writes_authorize_locally(self):
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            headers = {"Zotero-Server-ID": "local-server", "Last-Modified-Version": "7"}
            if request.url.path.endswith("/local/authorize"):
                self.assertEqual(request.headers["Zotero-Server-ID"], "local-server")
                return httpx.Response(
                    200, headers=headers, json={"key": "local-key", "remember": True}
                )
            if request.method == "PUT":
                self.assertEqual(request.headers["Zotero-API-Key"], "local-key")
                self.assertEqual(request.headers["Zotero-Server-ID"], "local-server")
                self.assertEqual(
                    json.loads(request.content),
                    {
                        "key": "ABC",
                        "version": 7,
                        "itemType": "journalArticle",
                        "tags": [{"tag": "topic/screening"}],
                    },
                )
                return httpx.Response(200, headers=headers, json={"successful": {"0": "ABC"}})
            item = {
                "key": "ABC",
                "version": 7,
                "data": {"key": "ABC", "version": 7, "itemType": "journalArticle", "tags": []},
            }
            return httpx.Response(200, headers=headers, content=json.dumps(item))

        client = ZoteroClient(
            ZoteroConfig(), client=httpx.Client(transport=httpx.MockTransport(handler))
        )
        self.assertEqual(client.library_version(), 7)
        self.assertEqual(client.server_id, "local-server")
        self.assertEqual(client.authorize_write(), "local-key")
        written = client.update_tags(
            {
                "key": "ABC",
                "version": 7,
                "data": {"key": "ABC", "version": 7, "itemType": "journalArticle", "tags": []},
            },
            {"topic/screening"},
        )
        self.assertEqual(written["key"], "ABC")
        self.assertTrue(any(call.method == "PUT" for call in calls))
        client.close()

    def test_zotero_9_fails_before_calling_missing_authorize_route(self):
        requests = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(
                200,
                headers={"X-Zotero-Version": "9.0.6", "Last-Modified-Version": "7"},
                json=[],
            )

        client = ZoteroClient(
            ZoteroConfig(), client=httpx.Client(transport=httpx.MockTransport(handler))
        )
        with self.assertRaisesRegex(LocalWriteUnsupported, "Zotero 9.0.6.*Zotero 10"):
            client.authorize_write()
        self.assertTrue(all(request.method == "GET" for request in requests))
        client.close()


if __name__ == "__main__":
    unittest.main()
