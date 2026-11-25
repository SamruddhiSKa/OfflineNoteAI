"""Run model outputs against the small manually reviewed reference set."""

from __future__ import annotations

import json
from pathlib import Path

from evaluation.metrics import content_word_recall, word_error_rate
from nlp.model import load_local_rewriter
from nlp.settings import MODEL_DIR, PROMPT_PREFIX

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "evaluation" / "sample_notes.json"


def main() -> None:
    samples = json.loads(DATASET.read_text(encoding="utf-8"))
    rewriter = load_local_rewriter(MODEL_DIR, prompt_prefix=PROMPT_PREFIX)
    rows = []
    for sample in samples:
        output = rewriter.rewrite(sample["rough"])
        rows.append({
            "id": sample["id"],
            "focus": sample.get("focus", "grammar and terminology"),
            "output": output,
            "reference_word_error_rate": round(
                word_error_rate(sample["reference"], output), 3
            ),
            "critical_terms_preserved": all(
                term.casefold() in output.casefold()
                for term in sample.get("critical_terms", [])
            ),
            "source_content_word_recall": round(
                content_word_recall(sample["rough"], output), 3
            ),
        })
    print(json.dumps(rows, indent=2, ensure_ascii=False))
    print(json.dumps({
        "sample_count": len(rows),
        "mean_reference_word_error_rate": round(
            sum(row["reference_word_error_rate"] for row in rows) / len(rows), 3
        ),
        "mean_source_content_word_recall": round(
            sum(row["source_content_word_recall"] for row in rows) / len(rows), 3
        ),
        "critical_term_checks_passed": sum(
            row["critical_terms_preserved"] for row in rows
        ),
        "warning": "Lexical proxies only; output fluency and similarity do not establish meaning preservation or coherence.",
    }, indent=2))
    print(
        "\nLexical metrics are reference-relative proxies, not a validated grammar "
        "or semantic-understanding score. Review outputs manually."
    )


if __name__ == "__main__":
    main()
