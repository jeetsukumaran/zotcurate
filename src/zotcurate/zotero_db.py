"""Zotero SQLite database interface.

Maps citation keys (user-facing) to Zotero item keys (API-facing)
by querying the native 'citationKey' field in zotero.sqlite.

Zotero 8 introduced a first-class Citation Key field stored in the
standard items/itemData/fields/itemDataValues schema.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from zotcurate.log import get_logger


@dataclass(frozen=True, slots=True)
class CitationKeyRecord:
    """A single citation key record from the Zotero database."""

    item_id: int
    item_key: str
    library_id: int
    citation_key: str

    def to_dict(self) -> dict[str, object]:
        return {
            "itemID": self.item_id,
            "itemKey": self.item_key,
            "libraryID": self.library_id,
            "citationKey": self.citation_key,
        }


@dataclass(frozen=True, slots=True)
class KeyMapping:
    """Mapping result for a single citation key lookup."""

    citation_key: str
    item_key: Optional[str]
    item_id: Optional[int]
    library_id: Optional[int]
    found: bool


_SQL_READ_CITATION_KEYS = """
SELECT
    i.itemID    AS itemID,
    i.key       AS itemKey,
    i.libraryID AS libraryID,
    idv.value   AS citationKey
FROM items i
JOIN itemData       id  ON i.itemID   = id.itemID
JOIN fields         f   ON id.fieldID = f.fieldID
JOIN itemDataValues idv ON id.valueID = idv.valueID
WHERE f.fieldName = 'citationKey'
  AND i.itemID NOT IN (SELECT itemID FROM deletedItems)
"""


def read_all_records(db_path: Path) -> list[CitationKeyRecord]:
    """Read all citation key records from zotero.sqlite."""
    logger = get_logger()
    resolved = db_path.expanduser().resolve()
    logger.debug("Opening Zotero database: %s", resolved)
    if not resolved.exists():
        raise FileNotFoundError(f"Zotero database not found: {resolved}")

    uri = f"file:{resolved}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        cursor = conn.execute(_SQL_READ_CITATION_KEYS)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
    finally:
        conn.close()

    logger.debug("Read %d citation key records from Zotero database", len(rows))
    records: list[CitationKeyRecord] = []
    for row in rows:
        raw = dict(zip(columns, row))
        records.append(
            CitationKeyRecord(
                item_id=raw["itemID"],
                item_key=raw["itemKey"],
                library_id=raw["libraryID"],
                citation_key=raw["citationKey"],
            )
        )
    return records


def build_citation_to_item_map(
    records: list[CitationKeyRecord],
    library_id: Optional[int] = None,
) -> dict[str, CitationKeyRecord]:
    """Build a mapping from citation key -> record, optionally filtered by library."""
    mapping: dict[str, CitationKeyRecord] = {}
    for rec in records:
        if library_id is not None and rec.library_id != library_id:
            continue
        mapping[rec.citation_key] = rec
    return mapping


def resolve_citation_keys(
    db_path: Path,
    citation_keys: list[str],
    library_id: Optional[int] = None,
) -> list[KeyMapping]:
    """Resolve a list of citation keys to Zotero item keys.

    Returns a KeyMapping for each input key, with found=False for unresolved keys.
    """
    logger = get_logger()
    records = read_all_records(db_path)
    ck_map = build_citation_to_item_map(records, library_id=library_id)

    results: list[KeyMapping] = []
    for ck in citation_keys:
        rec = ck_map.get(ck)
        if rec is not None:
            results.append(
                KeyMapping(
                    citation_key=ck,
                    item_key=rec.item_key,
                    item_id=rec.item_id,
                    library_id=rec.library_id,
                    found=True,
                )
            )
            logger.debug("Resolved: %s -> %s", ck, rec.item_key)
        else:
            results.append(
                KeyMapping(
                    citation_key=ck,
                    item_key=None,
                    item_id=None,
                    library_id=None,
                    found=False,
                )
            )
            logger.warning("Unresolved citation key: %s", ck)
    return results
