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


def _field(doc, label: str, value: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(f"{label}: ")
    run.bold = True
    p.add_run(value)


def build_mom_docx(minutes: MeetingMinutes) -> bytes:
    # Start from the shipped blank template so exports retain its editable
    # styles, page settings, borders, and reusable institutional structure.
    doc = Document(TEMPLATE_PATH) if TEMPLATE_PATH.is_file() else Document()
    body = doc._element.body
    for child in list(body):
        if child.tag != qn("w:sectPr"):
            body.remove(child)
    section = doc.sections[0]
    section.top_margin = Inches(.65)
    section.bottom_margin = Inches(.65)
    section.left_margin = Inches(.75)
    section.right_margin = Inches(.75)
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
    p.add_run(minutes.department)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(minutes.meeting_title or "MINUTES OF MEETING").bold = True
    if minutes.academic_year:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run(f"Academic Year {minutes.academic_year}")

    doc.add_heading("Meeting Details", level=1)
    for label, value in (
        ("Reference Number", minutes.reference_number), ("Meeting Number", minutes.meeting_number),
        ("Date", minutes.date),
        ("Start Time", minutes.start_time), ("End Time", minutes.end_time),
        ("Venue", minutes.venue), ("Coordinator", minutes.coordinator),
    ):
        _field(doc, label, value)
    doc.add_heading("Attendance", level=1)
    _field(doc, "Members Present", minutes.attendees)
    _field(doc, "Unable to Attend", minutes.absentees)
    _field(doc, "Absent Without Intimation", minutes.absent_without_intimation)
    _field(doc, "Substitutes / Representatives", minutes.substitutes)
    if minutes.opening_remarks:
        doc.add_heading("Opening Proceedings", level=1)
        doc.add_paragraph(minutes.opening_remarks)

    doc.add_heading("Agenda and Proceedings", level=1)
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

    doc.add_heading("Conclusion", level=1)
    doc.add_paragraph(minutes.conclusion)
    _field(doc, "Next Meeting Date", minutes.next_meeting_date)
    doc.add_paragraph("Submitted for review and approval.")
    doc.add_heading("Approval and Signatures", level=1)
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
