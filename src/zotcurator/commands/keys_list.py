"""``zotc keys list`` — Dump all BetterBibTeX citation key records."""

from __future__ import annotations

import argparse

from zotcurator.betterbibtex import read_all_records
from zotcurator.config import Config
from zotcurator.formatters import format_records, resolve_output_format, write_output
from zotcurator.log import get_logger


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``keys list`` subcommand."""
    parser = subparsers.add_parser(
        "list", help="List all BetterBibTeX citation key records"
    )
    parser.add_argument(
        "-t",
        "--to-format",
        choices=["plaintext", "csv", "tsv", "json", "yaml"],
        default=None,
        help="Output format (default: plaintext)",
    )
    parser.add_argument(
        "-o", "--output", default=None, help="Output file (default: stdout)"
    )
    parser.add_argument(
        "--delimiter", default=",", help="Delimiter for CSV output (default: ',')"
    )
    parser.add_argument(
        "--sort",
        choices=["citation-key", "item-key", "item-id"],
        default="citation-key",
        help="Sort order (default: citation-key)",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace, config: Config) -> int:
    """Execute the keys list command."""
    logger = get_logger()
    db_path = config.require_betterbibtex_db()
    records = read_all_records(db_path)

    if not records:
        logger.info("No records found in BetterBibTeX database.")
        return 0

    sort_key_map = {
        "citation-key": lambda r: r.citation_key.lower(),
        "item-key": lambda r: r.item_key,
        "item-id": lambda r: r.item_id,
    }
    records.sort(key=sort_key_map[args.sort])

    fmt = resolve_output_format(args.output, args.to_format, default="plaintext")
    output = format_records(records, fmt, delimiter=args.delimiter)
    write_output(output, args.output)

    logger.info("Listed %d records", len(records))
    return 0
