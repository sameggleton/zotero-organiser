from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from zotero_organiser.config import Config
from zotero_organiser.models import (
    EMBEDDING_MODELS,
    NLI_MODELS,
    active_spec,
    compatible_runtimes,
    detect_accelerator,
    download_embedding,
    embedding_cached,
    embedding_spec,
    format_bytes,
    huggingface_hub_dir,
    model_status,
    nli_cached,
    nli_spec,
    recommended_embedding_size,
    recommended_nli_size,
)


def base_config(root: Path) -> dict:
    return {
        "zotero": {},
        "attachments": {"path": root / "storage"},
        "backup": {"repository": str(root / "restic"), "prewrite_dir": root / "prewrite"},
        "state": {"database": root / "state.sqlite"},
    }


class ModelsTests(unittest.TestCase):
    def test_catalog_ids_and_nli_entailment_contract(self):
        self.assertEqual(
            [spec.model for spec in EMBEDDING_MODELS],
            ["BAAI/bge-small-en-v1.5", "BAAI/bge-base-en-v1.5", "BAAI/bge-large-en-v1.5"],
        )
        self.assertTrue(all(spec.entailment for spec in NLI_MODELS))
        self.assertEqual(nli_spec("small").model, "tasksource/ModernBERT-base-nli")
        self.assertEqual(nli_spec("large").model, "tasksource/ModernBERT-large-nli")
        self.assertEqual(embedding_spec("small").model, "BAAI/bge-small-en-v1.5")

    def test_recommended_pair_by_accelerator(self):
        self.assertEqual(recommended_embedding_size("cpu"), "small")
        self.assertEqual(recommended_nli_size("cpu"), "small")
        self.assertEqual(recommended_embedding_size("mps"), "medium")
        self.assertEqual(recommended_nli_size("mps"), "small")
        self.assertEqual(recommended_embedding_size("cuda"), "medium")
        self.assertEqual(recommended_nli_size("cuda"), "large")
        self.assertEqual(recommended_nli_size("rocm"), "large")

    def test_active_spec_prefers_recommended_then_largest_selected(self):
        selected = [embedding_spec("small"), embedding_spec("large")]
        self.assertEqual(active_spec(selected, "small").size, "small")
        self.assertEqual(active_spec(selected, "medium").size, "large")

    def test_detect_accelerator_never_offers_cuda_on_darwin(self):
        info = detect_accelerator(system="Darwin", machine="arm64", which=lambda _name: None)
        self.assertEqual(info.kind, "mps")
        runtimes = compatible_runtimes(info, system="Darwin")
        self.assertEqual([item.kind for item in runtimes], ["mps", "cpu"])
        x86 = detect_accelerator(
            system="Darwin", machine="x86_64", which=lambda _name: "/usr/bin/nvidia-smi"
        )
        self.assertEqual(x86.kind, "cpu")
        self.assertNotIn("cuda", [item.kind for item in compatible_runtimes(x86, system="Darwin")])

    def test_linux_nvidia_and_rocm_detection(self):
        info = detect_accelerator(
            system="Linux",
            machine="x86_64",
            which=lambda name: "/usr/bin/nvidia-smi" if name == "nvidia-smi" else None,
            nvidia_smi_output="CUDA Version: 12.8",
        )
        self.assertEqual(info.kind, "cuda")
        self.assertEqual(info.cuda_backend, "cu128")
        runtimes = compatible_runtimes(info, system="Linux")
        self.assertEqual(runtimes[0].kind, "cuda")
        self.assertEqual(runtimes[0].extras, "ranker-gpu,local-classifier")
        self.assertEqual(runtimes[0].ranking_backend, "fastembed-gpu")
        self.assertEqual(runtimes[0].torch_backend, "cu128")
        self.assertIn("cpu", [item.kind for item in runtimes])

        rocm = detect_accelerator(
            system="Linux",
            machine="x86_64",
            which=lambda name: "/usr/bin/rocminfo" if name == "rocminfo" else None,
        )
        self.assertEqual(rocm.kind, "rocm")
        rocm_runtimes = compatible_runtimes(rocm, system="Linux")
        self.assertEqual(rocm_runtimes[0].kind, "rocm")
        self.assertEqual(rocm_runtimes[0].ranking_backend, "fastembed-cpu")
        self.assertNotIn("cuda", [item.kind for item in rocm_runtimes])

    def test_cache_probe_and_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / "ranker"
            model_dir = cache / "models--BAAI--bge-small-en-v1.5" / "snapshots" / "abc"
            model_dir.mkdir(parents=True)
            (model_dir / "model.onnx").write_bytes(b"onnx")
            self.assertTrue(embedding_cached("BAAI/bge-small-en-v1.5", cache))
            self.assertFalse(embedding_cached("BAAI/bge-large-en-v1.5", cache))
            hub = root / "hub"
            nli_dir = hub / "models--tasksource--ModernBERT-base-nli" / "snapshots" / "abc"
            nli_dir.mkdir(parents=True)
            (nli_dir / "config.json").write_text("{}")
            self.assertTrue(nli_cached("tasksource/ModernBERT-base-nli", hub))
            raw = base_config(root)
            raw["ranking"] = {
                "enabled": True,
                "cache_dir": str(cache),
                "model": "BAAI/bge-small-en-v1.5",
            }
            raw["local_classifier"] = {
                "enabled": True,
                "model": "tasksource/ModernBERT-base-nli",
            }
            with patch("zotero_organiser.models.huggingface_hub_dir", return_value=hub):
                statuses = model_status(Config.model_validate(raw))
            self.assertTrue(all(item.cached for item in statuses))

    def test_cache_probe_ignores_incomplete_hub_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            hub = Path(directory) / "hub"
            repo = hub / "models--tasksource--ModernBERT-base-nli"
            missing = repo / ".no_exist"
            missing.mkdir(parents=True)
            (missing / "config.json").write_text("{}")
            (repo / "config.json.lock").write_bytes(b"lock")
            self.assertFalse(nli_cached("tasksource/ModernBERT-base-nli", hub))

            snapshot = repo / "snapshots" / "abc"
            snapshot.mkdir(parents=True)
            (snapshot / "config.json").write_bytes(b"")
            self.assertFalse(nli_cached("tasksource/ModernBERT-base-nli", hub))

            ranker = Path(directory) / "ranker"
            incomplete = ranker / "models--BAAI--bge-small-en-v1.5"
            incomplete.mkdir(parents=True)
            (incomplete / "model.onnx.lock").write_bytes(b"lock")
            (incomplete / ".no_exist" / "model.onnx").parent.mkdir(parents=True)
            (incomplete / ".no_exist" / "model.onnx").write_bytes(b"onnx")
            self.assertFalse(embedding_cached("BAAI/bge-small-en-v1.5", ranker))

    def test_huggingface_hub_dir_honours_hub_cache_env(self):
        with patch.dict(os.environ, {"HOME": "/Users/test"}, clear=True):
            self.assertEqual(huggingface_hub_dir(), Path("/Users/test/.cache/huggingface/hub"))
        with patch.dict(os.environ, {"HF_HOME": "/custom/hf"}, clear=True):
            self.assertEqual(huggingface_hub_dir(), Path("/custom/hf/hub"))
        with patch.dict(
            os.environ,
            {"HUGGINGFACE_HUB_CACHE": "/legacy/hub", "HF_HOME": "/ignored/hf"},
            clear=True,
        ):
            self.assertEqual(huggingface_hub_dir(), Path("/legacy/hub"))
        with patch.dict(
            os.environ,
            {
                "HF_HUB_CACHE": "~/custom-hub",
                "HUGGINGFACE_HUB_CACHE": "/ignored/legacy",
                "HF_HOME": "/ignored/hf",
                "HOME": "/Users/test",
            },
            clear=True,
        ):
            self.assertEqual(huggingface_hub_dir(), Path("/Users/test/custom-hub"))

    def test_format_bytes(self):
        self.assertEqual(format_bytes(130 * 1024 * 1024), "130 MB")
        self.assertEqual(format_bytes(1200 * 1024 * 1024), "1.2 GB")

    def test_download_embedding_uses_networked_backend(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("zotero_organiser.models.FastEmbedBackend") as backend_type:
                backend_type.return_value.embed.return_value = [[0.1]]
                download_embedding("BAAI/bge-small-en-v1.5", Path(directory), gpu=True)
            backend_type.assert_called_once_with(
                "BAAI/bge-small-en-v1.5",
                Path(directory),
                gpu=True,
                local_files_only=False,
            )


if __name__ == "__main__":
    unittest.main()
