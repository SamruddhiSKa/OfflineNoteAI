from io import BytesIO

import pytest
from docx import Document

from documents import build_mom_docx
from processing import AgendaItem, MeetingMinutes, organize_notes


def test_empty_notes_rejected():
    with pytest.raises(ValueError, match="Enter or upload"):
        organize_notes("  ")


def test_discussion_is_not_promoted_to_resolution_or_action():
    result = organize_notes("The lab timetable needs revision.")
    assert result.agenda_items[0].proceedings
    assert result.agenda_items[0].resolution == ""
    assert result.agenda_items[0].action_plan == ""
    assert result.attendees == result.date == result.approved_by == ""


def test_explicit_decision_and_action_are_retained_without_invented_deadline():
    result = organize_notes("The committee approved the revised timetable. Faculty should submit course files.")
    assert len(result.agenda_items) == 2
    assert "approved" in result.agenda_items[0].resolution
    assert result.agenda_items[1].action_plan.rstrip(".").endswith("course files")
    assert "Friday" not in result.agenda_items[1].action_plan


def test_original_notes_preserved_with_dates_and_times():
    notes = "Meeting held on 22 October at 11 am. HOD discussed syllabus completion."
    result = organize_notes(notes)
    assert result.original_notes == notes
    assert "22 October" in result.corrected_notes
    assert len(result.agenda_items) == 2


def test_sample_meeting_notes_keep_stated_deadline_without_filling_unknowns():
    notes = (
        "meeting held on 22 october at 11 am in computer science department. "
        "hod discussed syllabus completion. faculty should finish unit 4 before internal exams. "
        "lab timetable needs revision. coordinator asked faculty to submit updated course files by friday."
    )
    result = organize_notes(notes, corrected_notes="An invented resolution was approved.")
    assert len(result.agenda_items) == 5
    assert "22 october at 11 am" in result.agenda_items[0].proceedings
    assert result.agenda_items[1].resolution == ""
    assert result.agenda_items[3].action_plan == ""
    assert "friday" in result.agenda_items[4].action_plan.casefold()
    assert result.date == "22 october"
    assert result.start_time.casefold() == "11 am"
    assert result.venue == "computer science department"
    assert result.approved_by == result.attendees == ""


def test_docx_has_repeatable_agenda_tables_and_blank_approval_fields():
    minutes = MeetingMinutes(
        meeting_title="Faculty Meeting", date="22 October",
        agenda_items=[AgendaItem("Syllabus", "Unit 4 discussed", "", "Finish before exams"),
                      AgendaItem("Lab", "Timetable discussed")],
    )
    document = Document(BytesIO(build_mom_docx(minutes)))
    text = "\n".join(p.text for p in document.paragraphs)
    table_text = "\n".join(cell.text for table in document.tables for row in table.rows for cell in row.cells)
    assert "22 October" in text
    assert len(document.tables) == 3  # Two agenda tables and approval signatures.
    assert "Resolution" in table_text and "Action Plan" in table_text
    assert "Approved by" in table_text and "Signature:" in table_text
    assert "Finish before exams" in table_text
    assert "Dr. Reviewer" not in table_text


def test_reusable_template_is_editable_and_has_reference_sections():
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "templates" / "faculty_mom_template.docx"
    document = Document(path)
    text = "\n".join(p.text for p in document.paragraphs)
    table_text = "\n".join(cell.text for table in document.tables for row in table.rows for cell in row.cells)
    assert "MIT Art, Design and Technology University, Pune" in text
    assert all(label in table_text for label in ("Agenda Item", "Proceedings", "Resolution", "Action Plan"))
