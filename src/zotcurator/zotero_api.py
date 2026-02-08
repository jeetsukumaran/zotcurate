"""Zotero Web API client using only the standard library.

Provides collection listing, creation, and item management.
All mutating operations support dry-run mode (default).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Optional

from zotcurator.log import get_logger

BASE_URL = "https://api.zotero.org"


@dataclass(frozen=True, slots=True)
class ZoteroCollection:
    """A Zotero collection."""

    key: str
    name: str
    parent_key: Optional[str]
    version: int
    num_items: int

    @staticmethod
    def from_api(data: dict[str, Any]) -> ZoteroCollection:
        d = data.get("data", data)
        meta = data.get("meta", {})
        return ZoteroCollection(
            key=d["key"],
            name=d["name"],
            parent_key=d.get("parentCollection") or None,
            version=d.get("version", 0),
            num_items=meta.get("numItems", 0),
        )


@dataclass(slots=True)
class CollectionTree:
    """Hierarchical representation of collections."""

    collections: list[ZoteroCollection]
    children: dict[Optional[str], list[ZoteroCollection]] = field(
        default_factory=dict,
    )

    @staticmethod
    def build(collections: list[ZoteroCollection]) -> CollectionTree:
        children: dict[Optional[str], list[ZoteroCollection]] = {}
        for c in collections:
            children.setdefault(c.parent_key, []).append(c)
        for key in children:
            children[key].sort(key=lambda x: x.name.lower())
        return CollectionTree(collections=collections, children=children)

    def format_tree(self, *, filter_pattern: Optional[str] = None) -> str:
        """Format collections as a nested directory-like tree."""
        import re

        lines: list[str] = []
        compiled = (
            re.compile(filter_pattern, re.IGNORECASE) if filter_pattern else None
        )

        def _walk(parent_key: Optional[str], prefix: str) -> None:
            for coll in self.children.get(parent_key, []):
                path = f"{prefix}{coll.name}"
                has_children = coll.key in self.children
                display = f"{path}/" if has_children else path
                if compiled is None or compiled.search(display):
                    lines.append(display)
                _walk(coll.key, f"{path}/")

        _walk(None, "")
        return "\n".join(lines)

    def find_by_path(self, path: str) -> Optional[ZoteroCollection]:
        """Find a collection by slash-separated path (case-insensitive)."""
        parts = [p.strip() for p in path.strip("/").split("/") if p.strip()]
        if not parts:
            return None

        current_parent: Optional[str] = None
        found: Optional[ZoteroCollection] = None

        for part in parts:
            siblings = self.children.get(current_parent, [])
            match = None
            for c in siblings:
                if c.name.lower() == part.lower():
                    match = c
                    break
            if match is None:
                return None
            found = match
            current_parent = match.key

        return found


class ZoteroClient:
    """Minimal Zotero Web API client."""

    def __init__(
        self,
        library_id: str,
        api_key: str,
        library_type: str = "user",
    ) -> None:
        self._library_id = library_id
        self._api_key = api_key
        self._library_type = library_type
        self._base = f"{BASE_URL}/{library_type}s/{library_id}"
        self._logger = get_logger()

    def _request(
        self,
        method: str,
        path: str,
        *,
        data: Any = None,
        params: Optional[dict[str, str]] = None,
        extra_headers: Optional[dict[str, str]] = None,
    ) -> tuple[Any, dict[str, str]]:
        """Make an API request and return (parsed_json, response_headers)."""
        url = f"{self._base}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        headers: dict[str, str] = {
            "Zotero-API-Key": self._api_key,
            "Zotero-API-Version": "3",
        }
        if extra_headers:
            headers.update(extra_headers)

        body: Optional[bytes] = None
        if data is not None:
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"

        self._logger.debug("%s %s", method, url)
        if body:
            self._logger.debug("Request body: %s", body[:500])

        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                resp_headers = {k.lower(): v for k, v in resp.headers.items()}
                resp_body = resp.read().decode("utf-8")
                self._logger.debug(
                    "Response (%d): %s", resp.status, resp_body[:500]
                )
                if resp_body:
                    return json.loads(resp_body), resp_headers
                return None, resp_headers
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            self._logger.error(
                "API error %d %s: %s", e.code, e.reason, body_text[:500]
            )
            raise ZoteroAPIError(e.code, e.reason, body_text) from e

    def get_collections(self) -> list[ZoteroCollection]:
        """Fetch all collections, handling pagination."""
        collections: list[ZoteroCollection] = []
        start = 0
        limit = 100
        while True:
            data, headers = self._request(
                "GET",
                "/collections",
                params={"start": str(start), "limit": str(limit)},
            )
            if not data:
                break
            for item in data:
                collections.append(ZoteroCollection.from_api(item))
            total = int(headers.get("total-results", len(data)))
            start += limit
            if start >= total:
                break
        self._logger.info("Fetched %d collections", len(collections))
        return collections

    def get_collection_item_keys(self, collection_key: str) -> list[str]:
        """Get item keys in a collection using keys format."""
        url = f"{self._base}/collections/{collection_key}/items"
        params = {"format": "keys"}
        url += "?" + urllib.parse.urlencode(params)

        headers = {
            "Zotero-API-Key": self._api_key,
            "Zotero-API-Version": "3",
        }
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req) as resp:
                text = resp.read().decode("utf-8")
                return [k.strip() for k in text.strip().split("\n") if k.strip()]
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            raise ZoteroAPIError(e.code, e.reason, body_text) from e

    def create_collection(
        self,
        name: str,
        parent_key: Optional[str] = None,
        *,
        execute: bool = False,
    ) -> Optional[ZoteroCollection]:
        """Create a new collection. Returns None in dry-run mode."""
        payload: dict[str, Any] = {"name": name}
        if parent_key:
            payload["parentCollection"] = parent_key

        if not execute:
            self._logger.info(
                "[DRY RUN] Would create collection: %s (parent=%s)",
                name,
                parent_key or "root",
            )
            return None

        data, _ = self._request("POST", "/collections", data=[payload])
        if data and "successful" in data:
            for _key, val in data["successful"].items():
                return ZoteroCollection.from_api(val)
        return None

    def add_items_to_collection(
        self,
        collection_key: str,
        item_keys: list[str],
        *,
        execute: bool = False,
    ) -> int:
        """Add items to a collection by patching their collections arrays.

        Returns count of items processed.
        """
        if not item_keys:
            return 0

        if not execute:
            self._logger.info(
                "[DRY RUN] Would add %d items to collection %s",
                len(item_keys),
                collection_key,
            )
            return len(item_keys)

        added = 0
        for i in range(0, len(item_keys), 50):
            batch = item_keys[i : i + 50]
            items_data, _ = self._request(
                "GET",
                "/items",
                params={"itemKey": ",".join(batch), "format": "json"},
            )
            if not items_data:
                continue
            updates = []
            for item in items_data:
                item_data = item.get("data", item)
                collections = item_data.get("collections", [])
                if collection_key not in collections:
                    collections.append(collection_key)
                    updates.append(
                        {
                            "key": item_data["key"],
                            "version": item_data.get("version", 0),
                            "collections": collections,
                        }
                    )
            if updates:
                self._request("POST", "/items", data=updates)
                added += len(updates)
            else:
                added += len(batch)
        return added

    def remove_items_from_collection(
        self,
        collection_key: str,
        item_keys: list[str],
        *,
        execute: bool = False,
    ) -> int:
        """Remove items from a collection. Returns count processed."""
        if not item_keys:
            return 0

        if not execute:
            self._logger.info(
                "[DRY RUN] Would remove %d items from collection %s",
                len(item_keys),
                collection_key,
            )
            return len(item_keys)

        removed = 0
        for i in range(0, len(item_keys), 50):
            batch = item_keys[i : i + 50]
            items_data, _ = self._request(
                "GET",
                "/items",
                params={"itemKey": ",".join(batch), "format": "json"},
            )
            if not items_data:
                continue
            updates = []
            for item in items_data:
                item_data = item.get("data", item)
                collections = item_data.get("collections", [])
                if collection_key in collections:
                    collections.remove(collection_key)
                    updates.append(
                        {
                            "key": item_data["key"],
                            "version": item_data.get("version", 0),
                            "collections": collections,
                        }
                    )
            if updates:
                self._request("POST", "/items", data=updates)
                removed += len(updates)
        return removed

    def ensure_collection_path(
        self,
        path: str,
        tree: CollectionTree,
        *,
        execute: bool = False,
    ) -> Optional[str]:
        """Ensure all collections in a slash-separated path exist.

        Returns the key of the leaf collection, or None in dry-run mode
        if creation would be needed.
        """
        parts = [p.strip() for p in path.strip("/").split("/") if p.strip()]
        if not parts:
            raise ValueError("Empty collection path.")

        current_parent: Optional[str] = None
        for part in parts:
            siblings = tree.children.get(current_parent, [])
            match = None
            for c in siblings:
                if c.name.lower() == part.lower():
                    match = c
                    break
            if match is not None:
                current_parent = match.key
            else:
                coll = self.create_collection(
                    part, current_parent, execute=execute
                )
                if coll is None:
                    if not execute:
                        self._logger.info(
                            "[DRY RUN] Would create: %s (parent=%s)",
                            part,
                            current_parent or "root",
                        )
                        return None
                    raise ZoteroAPIError(
                        0,
                        "Creation failed",
                        f"Could not create collection: {part}",
                    )
                current_parent = coll.key
                tree.children.setdefault(coll.parent_key, []).append(coll)
                tree.collections.append(coll)

        return current_parent


class ZoteroAPIError(Exception):
    """Raised on Zotero API errors."""

    def __init__(self, code: int, reason: str, body: str) -> None:
        self.code = code
        self.reason = reason
        self.body = body
        super().__init__(f"Zotero API error {code} {reason}: {body[:200]}")
