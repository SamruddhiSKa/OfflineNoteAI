"""Editable faculty Minutes of Meeting DOCX creation."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

from processing import (
    AgendaItem,
    MeetingMinutes,
    _is_valid_topic_hint,
    action_table_rows,
)

TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "faculty_mom_template.docx"

EMPTY_PLACEHOLDER = "Not specified"


def _field(doc, label: str, value: str) -> None:
    if not value:
        return
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(f"{label}: ")
    run.bold = True
    p.add_run(value)


def _bullets(doc, items: list[str], label: str) -> None:
    if not items:
        return
    doc.add_heading(label, level=2)
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(item)
        p.paragraph_format.space_after = Pt(2)


def _numbered_items(doc, items: list[str], label: str) -> None:
    if not items:
        return
    doc.add_heading(label, level=2)
    for index, item in enumerate(items, 1):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(f"{index}. ")
        run.bold = True
        p.add_run(item)


def _heading(doc, text: str) -> None:
    doc.add_heading(text, level=1)


def _has_value(value: str) -> bool:
    return bool(value and value.strip())


def build_mom_docx(minutes: MeetingMinutes) -> bytes:
    invalid_titles = [
        item.agenda_item for item in (minutes.agenda_items or [])
        if item.agenda_item.strip() and not _is_valid_topic_hint(item.agenda_item)
    ]
    if invalid_titles:
        raise ValueError(
            "Cannot export agenda items with sentence-like titles: "
            + ", ".join(invalid_titles)
        )

    # Start from the shipped blank template so exports retain its editable
    # styles, page settings, borders, and reusable institutional structure.
    doc = Document(TEMPLATE_PATH) if TEMPLATE_PATH.is_file() else Document()
    body = doc._element.body
    for child in list(body):
        if child.tag != qn("w:sectPr"):
            body.remove(child)
    section = doc.sections[0]
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)
    normal = doc.styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(10)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(
        minutes.institution or "MIT Art, Design and Technology University, Pune"
    )
    r.bold = True
    r.font.size = Pt(15)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("Department / Committee: ").bold = True
    p.add_run(minutes.department or EMPTY_PLACEHOLDER)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(minutes.meeting_title or "MINUTES OF MEETING").bold = True
    if minutes.academic_year:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run(f"Academic Year {minutes.academic_year}")

    has_meeting_detail = any(
        _has_value(minutes.__dict__[key])
        for key in (
            "reference_number", "meeting_number", "date", "start_time",
            "end_time", "venue", "coordinator", "notes_recorded_by",
        )
    )
    if has_meeting_detail:
        _heading(doc, "Meeting Details")
        for label, value in (
            ("Reference Number", minutes.reference_number),
            ("Meeting Number", minutes.meeting_number),
            ("Date", minutes.date),
            ("Start Time", minutes.start_time),
            ("End Time", minutes.end_time),
            ("Venue", minutes.venue),
            ("Coordinator / Chair", minutes.coordinator),
            ("Notes recorded by", minutes.notes_recorded_by),
        ):
            _field(doc, label, value)

    has_attendance = any(
        _has_value(minutes.__dict__[key])
        for key in ("attendees", "absentees", "absent_without_intimation", "substitutes")
    )
    if has_attendance:
        _heading(doc, "Attendance")
        _field(doc, "Members Present", minutes.attendees or EMPTY_PLACEHOLDER)
        _field(doc, "Unable to Attend", minutes.absentees)
        _field(doc, "Absent Without Intimation", minutes.absent_without_intimation)
        _field(doc, "Substitutes / Representatives", minutes.substitutes)

    if minutes.opening_remarks:
        _heading(doc, "Opening Proceedings")
        doc.add_paragraph(minutes.opening_remarks)

    if minutes.agenda_items:
        _heading(doc, "Agenda and Proceedings")
        for item in minutes.agenda_items or []:
            table = doc.add_table(rows=0, cols=2)
            table.style = "Table Grid"
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            for label, value in (
                ("Agenda Item", item.agenda_item or "Not specified in the notes"),
                ("Proceedings", item.proceedings or "Not specified in the notes"),
                ("Resolution", item.resolution or "Not specified in the notes"),
                ("Action Plan", item.action_plan or "Not specified in the notes"),
            ):
                row = table.add_row().cells
                row[0].text = label
                row[1].text = value
                for paragraph in row[0].paragraphs:
                    for run in paragraph.runs:
                        run.bold = True
            doc.add_paragraph().paragraph_format.space_after = Pt(2)

    for supporting_table in minutes.supporting_tables:
        title = (
            supporting_table.title
            if isinstance(supporting_table, dict)
            else supporting_table.title
        )
        rows = (
            supporting_table.get("rows", [])
            if isinstance(supporting_table, dict)
            else supporting_table.rows
        )
        if not rows:
            continue
        _heading(doc, title or "Supporting Data")
        column_count = max((len(row) for row in rows), default=0)
        if not column_count:
            continue
        table = doc.add_table(rows=0, cols=column_count)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for row_values in rows:
            cells = table.add_row().cells
            for index, cell in enumerate(cells):
                cell.text = str(row_values[index]) if index < len(row_values) else ""
        if table.rows:
            for cell in table.rows[0].cells:
                for run in cell.paragraphs[0].runs:
                    run.bold = True

    action_rows = action_table_rows(minutes)
    if action_rows:
        _heading(doc, "Action Items")
        action_table = doc.add_table(rows=1, cols=3)
        action_table.style = "Table Grid"
        action_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for cell, label in zip(
            action_table.rows[0].cells,
            ("Responsible Person", "Action Required", "Deadline"),
        ):
            cell.text = label
            for run in cell.paragraphs[0].runs:
                run.bold = True
        for owner, description, deadline in action_rows:
            cells = action_table.add_row().cells
            cells[0].text = owner
            cells[1].text = description
            cells[2].text = deadline

    if minutes.other_matters:
        _heading(doc, "Other Matters")
        for item in minutes.other_matters:
            doc.add_paragraph(item)

    meeting_context = " ".join(
        value
        for item in (minutes.agenda_items or [])
        for value in (item.proceedings, item.resolution, item.action_plan)
    ).casefold()
    meeting_context += " " + " ".join(minutes.other_matters).casefold()
    meeting_context += " " + " ".join(
        " ".join(
            str(getattr(action, key, "") or "")
            for key in ("description", "source_statement", "owner", "deadline")
        )
        for action in minutes.structured_actions
    ).casefold()

    def unrepresented(values: list[str]) -> list[str]:
        return [
            value for value in values
            if value.strip() and value.strip().casefold() not in meeting_context
        ]

    seen_additional: set[str] = set()
    for label, values in (
        ("Additional Confirmed Decisions", minutes.key_decisions),
        ("Tentative Decisions", minutes.tentative_decisions),
        ("Tentative Matters", minutes.tentative_items),
        ("Pending Approvals", minutes.pending_approvals),
        ("Unresolved Questions", minutes.unresolved_questions),
    ):
        distinct_values = []
        for value in unrepresented(values):
            key = value.casefold()
            if key not in seen_additional:
                seen_additional.add(key)
                distinct_values.append(value)
        if distinct_values:
            _bullets(doc, distinct_values, label)

    if not minutes.review_required and not minutes.structured_actions:
        for label, values in (
            ("Additional Deadlines", minutes.deadlines),
            ("Responsible Persons", minutes.responsible_persons),
        ):
            if values:
                _bullets(doc, values, label)

    if minutes.conclusion:
        _heading(doc, "Closing Proceedings")
        doc.add_paragraph(minutes.conclusion)
    if _has_value(minutes.next_meeting_date):
        _heading(doc, "Next Meeting")
        doc.add_paragraph(minutes.next_meeting_date)
    doc.add_paragraph("Submitted for review and approval.")

    if minutes.prepared_by:
        _heading(doc, "Prepared by")
        name, separator, designation = minutes.prepared_by.partition(",")
        doc.add_paragraph(name.strip())
        if separator and designation.strip():
            doc.add_paragraph(designation.strip())

    out = BytesIO()
    doc.save(out)
    return out.getvalue()


def create_reusable_template() -> bytes:
    """Create a blank template with reusable sections and agenda table."""
    return build_mom_docx(MeetingMinutes(agenda_items=[AgendaItem("")]))
