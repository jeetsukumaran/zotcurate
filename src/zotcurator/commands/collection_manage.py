"""``zotc collection create/add/replace/diff`` — Manage Zotero collections."""

from __future__ import annotations

import argparse
import sys

from zotcurator.betterbibtex import resolve_citation_keys
from zotcurator.config import Config
from zotcurator.extractors import collect_keys_from_files
from zotcurator.log import get_logger
from zotcurator.zotero_api import CollectionTree, ZoteroClient


# ── Subcommand registration ──────────────────────────────────────────────────


def register_create(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "create", help="Create a new Zotero collection from citation keys"
    )
    _add_common_args(parser)
    parser.add_argument(
        "--on-conflict",
        choices=["abort", "add", "replace", "disambiguate", "skip"],
        default="abort",
        help="Action if collection already exists (default: abort)",
    )
    parser.set_defaults(func=run_create)


def register_add(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "add", help="Add items to an existing Zotero collection"
    )
    _add_common_args(parser)
    parser.set_defaults(func=run_add)


def register_replace(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "replace",
        help="Replace a Zotero collection's items with those from input",
    )
    _add_common_args(parser)
    parser.set_defaults(func=run_replace)


def register_diff(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "diff",
        help="Show symmetric difference between input and existing collection",
    )
    _add_common_args(parser)
    parser.set_defaults(func=run_diff)


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "collection_path",
        help="Collection path (use '/' for nesting, e.g. 'topic/subtopic')",
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="Input files containing citation keys (use '-' for stdin)",
    )
    parser.add_argument(
        "-f",
        "--from-format",
        choices=["bibtex", "csv", "tsv", "yaml", "json", "plaintext", "markdown"],
        default=None,
        help="Input format (guessed from extension if not given)",
    )
    parser.add_argument(
        "--delimiter",
        default=",",
        help="Delimiter for CSV input (default: ',')",
    )
    parser.add_argument(
        "--read-citation-key-field",
        default="citation-key",
        help="Field name for citation key in structured input (default: 'citation-key')",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually execute the operation (default: dry run)",
    )


# ── Shared helpers ────────────────────────────────────────────────────────────


def _resolve_input_keys(
    args: argparse.Namespace,
    config: Config,
) -> tuple[list[str], list[str]]:
    """Extract citation keys and resolve to Zotero item keys.

    Returns ``(resolved_item_keys, unresolved_citation_keys)``.
    """
    logger = get_logger()

    keys = collect_keys_from_files(
        args.files,
        fmt=args.from_format,
        delimiter=args.delimiter,
        citation_key_field=args.read_citation_key_field,
    )
    if not keys:
        logger.warning("No citation keys found in input.")
        return [], []

    db_path = config.require_betterbibtex_db()
    mappings = resolve_citation_keys(db_path, keys)

    item_keys = [m.item_key for m in mappings if m.found and m.item_key]
    unresolved = [m.citation_key for m in mappings if not m.found]

    if unresolved:
        preview = ", ".join(unresolved[:10])
        suffix = "..." if len(unresolved) > 10 else ""
        logger.warning(
            "%d citation keys could not be resolved: %s%s",
            len(unresolved),
            preview,
            suffix,
        )

    logger.info(
        "Resolved %d/%d citation keys to item keys",
        len(item_keys),
        len(keys),
    )
    return item_keys, unresolved


def _report(execute: bool, message: str) -> None:
    prefix = "" if execute else "[DRY RUN] "
    sys.stderr.write(f"{prefix}{message}\n")


def _disambiguate(path: str, tree: CollectionTree) -> str:
    for i in range(2, 100):
        candidate = f"{path} ({i})"
        if tree.find_by_path(candidate) is None:
            return candidate
    raise ValueError(f"Could not disambiguate collection path: {path}")


# ── Command runners ───────────────────────────────────────────────────────────


def run_create(args: argparse.Namespace, config: Config) -> int:
    logger = get_logger()
    library_id = config.require_library_id()
    api_key = config.require_api_key()
    execute = args.execute

    item_keys, unresolved = _resolve_input_keys(args, config)
    if not item_keys:
        logger.error("No resolvable items found. Aborting.")
        return 1

    client = ZoteroClient(library_id, api_key, config.library_type)
    collections = client.get_collections()
    tree = CollectionTree.build(collections)

    existing = tree.find_by_path(args.collection_path)
    if existing is not None:
        conflict = args.on_conflict
        if conflict == "abort":
            logger.error(
                "Collection '%s' already exists (key=%s). "
                "Use --on-conflict to specify behavior.",
                args.collection_path,
                existing.key,
            )
            return 1
        elif conflict == "add":
            logger.info("Collection exists; adding items to it.")
            count = client.add_items_to_collection(
                existing.key, item_keys, execute=execute
            )
            _report(execute, f"Added {count} items to '{args.collection_path}'")
            return 0
        elif conflict == "replace":
            logger.info("Collection exists; replacing items.")
            current_keys = client.get_collection_item_keys(existing.key)
            to_remove = [k for k in current_keys if k not in set(item_keys)]
            to_add = [k for k in item_keys if k not in set(current_keys)]
            client.remove_items_from_collection(
                existing.key, to_remove, execute=execute
            )
            client.add_items_to_collection(
                existing.key, to_add, execute=execute
            )
            _report(
                execute,
                f"Replaced '{args.collection_path}': "
                f"+{len(to_add)} added, -{len(to_remove)} removed",
            )
            return 0
        elif conflict == "skip":
            logger.info("Collection exists; skipping.")
            return 0
        elif conflict == "disambiguate":
            args.collection_path = _disambiguate(args.collection_path, tree)
            logger.info("Disambiguated to: %s", args.collection_path)

    coll_key = client.ensure_collection_path(
        args.collection_path, tree, execute=execute
    )

    if coll_key:
        count = client.add_items_to_collection(
            coll_key, item_keys, execute=execute
        )
        _report(execute, f"Created '{args.collection_path}' with {count} items")
    else:
        _report(
            execute,
            f"Would create '{args.collection_path}' with {len(item_keys)} items",
        )

    if unresolved:
        sys.stderr.write(
            f"Warning: {len(unresolved)} citation keys were not resolved.\n"
        )
    return 0


def run_add(args: argparse.Namespace, config: Config) -> int:
    logger = get_logger()
    library_id = config.require_library_id()
    api_key = config.require_api_key()
    execute = args.execute

    item_keys, _unresolved = _resolve_input_keys(args, config)
    if not item_keys:
        logger.error("No resolvable items found. Aborting.")
        return 1

    client = ZoteroClient(library_id, api_key, config.library_type)
    collections = client.get_collections()
    tree = CollectionTree.build(collections)

    existing = tree.find_by_path(args.collection_path)
    if existing is None:
        logger.error("Collection '%s' not found.", args.collection_path)
        return 1

    count = client.add_items_to_collection(
        existing.key, item_keys, execute=execute
    )
    _report(execute, f"Added {count} items to '{args.collection_path}'")
    return 0


def run_replace(args: argparse.Namespace, config: Config) -> int:
    logger = get_logger()
    library_id = config.require_library_id()
    api_key = config.require_api_key()
    execute = args.execute

    item_keys, _unresolved = _resolve_input_keys(args, config)
    if not item_keys:
        logger.error("No resolvable items found. Aborting.")
        return 1

    client = ZoteroClient(library_id, api_key, config.library_type)
    collections = client.get_collections()
    tree = CollectionTree.build(collections)

    existing = tree.find_by_path(args.collection_path)
    if existing is None:
        logger.error("Collection '%s' not found.", args.collection_path)
        return 1

    input_set = set(item_keys)
    current_keys = client.get_collection_item_keys(existing.key)
    current_set = set(current_keys)

    to_remove = [k for k in current_keys if k not in input_set]
    to_add = [k for k in item_keys if k not in current_set]

    logger.info(
        "Replace: +%d to add, -%d to remove, %d unchanged",
        len(to_add),
        len(to_remove),
        len(input_set & current_set),
    )

    client.remove_items_from_collection(
        existing.key, to_remove, execute=execute
    )
    client.add_items_to_collection(existing.key, to_add, execute=execute)

    _report(
        execute,
        f"Replaced '{args.collection_path}': "
        f"+{len(to_add)} added, -{len(to_remove)} removed",
    )
    return 0


def run_diff(args: argparse.Namespace, config: Config) -> int:
    logger = get_logger()
    library_id = config.require_library_id()
    api_key = config.require_api_key()

    item_keys, unresolved = _resolve_input_keys(args, config)

    client = ZoteroClient(library_id, api_key, config.library_type)
    collections = client.get_collections()
    tree = CollectionTree.build(collections)

    existing = tree.find_by_path(args.collection_path)
    if existing is None:
        logger.error("Collection '%s' not found.", args.collection_path)
        return 1

    input_set = set(item_keys)
    current_keys = client.get_collection_item_keys(existing.key)
    current_set = set(current_keys)

    only_in_input = sorted(input_set - current_set)
    only_in_collection = sorted(current_set - input_set)
    in_both = sorted(input_set & current_set)

    out = sys.stdout.write
    out(f"=== Diff: input vs '{args.collection_path}' ===\n\n")
    out(f"In both ({len(in_both)}):\n")
    for k in in_both:
        out(f"  {k}\n")
    out(f"\nOnly in input ({len(only_in_input)}):\n")
    for k in only_in_input:
        out(f"  + {k}\n")
    out(f"\nOnly in collection ({len(only_in_collection)}):\n")
    for k in only_in_collection:
        out(f"  - {k}\n")
    if unresolved:
        out(f"\nUnresolved citation keys ({len(unresolved)}):\n")
        for k in unresolved:
            out(f"  ? {k}\n")

    return 0
