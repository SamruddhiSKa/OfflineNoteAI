"""Download pinned project models once; inference itself never downloads models."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from huggingface_hub import snapshot_download
import spacy.cli

ROOT = Path(__file__).resolve().parents[1]
MODEL_SPECS = {
    "baseline": {
        "repo": "vennify/t5-base-grammar-correction",
        "revision": "9e4a09d21dca1072a69302df9261289d03c3ed78",
        "directory": "vennify-t5-base-grammar-correction",
        "weights": "pytorch_model.bin",
    },
    "compact": {
        "repo": "xhimanshuz/flan-t5-small-grammar-correction",
        "revision": "c2daa1321acfd4e8bd2c3e1b9d5b4c02a696c0de",
        "directory": "flan-t5-small-grammar-correction",
        "weights": "model.safetensors",
    },
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download local NLP models while internet access is available."
    )
    parser.add_argument(
        "--model",
        choices=tuple(MODEL_SPECS),
        default="baseline",
        help="Choose the default baseline or the smaller CoEdIT GEC comparison model.",
    )
    parser.add_argument(
        "--skip-spacy",
        action="store_true",
        help="Skip downloading the spaCy English pipeline.",
    )
    args = parser.parse_args()

    spec = MODEL_SPECS[args.model]
    model_dir = Path(os.environ.get(
        "OFFLINENOTE_MODEL_DIR", ROOT / "models" / spec["directory"]
    )).expanduser()
    model_dir.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {spec['repo']} ({spec['revision']}) into {model_dir}")
    snapshot_download(
        repo_id=spec["repo"],
        revision=spec["revision"],
        local_dir=str(model_dir),
        allow_patterns=[
            ".gitattributes",
            "README.md",
            "config.json",
            spec["weights"],
            "special_tokens_map.json",
            "spiece.model",
            "tokenizer.json",
            "tokenizer_config.json",
        ],
    )
    if not args.skip_spacy:
        print("Downloading spaCy en_core_web_sm")
        spacy.cli.download("en_core_web_sm")
    print("Model download complete. Verify offline before disconnecting.")


if __name__ == "__main__":
    main()
