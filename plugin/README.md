# Zotero Organiser (Native Zotero 10+ Plugin)

[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](../LICENSE)
[![Zotero 10+](https://img.shields.io/badge/zotero-10+-purple.svg)](https://www.zotero.org)

A native Zotero 10+ extension providing conservative, taxonomy-based automatic tag organisation for scientific literature.

## Features

- **Reactive Event System**: Listens directly to item additions and modifications via `Zotero.Notifier` in real-time.
- **Safety & Durability**:
  - Human tags are preserved.
  - Deleting an organiser-owned tag permanently suppresses it.
  - `status/*` and `priority/*` namespaces remain strictly human-owned.
  - Atomic tag mutation via `item.saveTx()`.
  - Automatic pre-write JSON snapshots saved before any changes.
- **25 Domain Taxonomy Profiles**: Built-in coverage of all 25 Australian Fields of Research (FoR) categories with multi-domain profile combiner.
- **Taxonomy Validation & GUI Manager**: Full in-app visual Taxonomy Manager with live Zod YAML validation, bounded editor, dirty state tracking, and drag-and-drop import/export.
- **Tier-1 Preference Memory**: Bounded personal cosine residual learning with SQLite exemplar persistence.
- **Candidate Ranking & Classification**: Hybrid dense + lexical scoring with per-namespace quotas, and support for local/remote LLM classifiers.
- **Native Zotero UI**:
  - **Item Pane Section**: Uses `Zotero.ItemPaneManager` to render real-time classification status, applied tags, interactive triage review cards, candidate expansion, and autocomplete search.
  - **Context Menu**: Right-click to trigger classification or preview proposals.
  - **Preferences Pane**: Native Zotero Settings tab via `Zotero.PreferencePanes.register()`.

## Development

### Prerequisites

- Node.js >= 24
- npm >= 10
- Zotero 10+

### Install Dependencies

```bash
cd plugin
npm install
```

### Run Tests

```bash
npm test
```

### Build & Package .xpi

```bash
# Build bundled script
npm run build

# Build and package as .xpi archive for distribution
npm run package
```

The output `.xpi` file will be generated in `dist/zotero-organiser.xpi`.

### Installing into Zotero

1. In Zotero, go to **Tools → Plugins** (or **Add-ons**).
2. Click the gear icon (**⚙**) in the top right and select **Install Add-on From File...**.
3. Select `plugin/dist/zotero-organiser.xpi`.
4. Alternatively, use an extension proxy file pointing to the `plugin` directory in your Zotero profile `extensions/` directory for live development.

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0-or-later)** (see [`LICENSE`](../LICENSE)).


