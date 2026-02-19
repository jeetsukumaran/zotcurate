"""``zotc collections list`` — List all Zotero collections."""

from __future__ import annotations

import argparse
import json as json_mod
import re
import sys
from typing import Optional

from zotcurate.config import Config
from zotcurate.log import get_logger
from zotcurate.zotero_api import CollectionTree, ZoteroClient, ZoteroCollection


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``collections list`` subcommand."""
    parser = subparsers.add_parser("list", help="List all Zotero collections")
    parser.add_argument(
        "pattern",
        nargs="?",
        default=None,
        help="Filter collections by regex pattern",
    )
    parser.add_argument(
        "--sort",
        choices=["name", "items"],
        default="name",
        help="Sort collections by name or item count (default: name)",
    )
    parser.add_argument(
        "-t",
        "--to-format",
        choices=["tree", "json", "csv", "plaintext"],
        default="tree",
        help="Output format (default: tree)",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace, config: Config) -> int:
    """Execute the collections list command."""
    logger = get_logger()
    library_id = config.require_library_id()
    api_key = config.require_api_key()

    client = ZoteroClient(library_id, api_key, config.library_type)
    collections = client.get_collections()

    if not collections:
        logger.info("No collections found.")
        return 0

    tree = CollectionTree.build(collections)
    fmt = args.to_format

    if fmt == "json":
        filtered = _filter_collections(collections, args.pattern)
        data = [
            {
                "key": c.key,
                "name": c.name,
                "parentKey": c.parent_key,
                "numItems": c.num_items,
            }
            for c in filtered
        ]
        output = json_mod.dumps(data, indent=2)
    elif fmt == "csv":
        filtered = _filter_collections(collections, args.pattern)
        lines = ["key,name,parentKey,numItems"]
        for c in filtered:
            lines.append(
                f"{c.key},{c.name},{c.parent_key or ''},{c.num_items}"
            )
        output = "\n".join(lines)
    else:
        output = tree.format_tree(filter_pattern=args.pattern)

    sys.stdout.write(output + "\n")
    return 0


def _filter_collections(
    collections: list[ZoteroCollection],
    pattern: Optional[str],
) -> list[ZoteroCollection]:
    """Filter collections by regex pattern."""
    if not pattern:
        return collections
    compiled = re.compile(pattern, re.IGNORECASE)
    return [c for c in collections if compiled.search(c.name)]
