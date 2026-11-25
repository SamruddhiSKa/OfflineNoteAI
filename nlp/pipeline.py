"""Sentence-aware note rewriting and conservative meaning-change review."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from spacy.language import Language

from nlp.model import TextRewriter
from nlp.preprocessing import PreprocessedNotes, preprocess_notes

_NUMBER_OR_UNIT = re.compile(
    r"(?<!\w)[+-]?\d+(?:\.\d+)?(?:\s?(?:%|[A-Za-zµμ°]+))?"
)
_FORMULA = re.compile(
    r"\b[A-Za-z][A-Za-z0-9_]*(?:\s*[=+\-*/^]\s*[A-Za-z0-9_().]+)+"
    r"|\b[A-Za-z]+\d+[A-Za-z0-9]*\b"
)
_NEGATION = re.compile(
    r"\b(?:no|not|never|neither|nor|without|cannot|can't|won't|doesn't|"
    r"didn't|isn't|aren't|wasn't|weren't)\b",
    re.IGNORECASE,
)
_WORD = re.compile(r"\b[\w'-]+\b", re.UNICODE)
_CONTENT_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "by", "for",
    "from", "in", "into", "is", "it", "of", "on", "or", "that", "the", "their",
    "this", "to", "was", "were", "which", "with",
}
_ENTITY_LABELS = {
    "DATE", "EVENT", "FAC", "GPE", "LAW", "LOC", "MONEY", "NORP", "ORDINAL",
    "ORG", "PERCENT", "PERSON", "PRODUCT", "QUANTITY", "TIME", "WORK_OF_ART",
}


@dataclass(frozen=True)
class ImprovementResult:
    original: str
    improved: str
    improved_paragraphs: tuple[str, ...]
    sentence_count: int
    warnings: tuple[str, ...]


def _critical_items(text: str, nlp: Language) -> set[str]:
    items = {
        match.group(0).strip().lower()
        for pattern in (_NUMBER_OR_UNIT, _NEGATION)
        for match in pattern.finditer(text)
    }
    items.update(
        re.sub(r"\s+", "", match.group(0)).casefold()
        for match in _FORMULA.finditer(text)
    )
    for paragraph in text.split("\n\n"):
        doc = nlp(paragraph)
        for entity in doc.ents:
            if entity.label_ in _ENTITY_LABELS:
                items.add(entity.text.casefold())
        for token in doc:
            if token.pos_ in {"NOUN", "PROPN"} and not token.is_stop and token.is_alpha:
                items.add(f"term:{(token.lemma_ or token.text).casefold()}")
    return items


def _review_warnings(original: str, improved: str, nlp: Language) -> tuple[str, ...]:
    warnings: list[str] = []
    original_sentences = preprocess_notes(original, nlp).sentences
    improved_sentences = preprocess_notes(improved, nlp).sentences
    sentence_key = lambda value: re.sub(r"[^\w']+", " ", value.casefold()).strip()
    repeated = {
        sentence for sentence, count in Counter(map(sentence_key, original_sentences)).items()
        if count > 1 and sentence
    }
    remaining = {
        sentence for sentence, count in Counter(map(sentence_key, improved_sentences)).items()
        if count > 1 and sentence
    }
    if repeated and repeated & remaining:
        warnings.append(
            "Repeated sentences remain in the output. Review whether they are "
            "intentional; repetition is preserved automatically."
        )
    lost = _critical_items(original, nlp) - _critical_items(improved, nlp)
    added = _critical_items(improved, nlp) - _critical_items(original, nlp)
    if lost:
        warnings.append(
            "Check preserved technical terms, numbers, formulas, named entities, "
            "or negation: " + ", ".join(sorted(lost))
        )
    if added:
        warnings.append(
            "Review newly introduced technical terms, numbers, formulas, "
            "named entities, or negation: " + ", ".join(sorted(added))
        )

    original_words = {
        word.casefold() for word in _WORD.findall(original)
        if word.casefold() not in _CONTENT_STOPWORDS
    }
    improved_words = {
        word.casefold() for word in _WORD.findall(improved)
        if word.casefold() not in _CONTENT_STOPWORDS
    }
    overlap = len(original_words & improved_words) / max(len(original_words), 1)
    if original_words and overlap < 0.65:
        warnings.append(
            f"Low content-word overlap ({overlap:.0%}); manually verify meaning."
        )
    if not improved.strip():
        warnings.append("The model returned empty text; do not use this result.")
    return tuple(warnings)


def _sentence_chunks(
    paragraphs: tuple[tuple[str, ...], ...],
    rewriter: TextRewriter,
    max_input_tokens: int,
) -> list[list[str]]:
    chunks: list[list[str]] = []
    for paragraph in paragraphs:
        current: list[str] = []
        for sentence in paragraph:
            candidate = " ".join((*current, sentence))
            if rewriter.count_tokens(candidate) > max_input_tokens:
                if not current:
                    raise ValueError(
                        "A sentence exceeds the local model input limit; "
                        "shorten or split it and try again."
                    )
                chunks.append(current)
                current = [sentence]
                if rewriter.count_tokens(sentence) > max_input_tokens:
                    raise ValueError(
                        "A sentence exceeds the local model input limit; "
                        "shorten or split it and try again."
                    )
            else:
                current.append(sentence)
        if current:
            chunks.append(current)
        chunks.append([])  # Paragraph boundary.
    if chunks and not chunks[-1]:
        chunks.pop()
    return chunks


def improve_notes(
    text: str,
    nlp: Language,
    rewriter: TextRewriter,
    *,
    max_input_tokens: int = 384,
    max_new_tokens: int = 256,
) -> ImprovementResult:
    """Rewrite text locally and return resource data and review warnings."""
    if not text.strip():
        raise ValueError("Enter or upload notes before improving them.")

    processed: PreprocessedNotes = preprocess_notes(text, nlp)
    if not processed.sentences:
        raise ValueError("No sentences were found in the supplied notes.")
    chunks = _sentence_chunks(processed.paragraphs, rewriter, max_input_tokens)

    rewrite_warnings: list[str] = []
    paragraphs: list[str] = []
    current_paragraph: list[str] = []
    for chunk in chunks:
        if chunk:
            try:
                current_paragraph.append(
                    rewriter.rewrite(" ".join(chunk), max_new_tokens)
                )
            except Exception as exc:  # noqa: BLE001 - preserve original text on failure
                current_paragraph.append(" ".join(chunk))
                rewrite_warnings.append(
                    f"Grammar correction failed for a segment; original wording retained: {exc}"
                )
        else:
            paragraphs.append(" ".join(current_paragraph))
            current_paragraph = []
    if current_paragraph:
        paragraphs.append(" ".join(current_paragraph))
    improved_paragraphs = tuple(paragraphs)
    improved = "\n\n".join(improved_paragraphs).strip()
    review_warnings = _review_warnings(text, improved, nlp)
    warnings = tuple(rewrite_warnings) + review_warnings
    return ImprovementResult(
        original=text,
        improved=improved,
        improved_paragraphs=improved_paragraphs,
        sentence_count=len(processed.sentences),
        warnings=warnings,
    )
