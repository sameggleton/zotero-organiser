# Third-party notices

zotero-organiser is an independent, unofficial project. It is not affiliated with, endorsed by, or sponsored by the Corporation for Digital Scholarship or the Zotero project. “Zotero” is a registered trademark of the Corporation for Digital Scholarship. See the [Zotero trademark policy](https://www.zotero.org/support/terms/trademark).

This file covers optional extras. Core runtime dependencies (`httpx`, `pydantic`, `PyYAML`) are declared in `pyproject.toml` and are not downloaded as models.

## Optional models

These weights are fetched from Hugging Face during `scripts/setup` or `zotero-organiser models download`. They do not ship in the wheel. Runtime classification loads cached files only.

| Model | Extra | License |
| --- | --- | --- |
| [BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5) | `ranker` / `ranker-gpu` (default `ranking.model`) | MIT |
| [BAAI/bge-base-en-v1.5](https://huggingface.co/BAAI/bge-base-en-v1.5) | `ranker` / `ranker-gpu` | MIT |
| [BAAI/bge-large-en-v1.5](https://huggingface.co/BAAI/bge-large-en-v1.5) | `ranker` / `ranker-gpu` | MIT |
| [tasksource/ModernBERT-base-nli](https://huggingface.co/tasksource/ModernBERT-base-nli) | `local-classifier` (default `local_classifier.model`) | Apache-2.0 |
| [tasksource/ModernBERT-large-nli](https://huggingface.co/tasksource/ModernBERT-large-nli) | `local-classifier` | Apache-2.0 |

BGE v1.5 models are released by BAAI as part of FlagEmbedding (MIT). Tasksource ModernBERT NLI checkpoints are Apache-2.0; the underlying ModernBERT architecture and weights from Answer.AI are also Apache-2.0.

## Optional Python dependencies

| Package | Extra | License |
| --- | --- | --- |
| [fastembed](https://github.com/qdrant/fastembed) | `ranker` | Apache-2.0 |
| [fastembed-gpu](https://github.com/qdrant/fastembed) | `ranker-gpu` | Apache-2.0 |
| [torch](https://github.com/pytorch/pytorch) | `local-classifier` | BSD-style (PyTorch) |
| [transformers](https://github.com/huggingface/transformers) | `local-classifier` | Apache-2.0 |

`ranker` and `ranker-gpu` are mutually exclusive (`onnxruntime` vs `onnxruntime-gpu`). Install extras as `zotero-organiser[ranker,local-classifier]` or `zotero-organiser[ranker-gpu,local-classifier]`. Downstream model licenses still apply when those extras download weights.
