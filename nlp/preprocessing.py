"""Text cleanup and sentence segmentation using a local spaCy model."""

from __future__ import annotations

import re
from dataclasses import dataclass

import spacy
from spacy.language import Language


@dataclass(frozen=True)
class PreprocessedNotes:
    paragraphs: tuple[tuple[str, ...], ...]
    sentences: tuple[str, ...]


def load_spacy_pipeline(model_name: str = "en_core_web_sm") -> Language:
    """Load the installed English pipeline without attempting a download."""
    try:
        return spacy.load(model_name)
    except OSError as exc:
        raise RuntimeError(
            f"spaCy model '{model_name}' is not installed. "
            "Run `python -m spacy download en_core_web_sm` before disconnecting."
        ) from exc


def preprocess_notes(text: str, nlp: Language) -> PreprocessedNotes:
    """Normalize line endings and whitespace, retaining paragraph boundaries."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = [
        re.sub(r"[ \t]+", " ", block).strip()
        for block in re.split(r"\n\s*\n", normalized)
    ]
    paragraphs: list[tuple[str, ...]] = []
    for block in blocks:
        if not block:
            continue
        sentences = tuple(
            sentence.text.strip()
            for sentence in nlp(block).sents
            if sentence.text.strip()
        )
        if sentences:
            paragraphs.append(sentences)
    return PreprocessedNotes(
        paragraphs=tuple(paragraphs),
        sentences=tuple(sentence for paragraph in paragraphs for sentence in paragraph),
    )
