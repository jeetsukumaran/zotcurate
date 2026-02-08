# Zotcurator (`zotc`)

Zotero collection curation utility.

## Install

```bash
pip install -e .
# or: pipx install .
```

## Quick Reference

```bash
zotc -b ~/Zotero/better-bibtex.sqlite keys list -t json
zotc -b bbt.sqlite keys extract paper.qmd -t json
zotc keys extract --keys-only paper.qmd
zotc -b bbt.sqlite collection create "Reading/2024" paper.qmd --execute
zotc -b bbt.sqlite collection diff "Reading/2024" paper.qmd
```

All mutating operations default to **dry run** — pass `--execute` to apply.

## Configuration

Resolved: CLI flags > env vars (`ZOTERO_LIBRARY_ID`, `ZOTERO_API_KEY`) > `.zotc/` config files > defaults.

## Verbosity

`-q` silent · `-v` warnings · *(default)* info · `-vvv` debug
