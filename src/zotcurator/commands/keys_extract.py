"""``zotc keys extract`` — Extract citation keys and resolve to Zotero item keys."""

from __future__ import annotations

import argparse

from zotcurator.betterbibtex import resolve_citation_keys
from zotcurator.config import Config
from zotcurator.extractors import collect_keys_from_files
from zotcurator.formatters import (
    format_key_mappings,
    format_plain_keys,
    resolve_output_format,
    write_output,
)
from zotcurator.log import get_logger


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``keys extract`` subcommand."""
    parser = subparsers.add_parser(
        "extract",
        help="Extract citation keys from files and resolve to Zotero item keys",
    )
    parser.add_argument(
        "files", nargs="+", help="Input files (use '-' for stdin)"
    )
    parser.add_argument(
        "-f",
        "--from-format",
        choices=["bibtex", "csv", "tsv", "yaml", "json", "plaintext", "markdown"],
        default=None,
        help="Input format (guessed from extension if not given)",
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
        "--delimiter",
        default=",",
        help="Delimiter for CSV input/output (default: ',')",
    )
    parser.add_argument(
        "--read-citation-key-field",
        default="citation-key",
        help="Field name for citation key in structured input (default: 'citation-key')",
    )
    parser.add_argument(
        "--write-citation-key-field",
        default="citation-key",
        help="Field name for citation key in output (default: 'citation-key')",
    )
    parser.add_argument(
        "--keys-only",
        action="store_true",
        help="Output only citation keys without resolving to Zotero item keys",
    )
    parser.add_argument(
        "--sort",
        choices=["alpha", "none"],
        default="alpha",
        help="Sort order for keys (default: alpha)",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace, config: Config) -> int:
    """Execute the keys extract command."""
    logger = get_logger()

    keys = collect_keys_from_files(
        args.files,
        fmt=args.from_format,
        delimiter=args.delimiter,
        citation_key_field=args.read_citation_key_field,
    )
    if not keys:
        logger.warning("No citation keys found in input.")
        return 1

    if args.sort == "alpha":
        keys.sort(key=str.lower)

    fmt = resolve_output_format(args.output, args.to_format, default="plaintext")

    # Keys-only mode: skip BetterBibTeX resolution
    if args.keys_only:
        output = format_plain_keys(
            keys,
            fmt,
            delimiter=args.delimiter,
            citation_key_field=args.write_citation_key_field,
        )
        write_output(output, args.output)
        logger.info("Extracted %d citation keys (keys-only mode)", len(keys))
        return 0

    # Resolve via BetterBibTeX
    db_path = config.require_betterbibtex_db()
    mappings = resolve_citation_keys(db_path, keys)

    resolved = sum(1 for m in mappings if m.found)
    unresolved = len(mappings) - resolved
    logger.info(
        "Resolved %d/%d keys (%d unresolved)", resolved, len(mappings), unresolved
    )

    output = format_key_mappings(
        mappings,
        fmt,
        delimiter=args.delimiter,
        citation_key_field=args.write_citation_key_field,
    )
    write_output(output, args.output)

    return 0 if unresolved == 0 else 2
