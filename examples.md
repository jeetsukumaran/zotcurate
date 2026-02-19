```
# ── First: check what zotc can detect automatically ───────────────────────────
# zotc auto-detects your Zotero data directory, BBT database, and library ID
# from your local Zotero installation. Only the API key must always be supplied.
# Run this first to see what was found:

zotc config


# ── Store your API key so you never have to pass it ───────────────────────────
# Get your API key from: https://www.zotero.org/settings/keys
# (Create a key with library read/write access)

mkdir -p ~/.zotc
echo "your_api_key" > ~/.zotc/api-key

# That's it. With credentials stored and auto-detection working, most commands
# need no flags at all:

zotc collection list
zotc keys extract --keys-only paper.qmd
zotc collection create "Reading/2024" paper.qmd --execute


# ── If auto-detection doesn't find everything, supply what's missing ───────────

# Explicit BBT path (if not auto-detected)
zotc -b ~/Zotero/better-bibtex.sqlite keys list

# Explicit library ID and API key (if not stored in ~/.zotc/)
zotc -i 1234567 -k your_api_key collection list

# All credentials explicit — long flags
zotc \
  --library-id    1234567 \
  --api-key       your_api_key \
  --better-bibtex ~/Library/Application\ Support/Zotero/better-bibtex.sqlite \
  collection create "Reading/2024" paper.qmd --execute

# For group libraries, add --library-type group and use the group ID
zotc -i 9876543 -k your_api_key --library-type group \
  collection create "SharedProject/References" paper.qmd --execute


# ── Inspect your BetterBibTeX citation key database ───────────────────────────

# List all citation key → Zotero item key mappings (plaintext: one pair per line)
zotc keys list

# As JSON (includes itemID, libraryID, pinned status)
zotc keys list -t json

# Export to CSV, sorted by item ID
zotc keys list -t csv --sort item-id -o all-keys.csv


# ── Extract citation keys from documents ──────────────────────────────────────
# Resolves each key against the BBT database to get the Zotero item key.
# Handles @key (Pandoc), [@key], [[path/@key]] (Obsidian), [text](@key.md) syntax.

# From a Quarto/R Markdown document
zotc keys extract paper.qmd

# From a BibTeX file (reads @article{key, ...} entry headers)
zotc keys extract references.bib

# From a CSV file with a "citation-key" column
zotc keys extract reading-list.csv

# From a plaintext file (one key per line, # comments ignored)
zotc keys extract keys.txt

# From multiple files at once (deduplicates across all inputs)
zotc keys extract intro.qmd methods.qmd discussion.qmd

# From stdin (format must be specified explicitly with -f)
cat keys.txt | zotc keys extract -f plaintext -

# Keys only — just list what citation keys were found, skip BBT resolution
# (does not require BBT database or any Zotero credentials)
zotc keys extract --keys-only paper.qmd

# Output resolved mappings as JSON (citation-key, itemKey, found: true/false)
zotc keys extract paper.qmd -t json

# Output as CSV, saved to file
zotc keys extract paper.qmd -t csv -o resolved.csv


# ── List and browse your Zotero collections ───────────────────────────────────

# Show all collections as a nested directory-style tree
zotc collection list

# Filter tree to collections matching a regex pattern
zotc collection list "Reading"
zotc collection list "2024"

# Full collection metadata as JSON (includes keys, item counts, parent keys)
zotc collection list -t json

# As CSV for spreadsheet use
zotc collection list -t csv


# ── Create a new collection from citation keys in a document ──────────────────
# Extracts citation keys from input files, resolves them via BBT, creates the
# collection via the Zotero API, and adds all resolved items to it.
# Parent collections in the path are created automatically if they don't exist.
# All operations are dry runs by default — pass --execute to apply.

# Dry run: preview what would be created (safe default)
zotc collection create "Reading/2024" paper.qmd

# Execute: create the collection and populate it
zotc collection create "Reading/2024" paper.qmd --execute

# From a BibTeX file
zotc collection create "Reading/2024" references.bib --execute

# From a CSV reading list
zotc collection create "Reading/2024" reading-list.csv --execute

# From multiple source files (all keys merged and deduplicated)
zotc collection create "Projects/MyPaper/References" \
  intro.qmd methods.qmd discussion.qmd --execute

# Control conflict behavior when the collection already exists:

# Add the new items to the existing collection (keep what's already there)
zotc collection create "Reading/2024" new.bib --on-conflict add     --execute

# Replace the existing collection's contents with the new input set
zotc collection create "Reading/2024" new.bib --on-conflict replace  --execute

# Do nothing if the collection already exists, exit cleanly
zotc collection create "Reading/2024" new.bib --on-conflict skip     --execute

# Auto-number to avoid the conflict: creates "Draft (2)", "Draft (3)", etc.
zotc collection create "Draft" paper.qmd     --on-conflict disambiguate --execute


# ── Add items to an existing collection ───────────────────────────────────────
# Adds items resolved from the input files without removing anything
# already in the collection.

zotc collection add "Reading/2024" new-papers.bib --execute
zotc collection add "Reading/2024" extra.qmd --execute


# ── Replace a collection's contents ───────────────────────────────────────────
# Syncs the collection to exactly match the resolved input: adds what is
# missing, removes what is no longer present, leaves the rest untouched.

zotc collection replace "Reading/2024" curated.bib --execute
zotc collection replace "Projects/MyPaper/References" paper.qmd --execute


# ── Diff a collection against your input ──────────────────────────────────────
# Shows what a replace would do — items only in input (+), only in the
# collection (-), in both, and any unresolved citation keys (?).
# Never modifies your library regardless of --execute.

zotc collection diff "Reading/2024" curated.bib
zotc collection diff "Projects/MyPaper/References" paper.qmd


# ── Verbosity ─────────────────────────────────────────────────────────────────

zotc -q   ...    # silent — no log output (only stdout results)
zotc -v   ...    # warnings only (unresolved keys, empty inputs)
zotc      ...    # info (default): progress, counts, dry-run summaries
zotc -vvv ...    # debug: full API URLs, request bodies, SQL query results
```
