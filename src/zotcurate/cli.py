"""``zotc`` — Zotero collection curation CLI entry point."""

from __future__ import annotations

import argparse
import sys

from zotcurate.config import ConfigError, resolve_config
from zotcurate.log import setup_logging


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser with all subcommands."""

    parser = argparse.ArgumentParser(
        prog="zotc",
        description="Zotero collection curation utility",
    )

    # ── Global options ────────────────────────────────────────────────────
    parser.add_argument(
        "-i",
        "--library-id",
        default=None,
        help="Zotero library ID (or $ZOTERO_LIBRARY_ID / .zotc/library)",
    )
    parser.add_argument(
        "-k",
        "--api-key",
        default=None,
        help="Zotero API key (or $ZOTERO_API_KEY / .zotc/api-key)",
    )
    parser.add_argument(
        "--library-type",
        default=None,
        choices=["user", "group"],
        help="Library type (default: user)",
    )
    parser.add_argument(
        "-b",
        "--bb",
        "--better-bibtex",
        dest="betterbibtex",
        default=None,
        help="Path to BetterBibTeX SQLite database",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        default=False,
        help="Silent mode (no messages)",
    )
    parser.add_argument(
        "-v",
        action="count",
        default=0,
        dest="verbose",
        help="Increase verbosity (-v warnings, -vv info [default], -vvv debug)",
    )

    # ── Subcommands ───────────────────────────────────────────────────────
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # zotc collections ...
    # collections_parser = subparsers.add_parser(
    #     "collections", help="Manage Zotero collections"
    # )
    # collections_sub = collections_parser.add_subparsers(
    #     dest="collections_command", help="Collection subcommands"
    # )
    # from zotcurate.commands.collections_list import (
    #     register as register_collections_list,
    # )
    #
    # register_collections_list(collections_sub)



    # zotc config
    from zotcurate.commands.config import register as register_config
    register_config(subparsers)

    # zotc collection ...
    collection_parser = subparsers.add_parser(
        "collection", help="List, create, modify, or diff collections"
    )
    collection_sub = collection_parser.add_subparsers(
        dest="collection_command", help="Collection management subcommands"
    )
    from zotcurate.commands.collections_list import (
        register as register_collections_list,
    )
    from zotcurate.commands.collection_manage import (
        register_add,
        register_create,
        register_diff,
        register_replace,
    )

    register_collections_list(collection_sub)
    register_create(collection_sub)
    register_add(collection_sub)
    register_replace(collection_sub)
    register_diff(collection_sub)

    # zotc keys ...
    keys_parser = subparsers.add_parser("keys", help="Citation key operations")
    keys_sub = keys_parser.add_subparsers(
        dest="keys_command", help="Key subcommands"
    )
    from zotcurate.commands.keys_extract import register as register_keys_extract
    from zotcurate.commands.keys_list import register as register_keys_list

    register_keys_extract(keys_sub)
    register_keys_list(keys_sub)


    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # -q => 0 (silent), -v => 1 (warnings), default => 2 (info), -vvv => 3 (debug)
    if args.quiet:
        verbosity = 0
    elif args.verbose > 0:
        verbosity = args.verbose
    else:
        verbosity = 2

    logger = setup_logging(verbosity)

    config = resolve_config(
        cli_library_id=args.library_id,
        cli_api_key=args.api_key,
        cli_library_type=args.library_type,
        cli_betterbibtex=args.betterbibtex,
    )

    if args.command is None:
        parser.print_help()
        return 0

    if not hasattr(args, "func"):
        parser.parse_args([args.command, "--help"])
        return 0

    try:
        return args.func(args, config)
    except ConfigError as e:
        logger.error("%s", e)
        return 1
    except FileNotFoundError as e:
        logger.error("%s", e)
        return 1
    except ValueError as e:
        logger.error("%s", e)
        return 1
    except KeyboardInterrupt:
        logger.info("Interrupted.")
        return 130
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=verbosity >= 3)
        return 1


if __name__ == "__main__":
    sys.exit(main())
