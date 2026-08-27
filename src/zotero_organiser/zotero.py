from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from .config import ZoteroConfig


class VersionConflict(RuntimeError):
    pass


class LocalWriteDenied(RuntimeError):
    pass


class LocalWriteUnsupported(RuntimeError):
    pass


class ZoteroClient:
    """Zotero desktop Local API client (API v3, localhost only)."""

    def __init__(
        self,
        config: ZoteroConfig,
        *,
        server_id: str | None = None,
        local_api_key: str | None = None,
        client: httpx.Client | None = None,
    ):
        self.config = config
        self.base = f"{config.base_url.rstrip('/')}/users/0"
        self.server_id = server_id
        self.local_api_key = local_api_key
        self.zotero_version: str | None = None
        self.client = client or httpx.Client(
            headers={"Zotero-API-Version": "3", "Zotero-Allowed-Request": "1"}, timeout=30
        )

    def close(self) -> None:
        self.client.close()

    def _headers(self, *, write: bool = False) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.server_id:
            headers["Zotero-Server-ID"] = self.server_id
        if write and self.local_api_key:
            headers["Zotero-API-Key"] = self.local_api_key
        return headers

    def _read(self, path: str, *, params: dict[str, str | int] | None = None) -> httpx.Response:
        response = self.client.get(f"{self.base}{path}", params=params, headers=self._headers())
        response.raise_for_status()
        self._remember_server(response)
        return response

    def _remember_server(self, response: httpx.Response) -> None:
        version = response.headers.get("X-Zotero-Version")
        if version:
            self.zotero_version = version
        server_id = response.headers.get("Zotero-Server-ID")
        if server_id:
            self.server_id = server_id

    def require_local_write_support(self) -> None:
        """Fail before classification when the running Zotero is read-only."""
        if self.zotero_version is None:
            self.library_version()
        if self.server_id:
            return
        version = f" {self.zotero_version}" if self.zotero_version else ""
        raise LocalWriteUnsupported(
            f"Zotero{version} Local API is read-only; install Zotero 10 or newer to tag items locally"
        )

    def changed_items(self, since: int) -> tuple[list[dict[str, Any]], int]:
        params: dict[str, str | int] = {"format": "json", "limit": 100, "since": since}
        items: list[dict[str, Any]] = []
        start = 0
        version: int | None = None
        while True:
            response = self._read("/items", params={**params, "start": start})
            page = response.json()
            items.extend(page)
            if version is None:
                version = int(response.headers["Last-Modified-Version"])
            if len(page) < int(params["limit"]):
                return items, version
            start += len(page)

    def top_items(self, *, direction: str = "asc") -> Iterator[dict[str, Any]]:
        """Yield top-level library items in stable chronological order."""
        if direction not in {"asc", "desc"}:
            raise ValueError("direction must be 'asc' or 'desc'")
        params: dict[str, str | int] = {
            "format": "json",
            "limit": 100,
            "sort": "dateAdded",
            "direction": direction,
        }
        start = 0
        while True:
            page = self._read("/items/top", params={**params, "start": start}).json()
            yield from page
            if len(page) < int(params["limit"]):
                return
            start += len(page)

    def collections(self) -> Iterator[dict[str, Any]]:
        """Yield every collection from the local library API."""
        yield from self._paginated("/collections")

    def collection_items(self, key: str) -> Iterator[dict[str, Any]]:
        """Yield items in a collection, without expanding child items."""
        yield from self._paginated(f"/collections/{key}/items/top")

    def _paginated(self, path: str) -> Iterator[dict[str, Any]]:
        params: dict[str, str | int] = {"format": "json", "limit": 100}
        start = 0
        while True:
            page = self._read(path, params={**params, "start": start}).json()
            yield from page
            if len(page) < int(params["limit"]):
                return
            start += len(page)

    def library_version(self) -> int:
        response = self._read("/items", params={"format": "json", "limit": 1})
        return int(response.headers["Last-Modified-Version"])

    def get_item(self, key: str) -> dict[str, Any]:
        return self._read(f"/items/{key}", params={"format": "json"}).json()

    def children(self, key: str) -> list[dict[str, Any]]:
        return list(self._paginated(f"/items/{key}/children"))

    def authorize_write(self) -> str:
        self.require_local_write_support()
        response = self.client.post(
            f"{self.config.base_url.rstrip('/')}/local/authorize",
            json={"appName": self.config.app_name},
            headers={"Content-Type": "application/json", **self._headers(write=True)},
        )
        if response.status_code == 403:
            raise LocalWriteDenied("local API write authorization was denied in Zotero")
        if response.status_code == 404:
            raise LocalWriteUnsupported(
                "this Zotero build does not expose local write authorization; install Zotero 10 or newer"
            )
        response.raise_for_status()
        self._remember_server(response)
        key = response.json().get("key")
        if not isinstance(key, str) or not key:
            raise RuntimeError("local API authorization returned no key")
        self.local_api_key = key
        return key

    def update_tags(self, item: dict[str, Any], tags: set[str]) -> dict[str, Any]:
        # GET responses wrap the API item JSON in a data object. PUT expects
        # that inner item JSON directly, not the read-response wrapper.
        payload = dict(item["data"], tags=[{"tag": tag} for tag in sorted(tags)])
        response = self.client.put(
            f"{self.base}/items/{item['key']}",
            json=payload,
            headers={
                "If-Unmodified-Since-Version": str(item["version"]),
                **self._headers(write=True),
            },
        )
        if response.status_code == 401:
            raise LocalWriteDenied("local API write authorization is required or expired")
        if response.status_code == 412:
            raise VersionConflict(item["key"])
        response.raise_for_status()
        self._remember_server(response)
        return self.get_item(item["key"])


def tags(item: dict[str, Any]) -> set[str]:
    return {entry["tag"] for entry in item["data"].get("tags", []) if "tag" in entry}


def eligible(item: dict[str, Any], allowed_types: set[str]) -> bool:
    data = item.get("data", {})
    return (
        not data.get("deleted", False)
        and data.get("itemType") in allowed_types
        and not data.get("parentItem")
    )
