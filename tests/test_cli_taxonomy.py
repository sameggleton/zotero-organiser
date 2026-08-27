from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from zotero_organiser.cli import main, parser
from zotero_organiser.taxonomy import AVAILABLE_PROFILES, packaged_taxonomy_path


class CliTaxonomyTests(unittest.TestCase):
    def test_taxonomy_subcommands_parse(self):
        p = parser()

        validate_args = p.parse_args(["taxonomy", "validate"])
        self.assertEqual(validate_args.command, "taxonomy")
        self.assertEqual(validate_args.taxonomy_command, "validate")

        path_args = p.parse_args(["taxonomy", "path"])
        self.assertEqual(path_args.command, "taxonomy")
        self.assertEqual(path_args.taxonomy_command, "path")

        init_args = p.parse_args(
            ["taxonomy", "init", "--force", "--from", "/tmp/t.yml", "--dest", "/tmp/out.yml"]
        )
        self.assertEqual(init_args.command, "taxonomy")
        self.assertEqual(init_args.taxonomy_command, "init")
        self.assertTrue(init_args.force)
        self.assertEqual(init_args.source, Path("/tmp/t.yml"))
        self.assertEqual(init_args.dest, Path("/tmp/out.yml"))

        audit_args = p.parse_args(
            ["taxonomy", "audit", "--threshold", "0.85", "--history", "--history-limit", "5"]
        )
        self.assertEqual(audit_args.command, "taxonomy")
        self.assertEqual(audit_args.taxonomy_command, "audit")
        self.assertEqual(audit_args.threshold, 0.85)
        self.assertTrue(audit_args.history)
        self.assertEqual(audit_args.history_limit, 5)

        profiles_list_args = p.parse_args(["taxonomy", "profiles", "list"])
        self.assertEqual(profiles_list_args.command, "taxonomy")
        self.assertEqual(profiles_list_args.taxonomy_command, "profiles")
        self.assertEqual(profiles_list_args.profiles_command, "list")

        profiles_show_args = p.parse_args(["taxonomy", "profiles", "show", "physics-astronomy"])
        self.assertEqual(profiles_show_args.command, "taxonomy")
        self.assertEqual(profiles_show_args.taxonomy_command, "profiles")
        self.assertEqual(profiles_show_args.profiles_command, "show")
        self.assertEqual(profiles_show_args.profile_id, "physics-astronomy")

    def test_taxonomy_profiles_list_command(self):
        buffer = io.StringIO()
        with (
            patch("sys.argv", ["zotero-organiser", "taxonomy", "profiles", "list"]),
            patch("zotero_organiser.cli.load_environment"),
            contextlib.redirect_stdout(buffer),
        ):
            main()

        output = buffer.getvalue()
        for profile_id in AVAILABLE_PROFILES:
            self.assertIn(profile_id, output, f"Profile {profile_id} should be in profiles list")
        self.assertIn("general-scholar", output)
        self.assertIn("physics-astronomy", output)
        self.assertIn("biological-sciences", output)
        self.assertIn("chemistry-molecular-sciences", output)
        self.assertIn("computer-information-sciences", output)
        self.assertIn("indigenous-studies", output)

    def test_taxonomy_profiles_show_all_domains(self):
        for profile_id in AVAILABLE_PROFILES:
            buffer = io.StringIO()
            with (
                patch("sys.argv", ["zotero-organiser", "taxonomy", "profiles", "show", profile_id]),
                patch("zotero_organiser.cli.load_environment"),
                contextlib.redirect_stdout(buffer),
            ):
                main()

            output = buffer.getvalue()
            self.assertIn(f"Profile: {profile_id}", output)
            self.assertIn("Namespaces:", output)
            self.assertIn("role", output)
            self.assertIn("topic", output)
            self.assertIn("system", output)
            self.assertIn("method", output)
            self.assertIn("Total tags:", output)

    def test_taxonomy_profiles_show_with_yml_extension(self):
        buffer = io.StringIO()
        with (
            patch(
                "sys.argv",
                ["zotero-organiser", "taxonomy", "profiles", "show", "physics-astronomy.yml"],
            ),
            patch("zotero_organiser.cli.load_environment"),
            contextlib.redirect_stdout(buffer),
        ):
            main()

        output = buffer.getvalue()
        self.assertIn("Profile: physics-astronomy", output)
        self.assertIn("quantum-physics", output)

    def test_taxonomy_profiles_show_unknown_profile_exits(self):
        with (
            patch(
                "sys.argv",
                ["zotero-organiser", "taxonomy", "profiles", "show", "nonexistent-domain"],
            ),
            patch("zotero_organiser.cli.load_environment"),
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as caught,
        ):
            main()
        self.assertNotEqual(caught.exception.code, 0)

    def test_taxonomy_validate_command(self):
        buffer = io.StringIO()
        with (
            patch("sys.argv", ["zotero-organiser", "taxonomy", "validate"]),
            patch("zotero_organiser.cli.load_environment"),
            contextlib.redirect_stdout(buffer),
        ):
            main()

        output = buffer.getvalue()
        self.assertIn("valid;", output)
        self.assertIn("allowed tags", output)

    def test_taxonomy_path_command(self):
        buffer = io.StringIO()
        with (
            patch("sys.argv", ["zotero-organiser", "taxonomy", "path"]),
            patch("zotero_organiser.cli.load_environment"),
            contextlib.redirect_stdout(buffer),
        ):
            main()

        output = buffer.getvalue().strip()
        self.assertEqual(output, str(packaged_taxonomy_path()))

    def test_taxonomy_init_command(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / "taxonomy.yml"
            buffer = io.StringIO()
            with (
                patch(
                    "sys.argv",
                    [
                        "zotero-organiser",
                        "--config",
                        str(Path(directory) / "config.yml"),
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


if __name__ == "__main__":
    unittest.main()
