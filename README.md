# Zotcurate (`zotc`)

**Zotero collection curation from the command line.**

`zotc` bridges your documents and your Zotero library. It reads citation keys from any file you're working in — a Quarto manuscript, a BibTeX export, a reading list CSV — and uses those keys to create, populate, or synchronize Zotero collections. The critical link is your local [BetterBibTeX](https://retorque.re/zotero-better-bibtex/) SQLite database, which maps the human-readable citation keys you write (e.g., `Smith2023evolution`) to the internal item keys the Zotero API expects (e.g., `X4K2MNPQ`).

## Summary

### What is Zotcurate?

Zotcurate is a command-line tool for creating, populating, and synchronizing Zotero collections from your documents and bibliography files. It reads citation keys from any file you're working in — a Quarto manuscript, a BibTeX export, a reading list CSV — and uses them to drive the Zotero Web API. The bridge between your documents and your library is your local BetterBibTeX SQLite database, which maps the human-readable citation keys you write (e.g., Smith2023evolution) to the internal item keys the API expects (e.g., X4K2MNPQ).

### Why use Zotcurate?

Zotcurate fills a major gap in Zotero workflows: there are many tools for getting references out of Zotero, into Obsidian via Zotero Integration, ZotLit or [Bibliosidian](https://github.com/jeetsukumaran/obsidian-bibliosidian) for example, but not much that goes the other way. The citations you actually used in a manuscript, the annotated bibliography or reading list you refined in Obsidian, the thematic grouping that emerged after months of note-taking: these are the intellectual output of working with your references, and they belong back in Zotero as proper collections. `zotc` is that return path. (See (Motivation)[MOTIVATION.md] for more details.)

---

## Table of Contents

- [Why This Exists](#why-this-exists)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Core Concepts](#core-concepts)
- [Command Reference](#command-reference)
  - [`keys list`](#keys-list)
  - [`keys extract`](#keys-extract)
  - [`collection list`](#collection-list)
  - [`collection create`](#collection-create)
  - [`collection add`](#collection-add)
  - [`collection replace`](#collection-replace)
  - [`collection diff`](#collection-diff)
- [Input Formats](#input-formats)
- [Output Formats](#output-formats)
- [Walkthroughs](#walkthroughs)
  - [Curating a reading list from a Quarto document](#walkthrough-1-curating-a-reading-list-from-a-quarto-document)
  - [Syncing a collection from a maintained bibliography file](#walkthrough-2-syncing-a-collection-from-a-maintained-bibliography-file)
  - [Building collections from a structured CSV table](#walkthrough-3-building-collections-from-a-structured-csv-table)
  - [Exploring your BetterBibTeX database](#walkthrough-4-exploring-your-betterbibtex-database)
  - [Checking what would change before committing](#walkthrough-5-checking-what-would-change-before-committing)
- [Exit Codes](#exit-codes)
- [Global Flags](#global-flags)

---

## Why This Exists

Zotero's collection system is powerful but manual. If you're writing a paper in Quarto and citing 40 sources, there's no built-in way to say "create a collection containing exactly the items I cited in this manuscript." You either manage collections by hand or ignore them.

`zotc` automates this. Common use cases:

- **Per-manuscript collections** — one collection per paper, auto-populated from the `.qmd` or `.rmd` file
- **Reading list curation** — maintain a `reading.csv` or `reading.bib` and sync it to a Zotero collection
- **Batch reorganization** — diff a collection against a new bibliography before making changes
- **Pipeline integration** — scriptable, machine-readable output formats (JSON, CSV, YAML), safe dry-run default

---

## Requirements

- Python 3.10+
- [Zotero](https://www.zotero.org/) desktop app with the [BetterBibTeX](https://retorque.re/zotero-better-bibtex/) plugin
- A Zotero API key (free, from [zotero.org/settings/keys](https://www.zotero.org/settings/keys))
- Your Zotero library ID (visible on the same API keys page)

No third-party Python packages are required — only the standard library.

---

## Installation

```bash
# Recommended: isolated install with pipx
pipx install .

# Or: editable dev install
pip install -e .
```

This installs the `zotc` command.

---

## Configuration

`zotc` resolves configuration in this priority order:

```
CLI flags  >  environment variables  >  .zotc/ config files  >  defaults
```

### CLI flags

| Flag | Purpose |
|---|---|
| `-i`, `--library-id` | Your Zotero library ID |
| `-k`, `--api-key` | Your Zotero API key |
| `--library-type` | `user` (default) or `group` |
| `-b`, `--better-bibtex` | Path to your BBT SQLite database |

### Environment variables

```bash
export ZOTERO_LIBRARY_ID=1234567
export ZOTERO_API_KEY=your_api_key_here
export ZOTERO_LIBRARY_TYPE=user
```

### Config files

Place single-line files in `.zotc/` in your project directory or `~/.zotc/` for global defaults:

```
~/.zotc/
├── library          # your numeric library ID
├── api-key          # your API key
└── library-type     # "user" or "group"
```

```bash
mkdir -p ~/.zotc
echo "1234567"       > ~/.zotc/library
echo "your_key_here" > ~/.zotc/api-key
```

Once your credentials are in `~/.zotc/`, you only need `-b` to point at the BetterBibTeX database:

```bash
zotc -b ~/Zotero/better-bibtex.sqlite collection create "Reading/2024" paper.qmd --execute
```

### Finding your BetterBibTeX database

The BBT database lives inside your Zotero data directory:

```
macOS:   ~/Library/Application Support/Zotero/better-bibtex.sqlite
Linux:   ~/.zotero/zotero/better-bibtex.sqlite
Windows: %APPDATA%\Zotero\Zotero\better-bibtex.sqlite
```

You can also find it via **Zotero → Edit → Preferences → Advanced → Files and Folders → Data Directory**.

---

## Core Concepts

### Citation keys vs. item keys

| Term | Example | What it is |
|---|---|---|
| **Citation key** | `Smith2023evolution` | The human-readable key BetterBibTeX assigns. What you type in `@Smith2023evolution` in your document. |
| **Item key** | `X4K2MNPQ` | Zotero's internal 8-character identifier. What the API uses. |

BetterBibTeX maintains a local SQLite database (`better-bibtex.sqlite`) that maps one to the other. `zotc` reads this database directly (read-only) to resolve your citation keys without making any API calls for that step.

### Collection paths

Collections can be nested. `zotc` uses slash-separated paths to refer to them:

```
Reading/2024
Projects/MyPaper/References
Courses/BIOL301
```

`zotc collection create "Reading/2024"` will create both `Reading` and `2024` if they don't exist, walking the path left-to-right.

### Dry run (default)

Every command that modifies your Zotero library prints `[DRY RUN]` messages showing what *would* happen, then exits without changing anything. Pass `--execute` to apply the changes.

---

## Command Reference

### Global flags

```
zotc [-i LIBRARY_ID] [-k API_KEY] [--library-type {user,group}]
     [-b BETTERBIBTEX_DB] [-q | -v | -vvv]
     {keys,collection} ...
```

| Flag | Effect |
|---|---|
| `-q` | Silent — no log output |
| `-v` | Warnings only |
| (default) | Info messages |
| `-vvv` | Debug — prints full API requests/responses |

---

### `keys list`

Dump all citation key records from your BetterBibTeX database.

```
zotc -b BBT_DB keys list [-t FORMAT] [-o OUTPUT] [--sort {citation-key,item-key,item-id}]
```

**Examples:**

```bash
# Print all keys in plaintext (citation-key TAB item-key)
zotc -b ~/Zotero/better-bibtex.sqlite keys list

# Export to JSON
zotc -b ~/Zotero/better-bibtex.sqlite keys list -t json

# Export to CSV, sorted by Zotero item key
zotc -b ~/Zotero/better-bibtex.sqlite keys list -t csv --sort item-key -o all-keys.csv
```

**Plaintext output (default):**
```
Abbott2019phylo      MNPQXK2A
Benton2021fossil     7YWRZ3CV
Smith2023evolution   X4K2MNPQ
```

**JSON output (`-t json`):**
```json
[
  {
    "citationKey": "Abbott2019phylo",
    "itemKey": "MNPQXK2A",
    "itemID": 1042,
    "libraryID": 1,
    "pinned": true,
    "lastPinned": "2024-01-15"
  },
  ...
]
```

---

### `keys extract`

Extract citation keys from one or more files and optionally resolve them to Zotero item keys.

```
zotc [-b BBT_DB] keys extract FILES... [-f FORMAT] [-t FORMAT] [-o OUTPUT]
     [--keys-only] [--sort {alpha,none}]
```

**Without `--keys-only`:** requires `-b` and returns citation key + item key pairs.
**With `--keys-only`:** no database needed; returns only the citation keys found in the file.

**Examples:**

```bash
# Extract and resolve keys from a Quarto document
zotc -b ~/Zotero/better-bibtex.sqlite keys extract paper.qmd

# Keys only (no resolution), output as JSON
zotc keys extract --keys-only paper.qmd -t json

# Extract from multiple files
zotc -b bbt.sqlite keys extract intro.qmd methods.qmd discussion.qmd

# Read from stdin (plaintext list of keys)
cat my-keys.txt | zotc -b bbt.sqlite keys extract -f plaintext -

# Extract from a BibTeX file, save resolved mapping as CSV
zotc -b bbt.sqlite keys extract refs.bib -t csv -o resolved.csv
```

**Plaintext output (default, with resolution):**
```
Abbott2019phylo      MNPQXK2A
Benton2021fossil     7YWRZ3CV
Smith2023evolution   X4K2MNPQ
Unknown2020xyz       NOT_FOUND
```

**JSON output (`-t json`, with resolution):**
```json
[
  {
    "citation-key": "Abbott2019phylo",
    "itemKey": "MNPQXK2A",
    "found": true
  },
  {
    "citation-key": "Unknown2020xyz",
    "itemKey": null,
    "found": false
  }
]
```

**`--keys-only` plaintext:**
```
Abbott2019phylo
Benton2021fossil
Smith2023evolution
```

---

### `collection list`

List all Zotero collections.

```
zotc -i LIBRARY_ID -k API_KEY collection list [PATTERN] [-t {tree,json,csv,plaintext}] [--sort {name,items}]
```

**Examples:**

```bash
# Tree view of all collections
zotc collection list

# Filter to collections matching a regex
zotc collection list "Reading"

# Find all collections with "2024" in the name
zotc collection list "2024"

# Machine-readable JSON for scripting
zotc collection list -t json

# Sort by item count
zotc collection list --sort items
```

**Tree output (default):**
```
Courses/
Courses/BIOL301
Courses/EVOL405
Projects/
Projects/MyPaper/
Projects/MyPaper/References
Reading/
Reading/2023
Reading/2024
```

**JSON output:**
```json
[
  {
    "key": "AB3K9WZP",
    "name": "2024",
    "parentKey": "X7MNPQR2",
    "numItems": 14
  },
  ...
]
```

---

### `collection create`

Create a new Zotero collection and populate it with items resolved from citation keys in your input files.

```
zotc -i ID -k KEY -b BBT_DB collection create COLLECTION_PATH FILES...
     [-f FORMAT] [--on-conflict {abort,add,replace,skip,disambiguate}]
     [--execute]
```

**Conflict strategies** (when the collection already exists):

| Strategy | Behavior |
|---|---|
| `abort` (default) | Exit with an error |
| `add` | Add the new items to the existing collection |
| `replace` | Replace collection contents with the new set |
| `skip` | Do nothing, exit cleanly |
| `disambiguate` | Create `Collection (2)`, `Collection (3)`, etc. |

**Examples:**

```bash
# Dry run — see what would be created (safe default)
zotc -b bbt.sqlite collection create "Reading/2024" paper.qmd

# Actually create the collection
zotc -b bbt.sqlite collection create "Reading/2024" paper.qmd --execute

# Create a nested collection (parents auto-created if needed)
zotc -b bbt.sqlite collection create "Projects/MyPaper/References" refs.bib --execute

# If the collection exists, add new items instead of aborting
zotc -b bbt.sqlite collection create "Reading/2024" new-papers.bib \
  --on-conflict add --execute

# Auto-number to avoid conflicts
zotc -b bbt.sqlite collection create "Draft" paper.qmd \
  --on-conflict disambiguate --execute
# → creates "Draft (2)" if "Draft" already exists
```

**Dry run output:**
```
[DRY RUN] Would create collection: Reading (parent=root)
[DRY RUN] Would create collection: 2024 (parent=Reading)
[DRY RUN] Would add 23 items to collection AB3K9WZP
[DRY RUN] Would create 'Reading/2024' with 23 items
Warning: 2 citation keys were not resolved.
```

---

### `collection add`

Add items to an **existing** collection without removing anything already there.

```
zotc -i ID -k KEY -b BBT_DB collection add COLLECTION_PATH FILES...
     [-f FORMAT] [--execute]
```

**Examples:**

```bash
# Preview what would be added
zotc -b bbt.sqlite collection add "Reading/2024" new-papers.bib

# Apply the additions
zotc -b bbt.sqlite collection add "Reading/2024" new-papers.bib --execute

# Add items from a Quarto doc that has new citations
zotc -b bbt.sqlite collection add "Projects/MyPaper/References" draft-v2.qmd --execute
```

---

### `collection replace`

Replace a collection's contents so it contains exactly the items from your input — adding what's missing, removing what's no longer present.

```
zotc -i ID -k KEY -b BBT_DB collection replace COLLECTION_PATH FILES...
     [-f FORMAT] [--execute]
```

This is the **sync** operation. It computes the symmetric difference and applies the minimal set of changes.

**Examples:**

```bash
# Preview the sync
zotc -b bbt.sqlite collection replace "Reading/2024" curated.bib

# Apply the sync
zotc -b bbt.sqlite collection replace "Reading/2024" curated.bib --execute
```

**Output:**
```
Replace 'Reading/2024': +5 added, -3 removed
```

---

### `collection diff`

Show what would change if you ran `replace` — without making any changes. Reads both the input files and the current collection, then prints a three-way comparison.

```
zotc -i ID -k KEY -b BBT_DB collection diff COLLECTION_PATH FILES...
     [-f FORMAT]
```

`diff` never modifies your library, regardless of whether `--execute` is passed.

**Example:**

```bash
zotc -b bbt.sqlite collection diff "Reading/2024" curated.bib
```

**Output:**
```
=== Diff: input vs 'Reading/2024' ===

In both (18):
  MNPQXK2A
  7YWRZ3CV
  ...

Only in input (5):
  + X4K2MNPQ
  + R9WZAB3K
  ...

Only in collection (3):
  - PQ7WRZAB
  - K2MNPQX4
  ...

Unresolved citation keys (1):
  ? Unknown2020xyz
```

---

## Input Formats

Format is auto-detected from the file extension. Use `-f`/`--from-format` to override.

| Format | Extensions | How citation keys are found |
|---|---|---|
| `bibtex` | `.bib`, `.bibtex` | `@article{citationKey,` entry headers |
| `csv` | `.csv` | Column named `citation-key` (configurable) |
| `tsv` | `.tsv` | Column named `citation-key` (configurable) |
| `yaml` | `.yaml`, `.yml` | Field named `citation-key` in each list item |
| `json` | `.json` | Field named `citation-key` in each array element |
| `plaintext` | `.txt`, `.text` | One key per line; `#` comments and leading `@` stripped |
| `markdown` | `.md`, `.qmd`, `.rmd` | Pandoc `@key`, `[@key1; @key2]`, Obsidian `[[path/@key]]`, Markdown links |

### Markdown extraction details

The Markdown extractor handles all common citation styles in Quarto and Obsidian:

```markdown
# Pandoc inline citation
See @Smith2023evolution for a review.

# Pandoc bracketed citation
Fossils from this period [@Benton2021fossil; @Abbott2019phylo] suggest...

# Suppressed author
[-@Smith2023evolution]

# Obsidian wiki-link to a literature note
![[Papers/@Abbott2019phylo]]
[[References/@Benton2021fossil.md]]

# Markdown link to a literature note
[Abbott et al.](notes/@Abbott2019phylo.md)
```

All four forms extract to the same citation key list.

### Custom field names for CSV/TSV/JSON/YAML

If your structured data uses a different column/field name:

```bash
# CSV with a "citekey" column instead of "citation-key"
zotc -b bbt.sqlite collection create "Reading/2024" refs.csv \
  --read-citation-key-field citekey --execute
```

### Reading from stdin

Use `-` as the filename to read from standard input. You must specify the format explicitly:

```bash
grep "^@" references.bib | zotc -b bbt.sqlite keys extract -f plaintext -
cat keys.txt | zotc -b bbt.sqlite collection add "Inbox" -f plaintext - --execute
```

---

## Output Formats

Specify with `-t`/`--to-format`. Output goes to stdout unless `-o FILE` is given (extension auto-detected).

| Format | Flag | Best for |
|---|---|---|
| `plaintext` | `-t plaintext` | Human reading, shell pipelines |
| `csv` | `-t csv` | Spreadsheets, further processing |
| `tsv` | `-t tsv` | `awk`, `cut`, tab-separated tools |
| `json` | `-t json` | Scripting, APIs, jq |
| `yaml` | `-t yaml` | Config files, Obsidian metadata |
| `tree` | `-t tree` | Collection listing only |

---

## Walkthroughs

### Walkthrough 1: Curating a reading list from a Quarto document

You've written `phylogeny-review.qmd` and want a Zotero collection containing exactly the papers you cited, organized under `Projects/PhyloReview`.

**Step 1: Check what keys are in your document.**

```bash
zotc keys extract --keys-only phylogeny-review.qmd
```
```
Abbott2019phylo
Benton2021fossil
Felsenstein1981distance
Smith2023evolution
...
```

**Step 2: See if they all resolve to Zotero items.**

```bash
zotc -b ~/Zotero/better-bibtex.sqlite keys extract phylogeny-review.qmd
```
```
INFO  Collected 31 unique citation keys
INFO  Resolved 30/31 keys (1 unresolved)
WARNING  Unresolved citation key: Felsenstein1981distance
Abbott2019phylo      MNPQXK2A
Benton2021fossil     7YWRZ3CV
Smith2023evolution   X4K2MNPQ
...
Felsenstein1981distance    NOT_FOUND
```

One key didn't resolve — probably not in your Zotero library yet. Add it to Zotero before continuing, or proceed and the missing item will be reported but skipped.

**Step 3: Dry-run the collection creation.**

```bash
zotc -b ~/Zotero/better-bibtex.sqlite \
  collection create "Projects/PhyloReview" phylogeny-review.qmd
```
```
[DRY RUN] Would create collection: Projects (parent=root)
[DRY RUN] Would create collection: PhyloReview (parent=Projects)
[DRY RUN] Would add 30 items to collection
[DRY RUN] Would create 'Projects/PhyloReview' with 30 items
Warning: 1 citation keys were not resolved.
```

**Step 4: Execute.**

```bash
zotc -b ~/Zotero/better-bibtex.sqlite \
  collection create "Projects/PhyloReview" phylogeny-review.qmd --execute
```
```
Created 'Projects/PhyloReview' with 30 items
Warning: 1 citation keys were not resolved.
```

Your Zotero library now has a `Projects/PhyloReview` collection with all 30 resolvable cited papers.

---

### Walkthrough 2: Syncing a collection from a maintained bibliography file

You maintain `curated-phylo.bib` as your canonical reference list for a project. As you add and remove entries from the `.bib` file, you want the Zotero collection to stay in sync.

**First time — create the collection:**
```bash
zotc -b ~/Zotero/better-bibtex.sqlite \
  collection create "Reading/Phylogenetics" curated-phylo.bib --execute
```

**After updating the `.bib` file — sync it:**
```bash
# Preview the changes
zotc -b ~/Zotero/better-bibtex.sqlite \
  collection diff "Reading/Phylogenetics" curated-phylo.bib
```
```
=== Diff: input vs 'Reading/Phylogenetics' ===

In both (47):
  7YWRZ3CV
  MNPQXK2A
  ...

Only in input (3):
  + X4K2MNPQ
  + AB3K9WZP
  + R9WZAB3K

Only in collection (1):
  - PQ7WRZAB
```

Good — 3 items will be added, 1 removed. Apply it:

```bash
zotc -b ~/Zotero/better-bibtex.sqlite \
  collection replace "Reading/Phylogenetics" curated-phylo.bib --execute
```
```
Replaced 'Reading/Phylogenetics': +3 added, -1 removed
```

Make this a regular part of your workflow — add it to a `Makefile` or shell alias.

---

### Walkthrough 3: Building collections from a structured CSV table

You've compiled a literature review table in a spreadsheet and exported it as `underwater-civilizations.csv`:

```csv
title,author,year,citation-key,genre,subgenre
Twenty Thousand Leagues Under the Sea,Jules Verne,1870,Verne1870leagues,Novel,Adventure
The Abyss,James Cameron,1989,Cameron1989abyss,Film,Sci-Fi
...
```

**Extract all citation keys from the table:**
```bash
zotc keys extract --keys-only underwater-civilizations.csv
```

**Create a Zotero collection from the whole table:**
```bash
zotc -b ~/Zotero/better-bibtex.sqlite \
  collection create "SFF/UnderwaterCivilizations" underwater-civilizations.csv --execute
```

**If you want to create per-genre subcollections, filter the CSV first:**
```bash
# Create a subcollection for Novels only
grep "Novel" underwater-civilizations.csv | \
  (head -1 underwater-civilizations.csv; cat) | \
  zotc -b ~/Zotero/better-bibtex.sqlite \
    collection create "SFF/UnderwaterCivilizations/Novels" -f csv - --execute
```

---

### Walkthrough 4: Exploring your BetterBibTeX database

Before working with collections, it's useful to understand what's in your BBT database.

**List all keys and spot-check coverage:**
```bash
zotc -b ~/Zotero/better-bibtex.sqlite keys list | wc -l
# → 1847

zotc -b ~/Zotero/better-bibtex.sqlite keys list | grep "2024"
# → items with "2024" in their citation key
```

**Export the full key mapping to a CSV for offline use:**
```bash
zotc -b ~/Zotero/better-bibtex.sqlite keys list -t csv -o all-keys.csv
```

**Check whether a specific key exists:**
```bash
zotc -b ~/Zotero/better-bibtex.sqlite keys list | grep "Smith2023"
```

**Find unresolved keys across all your active documents:**
```bash
zotc -b ~/Zotero/better-bibtex.sqlite \
  keys extract paper1.qmd paper2.qmd paper3.qmd -t json | \
  jq '[.[] | select(.found == false) | .["citation-key"]]'
```

---

### Walkthrough 5: Checking what would change before committing

You've received a collaborator's `.bib` file and want to see how it compares to your current `Projects/SharedPaper` collection before making any changes.

```bash
zotc -b ~/Zotero/better-bibtex.sqlite \
  collection diff "Projects/SharedPaper" collaborator-refs.bib
```

This is completely read-only — it fetches the current collection membership from the Zotero API, resolves the collaborator's keys via BBT, and reports the three-way comparison without touching anything. Good for code review-style workflows before executing a `replace`.

If the diff looks right:
```bash
zotc -b ~/Zotero/better-bibtex.sqlite \
  collection replace "Projects/SharedPaper" collaborator-refs.bib --execute
```

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Error (config missing, file not found, API error, no items resolved) |
| `2` | Partial success — command completed but some citation keys were unresolved (`keys extract` only) |
| `130` | Interrupted by Ctrl-C |

Exit code `2` from `keys extract` is useful in scripts: you can treat fully-resolved runs differently from partially-resolved ones without failing the whole pipeline.

---

## Verbosity

| Flag | Level | Shows |
|---|---|---|
| `-q` | Silent | Nothing |
| `-v` | Warnings | Unresolved keys, empty inputs |
| (default) | Info | Progress messages, counts, dry-run summaries |
| `-vvv` | Debug | Full API URLs, request/response bodies, SQL results |

```bash
# Debug mode for troubleshooting API calls
zotc -vvv -b bbt.sqlite collection list

# Silent mode for scripting (only stdout output, no log noise)
zotc -q -b bbt.sqlite keys extract paper.qmd -t json | jq ...
```
