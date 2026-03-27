<div align="center">

# bioportal-cli

![Python](https://img.shields.io/badge/python-3.11%2B-eab308)
![License](https://img.shields.io/badge/license-MIT-ca8a04)

Full-surface command-line wrapper for the NCBO BioPortal API, with search, ontology resources, collaboration resources, analytics, downloads, and machine-readable output.

</div>

> [!IMPORTANT]
> This codebase is entirely AI-generated. It is useful to me, I hope it might be useful to others, and issues and contributions are welcome.

## Map
- [Install](#install)
- [Functionality](#functionality)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [Credits](#credits)

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install .
bioportal --help
```

Development install:

```bash
pip install -e .[dev]
```

## Functionality

### Search and NLP
- `bioportal search`: term search with ontology filters, exact matching, suggestion mode, subtree/roots-only constraints, CUI and semantic-type filtering, paging, include fields, and language controls.
- `bioportal property-search`: property label/ID search with ontology-type and property-type filters, paging, and include fields.
- `bioportal annotator`: text annotation with ontology and semantic-type filtering, hierarchy and mapping expansion controls, stop-word tuning, and match behavior options.
- `bioportal recommender`: ontology recommendation from text or keyword lists, with output-mode controls (single ontology vs ontology sets), weighted ranking criteria, and ontology restrictions.

### Batch and Analytics
- `bioportal batch classes`: class batch resolution using the documented `/batch` payload model.
- `bioportal analytics global`: global analytics with optional month/year filters.
- `bioportal analytics ontology`: per-ontology analytics.

### Ontology Content Graph
- `bioportal ontologies`: full ontology resource coverage (`list`, `full`, `get`, `create`, `put`, `patch`, `delete`, `latest-submission`, `download`, `admin-log`, `pull`).
- `bioportal submissions`: global and ontology-scoped submission operations, item patch/delete, downloads, diff downloads, and bulk-delete status.
- `bioportal classes`: list/get/roots/tree/ancestor-descendant traversal, class instances, class mappings, and class notes.
- `bioportal properties`: list/get/roots/label/tree/ancestor-descendant traversal for ontology properties.
- `bioportal instances`: ontology and class-scoped instance retrieval.
- `bioportal collections` and `bioportal schemes`: SKOS collection/scheme listing and item retrieval.

### Mapping, Metrics, and Discussion
- `bioportal mappings`: list/recent/stats/get/create/delete plus ontology/class scoped mapping views.
- `bioportal metrics`: global, missing, ontology, and submission metrics.
- `bioportal notes`, `bioportal replies`, `bioportal reviews`: list/create/get/patch/delete plus ontology/class/note scoped listing where documented.

### Governance and Administration Resources
- `bioportal provisional-classes`: list/create/get/patch/delete plus ontology and user scoped lists.
- `bioportal provisional-relations`: list/create/get/delete.
- `bioportal categories`, `bioportal groups`, `bioportal projects`: full CRUD and ontology-scoped listing.
- `bioportal slices`: list/create/get/patch/delete and `sync-groups`.
- `bioportal users`: list/create/get/put/patch/delete plus `authenticate`, `create-reset-password-token`, and `reset-password`.

### Docs, Config, and Escape Hatch
- `bioportal docs info|catalog|families`: inspect wrapped API surface from bundled endpoint metadata.
- `bioportal config show|set`: saved defaults for key/base-url/timeout.
- `bioportal api request`: direct operation fallback (`method + path + query + optional body`) without reducing explicit wrapper coverage.

### Higher-Order Workflows
- `bioportal workflows concept-resolve <ontology> <term-or-id>`: resolve a concept via direct class lookup (URI-like IDs) or ontology-constrained search with best-match output.
- `bioportal workflows concept-expand <ontology> <class-id>`: aggregate class item, parents/children, ancestors/descendants, and paths-to-root into one graph-ready payload.
- `bioportal workflows concept-annotate-and-map --text ...`: annotate text and enrich each annotation with class details and mappings where available.
- `bioportal workflows ontology-profile <acronym>`: return ontology metadata, latest submission, metrics, analytics, categories, groups, and projects in one object.
- `bioportal workflows ontology-compare <left> <right> --by {metrics|mappings|coverage|all}`: compare two ontologies using metrics, mapping statistics, and optional probe-query coverage checks.
- `bioportal workflows recommender-explain --input ...`: run recommender and return weighted criterion context alongside raw recommender output.
- `bioportal workflows notes-thread-export [--global | --ontology X [--class-id Y]]`: export notes with threaded reply normalization.
- `bioportal workflows batch-classes-from-file <file>`: load class/ontology pairs from JSON or CSV-like lines and execute `/batch`.
- `bioportal workflows fetch-all <path>`: traverse pagination for list endpoints and return consolidated items.
- `bioportal workflows pipeline-suggest-ontologies --text ...`: recommender-driven ontology shortlist with search and annotator previews.

### Output and Paging
- Output modes: `--output json`, `--output jsonl`, `--output text`.
- File writes: `--output-file`.
- Download endpoints return binary and require `--output-file`.
- Pagination controls: `--page`, `--pagesize`, and optional traversal with `--all-pages --max-pages N`.

## Configuration

BioPortal API keys can be provided by flag, environment variable, or XDG config file.

Precedence (highest first):
1. CLI flags: `--api-key`, `--base-url`, `--timeout`
2. Environment: `BIOPORTAL_API_KEY`, `BIOPORTAL_BASE_URL`, `BIOPORTAL_TIMEOUT`
3. Config file: `$XDG_CONFIG_HOME/bioportal-cli/config.json` (or `~/.config/bioportal-cli/config.json`)
4. Built-ins: `https://data.bioontology.org`, timeout `30`

```bash
bioportal config set --api-key "YOUR_API_KEY"
bioportal config set --base-url "https://data.bioontology.org" --timeout 30
bioportal config show
```

## Quick Start

```bash
bioportal search --q melanoma --ontologies NCIT,GO --pagesize 10

bioportal annotator --text "Melanoma is a malignant tumor of melanocytes"

bioportal ontologies list --page 1 --pagesize 5
bioportal ontologies get NCIT --output text

bioportal classes get NCIT http%3A%2F%2Fpurl.bioontology.org%2Fontology%2FNCIT%2FC3224

bioportal analytics ontology NCIT

bioportal workflows concept-resolve NCIT melanoma

bioportal workflows ontology-profile NCIT

bioportal workflows ontology-compare NCIT EFO --by all --probe cancer --probe melanoma

bioportal workflows pipeline-suggest-ontologies --text "melanoma biomarkers" --top 3

bioportal docs catalog --output jsonl
```

## Credits

This client is built for the NCBO BioPortal API and is not affiliated with NCBO.

Credit goes to NCBO BioPortal for the ontology platform, data services, and API documentation this tool depends on.

Upstream references:
- `https://data.bioontology.org/documentation`
- `https://data.bioontology.org`
