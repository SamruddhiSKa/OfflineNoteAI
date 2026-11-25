"""Conservative organization of rough faculty meeting notes."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|[;\n]+")
_DECISION = re.compile(r"\b(resolved|approved|decided|agreed|it was decided|it was resolved)\b", re.I)
_ACTION = re.compile(r"\b(asked|requested|instructed|directed|will|must|shall|should|to submit|to complete|to revise|to prepare|to conduct)\b", re.I)
_DATE = re.compile(
    r"\b(?:held\s+on|meeting\s+on|on)\s+((?:\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+(?:,?\s+\d{4})?)|"
    r"(?:[A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?)|"
    r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    re.I,
)
_TIME = re.compile(r"\bat\s+(\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?))\b", re.I)


@dataclass
class AgendaItem:
    agenda_item: str
    proceedings: str = ""
    resolution: str = ""
    action_plan: str = ""


@dataclass
class MeetingMinutes:
    meeting_title: str = ""
    meeting_number: str = ""
    department: str = ""
    academic_year: str = ""
    reference_number: str = ""
    date: str = ""
    start_time: str = ""
    end_time: str = ""
    venue: str = ""
    coordinator: str = ""
    attendees: str = ""
    absentees: str = ""
    absent_without_intimation: str = ""
    substitutes: str = ""
    opening_remarks: str = ""
    agenda_items: list[AgendaItem] | None = None
    conclusion: str = ""
    next_meeting_date: str = ""
    prepared_by: str = ""
    reviewed_by: str = ""
    approved_by: str = ""
    approval_date: str = ""
    original_notes: str = ""
    corrected_notes: str = ""
    review_required: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def organize_notes(notes: str, corrected_notes: str | None = None) -> MeetingMinutes:
    """Group note sentences without inferring missing facts or decisions.

    Agenda classifications always come from the source notes, never from a
    grammar model rewrite. Every source segment remains in proceedings.
    Resolution/action fields require explicit wording cues. Users should verify
    these conservative cue-based classifications.
    """
    original = notes.strip()
    if not original:
        raise ValueError("Enter or upload meeting notes before generating minutes.")
    corrected = (corrected_notes or original).strip()
    sentences = [s.strip(" \t-•") for s in _SENTENCE_SPLIT.split(original) if s.strip(" \t-•")]
    intro = sentences[0] if sentences and re.search(r"\bmeeting\b", sentences[0], re.I) else ""
    date_match = _DATE.search(intro)
    time_match = _TIME.search(intro)
    venue_match = re.search(r"\bin\s+(.+?)(?=\s+(?:at|on)\b|[,.;]|$)", intro, re.I)
    items: list[AgendaItem] = []
    for sentence in sentences:
        item = AgendaItem(agenda_item=sentence, proceedings=sentence)
        if _DECISION.search(sentence):
            item.resolution = sentence
        if _ACTION.search(sentence):
            item.action_plan = sentence
        items.append(item)
    return MeetingMinutes(
        agenda_items=items,
        date=date_match.group(1).strip() if date_match else "",
        start_time=time_match.group(1).strip() if time_match else "",
        venue=venue_match.group(1).strip() if venue_match else "",
        original_notes=original,
        corrected_notes=corrected,
        review_required=True,
    )
