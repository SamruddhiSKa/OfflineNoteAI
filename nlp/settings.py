"""Runtime configuration for local, offline-first inference."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_DIR = ROOT / "models" / "vennify-t5-base-grammar-correction"
MODEL_DIR = Path(os.environ.get("OFFLINENOTE_MODEL_DIR", DEFAULT_MODEL_DIR)).expanduser()
SPACY_MODEL = os.environ.get("OFFLINENOTE_SPACY_MODEL", "en_core_web_sm")
PROMPT_PREFIX = os.environ.get("OFFLINENOTE_PROMPT_PREFIX", "grammar:")

# Inference always loads local files. These flags also prevent optional library
# components from trying the Hub when a file is missing.
OFFLINE_MODE = os.environ.get("OFFLINENOTE_OFFLINE", "1").strip().lower() not in {
    "0", "false", "no",
}
if OFFLINE_MODE:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
