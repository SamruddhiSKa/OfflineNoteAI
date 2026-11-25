"""Reference-relative lexical metrics; these are not semantic quality scores."""

from __future__ import annotations

import re

_TOKEN = re.compile(r"\b[\w'-]+\b", re.UNICODE)


def word_error_rate(reference: str, hypothesis: str) -> float:
    """Calculate normalized word-level Levenshtein distance."""
    ref = [token.casefold() for token in _TOKEN.findall(reference)]
    hyp = [token.casefold() for token in _TOKEN.findall(hypothesis)]
    if not ref:
        return 0.0 if not hyp else 1.0
    previous = list(range(len(hyp) + 1))
    for row, ref_token in enumerate(ref, start=1):
        current = [row]
        for column, hyp_token in enumerate(hyp, start=1):
            current.append(min(
                current[-1] + 1,
                previous[column] + 1,
                previous[column - 1] + (ref_token != hyp_token),
            ))
        previous = current
    return previous[-1] / len(ref)


def content_word_recall(source: str, hypothesis: str) -> float:
    """Return source-token overlap for a coarse review signal."""
    source_words = {token.casefold() for token in _TOKEN.findall(source)}
    hypothesis_words = {token.casefold() for token in _TOKEN.findall(hypothesis)}
    if not source_words:
        return 1.0
    return len(source_words & hypothesis_words) / len(source_words)
