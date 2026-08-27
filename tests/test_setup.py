from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from zotero_organiser.classify import Classification, Classifier
from zotero_organiser.config import Config
from zotero_organiser.models import AcceleratorInfo
from zotero_organiser.ranking import Candidate, Ranking
from zotero_organiser.setup import _default_paths, _run, main
from zotero_organiser.taxonomy import packaged_taxonomy_path
from zotero_organiser.terminal import Terminal


class SetupTests(unittest.TestCase):
    def terminal(self, answers: list[str], output: io.StringIO | None = None) -> Terminal:
        leftover = list(answers)
        buf = output or io.StringIO()

        def input_fn(prompt: str) -> str:
            if not leftover:
                raise AssertionError(f"no scripted answer for: {prompt}")
            return leftover.pop(0)

        return Terminal(input_fn=input_fn, output=buf)

    def wizard_answers(
        self,
        config_path: Path,
        *,
        method: str = "4",
        runtime: str = "",
        embeddings: str = "",
        nli: str = "",
        api_key: str = "",
        install: str = "n",
        download: str = "n",
        restic: str = "",
        doctor: str = "",
        profile: str = "",
        test: str = "",
    ) -> list[str]:
        answers = [str(config_path), "", "", "", "", method]
        if method in {"1", "3"}:
            answers.extend([runtime, embeddings, nli])
        if method in {"2", "3"}:
            answers.append(api_key)
        answers.extend(["", "n", install])
        if method in {"1", "3"}:
            answers.append(download)
        answers.extend([restic, doctor, profile, test])
        return answers

    def run_wizard(
        self,
        answers: list[str],
        *,
        run=None,
        which: str | None = "/usr/bin/uv",
        system: str = "Darwin",
        accelerator: AcceleratorInfo | None = None,
    ):
        output = io.StringIO()
        ui = self.terminal(answers, output)
        info = accelerator or AcceleratorInfo("cpu", "CPU")
        with (
            patch("zotero_organiser.setup.Terminal", return_value=ui),
            patch("zotero_organiser.setup.shutil.which", return_value=which),
            patch("zotero_organiser.setup.platform.system", return_value=system),
            patch(
                "zotero_organiser.setup.platform.platform",
                return_value="Linux-Ubuntu-24.04" if system == "Linux" else "macOS-15",
            ),
            patch("zotero_organiser.setup.detect_accelerator", return_value=info),
            patch("zotero_organiser.setup.download_models") as mocked_download,
            patch("zotero_organiser.setup.subprocess.run") as mocked_run,
        ):
            mocked_run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")
            if run is not None:
                mocked_run.side_effect = run
            code = main()
        return code, output.getvalue(), mocked_run, mocked_download

    def test_setup_keeps_existing_user_taxonomy(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.yml"
            existing = config_path.with_name("taxonomy.yml")
            existing.write_text("user owned\n")
            code, output, _mocked, _download = self.run_wizard(self.wizard_answers(config_path))
            self.assertEqual(code, 0)
            self.assertEqual(existing.read_text(), "user owned\n")
            self.assertIn("Keeping existing taxonomy", output)
            raw = yaml.safe_load(config_path.read_text())
            self.assertEqual(Path(raw["taxonomy"]["path"]), existing)

    def test_missing_uv_exits_nonzero_from_python_setup(self):
        code, output, _run_mock, _download = self.run_wizard([], which=None)
        self.assertEqual(code, 1)
        self.assertIn("uv is required", output)

    def test_setup_script_exits_nonzero_when_uv_missing(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "setup"
        with tempfile.TemporaryDirectory() as directory:
            bin_dir = Path(directory)
            for name in ("uname", "grep"):
                found = shutil.which(name)
                if found:
                    (bin_dir / name).symlink_to(found)
            result = subprocess.run(
                ["/bin/sh", str(script)],
                capture_output=True,
                text=True,
                env={**os.environ, "PATH": str(bin_dir)},
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("uv is required", result.stderr)

    def test_run_returns_false_on_failure_and_does_not_continue_safely(self):
        output = io.StringIO()
        ui = Terminal(input_fn=lambda _: "", output=output)
        with patch(
            "zotero_organiser.setup.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, ["uv"]),
        ):
            self.assertFalse(_run(ui, ["uv", "tool", "install", "--editable", "/repo"]))
        self.assertNotIn("continuing safely", output.getvalue())
        with patch("zotero_organiser.setup.subprocess.run") as mocked:
            mocked.return_value = subprocess.CompletedProcess([], 0)
            self.assertTrue(_run(ui, ["uv", "tool", "install", "--editable", "/repo"]))

    def test_linux_default_attachments_are_local_zotero_storage(self):
        with patch("zotero_organiser.setup.Path.home", return_value=Path("/home/user")):
            attachments, *_ = _default_paths()
        self.assertEqual(attachments, Path("/home/user/Zotero/storage"))
        self.assertNotEqual(attachments, Path("/srv/zotero-webdav"))

    def test_install_uses_project_root_not_cwd(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.yml"
            project_root = Path(directory) / "project"
            project_root.mkdir()
            cwd = Path(directory) / "elsewhere"
            cwd.mkdir()
            previous = Path.cwd()
            try:
                os.chdir(cwd)
                with patch.dict(os.environ, {"ZOTERO_ORGANISER_PROJECT_ROOT": str(project_root)}):
                    code, _output, mocked_run, _download = self.run_wizard(
                        self.wizard_answers(config_path, install="y"),
                    )
            finally:
                os.chdir(previous)
        self.assertEqual(code, 0)
        mocked_run.assert_called_once()
        command = mocked_run.call_args.args[0]
        self.assertEqual(command[:4], ["uv", "tool", "install", "--editable"])
        self.assertEqual(Path(command[4]).resolve(), project_root.resolve())
        self.assertNotEqual(command[4], ".")

    def test_install_failure_aborts(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.yml"
            code, output, _mocked_run, _download = self.run_wizard(
                self.wizard_answers(config_path, install="y"),
                run=subprocess.CalledProcessError(1, ["uv"]),
            )
        self.assertEqual(code, 1)
        self.assertIn("Install failed", output)
        self.assertNotIn("continuing safely", output)

    def test_restic_failure_aborts(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.yml"
            code, output, _mocked_run, _download = self.run_wizard(
                self.wizard_answers(config_path, restic="y"),
                run=subprocess.CalledProcessError(1, ["restic"]),
            )
        self.assertEqual(code, 1)
        self.assertIn("Restic initialization failed", output)
        self.assertNotIn("continuing safely", output)

    def test_optional_deps_use_extras_not_ad_hoc_with(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.yml"
            project_root = Path(directory) / "project"
            project_root.mkdir()
            with patch.dict(os.environ, {"ZOTERO_ORGANISER_PROJECT_ROOT": str(project_root)}):
                code, _output, mocked_run, _download = self.run_wizard(
                    self.wizard_answers(config_path, method="1", install="y", download="n"),
                )
        self.assertEqual(code, 0)
        mocked_run.assert_called_once()
        command = mocked_run.call_args.args[0]
        joined = " ".join(command)
        self.assertIn("[ranker,local-classifier]", joined)
        self.assertNotIn("ranker-gpu", joined)
        self.assertNotIn("--with", joined)
        self.assertNotIn("fastembed", joined)
        self.assertNotIn("transformers", joined)

    def test_cuda_runtime_installs_ranker_gpu_and_pins_torch(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.yml"
            project_root = Path(directory) / "project"
            project_root.mkdir()
            python = Path(directory) / "tools" / "zotero-organiser" / "bin" / "python"
            python.parent.mkdir(parents=True)
            python.write_text("")
            with (
                patch.dict(os.environ, {"ZOTERO_ORGANISER_PROJECT_ROOT": str(project_root)}),
                patch("zotero_organiser.setup._tool_python", return_value=python),
            ):
                code, _output, mocked_run, _download = self.run_wizard(
                    self.wizard_answers(config_path, method="1", install="y", download="n"),
                    system="Linux",
                    accelerator=AcceleratorInfo("cuda", "NVIDIA GPU", cuda_backend="cu126"),
                )
        self.assertEqual(code, 0)
        commands = [" ".join(call.args[0]) for call in mocked_run.call_args_list]
        self.assertTrue(any("[ranker-gpu,local-classifier]" in command for command in commands))
        self.assertTrue(
            any(
                "--torch-backend cu126" in command or command.endswith("cu126")
                for command in commands
            )
        )
        self.assertTrue(
            any(command.split()[:3] == ["uv", "pip", "install"] for command in commands)
        )

    def test_local_first_config_can_produce_tags(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.yml"
            code, output, _mocked_run, mocked_download = self.run_wizard(
                self.wizard_answers(config_path, method="1"),
            )
            text = config_path.read_text()
            taxonomy_path = config_path.with_name("taxonomy.yml")
            taxonomy_text = taxonomy_path.read_text()
        self.assertEqual(code, 0)
        self.assertNotIn("Doctor completed", output)
        self.assertNotIn("Test assistant completed", output)
        self.assertIn("WebDAV example: /srv/zotero-webdav", text)
        raw = yaml.safe_load(text)
        self.assertEqual(Path(raw["taxonomy"]["path"]), taxonomy_path)
        self.assertEqual(taxonomy_text, packaged_taxonomy_path().read_text())
        self.assertNotIn("allow_collection_changes", raw["safety"])
        self.assertEqual(
            raw["safety"],
            {
                "write_enabled": False,
                "require_backup": True,
                "only_new_items": True,
                "allow_tag_removal": False,
                "max_items_per_cycle": 5,
            },
        )
        self.assertTrue(raw["ranking"]["enabled"])
        self.assertEqual(raw["ranking"]["mode"], "shortlist")
        self.assertEqual(raw["ranking"]["backend"], "fastembed-cpu")
        self.assertEqual(raw["ranking"]["model"], "BAAI/bge-small-en-v1.5")
        self.assertTrue(raw["local_classifier"]["enabled"])
        self.assertEqual(raw["local_classifier"]["mode"], "primary")
        self.assertEqual(raw["local_classifier"]["model"], "tasksource/ModernBERT-base-nli")
        self.assertFalse(raw["local_classifier"]["fallback_to_remote"])
        self.assertFalse(raw["classification"]["enabled"])
        mocked_download.assert_not_called()
        config = Config.model_validate(raw)
        taxonomy = MagicMock()
        ranker = MagicMock()
        ranker.config = config.ranking
        ranker.rank.return_value = Ranking(
            (Candidate("topic/screening", 0.9, 0.4, frozenset({"dense"})),)
        )
        local = MagicMock()
        local.config = config.local_classifier
        local.score.return_value = {"topic/screening": 0.95}
        classifier = Classifier(config.classification, taxonomy, ranker, local)
        expected = Classification.model_validate(
            {"tags": [{"tag": "topic/screening", "confidence": 0.95}]}
        )
        classifier._local_classification = MagicMock(return_value=expected)
        result = classifier.classify(
            {"key": "ABC", "data": {"title": "Paper", "tags": [], "collections": []}}
        )
        self.assertEqual(result.tags[0].tag, "topic/screening")

    def test_remote_only_asks_for_api_key_and_skips_extras(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.yml"
            project_root = Path(directory) / "project"
            project_root.mkdir()
            with patch.dict(os.environ, {"ZOTERO_ORGANISER_PROJECT_ROOT": str(project_root)}):
                code, output, mocked_run, mocked_download = self.run_wizard(
                    self.wizard_answers(config_path, method="2", install="y"),
                )
            raw = yaml.safe_load(config_path.read_text())
        self.assertEqual(code, 0)
        self.assertTrue(raw["classification"]["enabled"])
        self.assertEqual(raw["classification"]["api_key_env"], "OPENAI_API_KEY")
        self.assertFalse(raw["ranking"]["enabled"])
        self.assertFalse(raw["local_classifier"]["enabled"])
        self.assertIn("will not be requested or displayed", output)
        command = mocked_run.call_args.args[0]
        self.assertNotIn("[", command[-1])
        mocked_download.assert_not_called()

    def test_local_fallback_enables_remote_and_downloads_selected_sizes(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.yml"
            code, _output, _mocked_run, mocked_download = self.run_wizard(
                self.wizard_answers(
                    config_path,
                    method="3",
                    embeddings="1,3",
                    nli="2",
                )
            )
            raw = yaml.safe_load(config_path.read_text())
        self.assertEqual(code, 0)
        self.assertTrue(raw["classification"]["enabled"])
        self.assertTrue(raw["local_classifier"]["fallback_to_remote"])
        self.assertEqual(raw["ranking"]["model"], "BAAI/bge-small-en-v1.5")
        self.assertEqual(raw["local_classifier"]["model"], "tasksource/ModernBERT-large-nli")
        mocked_download.assert_not_called()

    def test_model_prefetch_uses_tool_env_after_install(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.yml"
            python = Path(directory) / "tools" / "zotero-organiser" / "bin" / "python"
            python.parent.mkdir(parents=True)
            python.write_text("")
            with patch("zotero_organiser.setup._tool_python", return_value=python):
                code, output, mocked_run, mocked_download = self.run_wizard(
                    self.wizard_answers(
                        config_path,
                        method="3",
                        embeddings="1,3",
                        nli="2",
                        install="y",
                        download="y",
                    )
                )
        self.assertEqual(code, 0)
        self.assertIn("Downloaded selected local models.", output)
        mocked_download.assert_not_called()
        prefetch = next(
            call.args[0]
            for call in mocked_run.call_args_list
            if len(call.args[0]) >= 4 and call.args[0][1] == "-c"
        )
        self.assertEqual(prefetch[0], str(python))
        self.assertIn("from zotero_organiser.models import download_models", prefetch[2])
        payload = json.loads(prefetch[3])
        self.assertEqual(
            [item[0] for item in payload["embeddings"]],
            ["BAAI/bge-small-en-v1.5", "BAAI/bge-large-en-v1.5"],
        )
        self.assertEqual(payload["nli_models"], ["tasksource/ModernBERT-large-nli"])
        cache_dir = str(Path.home() / ".cache/zotero-organiser/ranker")
        self.assertTrue(
            all(item[1] == cache_dir and item[2] is False for item in payload["embeddings"])
        )
        joined = [" ".join(call.args[0]) for call in mocked_run.call_args_list]
        self.assertFalse(any(command.startswith("uv run ") for command in joined))

    def test_model_download_skipped_when_install_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.yml"
            code, output, mocked_run, mocked_download = self.run_wizard(
                self.wizard_answers(config_path, method="1", install="n", download="y"),
            )
        self.assertEqual(code, 0)
        mocked_download.assert_not_called()
        self.assertIn("Install the command first", output)
        self.assertNotIn("Downloaded selected local models.", output)
        commands = [call.args[0] for call in mocked_run.call_args_list]
        self.assertFalse(any(len(command) >= 2 and command[1] == "-c" for command in commands))
        self.assertFalse(any("models" in command and "download" in command for command in commands))

    def test_model_download_failure_aborts(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.yml"
            python = Path(directory) / "tools" / "zotero-organiser" / "bin" / "python"
            python.parent.mkdir(parents=True)
            python.write_text("")

            def run(command, **_kwargs):
                if len(command) >= 2 and command[1] == "-c":
                    raise subprocess.CalledProcessError(1, command)
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            with patch("zotero_organiser.setup._tool_python", return_value=python):
                code, output, _mocked_run, mocked_download = self.run_wizard(
                    self.wizard_answers(config_path, method="1", install="y", download="y"),
                    run=run,
                )
        self.assertEqual(code, 1)
        mocked_download.assert_not_called()
        self.assertIn("Model download failed", output)
        self.assertNotIn("continuing safely", output)

    def test_doctor_profile_test_use_installed_tool(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.yml"
            python = Path(directory) / "tools" / "zotero-organiser" / "bin" / "python"
            python.parent.mkdir(parents=True)
            python.write_text("")
            with patch("zotero_organiser.setup._tool_python", return_value=python):
                code, output, mocked_run, _download = self.run_wizard(
                    self.wizard_answers(
                        config_path,
                        method="1",
                        install="y",
                        download="n",
                        doctor="y",
                        profile="y",
                        test="y",
                    )
                )
        self.assertEqual(code, 0)
        self.assertIn("Doctor completed.", output)
        self.assertIn("Test assistant completed.", output)
        prefix = [str(python), "-m", "zotero_organiser.cli"]
        commands = [call.args[0] for call in mocked_run.call_args_list]
        self.assertTrue(
            any(command[:3] == prefix and command[-1] == "doctor" for command in commands)
        )
        self.assertTrue(
            any(
                command[:3] == prefix and command[-2:] == ["profile", "build"]
                for command in commands
            )
        )
        self.assertTrue(
            any(command[:3] == prefix and command[-1] == "test" for command in commands)
        )
        self.assertFalse(any(command[:2] == ["uv", "run"] for command in commands))

    def test_reusing_remote_only_config_skips_models_download_hint(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.yml"
            config_path.write_text(
                yaml.safe_dump(
                    {
                        "classification": {"enabled": True},
                        "ranking": {"enabled": False},
                        "local_classifier": {"enabled": False},
                    }
                )
            )
            original = config_path.read_text()
            code, output, _mocked_run, _download = self.run_wizard([str(config_path), "1"])
            reused = config_path.read_text()
        self.assertEqual(code, 0)
        self.assertEqual(reused, original)
        self.assertIn(f"Reusing {config_path}; no configuration changed.", output)
        self.assertNotIn("zotero-organiser models download", output)

    def test_reusing_local_enabled_config_prints_models_download_hint(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.yml"
            config_path.write_text(
                yaml.safe_dump(
                    {
                        "ranking": {"enabled": True},
                        "local_classifier": {"enabled": True},
                    }
                )
            )
            original = config_path.read_text()
            code, output, _mocked_run, _download = self.run_wizard([str(config_path), "1"])
            reused = config_path.read_text()
        self.assertEqual(code, 0)
        self.assertEqual(reused, original)
        self.assertIn(f"Reusing {config_path}; no configuration changed.", output)
        self.assertIn(
            "To download local models later, run: zotero-organiser models download", output
        )


if __name__ == "__main__":
    unittest.main()
