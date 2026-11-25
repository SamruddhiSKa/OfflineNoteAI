"""Conservative organization of rough faculty meeting notes."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

# ---------------------------------------------------------------------------
# Sentence splitting
# ---------------------------------------------------------------------------

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+|\n+")

_ABBREVIATIONS = re.compile(
    r"\b(?:Dr|Prof|Professor|Mr|Mrs|Ms|St|Mt|vs|etc|e\.g|i\.e|approx)\.",
    re.I,
)


# ---------------------------------------------------------------------------
# spaCy (optional, for noun-phrase title extraction)
# ---------------------------------------------------------------------------

_SPACY_NLP = None
_SPACY_NLP_ERROR = None


def _get_spacy_nlp():
    """Lazily load spaCy for noun-phrase extraction."""
    global _SPACY_NLP, _SPACY_NLP_ERROR
    if _SPACY_NLP is not None or _SPACY_NLP_ERROR is not None:
        return _SPACY_NLP, _SPACY_NLP_ERROR
    try:
        import spacy

        _SPACY_NLP = spacy.load("en_core_web_sm")
    except Exception:  # noqa: BLE001
        _SPACY_NLP_ERROR = True
        _SPACY_NLP = None
    return _SPACY_NLP, _SPACY_NLP_ERROR


def _extract_topic_title_from_noun_phrases(texts: list[str]) -> str:
    """Extract a concise topic title from noun phrases in the given texts."""
    nlp, _ = _get_spacy_nlp()
    if nlp is None:
        return ""
    combined = " ".join(texts)
    doc = nlp(combined)
    candidates = []
    for chunk in doc.noun_chunks:
        phrase = chunk.text.strip()
        if not phrase:
            continue
        words = phrase.split()
        if len(words) < 2 or len(words) > 6:
            continue
        stop_ratio = sum(
            1 for t in chunk if t.is_stop or t.pos_ == "PRON"
        ) / len(chunk)
        if stop_ratio > 0.5:
            continue
        candidates.append(phrase)
    if candidates:
        return max(candidates, key=len)
    return ""


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences while protecting common abbreviations.

    Protects abbreviation periods so they don't trigger sentence splits, then
    restores them after splitting.  Also merges abbreviation fragments
    (e.g. "Dr" + "Smith said...") that result from splitting.
    """
    protected = _ABBREVIATIONS.sub(
        lambda m: m.group(0).replace(".", "<DOT>"), text
    )
    parts = _SENTENCE_SPLIT.split(protected)
    sentences = [p.replace("<DOT>", ".").strip(" \t-•") for p in parts if p.strip(" \t-•")]
    # Capitalize first letter of each sentence after the first
    result = []
    for i, s in enumerate(sentences):
        if i > 0 and s and s[0].islower():
            s = s[0].upper() + s[1:]
        result.append(s)
    return result


# ---------------------------------------------------------------------------
# Classification patterns
# ---------------------------------------------------------------------------

_DECISION = re.compile(
    r"\b(resolved|approved|decided|agreed|it was decided|it was resolved|"
    r"will be made|will be selected|will be decided|"
    r"(?:is|was|are|were)\s+(?:fixed|scheduled)\s+for)\b",
    re.I,
)
_DECISION_LABEL = re.compile(r"^\s*(?:decision|resolution)\s*:\s*", re.I)
_ACTION_LABEL = re.compile(r"^\s*(?:action|task|follow-up|follow up)\s*:\s*", re.I)
_ACTION = re.compile(
    r"\b(asked|requested|instructed|directed|will|must|shall|should|to submit|to complete|to revise|to prepare|to conduct)\b",
    re.I,
)
_ACTION_VERBS = re.compile(
    r"\b(?:(?:will|must|shall|should|was\s+asked\s+to|were\s+asked\s+to|"
    r"was\s+requested\s+to|were\s+requested\s+to)\s+"
    r"(?:prepare|circulate|coordinate|check|contact|submit|upload|record|"
    r"display|recommend|arrange|conduct|finish|complete|revise|send|update|call|"
    r"test|collect|keep|show|publish|replace|repair|purchase|deploy|order|"
    r"verify|maintain|include|review|share)"
    r"|(?:will|must|shall|should)\s+be\s+ready"
    r"|(?:will|must|shall|should)\s+be\s+(?:reviewed|checked|completed|verified|"
    r"maintained|displayed|submitted|circulated|scheduled)"
    r"|(?:asked|requested|instructed|directed)\s+\w+\s+to\s+"
    r"(?:prepare|circulate|coordinate|check|contact|submit|upload|record|"
    r"display|recommend|arrange|conduct|finish|complete|revise|send|update|"
    r"call|test|collect|keep|show|publish|replace|repair|purchase|deploy|"
    r"order|verify|maintain|include|review|share))\b",
    re.I,
)
_IMPERATIVE_ACTION = re.compile(
    r"^\s*(?:finish|complete|submit|upload|record|prepare|circulate|coordinate|"
    r"check|contact|confirm|display|recommend|arrange|conduct|revise|send|update|call|"
    r"test|collect|keep|show|publish|replace|repair|purchase|deploy|order|"
    r"verify|maintain|include|review|share)\b",
    re.I,
)
_ASSIGNED_TO_ACTION = re.compile(
    r"\b(?:Dr|Prof|Professor|Mr|Mrs|Ms)?\.?\s+[A-Z][a-z]+"
    r"(?:\s+[A-Z][a-z]+)?\s+to\s+"
    r"(?:prepare|circulate|coordinate|check|contact|submit|upload|record|"
    r"display|recommend|arrange|conduct|finish|complete|revise|send|update|"
    r"call|collect|keep|show|publish|replace|repair|purchase|deploy|order|"
    r"verify|maintain|include|review|share)\b",
)
_RESPONSIBLE = re.compile(
    r"\b([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+"
    r"(?:will|must|shall|should)\s+",
    re.I,
)
_RESPONSIBLE_ASKED = re.compile(
    r"(?:asked|requested|instructed|directed|told)\s+"
    r"([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+to\s+",
    re.I,
)
_RESPONSIBLE_WAS_ASKED = re.compile(
    r"([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+was\s+asked\s+to\s+",
    re.I,
)
_RESPONSIBLE_MIXED = re.compile(
    r"\b([A-Za-z]+\s+[a-z]+)\s+"
    r"(?:will|must|shall|should|(?:was|were)\s+(?:asked|requested))\b",
    re.I,
)
_RESPONSIBLE_TENTATIVE = re.compile(
    r"([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(?:may|might|could|can)\s+",
    re.I,
)
_TENTATIVE = re.compile(
    r"\b(?:maybe|perhaps|possibly|probably|tentatively|might|could|may|"
    r"suggested|proposed|considering|planning|intends|likely|pending)\b",
    re.I,
)
_SUGGESTION = re.compile(
    r"\b(?:suggested|suggestion|proposed|proposal|recommend)\b",
    re.I,
)
_NEGATION = re.compile(
    r"\b(?:no|not|never|neither|nor|without|cannot|can't|won't|don't|doesn't|"
    r"didn't|isn't|aren't|wasn't|weren't)\b",
    re.I,
)
_QUESTION = re.compile(
    r"\b(?:unresolved|open question|to be decided|tbd|under discussion|"
    r"not yet decided|unclear|question remains)\b",
    re.I,
)
_PENDING_CUES = re.compile(
    r"\b(?:awaiting|pending|subject to|waiting for|needs approval|approval required)\b",
    re.I,
)
_EXPLANATORY_TEXT = re.compile(
    r"\b(?:this sample|these notes|this document|this file|intentionally|"
    r"fictional|for testing|for test purposes|rough grammar|sample data)\b",
    re.I,
)
_SECTION_HEADING = re.compile(
    r"^\s*(?:meeting\s+details|notes?\s*\(|agenda|minutes?|proceedings|"
    r"rough\s+notes|other\s+matte?rs?|additional\s+reminders|notes?\s+from\s+the\s+meeting|"
    r"next\s+meeting|people\s+present|could\s+not\s+attend|absent\s+(?:with|without)|"
    r"leave\s+informed|members?\s+present)\b",
    re.I,
)
_METADATA_LINE = re.compile(
    r"^\s*(?:department|meeting|date|time|room|venue|chair|chaired\s+by|prepared\s+by|"
    r"notes?\s+taken\s+by|people\s+present|present|could\s+not\s+attend|attendance|"
    r"absent|leave\s+informed|members?\s+present)\b",
    re.I,
)
_ATTENDEE_LIST = re.compile(
    r"^\s*(?:Dr|Prof|Professor|Mr|Mrs|Ms)\.?\s+[A-Z][a-z]+"
    r"(?:\s+[A-Z][a-z]+)?"
    r"(?:\s*\([^)]*\))?"
    r"(?:\s*,\s*(?:Dr|Prof|Professor|Mr|Mrs|Ms)\.?\s+[A-Z][a-z]+"
    r"(?:\s+[A-Z][a-z]+)?"
    r"(?:\s*\([^)]*\))?)*\s*\.?\s*$",
    re.I,
)
_TOPIC_HEADING = re.compile(
    r"^\s*(?!Decision:|Action:|Decision|Action|Chair:|Prepared by:|Date:|"
    r"Time:|Venue:|Department:|Meeting:|Present:|Absent:|Attendance:)"
    r"([A-Z][a-zA-Z0-9\s&'’-]{2,50}):\s", re.M
)
_DEADLINE = re.compile(
    r"\b(?:by|before|until|no later than|during the week of)\s+"
    r"((?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|"
    r"next\s+week|this\s+week|today|tomorrow|"
    r"(?:\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*(?:,?\s+\d{4})?)|"
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?)|"
    r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    re.I,
)
_DATE_STANDALONE = re.compile(
    r"\b(?:\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*(?:,?\s+\d{4})?|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?|"
    r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
    re.I,
)
_TENTATIVE_PREFIX = re.compile(
    r"\b(?:tentative|proposed|possible|likely|maybe|perhaps)\b", re.I
)
_INLINE_MEETING_METADATA = re.compile(
    r"^\s*(?:the\s+)?meeting\s+(?:was\s+)?(?:held|scheduled)\b", re.I
)
_VENUE_PATTERN = re.compile(
    r"\bin\s+([a-z][a-z0-9\s]+?)(?=\s+(?:at|on|by|from|to)\b|[,.;]|$)", re.I
)
_VENUE_AFTER_TIME = re.compile(
    r",\s*([a-z][a-z0-9\s]+?)(?=[,.;]|$)", re.I
)
_TIME_PATTERN = re.compile(
    r"\bat\s+(\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?))\b", re.I
)
_NEGATIVE_IMPERATIVE = re.compile(
    r"^\s*(?:do\s+not|don't|do not)\s+(?:finish|complete|submit|upload|record|prepare|circulate|coordinate|"
    r"check|contact|confirm|display|recommend|arrange|conduct|revise|send|update|call|"
    r"test|collect|keep|show|publish|replace|repair|purchase|deploy|order|"
    r"verify|maintain|include|review|share)\b",
    re.I,
)


_ACTION_TASK_VERB = (
    r"confirm|prepare|circulate|coordinate|check|contact|submit|upload|record|"
    r"display|recommend|arrange|conduct|finish|complete|revise|send|update|call|"
    r"test|collect|keep|show|publish|replace|repair|purchase|deploy|order|verify|"
    r"maintain|include|request|remind|share|schedule|organize|organise|"
    r"investigate|follow\s+up|notify|obtain|ensure"
)
_ACTION_CLAUSE = re.compile(
    rf"^\s*(?P<subject>.+?)\s+(?P<modal>will|must|shall|should)\s+"
    rf"(?P<verb>{_ACTION_TASK_VERB})\b(?P<rest>.*)$",
    re.I,
)
_ACTION_ASKED_CLAUSE = re.compile(
    rf"^\s*(?P<subject>.+?)\s+was\s+asked\s+to\s+"
    rf"(?P<verb>{_ACTION_TASK_VERB})\b(?P<rest>.*)$",
    re.I,
)
_ACTION_REQUESTED_CLAUSE = re.compile(
    rf"^\s*(?:.+?\s+)?(?:asked|requested|instructed|directed)\s+"
    rf"(?P<subject>.+?)\s+to\s+(?P<verb>{_ACTION_TASK_VERB})\b"
    rf"(?P<rest>.*)$",
    re.I,
)
_ACTION_ASSIGNED_CLAUSE = re.compile(
    rf"^\s*(?P<subject>(?:(?:Dr|Prof(?:essor)?|Mr|Mrs|Ms)\.?\s+)?"
    rf"[A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){{0,4}})\s+to\s+"
    rf"(?P<verb>{_ACTION_TASK_VERB})\b(?P<rest>.*)$",
    re.I,
)
_ACTION_IMPERATIVE_CLAUSE = re.compile(
    rf"^\s*(?P<verb>{_ACTION_TASK_VERB})\b(?P<rest>.*)$", re.I
)


def _action_owner(subject: str, attendees: str) -> str | None:
    """Return a grounded person or organizational unit from an action clause."""
    value = re.sub(r"^(?:the|each)\s+", "", subject.strip(), flags=re.I)
    if " said " in value.casefold():
        value = re.split(r"\bsaid\b", value, flags=re.I)[-1].strip()
    value = value.rsplit(",", 1)[-1].strip()
    value = re.sub(r"^(?:the|each)\s+", "", value, flags=re.I)
    value = re.sub(r"\s+with\s+.*$", "", value, flags=re.I).strip()
    if re.match(r"students\b", value, re.I):
        value = "Students"
    elif re.fullmatch(r"(?:all\s+)?project\s+teams?", value, re.I):
        value = "Project Teams"
    elif re.fullmatch(r"(?:all\s+)?teams?", value, re.I):
        value = "Teams"
    elif re.fullmatch(r"classroom\s+assistants?", value, re.I):
        value = "Classroom Assistants"
    elif re.fullmatch(r"department\s+office", value, re.I):
        value = "Department Office"
    elif re.fullmatch(r"placement\s+cell", value, re.I):
        value = "Placement Cell"
    elif re.fullmatch(r"project\s+mentors?", value, re.I):
        value = "Project Mentors"
    elif re.fullmatch(r"faculty\s+mentors?", value, re.I):
        value = "Faculty Mentors"
    elif re.fullmatch(r"departments?", value, re.I):
        value = "Departments"

    roster = re.findall(
        r"\b(?:Dr|Prof(?:essor)?|Mr|Mrs|Ms)\.?\s+[A-Z][a-z]+"
        r"(?:\s+[A-Z][a-z]+){0,2}\b",
        attendees,
    )
    if value and not re.search(r"\b(?:office|teams?|students|assistants|cell|mentors)\b", value, re.I):
        name_part = re.sub(
            r"^(?:Dr|Prof(?:essor)?|Mr|Mrs|Ms)\.?\s*",
            "",
            value,
            flags=re.I,
        )
        matches = [
            name for name in roster
            if name.split()[1].casefold() == name_part.split()[0].casefold()
        ]
        if len(matches) == 1:
            return matches[0]
        if re.search(r"\b(?:Dr|Prof|Professor|Mr|Mrs|Ms)\b", value, re.I):
            return value
        if len(value.split()) == 1 and len(matches) > 1:
            return None
        if len(value.split()) == 1 and value.isalpha() and value[0].isupper():
            return value
    if value and re.fullmatch(
        r"(?:Department Office|Classroom Assistants|Students|Departments|Project Teams|"
        r"Teams|Placement Cell|Project Mentors|Faculty Mentors|Office)",
        value,
        re.I,
    ):
        return " ".join(word.capitalize() for word in value.split())
    return None


def _extract_action_record(
    text: str,
    agenda_topic: str | None = None,
    attendees: str = "",
) -> ActionItem | None:
    """Extract one task and its metadata from the same source sentence."""
    source = _ACTION_LABEL.sub("", text.strip())
    if not source or re.search(
        r"\b(?:final decision|next review|no coordinator was appointed|"
        r"no one was assigned|not accepted the role)\b",
        source,
        re.I,
    ):
        return None

    clause = (
        _ACTION_ASKED_CLAUSE.match(source)
        or _ACTION_REQUESTED_CLAUSE.match(source)
        or _ACTION_CLAUSE.match(source)
    )
    assigned_clause = False
    if clause is None:
        clause = _ACTION_ASSIGNED_CLAUSE.match(source)
        assigned_clause = clause is not None
    if clause:
        subject = clause.group("subject")
        # A reported instruction can introduce the actual assigned unit.
        subject = re.split(r"\bsaid\b", subject, flags=re.I)[-1].strip()
        owner = _action_owner(subject, attendees)
        if assigned_clause and owner is None:
            return None
        description = clause.group("verb") + clause.group("rest")
        description = re.sub(r"^\s+|\s+$", "", description)
    else:
        imperative = _ACTION_IMPERATIVE_CLAUSE.match(
            re.sub(r"^\s*(?:please|kindly)\s+", "", source, flags=re.I)
        )
        if not imperative:
            return None
        owner = None
        description = imperative.group("verb") + imperative.group("rest")

    deadline_match = _DEADLINE.search(source)
    deadline = None
    if deadline_match:
        deadline = re.sub(
            r"^(?:by|before|until|no later than)\s+",
            "",
            deadline_match.group(0),
            flags=re.I,
        ).strip()
    description = _DEADLINE.sub("", description, count=1).strip(" \t,;:.")
    description = re.sub(r"\s+", " ", description)
    if (
        len(description.split()) < 2
        or not re.match(rf"^(?:{_ACTION_TASK_VERB})\b", description, re.I)
    ):
        return None
    description = description[0].upper() + description[1:]
    return ActionItem(
        description=description,
        owner=owner or "",
        responsible_person=owner,
        deadline=deadline,
        agenda_topic=agenda_topic,
        source_statement=text.strip(),
        source_text=text.strip(),
    )


def _is_action_sentence(text: str) -> bool:
    return bool(
        _ACTION.search(text)
        or _IMPERATIVE_ACTION.search(text)
        or _ASSIGNED_TO_ACTION.search(text)
    )


_NON_PERSON_WORDS = {
    "we", "us", "they", "them", "he", "she", "it", "i", "you",
    "the", "a", "an",
    "was", "were", "has", "have", "will", "would", "could", "should", "may", "might",
    "department", "team", "committee", "group", "faculty", "staff",
    "students", "office", "college", "university", "school",
    "management", "administration", "authority", "board", "council",
    "lab", "labs", "laboratory", "computer", "computers", "machine", "machines",
    "system", "systems", "equipment", "device", "devices", "room", "rooms",
    "project", "projects", "report", "reports", "file", "files", "document", "documents",
    "server", "servers", "network", "software", "hardware", "application",
    "window", "windows", "door", "doors", "building", "buildings",
}


def _clean_owner(owner: str) -> str:
    """Strip non-person words from an extracted owner."""
    if not owner:
        return ""
    words = owner.split()
    if words and words[0].casefold() in _NON_PERSON_WORDS:
        return ""
    cleaned = [w for w in words if w.casefold() not in _NON_PERSON_WORDS]
    return " ".join(cleaned).strip()


def _content_words(text: str) -> set[str]:
    """Return meaningful content words for topic similarity."""
    stop = {
        "the", "a", "an", "and", "but", "or", "nor", "for", "yet", "so",
        "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them",
        "my", "your", "his", "its", "our", "their",
        "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
        "do", "does", "did", "will", "would", "could", "should", "may", "might",
        "must", "shall", "can", "need", "dare", "ought",
        "in", "on", "at", "to", "for", "of", "with", "by", "from", "as",
        "this", "that", "these", "those", "here", "there", "when", "where", "why", "how",
        "all", "any", "both", "each", "few", "more", "most", "other", "some", "such",
        "no", "not", "only", "own", "same", "than", "too", "very",
        "said", "says", "tell", "told", "ask", "asked",
    }
    words = re.findall(r"\b[\w'-]+\b", text.casefold())
    return {w for w in words if w not in stop and len(w) > 2}


def _topic_similarity(a: str, b: str) -> float:
    """Jaccard similarity on content words."""
    wa, wb = _content_words(a), _content_words(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


# ---------------------------------------------------------------------------
# Sentence-embedding similarity (supporting evidence for topic grouping)
# ---------------------------------------------------------------------------

_SENTENCE_MODEL = None
_SENTENCE_MODEL_ERROR = None


def _get_sentence_model():
    """Lazily load the local sentence-embedding model."""
    global _SENTENCE_MODEL, _SENTENCE_MODEL_ERROR
    if _SENTENCE_MODEL is not None or _SENTENCE_MODEL_ERROR is not None:
        return _SENTENCE_MODEL, _SENTENCE_MODEL_ERROR
    try:
        from sentence_transformers import SentenceTransformer

        _SENTENCE_MODEL = SentenceTransformer(
            "all-MiniLM-L6-v2",
            local_files_only=True,
            device="cpu",
        )
    except Exception:  # noqa: BLE001
        _SENTENCE_MODEL_ERROR = True
        _SENTENCE_MODEL = None
    return _SENTENCE_MODEL, _SENTENCE_MODEL_ERROR


def _semantic_similarity(a: str, b: str) -> float:
    """Cosine similarity between two sentences using the local embedding model.

    Supporting evidence only; returns 0.0 when the model is unavailable.
    """
    model, _ = _get_sentence_model()
    if model is None:
        return 0.0
    try:
        import numpy as np

        embeddings = model.encode(
            [a, b], convert_to_numpy=True, normalize_embeddings=True
        )
        sim = float(np.dot(embeddings[0], embeddings[1]))
        return max(0.0, min(1.0, sim))
    except Exception:  # noqa: BLE001
        return 0.0


# ---------------------------------------------------------------------------
# Topic title validation
# ---------------------------------------------------------------------------

_TOPIC_TITLE_STOPWORDS = {
    "a", "an", "the", "few", "some", "several", "upcoming", "current",
    "first", "working", "frequently", "department", "meeting", "student",
    "students", "faculty", "team", "teams", "group", "groups", "assistant",
    "series", "side", "date", "dates", "week", "review", "discussion",
}


def _is_valid_topic_hint(title: str) -> bool:
    words = title.split()
    if len(words) > 8 or re.search(r"[.!?]", title):
        return False
    if len(words) == 1:
        if title.strip().casefold() in _TOPIC_TITLE_STOPWORDS:
            return False
    if title.strip().casefold() in {
        "date", "time", "date and time", "agenda", "meeting", "other matters",
        "discussion", "notes", "decision", "resolution", "action", "review",
    }:
        return False
    if re.match(
        r"^(?:this|that|there|it|he|she|they|we|i|no|not|prof|dr|mr|mrs|ms|hod)\b",
        title,
        re.I,
    ):
        return False
    if re.search(r"\b(?:said|reported|explained|mentioned|was|were|has|have|should|will)\b", title, re.I):
        return False
    return True


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SourceStatement:
    """A single statement extracted from the source with structural context."""

    text: str
    source_index: int
    structural_type: str = "paragraph"
    is_metadata: bool = False
    is_meeting_content: bool = True
    is_key_value: bool = False
    topic_hint: str = ""
    section: str = "agenda"
    labeled_kind: str = ""
    document_class: str = "DISCUSSION_CONTENT"
    source_block_index: int = -1


@dataclass
class ActionItem:
    description: str
    owner: str = ""
    deadline: str | None = None
    status: str = "Open"
    source_statement: str = ""
    agenda_topic: str | None = None
    responsible_person: str | None = None
    source_text: str = ""

    def __post_init__(self):
        if not self.deadline:
            self.deadline = None
        if self.responsible_person is None:
            self.responsible_person = self.owner or None
        if not self.owner:
            self.owner = self.responsible_person or ""
        if not self.source_text:
            self.source_text = self.source_statement
        if not self.source_statement:
            self.source_statement = self.source_text


@dataclass
class AgendaItem:
    agenda_item: str
    proceedings: str = ""
    resolution: str = ""
    action_plan: str = ""
    action_items: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)
    pending_matters: list = field(default_factory=list)


@dataclass
class SupportingTable:
    title: str
    rows: list[list[str]] = field(default_factory=list)


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
    other_matters: list = field(default_factory=list)
    deadlines: list = field(default_factory=list)
    responsible_persons: list = field(default_factory=list)
    discussion_points: list = field(default_factory=list)
    key_decisions: list = field(default_factory=list)
    action_items: list = field(default_factory=list)
    structured_actions: list = field(default_factory=list)
    tentative_items: list = field(default_factory=list)
    tentative_decisions: list = field(default_factory=list)
    pending_approvals: list = field(default_factory=list)
    unresolved_questions: list = field(default_factory=list)
    validation_warnings: list = field(default_factory=list)
    institution: str = ""
    notes_recorded_by: str = ""
    supporting_tables: list[SupportingTable] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Cluster helper
# ---------------------------------------------------------------------------


def _cluster_similar_statements(
    statements: list[SourceStatement],
) -> list[list[SourceStatement]]:
    """Cluster statements into topics using TF-IDF + semantic similarity."""
    n = len(statements)
    if n <= 1:
        return [statements]
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for i in range(n):
        for j in range(i + 1, n):
            si = statements[i].text
            sj = statements[j].text
            tfidf = _topic_similarity(si, sj)
            sem = _semantic_similarity(si, sj)
            if tfidf >= 0.35 or sem >= 0.6:
                union(i, j)

    groups: dict[int, list[SourceStatement]] = {}
    for i, stmt in enumerate(statements):
        groups.setdefault(find(i), []).append(stmt)
    result = list(groups.values())
    result.sort(key=lambda g: min(s.source_index for s in g))
    return result


# ---------------------------------------------------------------------------
# Venue extraction
# ---------------------------------------------------------------------------


def _extract_venue(text: str) -> str:
    """Extract venue from meeting context.

    Only extracts venue from sentences that also contain date/time context,
    to avoid matching unrelated "in X" phrases like "notes are kept in a folder".
    Supports both "in venue" and "at time, venue" patterns.
    """
    time_indicator = re.compile(
        r"\b(?:am|pm|a\.m\.|p\.m\.|\d{1,2}:\d{2}|\d{1,2}(?:st|nd|rd|th)?\s+"
        r"[A-Za-z]+|[A-Za-z]+\s+\d{1,2})\b",
        re.I,
    )
    for sentence in _split_sentences(text):
        if not time_indicator.search(sentence):
            continue
        m = _VENUE_PATTERN.search(sentence)
        if m:
            venue = m.group(1).strip()
            venue = re.sub(r"[,.;]$", "", venue).strip()
            if venue and venue.casefold() not in {"a folder", "the folder"}:
                return venue
        m = _VENUE_AFTER_TIME.search(sentence)
        if m:
            venue = m.group(1).strip()
            venue = re.sub(r"[,.;]$", "", venue).strip()
            if venue and len(venue.split()) >= 2:
                return venue
    return ""


_STRUCTURED_TIME = (
    r"\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)"
)


def _structured_metadata(text: str, values: dict[str, str]) -> bool:
    """Extract explicitly labeled metadata without guessing from prose."""
    extracted = False
    labels = {
        "institution": "institution",
        "university": "institution",
        "department": "department",
        "department / committee": "department",
        "meeting": "meeting_title",
        "meeting title": "meeting_title",
        "date": "date",
        "time": "time",
        "start time": "start_time",
        "end time": "end_time",
        "venue": "venue",
        "room": "venue",
        "chair": "coordinator",
        "chairperson": "coordinator",
        "chaired by": "coordinator",
        "meeting chaired by": "coordinator",
        "notes recorded by": "notes_recorded_by",
        "notes taken by": "notes_recorded_by",
        "prepared by": "notes_recorded_by",
        "present": "attendees",
        "members present": "attendees",
        "could not attend": "absentees",
        "unable to attend": "absentees",
        "absent": "absentees",
        "absent without intimation": "absent_without_intimation",
        "leave informed": "absentees",
    }
    for segment in re.split(r"\s*\|\s*", text.strip()):
        match = re.match(r"^\s*([^:]+)\s*:\s*(.*?)\s*$", segment)
        if not match:
            continue
        key = re.sub(r"\s+", " ", match.group(1).strip().casefold())
        value = match.group(2).strip()
        field_name = labels.get(key)
        if not field_name or not value:
            continue
        extracted = True
        if field_name == "time":
            time_range = re.search(
                rf"({_STRUCTURED_TIME})\s*(?:to|[-–])\s*({_STRUCTURED_TIME})",
                value,
                re.I,
            )
            if time_range:
                values["start_time"] = time_range.group(1).strip()
                values["end_time"] = time_range.group(2).strip()
            else:
                match_time = re.search(_STRUCTURED_TIME, value, re.I)
                if match_time:
                    values["start_time"] = match_time.group(0).strip()
        elif field_name == "coordinator":
            values[field_name] = value.split(",", 1)[0].strip()
        elif (
            field_name == "department"
            and values.get(field_name, "").casefold().startswith("department of ")
        ):
            continue
        else:
            values[field_name] = value
    return extracted


def _structured_section(text: str) -> str:
    """Recognize section boundaries from heading text, including Normal styles."""
    label = re.sub(r"\s+", " ", text.strip().rstrip(":")).casefold()
    if (
        "not part of the minutes" in label
        or "not minutes content" in label
        or "private reminder" in label
        or "rough reminders" in label
    ):
        return "private"
    if label in {"people", "attendance", "attendees"}:
        return "attendance"
    if label.startswith("meeting information"):
        return "metadata"
    if label in {"start", "opening", "opening proceedings"}:
        return "opening"
    if label in {
        "agenda", "discussion", "notes collected during discussion",
        "notes from the meeting", "notes from the discussion", "proceedings",
    }:
        return "agenda"
    if (
        label in {"figures mentioned", "supporting figures", "supporting data"}
        or label.startswith("quick figures")
    ):
        return "supporting"
    if label in {"other points", "other matters"} or label.startswith("other points mentioned"):
        return "other"
    if (
        label in {"closing", "conclusion", "closing proceedings"}
        or label.startswith("closing /")
    ):
        return "closing"
    if label in {"next meeting", "next meeting date"}:
        return "next_meeting"
    return ""


def _structured_topic_candidate(
    block: dict,
    next_block: dict | None,
) -> bool:
    """Identify contextual standalone topic labels, not arbitrary short prose."""
    if block.get("kind") != "paragraph" or block.get("is_list"):
        return False
    text = str(block.get("text", "")).strip()
    words = text.split()
    if not text or len(words) > 8 or re.search(r"[.!?;]$", text):
        return False
    if block.get("level", 0):
        return True
    if not next_block or next_block.get("kind") != "paragraph":
        return False
    next_words = str(next_block.get("text", "")).split()
    return len(next_words) >= 8


def _structured_group_text(blocks: list[dict]) -> str:
    lines = []
    for block in blocks:
        text = str(block.get("text", "")).strip()
        if block.get("is_list"):
            marker = "1. " if block.get("list_type") == "numbered" else "- "
            text = marker + text
        if text:
            lines.append(text)
    return "\n".join(lines)


def _format_structured_title(value: str) -> str:
    minor_words = {"a", "an", "and", "as", "at", "but", "by", "for", "in", "of", "on", "or", "the", "to"}
    words = value.split()
    return " ".join(
        word.title() if index == 0 or word.casefold() not in minor_words else word.casefold()
        for index, word in enumerate(words)
    )


def _infer_structured_topic_title(text: str, fallback: str) -> str:
    """Prefer a concise topic phrase already present in an unheaded block."""
    patterns = (
        r"\b([\w'-]+)\s+(?:clashes|issues?)\b",
        r"\b(?:discussion|conversation|update)\s+(?:about|on|regarding)\s+"
        r"(?:the\s+)?([A-Za-z][\w'-]*(?:\s+[\w'-]+){0,4})",
        r"\b(?:attend|attending)\s+(?:the\s+)?([A-Za-z][\w'-]*(?:\s+[\w'-]+){0,4})",
        r"\bfor\s+the\s+upcoming\s+([A-Za-z][\w'-]*(?:\s+[\w'-]+){0,3})",
        r"\bon\s+the\s+([A-Za-z][\w'-]*)\s+side\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        phrase = match.group(1).strip(" ,.;:")
        phrase = re.sub(r"\s+(?:has|have|was|were|is|are|will|should|must)\b.*$", "", phrase, flags=re.I)
        if re.search(r"\blab\b", phrase, re.I):
            return "Laboratory"
        if phrase and len(phrase.split()) <= 5:
            return _format_structured_title(phrase)
    return fallback


def _organize_structured_blocks(
    original: str,
    corrected: str,
    source_blocks: list,
) -> MeetingMinutes:
    """Route ordered DOCX blocks before applying sentence-level NLP within topics."""
    metadata: dict[str, str] = {}
    agenda_blocks: list[dict] = []
    opening: list[str] = []
    other: list[str] = []
    closing: list[str] = []
    next_meeting: list[str] = []
    supporting_tables: list[SupportingTable] = []
    section = "metadata"
    section_title = ""
    private = False

    for source_block in source_blocks:
        if isinstance(source_block, dict):
            block = source_block
        else:
            block = {
                name: getattr(source_block, name, "")
                for name in (
                    "kind", "text", "style", "rows", "level", "is_list",
                    "list_type",
                )
            }
        text = str(block.get("text", "")).strip()
        if not text:
            continue
        if private:
            is_heading = bool(block.get("level")) or str(block.get("style", "")).casefold().startswith("heading")
            resumed_section = _structured_section(text) if is_heading else ""
            if resumed_section and resumed_section != "private":
                private = False
                section = resumed_section
                section_title = text.rstrip(":")
                continue
            continue
        if any(
            marker in text.casefold()
            for marker in (
                "not part of the minutes",
                "not minutes content",
                "private reminder",
                "rough reminders",
            )
        ):
            private = True
            continue

        if block.get("kind") == "table":
            rows = [
                [str(cell).strip() for cell in row]
                for row in block.get("rows", ())
            ]
            if any(any(cell for cell in row) for row in rows):
                supporting_tables.append(
                    SupportingTable(
                        title=section_title if section == "supporting" else "Supporting Data",
                        rows=rows,
                    )
                )
            continue

        metadata_line = _structured_metadata(text, metadata)
        if (
            section == "metadata"
            and re.match(r"^\s*department\s+of\s+", text, re.I)
        ):
            department = re.split(r"\s+[–—-]\s+", text, maxsplit=1)[0].strip()
            metadata["department"] = department
            continue
        if (
            section == "metadata"
            and "institution" not in metadata
            and not metadata_line
            and re.search(r"\b(?:university|institute|college)\b", text, re.I)
            and not re.search(r"\brough meeting notes\b", text, re.I)
        ):
            metadata["institution"] = text
            continue
        if metadata_line:
            continue

        section_name = _structured_section(text)
        if section_name:
            section = section_name
            section_title = text.rstrip(":")
            continue

        if section == "opening":
            opening.append(text)
        elif section == "agenda":
            agenda_blocks.append(block)
        elif section == "supporting":
            supporting_tables.append(SupportingTable(title=section_title or "Supporting Data", rows=[[text]]))
        elif section == "other":
            other.append(text)
        elif section == "closing":
            next_meeting_match = re.match(
                r"^\s*(?:next\s+)?(?:coordination\s+)?meeting\s*:\s*(.+)$",
                text,
                re.I,
            )
            if next_meeting_match:
                next_meeting.append(next_meeting_match.group(1).strip())
            else:
                closing.append(text)
        elif section == "next_meeting":
            next_meeting.append(text)

    agenda_items: list[AgendaItem] = []
    all_deadlines: list[str] = []
    all_persons: list[str] = []
    all_actions: list[str] = []
    all_discussion: list[str] = []
    all_decisions: list[str] = []
    all_tentative: list[str] = []
    structured_actions: list[dict] = []

    candidate_indices: set[int] = set()
    for index, block in enumerate(agenda_blocks):
        following_index = index + 1
        while (
            following_index < len(agenda_blocks)
            and agenda_blocks[following_index].get("is_list")
        ):
            following_index += 1
        next_block = (
            agenda_blocks[following_index]
            if following_index < len(agenda_blocks)
            else None
        )
        if _structured_topic_candidate(block, next_block):
            candidate_indices.add(index)
    groups: list[tuple[str, list[dict]]] = []
    current_title = ""
    current_blocks: list[dict] = []
    for index, block in enumerate(agenda_blocks):
        if index in candidate_indices:
            if current_blocks:
                groups.append((current_title, current_blocks))
            current_title = str(block.get("text", "")).strip().rstrip(":")
            current_blocks = []
        else:
            current_blocks.append(block)
    if current_blocks:
        groups.append((current_title, current_blocks))

    clustered_unheaded = not candidate_indices and len(agenda_blocks) > 1
    if clustered_unheaded:
        statements = [
            SourceStatement(
                text=str(block.get("text", "")),
                source_index=index,
                structural_type=str(block.get("kind", "paragraph")),
            )
            for index, block in enumerate(agenda_blocks)
        ]
        groups = [
            ("", [agenda_blocks[statement.source_index] for statement in cluster])
            for cluster in _cluster_similar_statements(statements)
        ]
        block_terms = [_content_words(str(block.get("text", ""))) for block in agenda_blocks]
        term_counts: dict[str, int] = {}
        for terms in block_terms:
            for term in terms:
                term_counts[term] = term_counts.get(term, 0) + 1
        merged_groups: list[tuple[str, list[dict]]] = []
        for group_title, blocks in groups:
            current_text = _structured_group_text(blocks)
            repeat = re.search(r"\b(?P<term>[\w'-]+)\s+issue\b.*\bcame up again\b", current_text, re.I)
            reference = re.search(
                r"^\s*(?:some|several|a few|faculty members|they)\b.{0,100}"
                r"\b(?:the|this|that)\s+(?P<term>[\w'-]+)\b",
                current_text,
                re.I | re.S,
            )
            term = (repeat or reference).group("term").casefold() if repeat or reference else ""
            merge_index = None
            if term and term_counts.get(term) == 2:
                for prior_index, (_, prior_blocks) in enumerate(merged_groups):
                    prior_terms = set().union(*(
                        _content_words(str(block.get("text", "")))
                        for block in prior_blocks
                    ))
                    if term in prior_terms:
                        merge_index = prior_index
                        break
            if merge_index is None:
                merged_groups.append((group_title, blocks))
            else:
                prior_title, prior_blocks = merged_groups[merge_index]
                merged_groups[merge_index] = (
                    prior_title,
                    sorted(prior_blocks + blocks, key=agenda_blocks.index),
                )
        groups = merged_groups

    for title, blocks in groups:
        group_text = _structured_group_text(blocks)
        if not group_text:
            continue
        result = organize_notes(group_text)
        group_agenda = result.agenda_items or []
        fallback_title = group_agenda[0].agenda_item if group_agenda else "Discussion"
        topic_title = _format_structured_title(title) if title else (
            _infer_structured_topic_title(group_text, fallback_title)
            if clustered_unheaded else fallback_title
        )
        topic_actions = [
            action
            for block in blocks
            for sentence in _split_sentences(str(block.get("text", "")))
            if (action := _extract_action_record(
                sentence,
                agenda_topic=topic_title,
                attendees=metadata.get("attendees", ""),
            ))
        ]
        group_pending = [
            matter
            for item in group_agenda
            for matter in item.pending_matters
        ]
        for block in blocks:
            for sentence in _split_sentences(str(block.get("text", ""))):
                if re.search(
                    r"\bno\s+[\w -]+\s+(?:(?:has|have)\s+been|is|are)\s+confirmed\b|"
                    r"\bdates?\s+have\s+not\s+been\s+agreed\b|"
                    r"\b(?:asked|questioned)\s+whether\b.*\b(?:could|might|may)\b"
                    r".*\b(?:moved|changed|postponed)\b",
                    sentence,
                    re.I,
                ) and sentence not in group_pending:
                    group_pending.append(sentence)
        if title or clustered_unheaded:
            resolutions = [
                item.resolution
                for item in group_agenda
                if item.resolution
                and not _TENTATIVE.search(item.resolution)
                and not _SUGGESTION.search(item.resolution)
                and not _NEGATION.search(item.resolution)
            ]
            agenda_items.append(
                AgendaItem(
                    agenda_item=topic_title,
                    proceedings="\n".join(
                        item.proceedings for item in group_agenda if item.proceedings
                    ),
                    resolution="\n".join(resolutions),
                    action_plan="\n".join(action.description for action in topic_actions),
                    action_items=topic_actions,
                    suggestions=[
                        suggestion for item in group_agenda for suggestion in item.suggestions
                    ],
                    pending_matters=group_pending,
                )
            )
        else:
            for item in group_agenda:
                item_actions = [
                    action for action in topic_actions
                    if action.agenda_topic == topic_title
                ]
                item.action_items = item_actions
                item.action_plan = "\n".join(action.description for action in item_actions)
                agenda_items.append(item)
        structured_actions.extend(topic_actions)
        all_deadlines.extend(action.deadline for action in topic_actions if action.deadline)
        all_persons.extend(
            action.responsible_person for action in topic_actions
            if action.responsible_person
        )
        all_actions.extend(action.description for action in topic_actions)
        all_discussion.extend(result.discussion_points)
        all_decisions.extend(
            decision for decision in result.key_decisions
            if not _TENTATIVE.search(decision)
            and not _SUGGESTION.search(decision)
            and not _NEGATION.search(decision)
        )
        all_tentative.extend(result.tentative_items)
        all_tentative.extend(group_pending)

    for matter in other:
        sentences = _split_sentences(matter)
        for index, sentence in enumerate(sentences):
            action = _extract_action_record(
                sentence,
                agenda_topic="Other Matters",
                attendees=metadata.get("attendees", ""),
            )
            if action:
                if re.match(r"^replace\s+it$", action.description, re.I) and index:
                    object_match = re.search(
                        r"\b(?:displays|shows|lists|contains)\s+"
                        r"(?P<object>[^,.;]+)",
                        sentences[index - 1],
                        re.I,
                    )
                    if object_match:
                        action.description = (
                            "Replace " + object_match.group("object").strip()
                        )
                structured_actions.append(action)
                all_actions.append(action.description)
                if action.deadline:
                    all_deadlines.append(action.deadline)
                if action.responsible_person:
                    all_persons.append(action.responsible_person)

    def deduplicate(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            key = value.casefold()
            if key not in seen:
                seen.add(key)
                result.append(value)
        return result

    return MeetingMinutes(
        meeting_title=metadata.get("meeting_title", ""),
        department=metadata.get("department", ""),
        date=metadata.get("date", ""),
        start_time=metadata.get("start_time", ""),
        end_time=metadata.get("end_time", ""),
        venue=metadata.get("venue", ""),
        coordinator=metadata.get("coordinator", ""),
        attendees=metadata.get("attendees", ""),
        absentees=metadata.get("absentees", ""),
        absent_without_intimation=metadata.get("absent_without_intimation", ""),
        institution=metadata.get("institution", ""),
        notes_recorded_by=metadata.get("notes_recorded_by", ""),
        agenda_items=agenda_items,
        opening_remarks="\n".join(opening),
        conclusion="\n".join(closing),
        next_meeting_date="\n".join(next_meeting),
        other_matters=other,
        supporting_tables=supporting_tables,
        deadlines=deduplicate(all_deadlines),
        responsible_persons=deduplicate(all_persons),
        discussion_points=deduplicate(all_discussion),
        key_decisions=deduplicate(all_decisions),
        action_items=deduplicate(all_actions),
        structured_actions=structured_actions,
        tentative_items=deduplicate(all_tentative),
        pending_approvals=deduplicate(all_tentative),
        original_notes=original,
        corrected_notes=corrected,
        review_required=True,
    )


def _extract_plain_text_metadata(text: str) -> dict[str, str]:
    """Extract explicitly labeled details from text-only notes."""
    values: dict[str, str] = {}
    present_lines: list[str] = []
    reading_present_list = False
    for line in text.splitlines():
        value = line.strip()
        if not value:
            continue
        if re.fullmatch(r"people present|members present|attendees", value, re.I):
            reading_present_list = True
            continue
        if reading_present_list:
            if _ATTENDEE_LIST.fullmatch(value):
                present_lines.append(value.rstrip("."))
                continue
            reading_present_list = False
        if re.match(r"^department\s+of\s+.+$", value, re.I):
            values.setdefault("department", value)
        _structured_metadata(value, values)
    if present_lines and not values.get("attendees"):
        values["attendees"] = "; ".join(present_lines)
    return values


# ---------------------------------------------------------------------------
# organize_notes
# ---------------------------------------------------------------------------


def organize_notes(
    notes: str,
    corrected_notes: str | None = None,
    source_blocks: list | None = None,
) -> MeetingMinutes:
    """Group note sentences into a structured MoM draft.

    Pipeline:
      1. Split into sentences.
      2. Classify each sentence (metadata, discussion, decision, action, etc.).
      3. Group related sentences into agenda topics.
      4. Extract facts (decisions, actions, owners, deadlines).
      5. Build MeetingMinutes.
    """
    original = notes.strip()
    if not original:
        raise ValueError("Enter or upload meeting notes before generating minutes.")
    corrected = (corrected_notes or original).strip()
    if source_blocks:
        return _organize_structured_blocks(original, corrected, source_blocks)

    sentences = _split_sentences(original)
    text_metadata = _extract_plain_text_metadata(original)

    all_deadlines: list[str] = []
    all_persons: list[str] = []
    all_actions: list[str] = []
    all_discussion: list[str] = []
    all_decisions: list[str] = []
    all_tentative: list[str] = []
    all_other_matters: list[str] = []

    # Classify sentences
    statements: list[SourceStatement] = []
    for idx, sentence in enumerate(sentences):
        # A sentence is metadata only if it looks like a meeting detail line
        # (e.g. "Meeting held on 22 October").  A date inside a decision or
        # action sentence does NOT make it metadata.
        is_meta = bool(_INLINE_MEETING_METADATA.search(sentence)) or bool(
            _EXPLANATORY_TEXT.search(sentence)
        ) or bool(_SECTION_HEADING.search(sentence)) or bool(
            _METADATA_LINE.search(sentence)
        ) or bool(_ATTENDEE_LIST.search(sentence))
        document_class = "DISCUSSION_CONTENT"
        section = "agenda"
        if _DECISION_LABEL.search(sentence) or _DECISION.search(sentence):
            document_class = "DECISION_CONTENT"
        elif _PENDING_CUES.search(sentence):
            document_class = "PENDING_APPROVAL_CONTENT"
        elif _ACTION_LABEL.search(sentence) or _is_action_sentence(sentence):
            document_class = "ACTION_CONTENT"
        elif _TENTATIVE.search(sentence) or _SUGGESTION.search(sentence):
            document_class = "SUGGESTION_CONTENT"
        elif _QUESTION.search(sentence):
            document_class = "QUESTION_CONTENT"
        statements.append(
            SourceStatement(
                text=sentence,
                source_index=idx,
                structural_type="paragraph",
                is_metadata=is_meta,
                is_meeting_content=not is_meta,
                is_key_value=False,
                document_class=document_class,
                section=section,
            )
        )
        dm = _DEADLINE.search(sentence)
        if dm:
            all_deadlines.append(dm.group(0).strip())
    # Group into topics using heading detection first, then similarity
    # clustering for any remaining unheaded content.
    meeting_statements = [s for s in statements if s.is_meeting_content]
    topic_groups: list[list[SourceStatement]] = []

    # Detect explicit topic headings (e.g. "Final year project progress: ...")
    heading_indices: list[int] = []
    for i, stmt in enumerate(meeting_statements):
        m = _TOPIC_HEADING.search(stmt.text)
        if m:
            heading_indices.append(i)
            stmt.topic_hint = m.group(1).strip()
            stmt.document_class = "TOPIC_HEADING"
            # Split heading from content: keep only the text after the colon
            colon_pos = stmt.text.find(":")
            if colon_pos >= 0:
                rest = stmt.text[colon_pos + 1:].strip()
                if rest:
                    stmt.text = rest
                    stmt.document_class = "DISCUSSION_CONTENT"

    if heading_indices:
        # Split content into groups based on headings.
        prev_end = 0
        for idx, heading_idx in enumerate(heading_indices):
            # Content before this heading (not yet assigned)
            if heading_idx > prev_end:
                pre_group = meeting_statements[prev_end:heading_idx]
                if len(pre_group) > 1:
                    sub_groups = _cluster_similar_statements(pre_group)
                    topic_groups.extend(sub_groups)
                else:
                    topic_groups.append(pre_group)
            # The heading statement itself plus following content
            group = [meeting_statements[heading_idx]]
            end = heading_indices[idx + 1] if idx + 1 < len(heading_indices) else len(meeting_statements)
            group.extend(meeting_statements[heading_idx + 1:end])
            topic_groups.append(group)
            prev_end = end
        # Content after the last heading
        if prev_end < len(meeting_statements):
            post_group = meeting_statements[prev_end:]
            if len(post_group) > 1:
                sub_groups = _cluster_similar_statements(post_group)
                topic_groups.extend(sub_groups)
            else:
                topic_groups.append(post_group)
    else:
        # No headings found - use similarity clustering
        topic_groups = _cluster_similar_statements(meeting_statements)

    # Build agenda items
    agenda_items: list[AgendaItem] = []
    structured_actions: list[dict] = []
    opening_remarks: list[str] = []

    # If we have heading indices, content before the first heading that is
    # discussion content becomes opening remarks.
    first_heading_original_idx = None
    if heading_indices:
        first_heading_original_idx = meeting_statements[heading_indices[0]].source_index

    for group in topic_groups:
        # Check if this group is opening remarks (before first topic heading)
        is_opening = False
        if first_heading_original_idx is not None:
            if all(s.source_index < first_heading_original_idx for s in group):
                is_opening = True

        # Skip single-sentence topics that are pure actions with an owner --
        # they become flat action items instead of cluttering the agenda.
        if len(group) == 1:
            stmt = group[0]
            stext = stmt.text
            if (
                _is_action_sentence(stext)
                and not _DECISION.search(stext)
                and not _NEGATION.search(stext)
                and not _TENTATIVE.search(stext)
                and not _PENDING_CUES.search(stext)
            ):
                owner = ""
                m = (
                    _RESPONSIBLE.search(stext)
                    or _RESPONSIBLE_MIXED.search(stext)
                    or _RESPONSIBLE_ASKED.search(stext)
                    or _RESPONSIBLE_WAS_ASKED.search(stext)
                )
                if m:
                    owner = _clean_owner(m.group(1).strip())
                dm = _DEADLINE.search(stext)
                deadline = dm.group(0).strip() if dm else ""
                if deadline:
                    all_deadlines.append(deadline)
                if owner:
                    all_persons.append(owner)
                all_actions.append(stext)
                action_record = ActionItem(
                    description=stext,
                    owner=owner,
                    deadline=deadline,
                    source_statement=stext,
                    source_text=stext,
                )
                structured_actions.append(action_record)
                all_other_matters.append(stext)
                continue

        proceedings: list[str] = []
        resolution = ""
        action_plan: list[str] = []
        topic_actions: list[ActionItem] = []
        topic_suggestions: list[str] = []
        topic_pending: list[str] = []

        # Process statements in the group
        for stmt in group:
            # Skip topic heading statements - they provide the title only
            if stmt.document_class == "TOPIC_HEADING":
                continue
            stext = stmt.text
            has_negation = bool(_NEGATION.search(stext))
            is_decision = (
                _DECISION.search(stext) or stmt.document_class == "DECISION_CONTENT"
            ) and not has_negation
            is_action = (
                _is_action_sentence(stext)
                or stmt.document_class == "ACTION_CONTENT"
            ) and not has_negation and not _TENTATIVE.search(stext) and not _PENDING_CUES.search(stext)
            is_tentative = bool(
                _TENTATIVE.search(stext) or _SUGGESTION.search(stext)
            )
            is_pending = bool(
                _PENDING_CUES.search(stext)
                or stmt.document_class == "PENDING_APPROVAL_CONTENT"
            )

            if is_decision:
                resolution = stext
                all_decisions.append(stext)
            elif is_pending:
                topic_pending.append(stext)
                all_tentative.append(stext)
            elif is_action:
                action_plan.append(stext)
                all_actions.append(stext)
                owner = ""
                m = (
                    _RESPONSIBLE.search(stext)
                    or _RESPONSIBLE_MIXED.search(stext)
                    or _RESPONSIBLE_ASKED.search(stext)
                    or _RESPONSIBLE_WAS_ASKED.search(stext)
                )
                if m:
                    owner = _clean_owner(m.group(1).strip())
                dm = _DEADLINE.search(stext)
                deadline = dm.group(0).strip() if dm else ""
                if deadline:
                    all_deadlines.append(deadline)
                if owner:
                    all_persons.append(owner)
                action_record = ActionItem(
                    description=stext,
                    owner=owner,
                    deadline=deadline,
                    source_statement=stext,
                    source_text=stext,
                )
                topic_actions.append(action_record)
            elif is_tentative:
                dm = _DEADLINE.search(stext)
                deadline = dm.group(0).strip() if dm else ""
                if deadline:
                    all_deadlines.append(deadline)
                # Tentative items with an owner are pending approvals;
                # ownerless suggestions go to other matters.
                m = (
                    _RESPONSIBLE.search(stext)
                    or _RESPONSIBLE_MIXED.search(stext)
                    or _RESPONSIBLE_ASKED.search(stext)
                    or _RESPONSIBLE_WAS_ASKED.search(stext)
                    or _RESPONSIBLE_TENTATIVE.search(stext)
                )
                if m:
                    owner = _clean_owner(m.group(1).strip())
                    if owner:
                        all_persons.append(owner)
                        topic_suggestions.append(stext)
                        all_tentative.append(stext)
                        continue
                all_tentative.append(stext)
                all_other_matters.append(stext)
            else:
                # Short imperative sentences without an owner are other matters,
                # not discussion.  Also negative imperatives ("do not deploy").
                words = stext.split()
                is_short_imperative = (
                    len(words) <= 6
                    and (_IMPERATIVE_ACTION.search(stext)
                         or _NEGATIVE_IMPERATIVE.search(stext))
                    and not _RESPONSIBLE.search(stext)
                    and not _RESPONSIBLE_MIXED.search(stext)
                )
                if is_short_imperative:
                    all_other_matters.append(stext)
                else:
                    proceedings.append(stext)
                    all_discussion.append(stext)

        # Skip empty groups (all content was metadata/tentative/etc.)
        if not proceedings and not resolution and not action_plan and not topic_suggestions and not topic_pending:
            continue

        # Opening remarks: capture discussion before the first topic heading
        if is_opening:
            opening_remarks.extend(proceedings)
            continue

        # Derive a topic title - use heading if available
        title = ""
        for s in group:
            if s.topic_hint and _is_valid_topic_hint(s.topic_hint):
                title = s.topic_hint
                break
        if not title:
            # Try noun phrase extraction from group content
            group_texts = [s.text for s in group if s.document_class != "TOPIC_HEADING"]
            title = _extract_topic_title_from_noun_phrases(group_texts)
        if not title:
            for s in group:
                words = s.text.split()
                if 3 <= len(words) <= 10:
                    title = s.text
                    break
        if not title:
            title = group[0].text if group else "Discussion"

        # Clean up title: remove trailing punctuation, capitalize
        title = title.strip(" .:;")
        if title:
            title = title.title()
            # Remove trailing period if the title is a full sentence
            if title.endswith("."):
                title = title[:-1].strip()
            # Truncate overly long titles to first meaningful phrase
            if len(title.split()) > 6:
                title = " ".join(title.split()[:6])

        for action in topic_actions:
            action.agenda_topic = title
            structured_actions.append(action)

        agenda_items.append(
            AgendaItem(
                agenda_item=title,
                proceedings=" ".join(proceedings),
                resolution=resolution,
                action_plan=" ".join(action_plan),
                action_items=topic_actions,
                suggestions=topic_suggestions,
                pending_matters=topic_pending,
            )
        )

    # Deduplicate fact lists while preserving order (case-insensitive)
    def _dedup_case_insensitive(items: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for item in items:
            key = item.casefold()
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result

    all_deadlines = _dedup_case_insensitive(all_deadlines)
    all_persons = _dedup_case_insensitive(all_persons)
    all_actions = _dedup_case_insensitive(all_actions)
    all_decisions = _dedup_case_insensitive(all_decisions)
    all_tentative = _dedup_case_insensitive(all_tentative)
    all_discussion = _dedup_case_insensitive(all_discussion)

    # Extract dates/times from text
    date_match = _DATE_STANDALONE.search(original)
    extracted_date = date_match.group(0).strip() if date_match else ""
    extracted_venue = _extract_venue(original)
    time_match = _TIME_PATTERN.search(original)
    extracted_time = time_match.group(1).strip() if time_match else ""
    minutes = MeetingMinutes(
        meeting_title=text_metadata.get("meeting_title", ""),
        department=text_metadata.get("department", ""),
        start_time=text_metadata.get("start_time", extracted_time),
        end_time=text_metadata.get("end_time", ""),
        venue=text_metadata.get("venue", extracted_venue),
        coordinator=text_metadata.get("coordinator", ""),
        notes_recorded_by=text_metadata.get("notes_recorded_by", ""),
        attendees=text_metadata.get("attendees", ""),
        absentees=text_metadata.get("absentees", ""),
        agenda_items=agenda_items,
        date=text_metadata.get("date", extracted_date),
        original_notes=original,
        corrected_notes=corrected,
        review_required=True,
        other_matters=all_other_matters,
        deadlines=all_deadlines,
        responsible_persons=all_persons,
        discussion_points=all_discussion,
        key_decisions=all_decisions,
        action_items=all_actions,
        structured_actions=structured_actions,
        tentative_items=all_tentative,
        pending_approvals=all_tentative,
        opening_remarks=" ".join(opening_remarks),
    )
    return minutes


def action_table_rows(minutes: MeetingMinutes) -> list[tuple[str, str, str]]:
    """Format the meeting's existing structured action records for display."""
    rows: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    meeting_year = re.search(r"\b(?:19|20)\d{2}\b", minutes.date)
    for action in minutes.structured_actions:
        if isinstance(action, dict):
            description = str(action.get("description", "")).strip()
            owner = str(
                action.get("responsible_person") or action.get("owner") or ""
            ).strip()
            deadline = str(action.get("deadline") or "").strip()
        else:
            description = str(getattr(action, "description", "")).strip()
            owner = str(
                getattr(action, "responsible_person", None)
                or getattr(action, "owner", "")
            ).strip()
            deadline = str(getattr(action, "deadline", None) or "").strip()
        if (
            deadline
            and meeting_year
            and re.fullmatch(
                r"(?:\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+|[A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?)",
                deadline,
            )
        ):
            deadline = f"{deadline} {meeting_year.group(0)}"
        key = (description.casefold(), owner.casefold(), deadline.casefold())
        if description and key not in seen:
            seen.add(key)
            rows.append((owner or "Not specified", description, deadline or "Not specified"))
    if not rows:
        for description in minutes.action_items:
            text = str(description).strip()
            key = (text.casefold(), "", "")
            if text and key not in seen:
                seen.add(key)
                rows.append(("Not specified", text, "Not specified"))
    return rows
