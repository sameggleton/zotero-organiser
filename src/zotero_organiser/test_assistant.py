"""Read-only interactive sampling and reporting for a live Zotero library."""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from .config import Config
from .daemon import Organiser
from .taxonomy import Taxonomy
from .terminal import Terminal
from .zotero import ZoteroClient, eligible, tags

CLASSIFIER_PRIVACY_WARNING = (
    "The classifier is invoked: title, abstract, item type, publication title, "
    "and existing tags leave this machine when remote classification "
    "is enabled. PDFs are not parsed or sent."
)


@dataclass(frozen=True)
class Selection:
    items: list[dict]
    mode: str
    seed: int | None = None


def eligible_items(items: Iterable[dict], config: Config) -> list[dict]:
    return [item for item in items if eligible(item, config.daemon.allowed_item_types)]


def reservoir_sample(items: Iterable[dict], count: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    result: list[dict] = []
    for index, item in enumerate(items):
        if index < count:
            result.append(item)
        else:
            replacement = rng.randint(0, index)
            if replacement < count:
                result[replacement] = item
    return result


def isolated_config(config: Config, workspace: Path) -> Config:
    """Return a profile that cannot write or share production organiser state."""
    raw = config.model_dump()
    raw.update(
        {
            "state": {"database": workspace / "state.sqlite"},
            "backup": {**config.backup.model_dump(), "prewrite_dir": workspace / "prewrite"},
            "safety": {
                **config.safety.model_dump(),
                "write_enabled": False,
                "require_backup": False,
                "only_new_items": False,
            },
        }
    )
    return Config.model_validate(raw)


def _collection_title(collection: dict) -> str:
    return collection.get("data", {}).get("name", collection.get("key", "unnamed"))


def _choose_collections(ui: Terminal, client: ZoteroClient, config: Config) -> Selection:
    collections = list(client.collections())
    if not collections:
        raise ValueError("no collections found")
    while True:
        query = ui.ask("Collection name search (blank lists all)")
        matches = [c for c in collections if query.lower() in _collection_title(c).lower()]
        if not matches:
            ui.write("No matching collections.")
            continue
        for index, collection in enumerate(matches, 1):
            ui.write(f"  {index}. {_collection_title(collection)} ({collection['key']})")
        chosen = ui.ask("Select collection numbers (comma-separated)")
        try:
            indexes = {int(value.strip()) for value in chosen.split(",") if value.strip()}
        except ValueError:
            indexes = set()
        if not indexes or any(index < 1 or index > len(matches) for index in indexes):
            ui.write("Select one or more listed collection numbers.")
            continue
        seen: set[str] = set()
        items: list[dict] = []
        for index in sorted(indexes):
            for item in client.collection_items(matches[index - 1]["key"]):
                if item["key"] not in seen and eligible(item, config.daemon.allowed_item_types):
                    seen.add(item["key"])
                    items.append(item)
        return Selection(items, "collections")


def select_items(ui: Terminal, client: ZoteroClient, config: Config) -> Selection:
    choice = ui.choose(
        "Select live Zotero items to test",
        [
            "Specific collections",
            "Random sample",
            "Chronological sample",
            "Entire eligible library",
        ],
    )
    if choice == 0:
        return _choose_collections(ui, client, config)
    if choice == 1:
        count = _positive(ui, "Number of items")
        seed = random.SystemRandom().randrange(1, 2**63)
        return Selection(
            reservoir_sample(
                (i for i in client.top_items() if eligible(i, config.daemon.allowed_item_types)),
                count,
                seed,
            ),
            "random",
            seed,
        )
    if choice == 2:
        count = _positive(ui, "Number of items")
        direction = (
            "asc"
            if ui.choose("Chronological direction", ["Oldest first", "Newest first"]) == 0
            else "desc"
        )
        items = eligible_items(client.top_items(direction=direction), config)[:count]
        return Selection(items, f"chronological ({'oldest' if direction == 'asc' else 'newest'})")
    items = eligible_items(client.top_items(), config)
    if config.classification.enabled:
        cost = "remote classifier/API costs may apply"
        ui.write(CLASSIFIER_PRIVACY_WARNING)
    else:
        cost = "classification stays on this machine"
    if not ui.confirm(f"Test all {len(items)} eligible items? {cost}"):
        raise ValueError("full-library test cancelled")
    return Selection(items, "entire library")


def _positive(ui: Terminal, prompt: str) -> int:
    while True:
        try:
            value = int(ui.ask(prompt))
            if value > 0:
                return value
        except ValueError:
            pass
        ui.write("Enter a positive whole number.")


def run_interactive(
    config: Config, taxonomy: Taxonomy, *, ui: Terminal | None = None
) -> Path | None:
    ui = ui or Terminal()
    client = ZoteroClient(config.zotero)
    try:
        selection = select_items(ui, client, config)
    finally:
        client.close()
    if not selection.items:
        ui.write("No eligible items selected; nothing was run.")
        return None
    classifier_mode = (
        "local-first"
        if config.local_classifier.enabled and config.local_classifier.mode == "primary"
        else ("remote API" if config.classification.enabled else "disabled/manual triage")
    )
    ui.heading("Test selection")
    ui.write(f"{len(selection.items)} item(s); {selection.mode}; classifier: {classifier_mode}")
    ui.write("No Zotero writes will be made.")
    if config.classification.enabled:
        ui.write(CLASSIFIER_PRIVACY_WARNING)
    if not ui.confirm("Start this read-only dry run"):
        return None
    workspace = (
        config.state.database.parent / "tests" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    )
    workspace.mkdir(parents=True, exist_ok=False)
    test_config = isolated_config(config, workspace)
    organiser = Organiser(test_config, taxonomy)
    started = time.monotonic()
    report_items: list[dict] = []
    try:
        for item in selection.items:
            entry = {
                "key": item["key"],
                "title": item.get("data", {}).get("title", ""),
                "current_tags": sorted(tags(item)),
            }
            try:
                result = organiser.process(
                    item["key"], dry_run=True, force=True, allow_prebaseline=True
                )
                if result and "scores" in result:
                    entry["proposed_scores"] = result["scores"]
                    entry["proposed_tags"] = sorted(result["tags"])
                else:
                    entry["skipped"] = (
                        result.get("skipped", "not eligible or not ready")
                        if result
                        else "not eligible or not ready"
                    )
            except Exception as exc:  # preserve the rest of a representative run
                entry["failure"] = str(exc)
            report_items.append(entry)
    finally:
        organiser.close()
    report = {
        "started_at": datetime.now(UTC).isoformat(),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "selection": {
            "mode": selection.mode,
            "count": len(selection.items),
            "random_seed": selection.seed,
        },
        "classifier_mode": classifier_mode,
        "no_zotero_writes": True,
        "items": report_items,
    }
    path = workspace / "report.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    failures = sum("failure" in item for item in report_items)
    skipped = sum("skipped" in item for item in report_items)
    ui.write(
        f"Completed {len(report_items)} item(s): {failures} failure(s), {skipped} skipped. Report: {path}"
    )
    return path
