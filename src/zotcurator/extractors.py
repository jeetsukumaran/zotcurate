"""Citation key extraction from various file formats.

Supports: BibTeX, CSV/TSV, YAML, JSON, plaintext, Quarto/Pandoc Markdown.
"""

from __future__ import annotations

import csv
import io
import json
import re
import sys
from pathlib import Path
from typing import Optional

from zotcurator.log import get_logger

# ── Format detection ──────────────────────────────────────────────────────────

EXTENSION_FORMAT_MAP: dict[str, str] = {
    ".bib": "bibtex",
    ".bibtex": "bibtex",
    ".csv": "csv",
    ".tsv": "tsv",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".txt": "plaintext",
    ".text": "plaintext",
    ".md": "markdown",
    ".qmd": "markdown",
    ".rmd": "markdown",
}


def guess_format(filepath: str) -> Optional[str]:
    """Guess input format from file extension. Returns None if unknown."""
    suffix = Path(filepath).suffix.lower()
    return EXTENSION_FORMAT_MAP.get(suffix)


def detect_or_require_format(
    filepath: Optional[str],
    explicit_format: Optional[str],
) -> str:
    """Determine the format, raising if it cannot be inferred."""
    if explicit_format:
        return explicit_format.lower()
    if filepath and filepath != "-":
        fmt = guess_format(filepath)
        if fmt:
            return fmt
    raise ValueError(
        "Cannot determine input format. Use -f/--from-format to specify. "
        "Supported: bibtex, csv, tsv, yaml, json, plaintext, markdown"
    )


# ── Extractors ────────────────────────────────────────────────────────────────


def extract_bibtex(text: str) -> list[str]:
    """Extract citation keys from BibTeX entries.

    Matches patterns like: @article{key2023name,
    """
    logger = get_logger()
    pattern = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,", re.MULTILINE)
    keys = pattern.findall(text)
    if not keys:
        logger.warning(
            "No BibTeX entries found. Ensure entries follow the format: "
            "@type{citationKey, ...}"
        )
    return keys


def extract_delimited(
    text: str,
    *,
    delimiter: str = ",",
    citation_key_field: str = "citation-key",
) -> list[str]:
    """Extract citation keys from CSV/TSV/delimited data."""
    logger = get_logger()
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if reader.fieldnames is None:
        raise ValueError("Delimited data has no header row.")

    # Case-insensitive field matching
    field_map = {f.lower().strip(): f for f in reader.fieldnames}
    target = citation_key_field.lower().strip()
    actual_field = field_map.get(target)
    if actual_field is None:
        available = ", ".join(reader.fieldnames)
        raise ValueError(
            f"Field '{citation_key_field}' not found in delimited data. "
            f"Available fields: {available}. "
            f"Use --read-citation-key-field to specify."
        )

    keys: list[str] = []
    for i, row in enumerate(reader, start=2):
        val = row.get(actual_field, "").strip()
        if val:
            keys.append(val)
        else:
            logger.warning("Empty citation key at row %d", i)
    return keys


def extract_yaml(
    text: str,
    *,
    citation_key_field: str = "citation-key",
) -> list[str]:
    """Extract citation keys from YAML (list of objects).

    Uses a minimal parser — no PyYAML dependency. Falls back to JSON
    parsing first since valid JSON is a YAML subset.
    """
    try:
        data = json.loads(text)
        return _extract_from_records(data, citation_key_field)
    except json.JSONDecodeError:
        pass
    records = _parse_simple_yaml(text)
    return _extract_from_records(records, citation_key_field)


def _parse_simple_yaml(text: str) -> list[dict[str, str]]:
    """Parse a simple YAML list of flat mappings."""
    records: list[dict[str, str]] = []
    current: Optional[dict[str, str]] = None

    for line in text.splitlines():
        stripped = line.rstrip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            if current is not None:
                records.append(current)
            current = {}
            rest = stripped[2:].strip()
            if ":" in rest:
                k, v = rest.split(":", 1)
                current[_unquote(k.strip())] = _unquote(v.strip())
        elif stripped.startswith("  ") and current is not None and ":" in stripped:
            k, v = stripped.strip().split(":", 1)
            current[_unquote(k.strip())] = _unquote(v.strip())

    if current is not None:
        records.append(current)
    return records


def _unquote(s: str) -> str:
    """Remove surrounding quotes from a string."""
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    return s


def _extract_from_records(
    data: object,
    citation_key_field: str,
) -> list[str]:
    """Extract citation keys from a list of dict-like records."""
    if not isinstance(data, list):
        raise ValueError("Expected a list of records (objects/mappings).")

    target = citation_key_field.lower().strip()
    keys: list[str] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Record at index {i} is not a mapping/object.")
        field_map = {k.lower().strip(): k for k in item}
        actual = field_map.get(target)
        if actual is None:
            available = ", ".join(item.keys())
            raise ValueError(
                f"Field '{citation_key_field}' not found in record {i}. "
                f"Available: {available}. Use --read-citation-key-field to specify."
            )
        val = str(item[actual]).strip()
        if val:
            keys.append(val)
    return keys


def extract_json(
    text: str,
    *,
    citation_key_field: str = "citation-key",
) -> list[str]:
    """Extract citation keys from JSON (list of objects)."""
    data = json.loads(text)
    return _extract_from_records(data, citation_key_field)


def extract_plaintext(text: str) -> list[str]:
    """Extract citation keys from plaintext — one key per line."""
    keys: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            if stripped.startswith("@"):
                stripped = stripped[1:]
            keys.append(stripped)
    return keys


def extract_markdown(text: str) -> list[str]:
    """Extract citation keys from Quarto/Pandoc/Obsidian Markdown.

    Handles:
      - Pandoc-style: @citationKey, [@key1; @key2], [-@key]
      - Obsidian wiki links: [[path/to/@citationKey]] or [[path/to/@citationKey.md]]
      - Markdown links: [text](path/to/@citationKey.md)
    """
    keys: set[str] = set()

    # 1) Obsidian wiki-link: [[.../@citationKey]] or [[.../@citationKey.md]]
    wiki_pattern = re.compile(
        r"\[\[" r"[^\]]*?" r"@([A-Za-z0-9_:.\-]+?)" r"(?:\.md)?" r"\]\]"
    )
    for m in wiki_pattern.finditer(text):
        keys.add(m.group(1))

    # 2) Markdown link: [text](path/to/@citationKey.md)
    md_link_pattern = re.compile(
        r"\[[^\]]*\]" r"\(" r"[^)]*?" r"@([A-Za-z0-9_:.\-]+?)" r"(?:\.md)?" r"\)"
    )
    for m in md_link_pattern.finditer(text):
        keys.add(m.group(1))

    # 3) Pandoc inline citation: @citationKey
    pandoc_pattern = re.compile(
        r"(?<![A-Za-z0-9_/])" r"@([A-Za-z][A-Za-z0-9_:.\-]*[A-Za-z0-9])"
    )
    for m in pandoc_pattern.finditer(text):
        keys.add(m.group(1))

    return list(keys)


# ── Dispatcher ────────────────────────────────────────────────────────────────


def extract_citation_keys(
    text: str,
    fmt: str,
    *,
    delimiter: str = ",",
    citation_key_field: str = "citation-key",
) -> list[str]:
    """Extract citation keys from text in the given format.

    Returns raw (not yet deduplicated or sorted) keys.
    """
    fmt_lower = fmt.lower()
    if fmt_lower == "bibtex":
        return extract_bibtex(text)
    elif fmt_lower == "csv":
        return extract_delimited(
            text, delimiter=delimiter, citation_key_field=citation_key_field
        )
    elif fmt_lower == "tsv":
        return extract_delimited(
            text, delimiter="\t", citation_key_field=citation_key_field
        )
    elif fmt_lower == "yaml":
        return extract_yaml(text, citation_key_field=citation_key_field)
    elif fmt_lower == "json":
        return extract_json(text, citation_key_field=citation_key_field)
    elif fmt_lower == "plaintext":
        return extract_plaintext(text)
    elif fmt_lower == "markdown":
        return extract_markdown(text)
    else:
        raise ValueError(
            f"Unsupported format: '{fmt}'. "
            "Supported: bibtex, csv, tsv, yaml, json, plaintext, markdown"
        )


def normalize_key(key: str) -> str:
    """Normalize a citation key: strip whitespace and optional leading @."""
    key = key.strip()
    if key.startswith("@"):
        key = key[1:]
    return key


def collect_keys_from_files(
    files: list[str],
    *,
    fmt: Optional[str] = None,
    delimiter: str = ",",
    citation_key_field: str = "citation-key",
) -> list[str]:
    """Read and extract citation keys from one or more files.

    Deduplicates and normalizes. Preserves first-seen order.
    """
    logger = get_logger()
    all_keys: list[str] = []
    seen: set[str] = set()

    for filepath in files:
        resolved_fmt = detect_or_require_format(
            filepath if filepath != "-" else None, fmt
        )
        logger.info("Reading %s (format: %s)", filepath, resolved_fmt)

        if filepath == "-":
            text = sys.stdin.read()
        else:
            p = Path(filepath)
            if not p.exists():
                raise FileNotFoundError(f"Input file not found: {filepath}")
            text = p.read_text(encoding="utf-8")

        raw_keys = extract_citation_keys(
            text,
            resolved_fmt,
            delimiter=delimiter,
            citation_key_field=citation_key_field,
        )
        for k in raw_keys:
            nk = normalize_key(k)
            if nk and nk not in seen:
                all_keys.append(nk)
                seen.add(nk)

    logger.info("Collected %d unique citation keys", len(all_keys))
    return all_keys
