"""Editable faculty Minutes of Meeting DOCX creation."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

from processing import AgendaItem, MeetingMinutes

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


def _heading(doc, text: str) -> None:
    doc.add_heading(text, level=1)


def _has_value(value: str) -> bool:
    return bool(value and value.strip())


def build_mom_docx(minutes: MeetingMinutes) -> bytes:
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
    r = p.add_run("MIT Art, Design and Technology University, Pune")
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
            "end_time", "venue", "coordinator",
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
        for index, item in enumerate(minutes.agenda_items or [], 1):
            table = doc.add_table(rows=0, cols=2)
            table.style = "Table Grid"
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            for label, value in (
                ("Agenda Item", item.agenda_item),
                ("Proceedings", item.proceedings),
                ("Resolution", item.resolution),
                ("Action Plan", item.action_plan),
            ):
                cells = table.add_row().cells
                cells[0].text, cells[1].text = label, value
                cells[0].width = Inches(1.35)
                cells[1].width = Inches(5.9)
                cells[0].paragraphs[0].runs[0].bold = True
            doc.add_paragraph().paragraph_format.space_after = Pt(2)

    if minutes.key_decisions:
        _bullets(doc, minutes.key_decisions, "Key Decisions")

    if minutes.deadlines:
        _bullets(doc, minutes.deadlines, "Deadlines Stated in Notes")

    if minutes.responsible_persons:
        _bullets(doc, minutes.responsible_persons, "Responsible Persons Stated in Notes")

    if minutes.tentative_items:
        _heading(doc, "Matters Requiring Confirmation")
        doc.add_paragraph(
            "The following statements were tentative or uncertain in the source notes. "
            "Confirm or correct them before final approval."
        )
        for item in minutes.tentative_items:
            p = doc.add_paragraph(style="List Bullet")
            p.add_run(item)
            p.paragraph_format.space_after = Pt(2)

    if minutes.conclusion:
        _heading(doc, "Conclusion")
        doc.add_paragraph(minutes.conclusion)
    if _has_value(minutes.next_meeting_date):
        _field(doc, "Next Meeting Date", minutes.next_meeting_date)
    doc.add_paragraph("Submitted for review and approval.")

    # The approval/signature table is part of the shipped institutional template
    # and is always rendered so the structure is preserved; fields stay blank
    # until an authorized person supplies them.
    _heading(doc, "Approval and Signatures")
    signatures = doc.add_table(rows=2, cols=3)
    signatures.style = "Table Grid"
    for cell, label, name in zip(
        signatures.rows[0].cells,
        ("Prepared by", "Reviewed by", "Approved by"),
        (minutes.prepared_by, minutes.reviewed_by, minutes.approved_by),
    ):
        cell.text = f"{label}\n\nName: {name}"
    for cell in signatures.rows[1].cells:
        cell.text = "Designation: \n\nSignature: \n\nDate: "
    if minutes.approval_date:
        signatures.rows[1].cells[2].text += minutes.approval_date

    out = BytesIO()
    doc.save(out)
    return out.getvalue()


def create_reusable_template() -> bytes:
    """Create a blank template with reusable sections and agenda table."""
    return build_mom_docx(MeetingMinutes(agenda_items=[AgendaItem("")]))
