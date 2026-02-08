"""Output formatting for citation keys and key mappings."""

from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from zotcurator.betterbibtex import CitationKeyRecord, KeyMapping

# ── Format detection ──────────────────────────────────────────────────────────

OUTPUT_EXTENSION_MAP: dict[str, str] = {
    ".csv": "csv",
    ".tsv": "tsv",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".txt": "plaintext",
    ".text": "plaintext",
}


def guess_output_format(filepath: str) -> Optional[str]:
    """Guess output format from file extension."""
    suffix = Path(filepath).suffix.lower()
    return OUTPUT_EXTENSION_MAP.get(suffix)


def resolve_output_format(
    outfile: Optional[str],
    explicit_format: Optional[str],
    default: str = "plaintext",
) -> str:
    """Determine output format from explicit flag, outfile extension, or default."""
    if explicit_format:
        return explicit_format.lower()
    if outfile:
        fmt = guess_output_format(outfile)
        if fmt:
            return fmt
    return default


# ── Key mapping formatters ────────────────────────────────────────────────────


def format_key_mappings(
    mappings: Sequence[KeyMapping],
    fmt: str,
    *,
    delimiter: str = ",",
    citation_key_field: str = "citation-key",
) -> str:
    """Format key mappings for output."""
    fmt_lower = fmt.lower()
    if fmt_lower == "plaintext":
        return _mappings_plaintext(mappings)
    elif fmt_lower == "csv":
        return _mappings_delimited(
            mappings, delimiter=delimiter, ck_field=citation_key_field
        )
    elif fmt_lower == "tsv":
        return _mappings_delimited(
            mappings, delimiter="\t", ck_field=citation_key_field
        )
    elif fmt_lower == "json":
        return _mappings_json(mappings, ck_field=citation_key_field)
    elif fmt_lower == "yaml":
        return _mappings_yaml(mappings, ck_field=citation_key_field)
    else:
        raise ValueError(f"Unsupported output format: '{fmt}'")


def _mappings_plaintext(mappings: Sequence[KeyMapping]) -> str:
    lines: list[str] = []
    for m in mappings:
        status = m.item_key if m.found else "NOT_FOUND"
        lines.append(f"{m.citation_key}\t{status}")
    return "\n".join(lines)


def _mappings_delimited(
    mappings: Sequence[KeyMapping],
    *,
    delimiter: str,
    ck_field: str,
) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=delimiter)
    writer.writerow([ck_field, "itemKey", "found"])
    for m in mappings:
        writer.writerow([m.citation_key, m.item_key or "", m.found])
    return buf.getvalue().rstrip("\r\n")


def _mappings_json(
    mappings: Sequence[KeyMapping],
    *,
    ck_field: str,
) -> str:
    data = [
        {
            ck_field: m.citation_key,
            "itemKey": m.item_key,
            "found": m.found,
        }
        for m in mappings
    ]
    return json.dumps(data, indent=2)


def _mappings_yaml(
    mappings: Sequence[KeyMapping],
    *,
    ck_field: str,
) -> str:
    lines: list[str] = []
    for m in mappings:
        lines.append(f"- {ck_field}: {m.citation_key}")
        lines.append(f"  itemKey: {m.item_key or ''}")
        lines.append(f"  found: {str(m.found).lower()}")
    return "\n".join(lines)


# ── Full record formatters (for `keys list`) ─────────────────────────────────


def format_records(
    records: Sequence[CitationKeyRecord],
    fmt: str,
    *,
    delimiter: str = ",",
) -> str:
    """Format full BBT records for output."""
    fmt_lower = fmt.lower()
    if fmt_lower == "json":
        return json.dumps([r.to_dict() for r in records], indent=2)
    elif fmt_lower in ("csv", "tsv"):
        delim = "\t" if fmt_lower == "tsv" else delimiter
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=delim)
        writer.writerow(["citationKey", "itemKey", "itemID", "libraryID", "pinned"])
        for r in records:
            writer.writerow(
                [r.citation_key, r.item_key, r.item_id, r.library_id, r.pinned]
            )
        return buf.getvalue().rstrip("\r\n")
    elif fmt_lower == "yaml":
        lines: list[str] = []
        for r in records:
            lines.append(f"- citationKey: {r.citation_key}")
            lines.append(f"  itemKey: {r.item_key}")
            lines.append(f"  itemID: {r.item_id}")
            lines.append(f"  libraryID: {r.library_id}")
            lines.append(f"  pinned: {str(r.pinned).lower()}")
        return "\n".join(lines)
    elif fmt_lower == "plaintext":
        return "\n".join(f"{r.citation_key}\t{r.item_key}" for r in records)
    else:
        raise ValueError(f"Unsupported output format: '{fmt}'")


# ── Simple key list formatters ────────────────────────────────────────────────


def format_plain_keys(
    keys: Sequence[str],
    fmt: str,
    *,
    delimiter: str = ",",
    citation_key_field: str = "citation-key",
) -> str:
    """Format a simple list of citation key strings."""
    fmt_lower = fmt.lower()
    if fmt_lower == "plaintext":
        return "\n".join(keys)
    elif fmt_lower in ("csv", "tsv"):
        delim = "\t" if fmt_lower == "tsv" else delimiter
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=delim)
        writer.writerow([citation_key_field])
        for k in keys:
            writer.writerow([k])
        return buf.getvalue().rstrip("\r\n")
    elif fmt_lower == "json":
        data = [{citation_key_field: k} for k in keys]
        return json.dumps(data, indent=2)
    elif fmt_lower == "yaml":
        return "\n".join(f"- {citation_key_field}: {k}" for k in keys)
    else:
        raise ValueError(f"Unsupported output format: '{fmt}'")


# ── Output writing ────────────────────────────────────────────────────────────


def write_output(text: str, outfile: Optional[str] = None) -> None:
    """Write formatted output to file or stdout."""
    if outfile:
        Path(outfile).write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")
