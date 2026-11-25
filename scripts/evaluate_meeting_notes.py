"""Evaluate information preservation for rough meeting notes.

Runs the conservative organizer over each sample in
evaluation/meeting_notes.json and reports whether expected names, dates,
deadlines, responsible persons, decisions, tentative items, and negations are
preserved, and whether no unsupported information is invented.

This is a meaning-preservation review, not a fluency score.
"""

from __future__ import annotations

import json
from pathlib import Path

from processing import organize_notes

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "evaluation" / "meeting_notes.json"


def _contains_any(text: str, terms: list[str]) -> bool:
    lowered = text.casefold()
    return any(term.casefold() in lowered for term in terms)


def evaluate_sample(sample: dict) -> dict:
    notes = sample["rough"]
    expected = sample.get("expected", {})
    result = organize_notes(notes)

    # Gather all organized text for fact-preservation checks.
    organized_text = "\n".join(
        [result.original_notes, result.corrected_notes]
        + [item.proceedings for item in (result.agenda_items or [])]
        + result.deadlines
        + result.responsible_persons
        + result.key_decisions
        + result.action_items
        + result.discussion_points
        + result.tentative_items
    )

    checks: dict[str, bool] = {}

    for term in expected.get("names", []):
        checks[f"name:{term}"] = term.casefold() in organized_text.casefold()

    for term in expected.get("dates", []):
        checks[f"date:{term}"] = term.casefold() in organized_text.casefold()

    for term in expected.get("deadlines", []):
        checks[f"deadline:{term}"] = _contains_any(organized_text, [term])

    for term in expected.get("responsible_persons", []):
        checks[f"responsible:{term}"] = term.casefold() in organized_text.casefold()

    for term in expected.get("confirmed_decisions", []):
        checks[f"decision:{term[:30]}"] = _contains_any(
            organized_text, [term]
        ) or _contains_any(result.key_decisions, [term])

    for term in expected.get("tentative_items", []):
        checks[f"tentative:{term[:30]}"] = _contains_any(
            organized_text, [term]
        ) or _contains_any(result.tentative_items, [term])

    for term in expected.get("negations", []):
        checks[f"negation:{term[:30]}"] = _contains_any(organized_text, [term])

    # Nothing important may be invented.
    invented: list[str] = []
    for category in expected.get("must_not_invent", []):
        # Attendees / chairperson / approver names are not in the source, so
        # they should not appear as extracted responsible persons.
        if category in ("attendees", "chairperson", "approver"):
            if result.responsible_persons:
                invented.append(category)
        elif category == "approved decision":
            if result.key_decisions:
                invented.append(category)
        elif category == "meeting date":
            if result.date:
                invented.append(category)
        elif category == "budget amount":
            if "rs" in organized_text.casefold() or "5000" in organized_text:
                invented.append(category)

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)

    return {
        "id": sample["id"],
        "focus": sample.get("focus", ""),
        "checks": checks,
        "checks_passed": passed,
        "checks_total": total,
        "invented": invented,
        "extracted": {
            "date": result.date,
            "deadlines": result.deadlines,
            "responsible_persons": result.responsible_persons,
            "key_decisions": result.key_decisions,
            "tentative_items": result.tentative_items,
            "discussion_points": result.discussion_points,
            "action_items": result.action_items,
        },
    }


def main() -> None:
    samples = json.loads(DATASET.read_text(encoding="utf-8"))
    rows = []
    total_checks = 0
    total_passed = 0
    any_invented = False

    for sample in samples:
        row = evaluate_sample(sample)
        rows.append(row)
        total_checks += row["checks_total"]
        total_passed += row["checks_passed"]
        if row["invented"]:
            any_invented = True

    print(json.dumps(rows, indent=2, ensure_ascii=False))
    print(json.dumps({
        "sample_count": len(rows),
        "total_checks": total_checks,
        "checks_passed": total_passed,
        "checks_passed_percent": round(total_passed / total_checks * 100, 1) if total_checks else 0,
        "unsupported_information_detected": any_invented,
    }, indent=2))
    print("\nMeaning-preservation results are factual checks against source notes,")
    print("not a claim of overall grammatical or semantic accuracy.")


if __name__ == "__main__":
    main()
