# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Native Zotero 10+ Plugin (`.xpi`)**:
  - In-app Item Pane section (`Zotero.ItemPaneManager`) with real-time classification status, confidence score badges, interactive triage review cards (1-click Accept, Dismiss, and Override), and candidate tag autocomplete.
  - Visual Taxonomy Manager in Zotero Settings (`Zotero.PreferencePanes.register()`) with live Zod YAML validation, clickable line error jumps, dirty-state tracking, and drag-and-drop import/export.
  - Multi-Domain Profile Combiner enabling automatic synthesis of interdisciplinary taxonomies across multiple research domains.
  - Reactive `Zotero.Notifier` event loop for automatic background tag proposals on paper additions or updates.
  - Context menu integration for on-demand library and collection tag organisation.
  - Vitest test suite, TypeScript compilation, and `.xpi` packaging workflow.
- **25 Australian Fields of Research (FoR) Academic Domain Profiles**:
  - Ready-to-use domain profiles covering all 25 FoR categories in `src/zotero_organiser/profiles/` and `examples/taxonomies/profiles/`.
  - CLI commands `zotero-organiser taxonomy profiles list` and `taxonomy profiles show <profile_id>`.
  - Bundled profiles included in Python wheel distribution.
- **Local AI Models & Setup**:
  - Guided setup wizard (`./scripts/setup`) offering hardware-filtered runtimes (CPU, Apple MPS, NVIDIA CUDA, AMD ROCm), multi-select model size prefetching, and secure environment configuration.
  - CLI commands `zotero-organiser models download` and `models status`.
  - `ranker-gpu` extra for CUDA FastEmbed (`fastembed-gpu`).
- **Security, Documentation & Packaging**:
  - GNU Affero General Public License v3.0 (`AGPL-3.0-or-later`) and updated package metadata.
  - `SECURITY.md` covering Zotero-library writes and the Local API key stored in SQLite.
  - `THIRD_PARTY.md` covering optional model and dependency licenses, plus Zotero trademark notice.
  - GitHub Actions CI workflow: pytest on Python 3.12 and 3.13 (macOS and Ubuntu), Ruff format and linting, packaged and example taxonomy validation, example config verification, and plugin Vitest and packaging on Node.js 24.
  - `taxonomy init` / `taxonomy path`, and user taxonomy copy management next to configuration files.

### Changed

- New installs default to the local embedding + NLI pipeline. The OpenAI-compatible API is opt-in. Example configs and `classification.enabled`'s pydantic default match that. Existing configs that already enable remote classification are not rewritten.
- Local inference loads cached weights only (`local_files_only`); missing caches fail with a pointer to `models download` instead of fetching on first classify.
- Packaged taxonomy is a small generic seed. Chemistry tags live in `examples/taxonomies/molecular-simulation.yml`.
- `run` / `once` skip classification while writes are disabled. `classify` / `dry-run` use isolated state.
- GitHub Actions CI uses `actions/checkout@v5` and `astral-sh/setup-uv@v7` running on Node.js 24. Only the pytest jobs save the uv cache so concurrent Ubuntu 3.13 jobs do not race on the same key.

## [0.3.1] - 2026-08-24

### Deprecated

- `webdav.path` is a pre-0.2 compatibility key. Use `attachments.path`. Configurations that still set only `webdav.path` continue to load, and `backup.source` defaults to that path.
