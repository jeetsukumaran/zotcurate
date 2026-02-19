## Motivation

### The outbound pipeline is well-served

Zotero has a rich and mature ecosystem of plugins that make it easy to get your references *out* of your library and into wherever you do your thinking and writing.

At the foundation is [**Better BibTeX (BBT)**](https://retorque.re/zotero-better-bibtex/), which gives every item in your library a stable, human-readable citation key and can continuously export your library or individual collections as `.bib` files that stay in sync on disk. This is what makes text-based authoring workflows — Quarto, R Markdown, LaTeX, Typst — tractable: your citation keys are predictable, your `.bib` files are always fresh, and any tool that speaks BibTeX can participate.

From there, the ecosystem fans out in several directions. For writing in plain text and editors, [**zotxt**](https://github.com/egh/zotxt) exposes a local API that lets tools like `pandoc-zotxt` resolve citation keys at compile time, while the [**VS Code Citation Picker for Zotero**](https://github.com/mblode/vscode-zotero) brings a searchable citation dialog into VS Code. RStudio and Quarto's Visual Editor have native Zotero integration built in. For notes enrichment, [**Zotero Better Notes**](https://github.com/windingwind/zotero-better-notes) adds bidirectional Markdown sync, templates, and structured note-taking directly inside Zotero, and [**Mdnotes**](https://github.com/argenos/zotero-mdnotes) can export item metadata and annotations as Markdown files ready for import into a PKM. Plugins like [**Notero**](https://github.com/dvanoni/notero) sync items and notes into Notion. For metadata enrichment, [**Zotero Citation Counts Manager**](https://github.com/eschnett/zotero-citationcounts) pulls live citation counts from Crossref, Semantic Scholar, and NASA/ADS. [**Zotero MCP**](https://github.com/kaliaboi/zotero-mcp) connects your library to Claude and other AI assistants via the Model Context Protocol.

### Obsidian in particular has become a rich destination

Among personal knowledge management tools, [**Obsidian**](https://obsidian.md/) has attracted by far the most Zotero integration work, with multiple mature plugins representing different philosophies about where reference management should live.

[**Zotero Integration**](https://github.com/mgmeyers/obsidian-zotero-integration) (by mgmeyers) is the most widely used: it imports citations, formatted bibliographies, Zotero notes, and PDF annotations directly into Obsidian using customizable Nunjucks/Eta templates. It requires BBT and essentially treats Zotero as the canonical source of truth, pulling structured data into Obsidian on demand. [**ZotLit**](https://github.com/PKM-er/obsidian-zotlit) takes a similar approach but reads the Zotero SQLite database directly (without going through the BBT API) for faster, lower-latency access, and provides a matching Zotero-side plugin for a tighter two-plugin integration. The [**Citations plugin**](https://github.com/hans/obsidian-citation-plugin) works from an exported `.bib` or CSL-JSON file on disk rather than a live Zotero connection, which means it works without BBT but requires a manual or automated export step.

[**Bibliosidian**](https://github.com/jeetsukumaran/obsidian-bibliosidian) takes a different stance entirely: rather than treating Zotero as foundational, it treats your reference manager as an upstream data source and makes Obsidian itself the reference graph. You paste a BibTeX snippet — from Zotero, Google Scholar, Litmaps, wherever — and Bibliosidian creates or updates both a reference note and linked author notes in your vault, with all bibliographic metadata stored in Obsidian properties. The reference graph lives entirely in Obsidian, decoupled from any particular external tool and its versioning constraints.

### All of this flows in one direction

What these tools share — despite their different philosophies about *where* reference management should live — is that they are fundamentally concerned with getting data *out of* Zotero and *into* your working environment. BBT exports your library. Zotero Integration pulls annotations into your vault. ZotLit reads your Zotero database. Mdnotes generates Markdown. Notero syncs to Notion.

This makes sense as a starting point. Zotero is where you collect, where metadata lives, where PDFs are stored and annotated. It is the upstream source.

But thinking is not a one-pass process. You do not just receive references from Zotero and consume them — you work with them. You read and annotate. You organize by theme. You discover that the papers you actually cited are a more refined set than what you originally collected. You build reading lists. You create topic groupings that only make sense in retrospect, after you have spent time with the material. You maintain a canonical bibliography for a project that evolves over months. All of this intellectual work happens *downstream* of Zotero, in your documents and your PKM — but it produces artifacts that are meaningful *back upstream* in Zotero: a curated, refined set of references that now deserves to be a proper collection.

### The gap: nothing goes back

There is currently no tool designed for the return journey.

If your Quarto manuscript cites 35 papers, creating a Zotero collection containing exactly those 35 papers requires opening Zotero and manually dragging each one. If you maintain a reading list in Obsidian and want it mirrored as a Zotero collection so you can use Zotero's PDF management, annotation tools, and group library sharing — there is no automated path. If your collaborator sends you their `.bib` file and you want to see how it differs from what you already have in a shared collection, you have to check by hand. If you want to reorganize your library based on the structure that emerged from months of note-taking in Obsidian, you do that manually, one item at a time.

The entire plugin ecosystem described above assumes that Zotero is the origin. `zotc` is built on the premise that sometimes Zotero should be the *destination* — that the output of your thinking, reading, and writing is itself a meaningful artifact that belongs back in your reference library as a curated collection, and that getting it there should be as scriptable, safe, and composable as any other step in a modern research workflow.
