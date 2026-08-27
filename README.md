# zotero-organiser

[![CI Status](https://github.com/sameggleton/zotero-organiser/actions/workflows/ci.yml/badge.svg)](https://github.com/sameggleton/zotero-organiser/actions)
[![Release: v1.0.0](https://img.shields.io/badge/release-v1.0.0-purple.svg)](https://github.com/sameggleton/zotero-organiser/releases/tag/v1.0.0)
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)
[![Zotero 10+](https://img.shields.io/badge/zotero-10+-purple.svg)](https://www.zotero.org)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

A conservative, privacy-first automatic tag organiser and taxonomy management system for your local [Zotero 10+](https://www.zotero.org/) library.

Available as:
1. **[Native Zotero Plugin (`.xpi`)](#zotero-plugin-quickstart)**: In-app sidebar UI with triage review cards, candidate autocomplete, and a visual Taxonomy Manager in Settings.
2. **[Python CLI & Daemon](#python-cli-quickstart)**: Background service with Restic backup gating and local hardware-accelerated AI models.

---

## Core Features

- **In-Zotero Item Pane UI**: View real-time tag confidence badges and review triage candidates (confidence 0.65–0.85) with 1-click **Accept (✓)**, **Dismiss (✗)**, or **Override** directly in Zotero.
- **Visual Taxonomy Manager**: Edit taxonomies in **Zotero Settings → Zotero Organiser** with live schema validation, line-number error jump, and drag-and-drop import/export.
- **25 Academic Domain Profiles**: Ready-to-use profiles based on the Australian **Fields of Research (FoR)** standard (CS, Physics, Chemistry, Biology, Medicine, Economics, Humanities, etc.).
- **Multi-Domain Combiner**: Select multiple profiles (e.g. *Computer Science* + *Psychology*) to generate a unified interdisciplinary taxonomy automatically.
- **100% Local & Private AI**: Runs FastEmbed BGE embeddings + ModernBERT NLI cross-encoder locally on CPU, Apple Silicon (MPS), NVIDIA CUDA, or AMD ROCm. Never uploads metadata and never parses PDFs.
- **Conservative Guarantees**:
  - **Human tags preserved**: Never deletes or alters manually added tags.
  - **Durable suppression**: Deleting an organiser-added tag suppresses it permanently for that item.
  - **Human-only workflows**: `status/*` and `priority/*` tags are never touched by AI.
  - **Atomic writes**: Uses transactional mutations (`item.saveTx()`) with pre-write JSON snapshots.

---

## Installation

### Zotero Plugin Quickstart (Recommended)

1. Download **[`zotero-organiser.xpi`](https://github.com/sameggleton/zotero-organiser/releases/latest/download/zotero-organiser.xpi)** from the latest release.
2. In Zotero 10+, go to **Tools → Plugins** (or **Add-ons**).
3. Click the gear icon (**⚙**) in the top right corner and select **Install Add-on From File...**.
4. Select the downloaded `zotero-organiser.xpi` file and confirm.
5. Open **Settings → Zotero Organiser** to select a preset profile or customize your taxonomy.

#### Building the Plugin from Source

```bash
cd plugin
npm install
npm test            # Run Vitest test suite
npm run package     # Generates dist/zotero-organiser.xpi
```

---

### Python CLI Quickstart

For automated batch tagging, background sync, or headless machines (macOS / Ubuntu):

```bash
# Clone the repository
git clone https://github.com/sameggleton/zotero-organiser.git
cd zotero-organiser

# Run the interactive setup wizard (installs dependencies & downloads local models)
./scripts/setup
```

Or install via [uv](https://docs.astral.sh/uv/) / pipx:

```bash
uv tool install ".[ranker,local-classifier]"
zotero-organiser models download
```

#### Common CLI Commands

```bash
# Verify environment, Local API connection, and taxonomy
zotero-organiser doctor

# List and preview available academic domain profiles
zotero-organiser taxonomy profiles list
zotero-organiser taxonomy profiles show computer-information-sciences

# Preview proposed tags for a paper without modifying Zotero
zotero-organiser classify ITEM_KEY

# Tag untagged papers (respects write safety gates)
zotero-organiser tag-untagged 10

# Run continuous background daemon
zotero-organiser run
```

---

## Academic Domain Profiles (Australian FoR)

`zotero-organiser` bundles 25 discipline profiles in [`examples/taxonomies/profiles/`](examples/taxonomies/profiles/):

| | Domain Profiles | |
|---|---|---|
| • `general-scholar` | • `biological-sciences` | • `society-politics-human-geography` |
| • `mathematics-statistics` | • `biomedical-clinical-sciences` | • `education-learning-sciences` |
| • `computer-information-sciences` | • `health-sciences` | • `law-criminology-justice` |
| • `physics-astronomy` | • `agricultural-veterinary-food` | • `language-communication-culture` |
| • `chemistry-molecular-sciences` | • `earth-atmospheric-ocean` | • `literature-writing` |
| • `engineering-technology` | • `environmental-sustainability` | • `history-heritage-archaeology` |
| • `built-environment-architecture` | • `economics` | • `philosophy-ethics-religious` |
| • `psychology-cognitive-sciences` | • `business-management` | • `creative-arts-design` / `indigenous-studies` |

Combine profiles in the **Zotero Settings → Zotero Organiser → Profiles** tab, or initialize the CLI with:

```bash
zotero-organiser taxonomy init --from examples/taxonomies/profiles/physics-astronomy.yml
```

---

## Development

```bash
# Python tests & linting
uv run pytest
uv run ruff check src tests

# Plugin tests & build
cd plugin && npm test && npm run build
```

---

## License

GNU Affero General Public License v3.0 ([`AGPL-3.0-or-later`](LICENSE)). See [`THIRD_PARTY.md`](THIRD_PARTY.md) for bundled model notices.
