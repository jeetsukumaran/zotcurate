"""``zotc config`` — Show resolved configuration and auto-detected values."""

from __future__ import annotations

import argparse

from zotcurate.config import Config
from zotcurate.detect import detect_defaults


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``config`` subcommand."""
    parser = subparsers.add_parser(
        "config",
        help="Show resolved configuration and auto-detected Zotero values",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace, config: Config) -> int:
    """Print the resolved configuration, indicating the source of each value."""

    detected = detect_defaults()

    def _source(value: str | None, detected_value: str | None) -> str:
        """Label where a value came from."""
        if value is None:
            return "(not set)"
        if detected_value and str(value) == str(detected_value):
            return f"{value}  [auto-detected]"
        return str(value)

    lines = [
        ("Library ID",         _source(config.library_id,  detected["library_id"])),
        ("API key",            ("(set)" if config.api_key else "(not set)")),
        ("Library type",       config.library_type),
        ("BetterBibTeX DB",    _source(
                                    str(config.betterbibtex_db) if config.betterbibtex_db else None,
                                    detected["betterbibtex"],
                                )),
        ("Zotero data dir",    detected["data_dir"] or "(not found)"),
    ]

    width = max(len(k) for k, _ in lines)
    for key, val in lines:
        print(f"  {key:<{width}}  {val}")

    return 0
