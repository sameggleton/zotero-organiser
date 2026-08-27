from __future__ import annotations

import argparse
import contextlib
import io
import signal
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from zotero_organiser import __version__
from zotero_organiser.cli import _handle_shutdown, _isolated_preview, main, parser
from zotero_organiser.taxonomy import packaged_taxonomy_path
from zotero_organiser.config import Config
from zotero_organiser.test_assistant import CLASSIFIER_PRIVACY_WARNING, isolated_config


class CliTests(unittest.TestCase):
    def test_version_flag_uses_package_version(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), self.assertRaises(SystemExit) as caught:
            parser().parse_args(["--version"])
        self.assertEqual(caught.exception.code, 0)
        self.assertIn(__version__, buffer.getvalue())

    def test_every_subparser_has_help(self):
        def walk(parser_obj: argparse.ArgumentParser) -> None:
            for action in parser_obj._actions:
                if not isinstance(action, argparse._SubParsersAction):
                    continue
                named = {choice.dest: choice.help for choice in action._choices_actions}
                for name, sub in action.choices.items():
                    self.assertTrue(named.get(name), f"missing help= for {name}")
                    walk(sub)

        walk(parser())

    def test_taxonomy_flag_overrides_default(self):
        args = parser().parse_args(["--taxonomy", "/tmp/custom.yml", "status"])
        self.assertEqual(args.taxonomy, Path("/tmp/custom.yml"))

    def test_classify_is_a_preview_command(self):
        args = parser().parse_args(["classify", "ABCD1234"])
        self.assertEqual(args.command, "classify")
        self.assertEqual(args.item_key, "ABCD1234")

    def test_write_is_not_a_command(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            parser().parse_args(["write", "ABCD1234"])
        self.assertNotEqual(caught.exception.code, 0)
        names: set[str] = set()
        for action in parser()._actions:
            if isinstance(action, argparse._SubParsersAction):
                names.update(action.choices)
        self.assertNotIn("write", names)
        self.assertIn("retry", names)

    def test_retry_is_the_one_item_write(self):
        args = parser().parse_args(["retry", "ABCD1234"])
        self.assertEqual(args.command, "retry")
        self.assertEqual(args.item_key, "ABCD1234")

    def test_isolated_preview_uses_isolated_state_and_warns(self):
        production = Config.model_validate(
            {
                "zotero": {},
                "attachments": {"path": "/tmp/storage"},
                "backup": {"repository": "/tmp/restic", "prewrite_dir": "/tmp/prewrite"},
                "state": {"database": "/tmp/production.sqlite"},
            }
        )
        with (
            patch("zotero_organiser.cli.Organiser") as organiser_type,
            patch("zotero_organiser.cli.isolated_config", wraps=isolated_config) as isolated,
            contextlib.redirect_stdout(io.StringIO()) as stdout,
        ):
            instance = organiser_type.return_value
            instance.process.return_value = None
            _isolated_preview(production, MagicMock(), "ABCD1234", force=True)
        isolated.assert_called_once()
        used = organiser_type.call_args.args[0]
        self.assertNotEqual(used.state.database, production.state.database)
        self.assertFalse(used.safety.write_enabled)
        instance.process.assert_called_once()
        self.assertTrue(instance.process.call_args.kwargs["dry_run"])
        instance.close.assert_called_once()
        self.assertNotIn(CLASSIFIER_PRIVACY_WARNING, stdout.getvalue())

    @patch("zotero_organiser.cli.load_taxonomy")
    @patch("zotero_organiser.cli.load_config")
    @patch("zotero_organiser.cli._isolated_preview", return_value=None)
    @patch("zotero_organiser.cli.load_environment")
    def test_classify_and_dry_run_use_isolated_preview(self, _env, preview, _config, _taxonomy):
        for command in ("dry-run", "classify"):
            preview.reset_mock()
            with patch("sys.argv", ["zotero-organiser", command, "ABCD1234"]):
                main()
            preview.assert_called_once()
            self.assertEqual(preview.call_args.args[2], "ABCD1234")
            self.assertTrue(preview.call_args.kwargs["force"])

    @patch("zotero_organiser.cli.load_taxonomy")
    @patch("zotero_organiser.cli.load_config")
    @patch("zotero_organiser.cli.Organiser")
    @patch("zotero_organiser.cli.load_environment")
    def test_retry_processes_one_item_with_writes_gated(
        self, _env, organiser_type, _config, _taxonomy
    ):
        instance = organiser_type.return_value
        instance.process.return_value = None
        with patch("sys.argv", ["zotero-organiser", "retry", "ABCD1234"]):
            main()
        instance.process.assert_called_once_with("ABCD1234", dry_run=False, force=True)
        instance.close.assert_called_once()

    @patch("zotero_organiser.cli.load_taxonomy")
    @patch("zotero_organiser.cli.load_config")
    @patch("zotero_organiser.cli.Organiser")
    @patch("zotero_organiser.cli.load_environment")
    def test_run_keyboard_interrupt_closes_and_exits_zero(
        self, _env, organiser_type, _config, _taxonomy
    ):
        instance = MagicMock()
        instance.run.side_effect = KeyboardInterrupt
        organiser_type.return_value = instance
        with (
            patch("sys.argv", ["zotero-organiser", "run"]),
            patch("zotero_organiser.cli.signal.signal") as sig,
        ):
            main()
        sig.assert_any_call(signal.SIGTERM, _handle_shutdown)
        instance.close.assert_called_once()

    def test_shutdown_handler_raises_keyboard_interrupt(self):
        with self.assertRaises(KeyboardInterrupt):
            _handle_shutdown(signal.SIGTERM, None)

    def test_tag_untagged_accepts_positive_count(self):
        args = parser().parse_args(["tag-untagged", "12"])
        self.assertEqual(args.command, "tag-untagged")
        self.assertEqual(args.count, 12)

    def test_tag_untagged_rejects_zero(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser().parse_args(["tag-untagged", "0"])

    def test_models_subcommands_parse(self):
        download = parser().parse_args(["models", "download"])
        self.assertEqual(download.command, "models")
        self.assertEqual(download.models_command, "download")
        status = parser().parse_args(["models", "status"])
        self.assertEqual(status.models_command, "status")

    def test_isolated_preview_warns_when_remote_classification_is_enabled(self):
        production = Config.model_validate(
            {
                "zotero": {},
                "attachments": {"path": "/tmp/storage"},
                "backup": {"repository": "/tmp/restic", "prewrite_dir": "/tmp/prewrite"},
                "state": {"database": "/tmp/production.sqlite"},
                "classification": {"enabled": True},
            }
        )
        with (
            patch("zotero_organiser.cli.Organiser") as organiser_type,
            contextlib.redirect_stdout(io.StringIO()) as stdout,
        ):
            organiser_type.return_value.process.return_value = None
            _isolated_preview(production, MagicMock(), "ABCD1234", force=True)
        self.assertIn(CLASSIFIER_PRIVACY_WARNING, stdout.getvalue())

    def test_taxonomy_init_and_path_parse(self):
        init = parser().parse_args(["taxonomy", "init", "--force", "--from", "/tmp/src.yml"])
        self.assertEqual(init.taxonomy_command, "init")
        self.assertTrue(init.force)
        self.assertEqual(init.source, Path("/tmp/src.yml"))
        path = parser().parse_args(["taxonomy", "path"])
        self.assertEqual(path.taxonomy_command, "path")

    def test_taxonomy_path_prints_packaged_seed_without_config(self):
        buffer = io.StringIO()
        with (
            patch(
                "sys.argv",
                ["zotero-organiser", "--config", "/missing/config.yml", "taxonomy", "path"],
            ),
            patch("zotero_organiser.cli.load_environment"),
            contextlib.redirect_stdout(buffer),
        ):
            main()
        self.assertEqual(buffer.getvalue().strip(), str(packaged_taxonomy_path()))

    def test_taxonomy_init_writes_user_copy_and_refuses_second_write(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / "taxonomy.yml"
            config = Path(directory) / "missing.yml"
            buffer = io.StringIO()
            with (
                patch(
                    "sys.argv",
                    [
                        "zotero-organiser",
                        "--config",
                        str(config),
                        "taxonomy",
                        "init",
                        "--dest",
                        str(dest),
                    ],
                ),
                patch("zotero_organiser.cli.load_environment"),
                contextlib.redirect_stdout(buffer),
            ):
                main()
            self.assertTrue(dest.is_file())
            self.assertIn(str(dest), buffer.getvalue())
            with (
                patch(
                    "sys.argv",
                    [
                        "zotero-organiser",
                        "--config",
                        str(config),
                        "taxonomy",
                        "init",
                        "--dest",
                        str(dest),
                    ],
                ),
                patch("zotero_organiser.cli.load_environment"),
                contextlib.redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit) as caught,
            ):
                main()
            self.assertNotEqual(caught.exception.code, 0)

    def test_taxonomy_audit_accepts_threshold_and_history(self):
        args = parser().parse_args(["taxonomy", "audit", "--threshold", "0.9", "--history"])
        self.assertEqual(args.taxonomy_command, "audit")
        self.assertEqual(args.threshold, 0.9)
        self.assertTrue(args.history)

    def test_profile_mapping_command_accepts_raw_and_canonical_tags(self):
        args = parser().parse_args(["profile", "map", "legacy", "topic/screening"])
        self.assertEqual(args.profile_command, "map")
        self.assertEqual(args.raw_tag, "legacy")

    def test_test_command_parses(self):
        args = parser().parse_args(["test"])
        self.assertEqual(args.command, "test")


if __name__ == "__main__":
    unittest.main()
