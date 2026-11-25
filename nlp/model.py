"""Explicitly local Transformers model loading and generation."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


class TextRewriter(Protocol):
    def count_tokens(self, text: str) -> int: ...

    def rewrite(self, text: str, max_new_tokens: int) -> str: ...


class LocalT5Rewriter:
    """CPU-capable deterministic text generation from a local model directory."""

    def __init__(
        self, tokenizer: object, model: object, prompt_prefix: str = "grammar:"
    ) -> None:
        self.tokenizer = tokenizer
        self.model = model
        self.prompt_prefix = prompt_prefix.strip()
        self.model.eval()

    def count_tokens(self, text: str) -> int:
        prompt = f"{self.prompt_prefix} {text}" if self.prompt_prefix else text
        return len(self.tokenizer.encode(prompt, add_special_tokens=True))

    def rewrite(self, text: str, max_new_tokens: int = 256) -> str:
        prompt = f"{self.prompt_prefix} {text}" if self.prompt_prefix else text
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=False)
        try:
            with torch.inference_mode():
                output_ids = self.model.generate(
                    **inputs,
                    do_sample=False,
                    num_beams=4,
                    max_new_tokens=max_new_tokens,
                )
        except Exception as exc:  # noqa: BLE001 - surface generation errors to caller
            raise RuntimeError(f"Local T5 generation failed: {exc}") from exc
        return self.tokenizer.decode(output_ids[0], skip_special_tokens=True).strip()


def load_local_rewriter(
    model_dir: str | Path,
    *,
    quantize: bool = False,
    prompt_prefix: str = "grammar:",
) -> LocalT5Rewriter:
    """Load model artifacts from disk only; never resolve a Hub identifier.

    ``prompt_prefix`` should match the fine-tuning instruction used by the
    selected checkpoint (for example, ``grammar:`` or ``Fix the grammar:``).
    """
    path = Path(model_dir)
    required_files = ("config.json", "tokenizer_config.json")
    missing = [name for name in required_files if not (path / name).is_file()]
    if not any((path / name).is_file() for name in ("tokenizer.json", "spiece.model")):
        missing.append("tokenizer.json or spiece.model")
    if not any((path / name).is_file() for name in ("pytorch_model.bin", "model.safetensors")):
        missing.append("pytorch_model.bin or model.safetensors")
    if not path.is_dir() or missing:
        raise FileNotFoundError(
            f"Required local model files were not found in '{path}': "
            f"{', '.join(missing) or 'model directory'}. "
            "Run `python scripts/download_models.py` while online."
        )
    tokenizer = AutoTokenizer.from_pretrained(
        str(path), local_files_only=True, use_fast=True
    )
    model = AutoModelForSeq2SeqLM.from_pretrained(
        str(path), local_files_only=True
    )
    if quantize:
        if not hasattr(torch, "ao"):
            raise RuntimeError("This PyTorch build does not provide dynamic quantization.")
        model = torch.ao.quantization.quantize_dynamic(
            model, {torch.nn.Linear}, dtype=torch.qint8
        )
    return LocalT5Rewriter(tokenizer, model, prompt_prefix=prompt_prefix)
