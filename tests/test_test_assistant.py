from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

from zotero_organiser.config import Config
from zotero_organiser.terminal import Terminal
from zotero_organiser.test_assistant import (
    CLASSIFIER_PRIVACY_WARNING,
    isolated_config,
    reservoir_sample,
    run_interactive,
    select_items,
)


def config(tmp_path: Path) -> Config:
    return Config.model_validate(
        {
            "zotero": {},
            "attachments": {"path": str(tmp_path / "attachments")},
            "backup": {
                "source": str(tmp_path / "attachments"),
                "repository": str(tmp_path / "restic"),
                "prewrite_dir": str(tmp_path / "prewrite"),
            },
            "state": {"database": str(tmp_path / "production.sqlite")},
        }
    )


def test_reservoir_sample_is_deterministic_and_bounded():
    items = [{"key": str(index)} for index in range(20)]
    assert reservoir_sample(items, 5, 47) == reservoir_sample(items, 5, 47)
    assert len(reservoir_sample(items, 30, 47)) == 20


def test_isolated_config_never_uses_production_state_or_writes(tmp_path: Path):
    production = config(tmp_path)
    isolated = isolated_config(production, tmp_path / "tests" / "case")
    assert isolated.state.database == tmp_path / "tests" / "case" / "state.sqlite"
    assert isolated.state.database != production.state.database
    assert isolated.backup.prewrite_dir == tmp_path / "tests" / "case" / "prewrite"
    assert not isolated.safety.write_enabled
    assert not isolated.safety.require_backup
    assert not isolated.safety.only_new_items
    assert not hasattr(isolated.safety, "allow_collection_changes")


class FakeClient:
    def __init__(self):
        self._items = [
            {
                "key": "A",
                "data": {"itemType": "journalArticle", "dateAdded": "2020-01-01T00:00:00Z"},
            },
            {
                "key": "B",
                "data": {"itemType": "journalArticle", "dateAdded": "2021-01-01T00:00:00Z"},
            },
            {
                "key": "C",
                "data": {"itemType": "journalArticle", "dateAdded": "2022-01-01T00:00:00Z"},
            },
        ]

    def top_items(self, *, direction="asc"):
        return iter(self._items if direction == "asc" else list(reversed(self._items)))

    def collections(self):
        return iter(
            [{"key": "ONE", "data": {"name": "First"}}, {"key": "TWO", "data": {"name": "Second"}}]
        )

    def collection_items(self, key):
        return iter(self._items[:2] if key == "ONE" else self._items[1:])

    def close(self):
        return None


def ui_for(*answers: str) -> Terminal:
    values = iter(answers)
    return Terminal(input_fn=lambda _prompt: next(values))


def test_collection_selection_unions_and_deduplicates(tmp_path: Path):
    selected = select_items(ui_for("1", "", "1,2"), FakeClient(), config(tmp_path))
    assert selected.mode == "collections"
    assert [item["key"] for item in selected.items] == ["A", "B", "C"]


def test_chronological_and_full_library_confirmation(tmp_path: Path):
    selected = select_items(ui_for("3", "2", "2"), FakeClient(), config(tmp_path))
    assert [item["key"] for item in selected.items] == ["C", "B"]
    try:
        select_items(ui_for("4", "no"), FakeClient(), config(tmp_path))
    except ValueError as exc:
        assert "cancelled" in str(exc)
    else:
        raise AssertionError("full library selection should require confirmation")


def test_privacy_warning_lists_fields_that_leave_the_machine():
    text = CLASSIFIER_PRIVACY_WARNING.lower()
    for field in ("title", "abstract", "item type", "publication title", "existing tags"):
        assert field in text
    assert "collection" not in text
    assert "pdf" in text


def test_entire_library_selection_warns_about_payload(tmp_path: Path):
    output = io.StringIO()
    answers = iter(["4", "no"])
    ui = Terminal(input_fn=lambda _prompt: next(answers), output=output)
    try:
        select_items(ui, FakeClient(), config(tmp_path))
    except ValueError as exc:
        assert "cancelled" in str(exc)
    else:
        raise AssertionError("full library selection should require confirmation")
    assert CLASSIFIER_PRIVACY_WARNING not in output.getvalue()


@patch("zotero_organiser.test_assistant.ZoteroClient")
@patch("zotero_organiser.test_assistant.Organiser")
def test_interactive_run_warns_before_starting(organiser_type, client_type, tmp_path: Path):
    output = io.StringIO()
    answers = iter(["2", "1", "y"])
    ui = Terminal(input_fn=lambda _prompt: next(answers), output=output)
    instance = organiser_type.return_value
    instance.process.return_value = {"skipped": "not ready"}
    client = FakeClient()
    client.close = MagicMock()
    client_type.return_value = client
    run_interactive(config(tmp_path), MagicMock(), ui=ui)
    assert CLASSIFIER_PRIVACY_WARNING not in output.getvalue()
    instance.close.assert_called()
    client.close.assert_called()
