# zotero-organiser

[![CI Status](https://github.com/sameggleton/zotero-organiser/actions/workflows/ci.yml/badge.svg)](https://github.com/sameggleton/zotero-organiser/actions)
[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Zotero 10+](https://img.shields.io/badge/zotero-10+-purple.svg)](https://www.zotero.org)
[![Node.js 24+](https://img.shields.io/badge/node-24+-green.svg)](https://nodejs.org)

A conservative, privacy-first automatic tag organiser and taxonomy management system for your local [Zotero](https://www.zotero.org/) library.

`zotero-organiser` is available as:
1. **A Native Zotero 10+ GUI Plugin (`.xpi`)**: Provides an interactive Item Pane UI, a visual Taxonomy Manager in Zotero Settings with 25 Australian Fields of Research (FoR) domain profiles, a multi-domain profile combiner, live YAML validation, and reactive event-based tagging.
2. **A Conservative Python CLI & Background Daemon**: Provides continuous background sync, Restic backup gating, pre-write JSON snapshots, and local hardware-accelerated embedding + NLI classification models (CPU, Apple Silicon MPS, NVIDIA CUDA, AMD ROCm).

This project is unofficial and is not affiliated with the Corporation for Digital Scholarship.

---

## Core Safety Guarantees

- **Human Tags Retained**: Manually added tags are never deleted, altered, or overwritten.
- **Durable Deletion Suppression**: If you delete an organiser-added tag in Zotero, the organiser records that decision in SQLite and permanently suppresses that tag for that item.
- **Human-Owned Namespaces**: `status/*` (workflow) and `priority/*` (judgement) tags are exclusively human-owned. The automated classifier never adds, removes, or modifies them.
- **Atomic & Reversible**: Tag mutations use atomic transactions (`item.saveTx()` in the plugin, `If-Unmodified-Since-Version` in the CLI). Full pre-write JSON dumps are saved before every mutation.
- **100% Local & Private**: All metadata stays on your machine by default. No PDFs are parsed, no attachment bytes are uploaded, and no cloud AI APIs are called unless you explicitly opt in.
- **Strict Taxonomy Enforcement**: The organiser only applies canonical tags defined in **your** taxonomy YAML. It never invents halluncinated tags.

---

## Contents

- [Native Zotero Plugin](#native-zotero-plugin)
  - [Item Pane UI](#item-pane-ui)
  - [Visual Taxonomy Manager](#visual-taxonomy-manager)
  - [Installing the Plugin (.xpi)](#installing-the-plugin-xpi)
  - [Building from Source](#building-from-source)
- [25 Domain Taxonomy Profiles (Australian FoR Standard)](#25-domain-taxonomy-profiles-australian-for-standard)
  - [Profile Catalog](#profile-catalog)
  - [Multi-Domain Profile Combiner](#multi-domain-profile-combiner)
- [Python CLI & Daemon](#python-cli--daemon)
  - [Requirements](#requirements)
  - [Five-Minute Setup Wizard](#five-minute-setup-wizard)
  - [Command Reference](#command-reference)
  - [Safe Rollout Checklist](#safe-rollout-checklist)
- [Local AI & Classification Pipeline](#local-ai--classification-pipeline)
  - [Hybrid Candidate Retrieval & NLI Reranking](#hybrid-candidate-retrieval--nli-reranking)
  - [Preference Memory (Personalization)](#preference-memory-personalization)
  - [Hardware Acceleration](#hardware-acceleration)
  - [Optional Remote Classifier](#optional-remote-classifier)
- [Taxonomy Authoring](#taxonomy-authoring)
- [Backups, Recovery & Privacy](#backups-recovery--privacy)
- [Development & Testing](#development--testing)
- [License & Third-Party Notices](#license--third-party-notices)

---

## Native Zotero Plugin

The native Zotero 10+ plugin (`.xpi`) provides a seamless, in-app experience directly within the Zotero desktop application.

```text
┌───────────────────────────────────────────────────────────────────────┐
│ Zotero 10 Desktop                                                    │
├───────────────────────┬───────────────────────────────────────────────┤
│ Collections & Library │ Item Pane: Zotero Organiser Section           │
│                       ├───────────────────────────────────────────────┤
│ 📄 Paper Title        │ Status: Classified (Local BGE + ModernBERT)   │
│   • Author (2026)     │                                               │
│                       │ Applied Tags:                                 │
│                       │  [role/empirical 0.94]  [method/nlp 0.91]     │
│                       │                                               │
│                       │ Review Queue (Triage):                        │
│                       │  ? topic/information-retrieval (0.78)         │
│                       │    [ ✓ Accept ]  [ ✗ Dismiss ]  [ Override ]   │
│                       │                                               │
│                       │ Add Taxonomy Tag: [ Search topics, methods... ]│
└───────────────────────┴───────────────────────────────────────────────┘
```

### Item Pane UI

Integrated into Zotero's right-hand metadata pane via `Zotero.ItemPaneManager`:

- **Real-Time Classification Badges**: Displays assigned taxonomy tags with confidence scores and color-coded namespace indicators.
- **Interactive Triage Review Cards**: Items in the review range (confidence between `0.65` and `0.85`) present quick 1-click **Accept (✓)**, **Dismiss (✗)**, and **Override** buttons directly in the sidebar.
- **Candidate Tag Autocomplete & Search**: Search your active taxonomy with instant prefix matching, displaying tag descriptions, aliases, and scope constraints for manual tagging.
- **Context Menu Actions**: Right-click any library item or collection to trigger on-demand tag organisation or preview proposed changes without mutating the item.

### Visual Taxonomy Manager

Located in **Zotero Settings → Zotero Organiser** (registered via `Zotero.PreferencePanes`):

- **25 Ready-to-Use Domain Profiles**: One-click selection covering all 25 Australian Fields of Research (FoR) disciplines.
- **Multi-Domain Profile Combiner**: Select multiple profiles (e.g. *Computer & Information Sciences* + *Psychology & Cognitive Sciences* + *Indigenous Studies*) to automatically synthesize an integrated interdisciplinary taxonomy with reconciled namespaces and quotas.
- **Live YAML Validation with Error Highlighting**: Built-in editor with instant Zod schema validation, clickable line-number error jump, and dirty state tracking (Save / Discard).
- **Drag-and-Drop Import & Export**: Import your existing `taxonomy.yml` or export your customized taxonomy to disk with a single click.

### Installing the Plugin (.xpi)

1. Download the latest `zotero-organiser.xpi` release from GitHub Releases (or build it from source below).
2. In Zotero 10+, go to **Tools → Plugins** (or **Add-ons**).
3. Click the gear icon (**⚙**) in the top right corner and select **Install Add-on From File...**.
4. Select `zotero-organiser.xpi` and confirm installation.
5. Open **Settings → Zotero Organiser** to select or customize your domain taxonomy.

### Building from Source

To build the plugin `.xpi` package from a repository checkout:

```bash
cd plugin
npm install
npm test            # Run Vitest test suite
npm run build       # Build bundle (esbuild)
npm run package     # Package into dist/zotero-organiser.xpi
```

For live development, create an extension proxy file pointing to the `plugin` directory in your Zotero profile's `extensions/` folder.

---

## 25 Domain Taxonomy Profiles (Australian FoR Standard)

`zotero-organiser` includes **25 ready-to-use domain taxonomy profiles** aligned with the Australian Government Department of Industry, Science and Resources **Fields of Research (FoR)** standard.

Each profile defines a complete, multi-namespace taxonomy:
- **`role`**: Contribution style and epistemic purpose (e.g. `role/empirical`, `role/theoretical`, `role/methodological`, `role/review`).
- **`topic`**: Domain-specific conceptual areas and subject matter.
- **`system`**: Physical, biological, technological, or social objects of study.
- **`method`**: Empirical, analytical, experimental, computational, or qualitative methodology.
- **`status`**: Human-managed reading lifecycle (`status/needs-triage`, `status/to-read`, `status/reading`, `status/read`, `status/processed`).
- **`priority`**: Human judgement levels (`priority/core`, `priority/marginal`).

### Profile Catalog

| # | Profile Name | Identifier | Included Subdomains |
|---|---|---|---|
| 1 | **General Scholar** | `general-scholar` | Interdisciplinary, Research Design, Open Science, Empirical Methods |
| 2 | **Mathematics & Statistics** | `mathematics-statistics` | Pure & Applied Mathematics, Probability, Statistics, Optimisation |
| 3 | **Computer & Information Sciences** | `computer-information-sciences` | Machine Learning, AI, Algorithms, Software Engineering, Systems |
| 4 | **Physics & Astronomy** | `physics-astronomy` | Quantum Physics, Condensed Matter, Astrophysics, Particle Physics, Optics |
| 5 | **Chemistry & Molecular Sciences** | `chemistry-molecular-sciences` | Organic, Inorganic, Physical, Computational Chemistry, Electrochemistry |
| 6 | **Biological Sciences** | `biological-sciences` | Cell Biology, Genetics, Microbiology, Evolution, Bioinformatics |
| 7 | **Biomedical & Clinical Sciences** | `biomedical-clinical-sciences` | Neuroscience, Immunology, Cancer, Pharmacology, Pathology |
| 8 | **Health Sciences** | `health-sciences` | Epidemiology, Public Health, Health Services, Nursing, Policy |
| 9 | **Agricultural, Veterinary & Food** | `agricultural-veterinary-food` | Agronomy, Crop Science, Animal Science, Food Science, Veterinary |
| 10 | **Earth, Atmospheric & Ocean** | `earth-atmospheric-ocean` | Geology, Geophysics, Oceanography, Climate Science, Meteorology |
| 11 | **Environmental & Sustainability** | `environmental-sustainability` | Ecology, Conservation, Biodiversity, Sustainability, Environmental Management |
| 12 | **Engineering & Technology** | `engineering-technology` | Electrical, Mechanical, Chemical, Robotics, Materials Engineering |
| 13 | **Built Environment & Architecture** | `built-environment-architecture` | Architecture, Urban Planning, Building Science, Sustainable Design |
| 14 | **Psychology & Cognitive Sciences** | `psychology-cognitive-sciences` | Cognition, Behaviour, Cognitive Neuroscience, Mental Health |
| 15 | **Economics** | `economics` | Econometrics, Macroeconomics, Microeconomics, Labour, Behavioural Economics |
| 16 | **Business & Management** | `business-management-organisations` | Finance, Management, Marketing, Strategy, Entrepreneurship |
| 17 | **Society, Politics & Geography** | `society-politics-human-geography` | Sociology, Political Science, Public Policy, Anthropology, Geography |
| 18 | **Education & Learning Sciences** | `education-learning-sciences` | Pedagogy, Curriculum, Educational Technology, Higher Education |
| 19 | **Law, Criminology & Justice** | `law-criminology-justice` | Public Law, Private Law, International Law, Criminology, Criminal Justice |
| 20 | **Language, Communication & Culture** | `language-communication-culture` | Linguistics, Communication, Media Studies, Cultural Studies |
| 21 | **Literature & Writing** | `literature-writing` | Literature, Literary Theory, Comparative Literature, Creative Writing |
| 22 | **History, Heritage & Archaeology** | `history-heritage-archaeology` | History, Archaeology, Heritage, Historiography, Material Culture |
| 23 | **Philosophy, Ethics & Religion** | `philosophy-ethics-religious` | Philosophy, Ethics, Epistemology, Logic, Philosophy of Science |
| 24 | **Creative Arts & Design** | `creative-arts-design` | Visual Arts, Music, Performing Arts, Design, Creative Practice |
| 25 | **Indigenous Studies** | `indigenous-studies` | Indigenous Knowledge, Decolonial Research, Indigenous Health & Governance |

### Multi-Domain Profile Combiner

In the Zotero GUI Plugin, navigate to **Settings → Zotero Organiser → Profiles** and select any combination of profiles to generate an interdisciplinary taxonomy automatically.

In the CLI, list and inspect domain profiles:

```sh
# List all 25 available profiles
zotero-organiser taxonomy profiles list

# View summary and tag structure of a profile
zotero-organiser taxonomy profiles show computer-information-sciences

# Initialize your library's taxonomy from any profile
zotero-organiser taxonomy init --from examples/taxonomies/profiles/physics-astronomy.yml
```

---

## Python CLI & Daemon

The Python CLI and continuous daemon provide automated background tagging, bulk untagged processing, Restic backup-gated pipelines, and hardware-accelerated local model execution.

### Requirements

- **macOS or Ubuntu** (Windows is not supported)
- Python 3.12 or newer
- Zotero desktop 10 or newer with **Settings → Advanced → Allow other applications on this computer to communicate with Zotero** enabled
- [Restic](https://restic.net/) (required for backup gating unless deliberately disabled)
- Disk space for local embedding and NLI model weights (~600 MB for default CPU models)

### Five-Minute Setup Wizard

From a repository checkout, run the guided interactive setup wizard:

```sh
./scripts/setup
```

The wizard:
1. Detects your hardware (CPU, Apple Silicon MPS, NVIDIA CUDA, AMD ROCm).
2. Generates an isolated, write-disabled configuration file.
3. Initializes a user taxonomy copy next to your config.
4. Creates a secure environment file (file mode `0600`).
5. Downloads the FastEmbed embedding and ModernBERT NLI reranker weights.

Or install manually using [uv](https://docs.astral.sh/uv/) or pipx:

```sh
uv tool install ".[ranker,local-classifier]"
# Or for NVIDIA CUDA ONNX Runtime:
# uv tool install ".[ranker-gpu,local-classifier]"

zotero-organiser models download
zotero-organiser models status
```

#### XDG File Layout (macOS & Ubuntu)

| Role | Path |
| --- | --- |
| Config | `~/.config/zotero-organiser/config.yml` |
| Taxonomy (edit this) | `~/.config/zotero-organiser/taxonomy.yml` |
| Secrets / API keys | `~/.config/zotero-organiser/environment` |
| State Database (secret) | `~/.local/state/zotero-organiser/state.sqlite` |
| Pre-write JSON & Restic Repo | `~/.local/share/zotero-organiser/` |
| Embedding Cache | `~/.cache/zotero-organiser/ranker` |
| Attachments Directory | `~/Zotero/storage` |

### Command Reference

Global invocation:
```text
zotero-organiser --config PATH --env-file PATH --taxonomy PATH COMMAND
```

| Command | Classifier? | Writes Zotero? | Description |
| --- | --- | --- | --- |
| `classify ITEM_KEY` | Yes (preview) | Never | Preview tags for one item in isolated state |
| `dry-run ITEM_KEY` | Yes (preview) | Never | Alias for `classify` |
| `test` | Yes (sample) | Never | Interactive dry-run assistant over live library (sidecar DB) |
| `retry ITEM_KEY` | Yes | If `write_enabled: true` | Reprocess and write tags for a specific item |
| `tag-untagged N` | Yes | If `write_enabled: true` | Classify and tag up to N items lacking taxonomy tags |
| `run` / `once` | If writes enabled | If `write_enabled: true` | Continuous daemon (`run`) or single sync pass (`once`) |
| `models download` | No | No | Prefetch configured embedding and NLI models |
| `models status` | No | No | Check model cache status on disk |
| `doctor` | No | No | Check Local API, attachments, Restic, credentials, and taxonomy |
| `status` | No | No | Show organiser queue and backup status |
| `taxonomy init` | No | No | Copy starter or preset taxonomy (`--from`) to config directory |
| `taxonomy validate` | No | No | Check taxonomy YAML schema and constraints |
| `taxonomy audit` | Ranker | No | Detect high-similarity overlapping tags via embeddings |
| `taxonomy profiles list` | No | No | List all 25 FoR domain academic profiles |
| `taxonomy profiles show ID` | No | No | Display summary of namespaces and tags in a domain profile |
| `profile build` / `status` | No | No | Build or view local historical tag-preference profile |
| `profile map` / `export` | No | No | Map raw library tags to canonical taxonomy tags |

### Safe Rollout Checklist

New configurations default to `write_enabled: false`, `require_backup: true`, `only_new_items: true`, `allow_tag_removal: false`, and `max_items_per_cycle: 5`.

1. Run `zotero-organiser doctor` and `zotero-organiser taxonomy validate`. Confirm all integration checks pass.
2. Run `zotero-organiser once` to establish a clean library baseline timestamp without mutating items.
3. Preview proposals on sample papers with `zotero-organiser classify ITEM_KEY` or interactive `zotero-organiser test`.
4. Create a sandbox collection in Zotero with 5–10 test papers. Temporarily set `safety.write_enabled: true` and run `zotero-organiser retry ITEM_KEY`.
5. Verify the Restic snapshot, pre-write JSON in `~/.local/share/zotero-organiser/prewrite/`, and final Zotero tags.
6. Delete an organiser-added tag in Zotero, re-run `retry`, and verify that the tag remains suppressed.

---

## Local AI & Classification Pipeline

### Hybrid Candidate Retrieval & NLI Reranking

```text
Title + Abstract Metadata
          │
          ▼
1. FastEmbed BGE Dense Retrieval
   (Retrieves top-k candidate taxonomy tags via cosine similarity)
          │
          ▼
2. ModernBERT Cross-Encoder NLI
   (Zero-shot premise/hypothesis entailment scoring)
          │
          ▼
3. Preference Memory Personalization Residual
   (Applies strictly bounded ±0.18 adjustment from user feedback)
          │
          ▼
4. Policy Decision Gate
   (Enforces confidence threshold >= 0.85, per-namespace quotas, exclusions)
```

### Supported Models

Embedding models (FastEmbed ONNX, MIT License):
| Size | Model | Typical Download |
| --- | --- | --- |
| Small (Default) | `BAAI/bge-small-en-v1.5` | ~130 MB |
| Medium | `BAAI/bge-base-en-v1.5` | ~210 MB |
| Large | `BAAI/bge-large-en-v1.5` | ~1.2 GB |

NLI Reranker models (Transformers, Apache-2.0 License):
| Size | Model | Typical Download |
| --- | --- | --- |
| Small (Default) | `tasksource/ModernBERT-base-nli` | ~0.5 GB |
| Large | `tasksource/ModernBERT-large-nli` | ~1.6 GB |

### Preference Memory (Personalization)

Both the native plugin and CLI track your tag acceptance and deletion decisions:
- Stores user feedback exemplars in SQLite.
- Applies a bounded cosine residual:
  $$\text{score} = \text{base\_score} + \alpha \cdot \text{sim}(\text{pos}) - \beta \cdot \text{sim}(\text{neg})$$
- The residual is strictly clamped ($\pm 0.18$), guaranteeing that user preferences adjust candidate rankings without violating taxonomy boundaries or rules.

### Hardware Acceleration

- **CPU**: Always supported via ONNX FastEmbed and PyTorch CPU.
- **Apple Silicon (MPS)**: FastEmbed ONNX on CPU + Metal Performance Shaders (MPS) for PyTorch NLI scoring.
- **NVIDIA CUDA**: CUDA-accelerated ONNX Runtime (`fastembed-gpu`) + CUDA PyTorch.
- **AMD ROCm**: ONNX CPU embeddings + ROCm PyTorch NLI reranking.

### Optional Remote Classifier

Remote OpenAI-compatible classification is completely opt-in (`classification.enabled: true` in `config.yml`):

```yaml
classification:
  enabled: true
  provider: openai_compatible
  endpoint: https://api.openai.com/v1/chat/completions
  api_key_env: OPENAI_API_KEY
  model: gpt-4.1-mini
```

---

## Taxonomy Authoring

Taxonomies are defined in clean, readable YAML:

```yaml
schema_version: 1
version: "1.0.0"

classifier:
  semantic_namespaces: [role, topic, method]
  workflow_namespaces: [status]
  human_only_namespaces: [priority]

namespaces:
  status:
    kind: workflow
    classifier_eligible: false
    max_tags: 1
    values:
      to-read:
        description: "In the reading queue."
  topic:
    kind: semantic
    max_tags: 3
    values:
      information-retrieval:
        description: "Substantively about retrieving information from corpora."
        aliases: [IR, search]
        include: [retrieval-augmented generation as primary subject]
        exclude: [passing mention of a search bar]
```

- **`aliases`**: Recognition aliases normalized to canonical tags (never emitted directly).
- **`include` / `exclude`**: Disambiguation boundaries ensuring high precision.
- **`max_tags`**: Per-namespace limit on tags emitted per document.
- **`classifier_eligible: false`**: Excludes workflow or priority namespaces from automatic classifier emission.

Validate your taxonomy with `zotero-organiser taxonomy validate` or audit similarity with `zotero-organiser taxonomy audit`.

---

## Backups, Recovery & Privacy

- **Zero Cloud Uploads**: The default local pipeline never transmits library titles, abstracts, or metadata off your machine.
- **No PDF Parsing**: PDFs and file attachments are never opened, parsed, or uploaded.
- **Restic Backup Gating**: Real writes are blocked unless Restic confirms repository accessibility and records a valid snapshot before mutation.
- **Pre-write JSON Snapshots**: Exact item metadata is saved to `~/.local/share/zotero-organiser/prewrite/` immediately prior to any modification.
- **Local API Security**: Zotero 10+ local authorization tokens are saved with strict owner-only permissions (`0600`) in `state.sqlite`.

---

## Development & Testing

### Python Backend

```sh
# Run pytest test suite (170 tests)
uv run --extra dev pytest

# Format and lint with Ruff
uv run ruff format --check src tests
uv run ruff check src tests

# Validate bundled taxonomy
uv run zotero-organiser taxonomy validate
```

### Native Zotero Plugin

```sh
cd plugin

# Install dependencies
npm install

# Run Vitest test suite (Node.js 24)
npm test

# Typecheck TypeScript
npx tsc --noEmit

# Build bundle and package .xpi
npm run build
npm run package
```

---

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0-or-later)** (see [`LICENSE`](LICENSE)).

- **Copyleft**: Any modifications, derivative works, or network-accessible deployments must remain free and open source under the AGPLv3.
- **Third-Party Notices**: See [`THIRD_PARTY.md`](THIRD_PARTY.md) for licenses of bundled models and libraries.
