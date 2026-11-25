"""Single-page faculty Minutes of Meeting generator."""

from __future__ import annotations

import html
import hashlib
import importlib.util
import re
from pathlib import Path
from uuid import uuid4

import streamlit as st

from documents import build_mom_docx
from nlp.docx_io import DocxInputError, extract_docx_text
from processing import AgendaItem, MeetingMinutes, organize_notes

MAX_UPLOAD_SIZE_MB = 10

st.set_page_config(
    page_title="OfflineNote AI | Minutes of Meeting",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      :root {
        --paper-bg: #E9E2D3;
        --input-bg: #FBF8F1;
        --document-bg: #FFFEFB;
        --line: #DED6C4;
        --navy: #1B2540;
        --brass: #B08D57;
        --green: #2F7D5B;
        --ink: #292923;
        --muted: #77736B;
        --warning-bg: #F7E8BF;
        --sans: Inter, Aptos, "Segoe UI", sans-serif;
        --serif: Fraunces, "Iowan Old Style", "Palatino Linotype", Georgia, serif;
        --radius: 7px;
      }
      .stApp {
        background: var(--paper-bg);
        color: var(--ink);
        font-family: var(--sans);
      }
      .block-container {
        max-width: 900px;
        padding: 1.1rem 1.25rem 3rem;
      }
      .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
        color: var(--navy);
        font-family: var(--serif);
        font-weight: 400;
      }
      .stApp h1 {
        font-size: clamp(1.8rem, 3vw, 2.25rem);
        letter-spacing: -0.035em;
        line-height: 1.06;
        margin: 0.05rem 0 0;
      }
      .stApp p, .stApp label, .stApp input, .stApp textarea, .stApp button {
        font-family: var(--sans);
      }
      [class*="st-key-attendees_remove_"] button,
      [class*="st-key-edit_attendees_remove_"] button {
        background: #EFE7D6;
        border: 1px solid var(--line);
        border-radius: 999px;
        color: var(--navy);
        font-size: 0.76rem;
        min-height: 2rem;
        padding: 0.1rem 0.45rem;
      }
      [class*="st-key-attendees_remove_"] button:hover,
      [class*="st-key-edit_attendees_remove_"] button:hover {
        background: #E4DAC6;
        border-color: var(--brass);
        color: var(--navy);
      }
      .title-second-line {
        color: var(--navy);
        font-family: var(--serif);
        font-size: clamp(1.65rem, 2.8vw, 2rem);
        line-height: 1.05;
        margin: 0.02rem 0 0.4rem;
      }
      .title-second-line em {
        color: var(--brass);
        font-style: italic;
      }
      .intro-copy {
        color: var(--muted);
        font-size: 0.86rem;
        line-height: 1.45;
        margin: 0 0 1.3rem;
        max-width: 35rem;
      }
      .section-title {
        align-items: baseline;
        border-bottom: 1px solid var(--line);
        color: var(--navy);
        display: flex;
        font-family: var(--serif);
        font-size: 1.22rem;
        gap: 0.55rem;
        line-height: 1.25;
        margin: 1rem 0 0.65rem;
        padding: 0 0 0.38rem;
      }
      .section-number {
        color: var(--brass);
        font-family: var(--serif);
        font-size: 1.42rem;
        font-style: italic;
      }
      .section-note {
        color: var(--muted);
        font-size: 0.78rem;
        margin: -0.25rem 0 0.6rem;
      }
      .stApp [data-testid="stTextInput"] input,
      .stApp [data-testid="stTextArea"] textarea,
      .stApp [data-testid="stMultiSelect"] > div > div {
        background: var(--input-bg);
        border: 1px solid var(--line);
        border-radius: var(--radius);
        color: var(--ink);
      }
      .stApp [data-testid="stTextInput"] input,
      .stApp [data-testid="stMultiSelect"] > div > div { min-height: 2.45rem; }
      .stApp [data-testid="stTextArea"] textarea:focus,
      .stApp [data-testid="stTextInput"] input:focus,
      .stApp [data-testid="stMultiSelect"] > div > div:focus-within {
        border-color: var(--navy);
        box-shadow: 0 0 0 1px var(--navy);
      }
      textarea[aria-label="Rough meeting notes"] {
        background-color: var(--input-bg) !important;
        background-image:
          linear-gradient(to right, transparent 0, transparent 30px, #DCAFA5 30px, #DCAFA5 31px, transparent 31px),
          repeating-linear-gradient(to bottom, transparent 0, transparent 27px, #E8DFCF 27px, #E8DFCF 28px) !important;
        background-position: 0 0, 0 10px !important;
        background-size: 100% 100%, 100% 28px !important;
        line-height: 28px !important;
        padding: 6px 12px 6px 42px !important;
      }
      .st-key-upload_zone {
        background: rgba(251, 248, 241, 0.52);
        border: 1px dashed var(--brass) !important;
        border-radius: var(--radius);
        padding: 0.15rem 0.65rem 0.5rem;
      }
      .st-key-upload_zone [data-testid="stFileUploader"] section {
        background: transparent;
        border: 0;
        min-height: 3rem;
      }
      .st-key-grammar_panel {
        background: rgba(251, 248, 241, 0.45);
        border: 1px dashed var(--line) !important;
        border-radius: var(--radius);
        padding: 0.65rem 0.8rem 0.45rem;
      }
      .grammar-title {
        color: var(--navy);
        font-family: var(--serif);
        font-size: 1rem;
        margin: 0;
      }
      .grammar-subtitle {
        color: var(--muted);
        font-size: 0.75rem;
        margin: 0.12rem 0 0;
      }
      .optional-badge {
        background: #EFE7D6;
        border: 1px solid var(--line);
        border-radius: 999px;
        color: #6B5A3E;
        display: inline-block;
        font-family: var(--sans);
        font-size: 0.65rem;
        margin-left: 0.35rem;
        padding: 0.08rem 0.4rem;
        vertical-align: 0.12rem;
      }
      .st-key-generate_minutes button {
        background: var(--navy);
        border: 0;
        border-bottom: 2px solid var(--brass);
        border-radius: 7px;
        color: #FFFDF8;
        font-family: var(--serif);
        font-size: 1rem;
        min-height: 2.65rem;
        transition: background-color 120ms ease;
      }
      .st-key-generate_minutes button:hover { background: #293654; color: #FFFDF8; }
      .st-key-generate_minutes button:focus-visible,
      .st-key-preview_button button:focus-visible,
      .st-key-download_mom button:focus-visible {
        outline: 3px solid var(--brass);
        outline-offset: 2px;
      }
      .toolbar-label {
        color: var(--muted);
        font-size: 0.76rem;
        padding-top: 0.45rem;
      }
      .paper-preview {
        background: var(--document-bg);
        border: 1px solid #E3DED3;
        border-radius: 3px;
        box-shadow: 0 5px 18px rgba(50, 43, 30, 0.10);
        color: #252525;
        margin: 0.25rem 0 1rem;
        min-height: 24rem;
        padding: clamp(1.4rem, 5vw, 3.4rem) clamp(1.15rem, 5.5vw, 3.65rem);
      }
      .paper-institution {
        color: #5D5A55;
        font-family: var(--sans);
        font-size: 0.69rem;
        letter-spacing: 0.03em;
        text-align: center;
      }
      .paper-department {
        color: #5D5A55;
        font-family: var(--sans);
        font-size: 0.75rem;
        margin-top: 0.8rem;
        text-align: center;
      }
      .paper-title {
        color: #191919;
        font-family: var(--serif);
        font-size: clamp(1.25rem, 2.4vw, 1.65rem);
        line-height: 1.2;
        margin: 0.42rem 0 0.25rem;
        text-align: center;
      }
      .paper-meta {
        color: #77736B;
        font-family: var(--sans);
        font-size: 0.72rem;
        line-height: 1.55;
        text-align: center;
      }
      .paper-rule {
        border: 0;
        border-top: 1px solid var(--navy);
        margin: 0.8rem 0 0.85rem;
      }
      .paper-section {
        border-left: 2px solid var(--green);
        margin: 0.45rem 0 1.05rem;
        padding: 0.05rem 0 0.1rem 0.65rem;
      }
      .paper-section h3, .paper-agenda h3 {
        color: #252525;
        font-family: var(--serif);
        font-size: 1rem;
        font-weight: 500;
        margin: 0 0 0.3rem;
      }
      .paper-section p, .paper-agenda p {
        color: #383632;
        font-family: var(--serif);
        font-size: 0.83rem;
        line-height: 1.58;
        margin: 0.15rem 0;
        white-space: normal;
      }
      .paper-agenda {
        border-top: 1px solid #E9E3D7;
        margin: 0.65rem 0;
        padding-top: 0.55rem;
      }
      .paper-label { color: #666158; font-family: var(--sans); font-size: 0.69rem; }
      .empty-note {
        color: #857B6D;
        font-family: var(--serif);
        font-size: 0.83rem;
        font-style: italic;
        margin: 1.25rem 0 1.55rem;
        text-align: center;
      }
      .skeleton-line {
        background: #EEE8D9;
        border-radius: 999px;
        height: 6px;
        margin: 0.45rem 0;
      }
      .st-key-preview_button button {
        background: transparent;
        border: 1px solid var(--navy);
        color: var(--navy);
      }
      .st-key-download_mom button {
        background: var(--navy);
        border-color: var(--navy);
        color: #FFFDF8;
      }
      .stApp [data-testid="stFileUploader"] { color: var(--muted); }
      .stApp hr { border-color: var(--line); }
      @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after { scroll-behavior: auto !important; transition: none !important; }
      }
      @media (max-width: 680px) {
        .block-container { padding: 0.85rem 0.8rem 2rem; }
        .paper-preview { min-height: 18rem; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def _local_grammar_status() -> tuple[bool, str]:
    """Check local artifacts without loading the large model into memory."""
    from nlp.settings import MODEL_DIR, SPACY_MODEL

    model_files = (
        (MODEL_DIR / "config.json").is_file()
        and (MODEL_DIR / "tokenizer_config.json").is_file()
        and any((MODEL_DIR / name).is_file() for name in ("tokenizer.json", "spiece.model"))
        and any((MODEL_DIR / name).is_file() for name in ("pytorch_model.bin", "model.safetensors"))
    )
    try:
        spacy_available = importlib.util.find_spec(SPACY_MODEL) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        spacy_available = Path(SPACY_MODEL).exists()
    if model_files and spacy_available:
        return True, "Local model and spaCy files detected"
    missing = []
    if not model_files:
        missing.append("T5 model files")
    if not spacy_available:
        missing.append("spaCy English model")
    return False, "Optional grammar correction unavailable: " + " and ".join(missing)


def _read_upload(upload) -> tuple[str | None, str | None, str | None]:
    """Return extracted text, upload identity, and a validation message."""
    if upload is None:
        return None, None, None
    if upload.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        return None, None, f"Files must be {MAX_UPLOAD_SIZE_MB} MB or smaller."
    content = upload.getvalue()
    identity = hashlib.sha256(upload.name.encode("utf-8") + content).hexdigest()
    if upload.name.casefold().endswith(".txt"):
        try:
            return content.decode("utf-8-sig"), identity, None
        except UnicodeDecodeError:
            return None, identity, "TXT files must use UTF-8 encoding."
    try:
        return extract_docx_text(content, upload.name).text, identity, None
    except DocxInputError as exc:
        return None, identity, str(exc)


def _load_uploaded_notes() -> None:
    """Use the uploader callback so notes update before their widget rerenders."""
    upload = st.session_state.get("source_upload")
    if upload is None:
        st.session_state["_upload_error"] = None
        st.session_state["_upload_name"] = None
        st.session_state["_upload_size"] = None
        return
    text, identity, error = _read_upload(upload)
    st.session_state["_upload_error"] = error
    st.session_state["_upload_name"] = upload.name
    st.session_state["_upload_size"] = upload.size
    if not error and identity != st.session_state.get("_source_identity"):
        st.session_state["source_notes"] = text or ""
        st.session_state["_source_identity"] = identity


def _split_attendees(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,;\n]+", value or "") if part.strip()]


def _split_lines(value: str) -> list[str]:
    return [line.strip() for line in (value or "").splitlines() if line.strip()]


def _add_attendee(state_key: str, input_key: str) -> None:
    name = st.session_state.get(input_key, "").strip()
    current = list(st.session_state.get(state_key, []))
    if name and name.casefold() not in {value.casefold() for value in current}:
        current.append(name)
    st.session_state[state_key] = current
    st.session_state[input_key] = ""


def _remove_attendee(state_key: str, index: int) -> None:
    current = list(st.session_state.get(state_key, []))
    if 0 <= index < len(current):
        current.pop(index)
    st.session_state[state_key] = current


def _attendee_editor(state_key: str, source: str, prefix: str, label: str) -> str:
    if state_key not in st.session_state:
        st.session_state[state_key] = _split_attendees(source)
    names = st.session_state[state_key]
    if names:
        for row_start in range(0, len(names), 5):
            row = st.columns(5)
            for index in range(row_start, min(row_start + 5, len(names))):
                row[index - row_start].button(
                    f"{names[index]}  ×",
                    key=f"{prefix}_remove_{index}",
                    help=f"Remove {names[index]}",
                    on_click=_remove_attendee,
                    args=(state_key, index),
                    use_container_width=True,
                )
    add_col, button_col = st.columns([5, 1])
    add_col.text_input(label, key=f"{prefix}_new", placeholder="Add a name")
    button_col.markdown("<div style='height:1.65rem'></div>", unsafe_allow_html=True)
    button_col.button(
        "Add",
        key=f"{prefix}_add",
        on_click=_add_attendee,
        args=(state_key, f"{prefix}_new"),
        use_container_width=True,
    )
    return ", ".join(st.session_state.get(state_key, []))


def _append_agenda_item() -> None:
    mom = st.session_state.get("mom")
    if mom is not None:
        mom.setdefault("agenda_items", []).append(
            {"_ui_id": uuid4().hex, "agenda_item": "", "proceedings": "", "resolution": "", "action_plan": ""}
        )


def _remove_agenda_item(item_id: str) -> None:
    mom = st.session_state.get("mom")
    if mom is not None:
        mom["agenda_items"] = [
            item for item in mom.get("agenda_items", [])
            if item.get("_ui_id") != item_id
        ]


def _escape(value: object) -> str:
    return html.escape(str(value or "")).replace("\n", "<br>")


def _preview_markup(minutes: MeetingMinutes, generated: bool) -> str:
    title = minutes.meeting_title or "Minutes of Meeting"
    details = [minutes.date, minutes.start_time, minutes.end_time, minutes.venue]
    meta = [value for value in details if value]
    if minutes.coordinator:
        meta.append(f"Chair: {minutes.coordinator}")
    parts = [
        '<article class="paper-preview">',
        '<div class="paper-institution">MIT Art, Design and Technology University, Pune</div>',
        f'<div class="paper-department">{_escape(minutes.department)}</div>' if minutes.department else "",
        f'<div class="paper-title">{_escape(title)}</div>',
        f'<div class="paper-meta">{_escape(" · ".join(meta))}</div>' if meta else "",
        '<hr class="paper-rule">',
    ]
    attendees = _escape(minutes.attendees)
    absentees = _escape(minutes.absentees)
    absent_no_intimation = _escape(minutes.absent_without_intimation)
    substitutes = _escape(minutes.substitutes)
    parts.append('<section class="paper-section"><h3>Attendance</h3>')
    if attendees:
        parts.append(f'<p><span class="paper-label">Present: </span>{attendees}</p>')
    if absentees:
        parts.append(f'<p><span class="paper-label">Unable to attend: </span>{absentees}</p>')
    if absent_no_intimation:
        parts.append(f'<p><span class="paper-label">Absent without intimation: </span>{absent_no_intimation}</p>')
    if substitutes:
        parts.append(f'<p><span class="paper-label">Substitutes / representatives: </span>{substitutes}</p>')
    parts.append('</section>')

    if not generated:
        parts.extend([
            '<div class="empty-note">Sections appear here after you generate.</div>',
            '<div class="skeleton-line" style="width:100%"></div>',
            '<div class="skeleton-line" style="width:92%"></div>',
            '<div class="skeleton-line" style="width:84%"></div>',
            '<div class="skeleton-line" style="width:62%"></div>',
        ])
    else:
        if minutes.opening_remarks:
            parts.append(f'<section class="paper-agenda"><h3>Opening Proceedings</h3><p>{_escape(minutes.opening_remarks)}</p></section>')
        for index, item in enumerate(minutes.agenda_items or [], 1):
            if isinstance(item, dict):
                item = AgendaItem(
                    agenda_item=item.get("agenda_item", ""),
                    proceedings=item.get("proceedings", ""),
                    resolution=item.get("resolution", ""),
                    action_plan=item.get("action_plan", ""),
                )
            parts.append(f'<section class="paper-agenda"><h3>Agenda item {index}: {_escape(item.agenda_item)}</h3>')
            for label, value in (
                ("Proceedings", item.proceedings),
                ("Resolution", item.resolution),
                ("Action Plan", item.action_plan),
            ):
                if value:
                    parts.append(f'<p><span class="paper-label">{label}: </span>{_escape(value)}</p>')
            parts.append('</section>')
        if minutes.conclusion:
            parts.append(f'<section class="paper-agenda"><h3>Conclusion</h3><p>{_escape(minutes.conclusion)}</p></section>')
        if minutes.next_meeting_date:
            parts.append(f'<p><span class="paper-label">Next meeting: </span>{_escape(minutes.next_meeting_date)}</p>')
        parts.append('<p class="paper-label">Submitted for review and approval.</p>')
    parts.append('</article>')
    return "".join(part for part in parts if part)


@st.dialog("Document preview")
def _show_preview(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


@st.cache_resource(show_spinner="Loading local grammar model…")
def load_grammar_tools():
    from nlp.model import load_local_rewriter
    from nlp.preprocessing import load_spacy_pipeline
    from nlp.settings import MODEL_DIR, PROMPT_PREFIX

    return load_spacy_pipeline(), load_local_rewriter(MODEL_DIR, prompt_prefix=PROMPT_PREFIX)


st.title("Minutes of Meeting,")
st.markdown('<div class="title-second-line"><em>typeset</em> from your notes.</div>', unsafe_allow_html=True)
st.markdown(
    '<p class="intro-copy">Everything runs on this computer. Fill in the details and watch '
    'the record take shape on the right.</p>',
    unsafe_allow_html=True,
)
st.markdown('<div class="section-title"><span class="section-number">1</span> Meeting details</div>', unsafe_allow_html=True)
meeting_title = st.text_input("Meeting title", key="meeting_title")
department = st.text_input("Department", key="department")
date_col, time_col = st.columns(2)
meeting_date = date_col.text_input("Date", key="meeting_date", placeholder="e.g. 22 October 2026")
start_time = time_col.text_input("Time", key="start_time", placeholder="e.g. 10:30 AM")
venue_col, chair_col = st.columns(2)
venue = venue_col.text_input("Venue", key="venue", placeholder="Meeting venue")
coordinator = chair_col.text_input("Chaired by", key="coordinator", placeholder="Meeting chair")
with st.expander("Additional meeting details", expanded=False):
    optional_a, optional_b, optional_c = st.columns(3)
    meeting_number = optional_a.text_input("Meeting number (optional)", key="meeting_number")
    academic_year = optional_b.text_input("Academic year (optional)", key="academic_year")
    reference = optional_c.text_input("Reference number (optional)", key="reference_number")
    end_time = st.text_input("End time (optional)", key="end_time")

st.markdown("**Attendance**")
attendees_text = _attendee_editor(
    "attendee_chips", st.session_state.get("attendees", ""), "attendees", "Add an attendee"
)
with st.expander("Other attendance details", expanded=False):
    attendance_a, attendance_b = st.columns(2)
    absentees = attendance_a.text_area("Unable to attend (if known)", key="absentees", height=70)
    absent_without_intimation = attendance_b.text_area(
        "Absent without intimation (if known)", key="absent_without_intimation", height=70
    )
    substitutes = st.text_area("Substitutes / representatives (if any)", key="substitutes", height=70)

st.markdown('<div class="section-title"><span class="section-number">2</span> Your notes</div>', unsafe_allow_html=True)
st.session_state.setdefault("source_notes", "")
notes = st.text_area(
    "Rough meeting notes",
    key="source_notes",
    height=245,
    placeholder="Write what was discussed, what was explicitly decided, and any stated follow-up. Do not add details that were not recorded.",
)
with st.container(key="upload_zone", border=False):
    uploaded = st.file_uploader(
        "Drop TXT or DOCX to replace",
        type=["txt", "docx"],
        key="source_upload",
        on_change=_load_uploaded_notes,
        help="UTF-8 TXT or DOCX, up to 10 MB.",
    )
    upload_error = st.session_state.get("_upload_error")
    if upload_error:
        st.error(upload_error)
    elif uploaded is not None:
        size_kb = uploaded.size / 1024
        st.caption(f"{uploaded.name} · {size_kb:.0f} KB · Drop another file to replace")

grammar_ready, grammar_status = _local_grammar_status()
with st.container(key="grammar_panel", border=False):
    grammar_left, grammar_right = st.columns([5, 1])
    grammar_left.markdown(
        '<div class="grammar-title">Fix grammar with local T5 '
        '<span class="optional-badge">Optional</span></div>'
        '<div class="grammar-subtitle">Slower. Cleans spelling before organizing.</div>',
        unsafe_allow_html=True,
    )
    use_grammar = grammar_right.toggle(
        "Fix grammar with local T5",
        value=True,
        key="use_local_grammar",
        label_visibility="collapsed",
        help="Use the local T5 model before organizing the notes.",
    )
    if not grammar_ready:
        st.warning(f"{grammar_status}. You can still generate minutes without correction.")
    else:
        st.caption(grammar_status)

generate = st.button("Generate minutes", type="primary", key="generate_minutes", use_container_width=True)

if generate:
    if not notes.strip():
        st.error("Enter notes before generating minutes.")
    elif uploaded is not None and upload_error:
        st.error("Resolve the selected file error or remove the file before generating.")
    else:
        corrected = notes.strip()
        correction_warnings = []
        correction_notice = "Grammar correction was not requested; source notes were used as-is."
        if use_grammar:
            try:
                from nlp.pipeline import improve_notes
                from nlp.settings import MODEL_DIR

                nlp, rewriter = load_grammar_tools()
                with st.spinner("Correcting grammar locally…"):
                    correction_result = improve_notes(notes, nlp, rewriter, model_dir=str(MODEL_DIR))
                    corrected = correction_result.improved
                    correction_warnings = list(correction_result.warnings)
                correction_notice = (
                    "Local grammar correction completed. Compare with the preserved source notes "
                    "and review for meaning changes."
                )
            except (FileNotFoundError, RuntimeError, ValueError, OSError, ImportError) as exc:
                correction_notice = (
                    f"Grammar correction unavailable ({exc}). Source notes were retained without correction."
                )
        try:
            mom = organize_notes(notes, corrected)
        except ValueError as exc:
            st.error(str(exc))
        else:
            mom.meeting_title = meeting_title
            mom.meeting_number = meeting_number
            mom.department = department
            mom.academic_year = academic_year
            mom.reference_number = reference
            mom.date = meeting_date or mom.date
            mom.start_time = start_time or mom.start_time
            mom.end_time = end_time
            mom.venue = venue or mom.venue
            mom.coordinator = coordinator
            mom.attendees = attendees_text
            mom.absentees = absentees
            mom.absent_without_intimation = absent_without_intimation
            mom.substitutes = substitutes
            mom_data = mom.to_dict()
            for item in mom_data.get("agenda_items") or []:
                item["_ui_id"] = uuid4().hex
            st.session_state["mom"] = mom_data
            st.session_state["generated_from"] = notes
            st.session_state["correction_notice"] = correction_notice
            st.session_state["grammar_warnings"] = correction_warnings
            st.success("Minutes draft generated. Review each field before exporting.")


if "mom" in st.session_state:
    data = st.session_state["mom"]
    st.markdown('<div class="section-title">Review and edit generated minutes</div>', unsafe_allow_html=True)
    st.caption(st.session_state.get("correction_notice", "Review all generated fields."))
    if notes != st.session_state.get("generated_from", ""):
        st.warning("Source notes have changed since this draft was generated. Generate again to rebuild the minutes from the current source.")
    for warning in st.session_state.get("grammar_warnings", []):
        st.warning(warning)
    st.warning(
        "Agenda items are split from the supplied source notes. Resolutions and action plans "
        "use explicit wording cues and may be incomplete or wrong. Verify them against the original notes."
    )
    with st.expander("Compare original and corrected notes", expanded=False):
        source_col, corrected_col = st.columns(2)
        source_col.text_area("Original notes (preserved)", data["original_notes"], height=150, disabled=True)
        data["corrected_notes"] = corrected_col.text_area(
            "Corrected wording", data.get("corrected_notes", ""), height=150, key="corrected_notes_edit"
        )

    with st.expander("Edit meeting details and attendance", expanded=False):
        edit_a, edit_b, edit_c = st.columns(3)
        for key, label, column in (
            ("meeting_title", "Meeting title", edit_a),
            ("department", "Department / committee", edit_b),
            ("meeting_number", "Meeting number", edit_c),
            ("academic_year", "Academic year", edit_a),
            ("reference_number", "Reference number", edit_b),
            ("date", "Date", edit_c),
            ("start_time", "Start time", edit_a),
            ("end_time", "End time", edit_b),
            ("venue", "Venue", edit_c),
            ("coordinator", "Chaired by", edit_a),
        ):
            data[key] = column.text_input(label, data.get(key, ""), key=f"edit_{key}")
        data["attendees"] = _attendee_editor(
            "edit_attendee_chips", data.get("attendees", ""), "edit_attendees", "Add an attendee"
        )
        edit_attendance_a, edit_attendance_b = st.columns(2)
        data["absentees"] = edit_attendance_a.text_area(
            "Unable to attend", data.get("absentees", ""), key="edit_absentees"
        )
        data["absent_without_intimation"] = edit_attendance_b.text_area(
            "Absent without intimation", data.get("absent_without_intimation", ""), key="edit_absent_without_intimation"
        )
        data["substitutes"] = st.text_area(
            "Substitutes / representatives", data.get("substitutes", ""), key="edit_substitutes"
        )
        data["opening_remarks"] = st.text_area(
            "Opening proceedings", data.get("opening_remarks", ""), key="edit_opening"
        )

    st.markdown("#### Agenda and proceedings")
    agenda = data.setdefault("agenda_items", [])
    st.button("Add agenda item", on_click=_append_agenda_item, key="add_agenda_item")
    for index, item in enumerate(agenda):
        item_id = item.setdefault("_ui_id", uuid4().hex)
        with st.expander(f"Agenda item {index + 1}", expanded=(index == 0)):
            item["agenda_item"] = st.text_input(
                "Agenda Item", item.get("agenda_item", ""), key=f"agenda_{item_id}"
            )
            item["proceedings"] = st.text_area(
                "Proceedings", item.get("proceedings", ""), key=f"proceedings_{item_id}"
            )
            resolution_col, action_col = st.columns(2)
            item["resolution"] = resolution_col.text_area(
                "Resolution (only if explicitly decided)",
                item.get("resolution", ""), key=f"resolution_{item_id}"
            )
            item["action_plan"] = action_col.text_area(
                "Action plan (only stated responsibilities/deadlines)",
                item.get("action_plan", ""), key=f"action_{item_id}"
            )
            st.button(
                "Remove agenda item", key=f"remove_{item_id}",
                on_click=_remove_agenda_item, args=(item_id,)
            )

    data["conclusion"] = st.text_area(
        "Conclusion / closing remarks", data.get("conclusion", ""), key="edit_conclusion"
    )
    data["next_meeting_date"] = st.text_input(
        "Next meeting date", data.get("next_meeting_date", ""), key="edit_next_meeting"
    )
    with st.expander("Approval fields (blank unless supplied by an authorized person)"):
        for key, label in (
            ("prepared_by", "Prepared by"), ("reviewed_by", "Reviewed by"),
            ("approved_by", "Approved by"), ("approval_date", "Approval date"),
        ):
            data[key] = st.text_input(label, data.get(key, ""), key=f"edit_{key}")

    st.markdown("#### Extracted facts (review and correct before exporting)")
    st.caption(
        "These were extracted from your notes using conservative wording cues. "
        "Correct or remove anything that does not match the original notes."
    )
    fact_a, fact_b, fact_c = st.columns(3)
    data["deadlines"] = _split_lines(
        fact_a.text_area(
            "Deadlines (one per line)", "\n".join(data.get("deadlines", [])),
            key="edit_deadlines", height=110,
        )
    )
    data["responsible_persons"] = _split_lines(
        fact_b.text_area(
            "Responsible persons (one per line)", "\n".join(data.get("responsible_persons", [])),
            key="edit_responsible_persons", height=110,
        )
    )
    data["key_decisions"] = _split_lines(
        fact_c.text_area(
            "Confirmed decisions (one per line)", "\n".join(data.get("key_decisions", [])),
            key="edit_key_decisions", height=110,
        )
    )
    fact_d, fact_e, fact_f = st.columns(3)
    data["action_items"] = _split_lines(
        fact_d.text_area(
            "Action items (one per line)", "\n".join(data.get("action_items", [])),
            key="edit_action_items", height=110,
        )
    )
    data["discussion_points"] = _split_lines(
        fact_e.text_area(
            "Discussion points (one per line)", "\n".join(data.get("discussion_points", [])),
            key="edit_discussion_points", height=110,
        )
    )
    data["tentative_items"] = _split_lines(
        fact_f.text_area(
            "Tentative / uncertain items (one per line)", "\n".join(data.get("tentative_items", [])),
            key="edit_tentative_items", height=110,
        )
    )
    st.session_state["mom"] = data

    agenda_for_export = [
        AgendaItem(
            agenda_item=item.get("agenda_item", ""),
            proceedings=item.get("proceedings", ""),
            resolution=item.get("resolution", ""),
            action_plan=item.get("action_plan", ""),
        )
        for item in agenda
    ]
    minutes_data = {key: value for key, value in data.items() if key != "agenda_items"}
    minutes = MeetingMinutes(**minutes_data, agenda_items=agenda_for_export)
    generated = True
else:
    minutes = MeetingMinutes(
        meeting_title=meeting_title,
        department=department,
        meeting_number=meeting_number if "meeting_number" in locals() else "",
        academic_year=academic_year if "academic_year" in locals() else "",
        reference_number=reference if "reference" in locals() else "",
        date=meeting_date,
        start_time=start_time,
        end_time=end_time if "end_time" in locals() else "",
        venue=venue,
        coordinator=coordinator,
        attendees=attendees_text,
        absentees=absentees if "absentees" in locals() else "",
        absent_without_intimation=absent_without_intimation if "absent_without_intimation" in locals() else "",
        substitutes=substitutes if "substitutes" in locals() else "",
        agenda_items=[],
    )
    generated = False

preview = _preview_markup(minutes, generated)
st.divider()
toolbar_left, toolbar_preview, toolbar_download = st.columns([5, 1.15, 1.55], vertical_alignment="center")
toolbar_left.markdown('<div class="toolbar-label">Live preview</div>', unsafe_allow_html=True)
preview_clicked = toolbar_preview.button("Preview", key="preview_button", use_container_width=True)
docx_bytes = build_mom_docx(minutes) if generated else None
if generated:
    toolbar_download.download_button(
        "Download DOCX",
        data=docx_bytes,
        file_name="faculty_minutes_of_meeting.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        type="primary",
        key="download_mom",
        use_container_width=True,
    )
else:
    toolbar_download.button("Download DOCX", disabled=True, key="download_mom_disabled", use_container_width=True)
if preview_clicked:
    _show_preview(preview)

st.markdown(preview, unsafe_allow_html=True)
