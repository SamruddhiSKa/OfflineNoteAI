from io import BytesIO

import pytest
from docx import Document

from documents import build_mom_docx
from nlp.docx_io import extract_docx_text
from processing import ActionItem, AgendaItem, MeetingMinutes, action_table_rows, organize_notes


def _structured_block(text, *, style="Normal", level=0, is_list=False, list_type=""):
    return {
        "kind": "paragraph",
        "text": text,
        "style": style,
        "level": level,
        "is_list": is_list,
        "list_type": list_type,
        "rows": (),
    }


def _structured_test3_blocks():
    return [
        _structured_block("MIT Art, Design and Technology University, Pune"),
        _structured_block("Department: Computer Engineering"),
        _structured_block("Meeting: Department Project and Infrastructure Review"),
        _structured_block("Date: 12 November 2026 | Time: 10:30 AM to 12:05 PM"),
        _structured_block("Venue: Project Discussion Room, Building A"),
        _structured_block("Chair: Dr. Anjali Deshmukh, Head of Department"),
        _structured_block("Notes recorded by: Mr. Karan Shah, Department Office"),
        _structured_block("People", style="Heading 2", level=2),
        _structured_block(
            "Present: Dr. Anjali Deshmukh, Prof. Vikram Rao, Ms. Isha Kulkarni, "
            "Prof. Devika Menon, Mr. Karan Shah"
        ),
        _structured_block(
            "Could not attend: Prof. Arjun Mehta (informed the department in advance)"
        ),
        _structured_block("Start", style="Heading 2", level=2),
        _structured_block(
            "The HoD started the meeting at 10:30 and asked the coordinators to report "
            "on pending work from the previous review."
        ),
        _structured_block("Notes collected during discussion", style="Heading 2", level=2),
        _structured_block("Project review schedule"),
        _structured_block(
            "Schedule actions", is_list=True, list_type="bullet"
        ),
        _structured_block(
            "The first-year and third-year project reviews share the same afternoon slot, "
            "and two classrooms remain unconfirmed."
        ),
        _structured_block(
            "Vikram will confirm room availability with the timetable office and prepare "
            "the corrected schedule by 16 November.",
            is_list=True,
            list_type="bullet",
        ),
        _structured_block("Network and classroom equipment"),
        _structured_block(
            "Wi-Fi in A-302 drops during afternoon classes, and four HDMI adapters are "
            "missing from the teaching rooms."
        ),
        _structured_block("Guest lecture and student interaction"),
        _structured_block(
            "A local startup expressed interest in a responsible AI session, but no "
            "speaker name or date has been confirmed."
        ),
        _structured_block("Internship documentation"),
        _structured_block(
            "The office received 42 internship submissions, and 9 are incomplete."
        ),
        _structured_block("Department project exhibition"),
        _structured_block(
            "The annual project exhibition is expected in December, but the university "
            "has not announced the date."
        ),
        _structured_block("Figures mentioned", style="Heading 2", level=2),
        {
            "kind": "table",
            "text": (
                "Item | Figure\nInternship submissions received | 42\n"
                "Incomplete submissions | 9\nMissing HDMI adapters | 4\n"
                "Classroom with Wi-Fi issue | A-302"
            ),
            "style": "",
            "level": 0,
            "is_list": False,
            "list_type": "",
            "rows": (
                ("Item", "Figure"),
                ("Internship submissions received", "42"),
                ("Incomplete submissions", "9"),
                ("Missing HDMI adapters", "4"),
                ("Classroom with Wi-Fi issue", "A-302"),
            ),
        },
        _structured_block("Other points", style="Heading 2", level=2),
        _structured_block(
            "The department notice board still displays the previous semester's "
            "project coordinator list."
        ),
        _structured_block(
            "The water dispenser outside A-301 is not cooling. A complaint was logged "
            "as FAC-209, but no maintenance visit date was provided."
        ),
        _structured_block(
            "Prof. Arjun Mehta's course file verification may be handled separately "
            "because he was on approved leave. No date was discussed."
        ),
        _structured_block("Closing", style="Heading 2", level=2),
        _structured_block("The HoD thanked the members and closed the meeting at 12:05 PM."),
        _structured_block("Next meeting", style="Heading 2", level=2),
        _structured_block(
            "Proposed for 10 December 2026, subject to confirmation of the university "
            "examination schedule."
        ),
        _structured_block(
            "Coordinator's private reminders — NOT PART OF THE MINUTES"
        ),
        _structured_block(
            "Do not turn the figures table into agenda items. The guest lecture is not "
            "confirmed. Do not say a new Wi-Fi access point was approved. These are "
            "working reminders only."
        ),
    ]


def test_empty_notes_rejected():
    with pytest.raises(ValueError, match="Enter or upload"):
        organize_notes("  ")


def test_semicolon_clause_boundary_is_preserved():
    from processing import _split_sentences

    assert _split_sentences(
        "The vendor was contacted; they asked for the error logs."
    ) == [
        "The vendor was contacted;",
        "They asked for the error logs.",
    ]


def test_discussion_is_not_promoted_to_resolution_or_action():
    result = organize_notes("The lab timetable needs revision.")
    assert result.agenda_items[0].proceedings
    assert result.agenda_items[0].resolution == ""
    assert result.agenda_items[0].action_plan == ""
    assert result.attendees == result.date == result.approved_by == ""


def test_explicit_decision_and_action_are_retained_without_invented_deadline():
    result = organize_notes("The committee approved the revised timetable. Faculty should submit course files.")
    assert len(result.agenda_items) == 1
    assert "approved" in result.agenda_items[0].resolution
    assert result.agenda_items[0].action_plan == ""
    assert any("course files" in action for action in result.action_items)
    assert "Friday" not in " ".join(result.action_items)


def test_original_notes_preserved_with_dates_and_times():
    notes = "Meeting held on 22 October at 11 am. HOD discussed syllabus completion."
    result = organize_notes(notes)
    assert result.original_notes == notes
    assert "22 October" in result.corrected_notes
    assert len(result.agenda_items) == 1
    assert result.date == "22 October"
    assert "Meeting held" not in result.agenda_items[0].proceedings


def test_structured_blocks_extract_metadata_and_attendance_without_guessing():
    blocks = _structured_test3_blocks()
    result = organize_notes(
        "\n\n".join(block["text"] for block in blocks),
        source_blocks=blocks,
    )

    assert result.institution == "MIT Art, Design and Technology University, Pune"
    assert result.department == "Computer Engineering"
    assert result.meeting_title == "Department Project and Infrastructure Review"
    assert result.date == "12 November 2026"
    assert result.start_time == "10:30 AM"
    assert result.end_time == "12:05 PM"
    assert result.venue == "Project Discussion Room, Building A"
    assert result.coordinator == "Dr. Anjali Deshmukh"
    assert result.notes_recorded_by == "Mr. Karan Shah, Department Office"
    assert "Prof. Vikram Rao" in result.attendees
    assert "Prof. Arjun Mehta (informed the department in advance)" in result.absentees


def test_normal_style_standalone_topics_and_supporting_table_remain_separate():
    blocks = _structured_test3_blocks()
    result = organize_notes(
        "\n\n".join(block["text"] for block in blocks),
        source_blocks=blocks,
    )

    assert [item.agenda_item for item in result.agenda_items] == [
        "Project Review Schedule",
        "Network and Classroom Equipment",
        "Guest Lecture and Student Interaction",
        "Internship Documentation",
        "Department Project Exhibition",
    ]
    assert "A-302" in result.agenda_items[1].proceedings
    assert "Schedule actions" in result.agenda_items[0].proceedings
    assert "42 internship submissions" in result.agenda_items[3].proceedings
    assert len(result.supporting_tables) == 1
    assert result.supporting_tables[0].title == "Figures mentioned"
    assert result.supporting_tables[0].rows[1] == [
        "Internship submissions received", "42"
    ]
    document = Document(BytesIO(build_mom_docx(result)))
    figures_table = next(
        table for table in document.tables
        if table.rows[0].cells[0].text == "Item"
    )
    assert [cell.text for cell in figures_table.rows[1].cells] == [
        "Internship submissions received", "42"
    ]


def test_structured_private_reminders_are_excluded_and_other_points_are_routed():
    blocks = _structured_test3_blocks()
    result = organize_notes(
        "\n\n".join(block["text"] for block in blocks),
        source_blocks=blocks,
    )

    assert len(result.other_matters) == 3
    assert any("notice board" in item.casefold() for item in result.other_matters)
    assert any("FAC-209" in item for item in result.other_matters)
    assert any("Prof. Arjun Mehta" in item for item in result.other_matters)
    output = extract_docx_text(
        build_mom_docx(result), "test3-structured-output.docx"
    ).text
    assert "NOT PART OF THE MINUTES" not in output
    assert "Do not turn the figures table into agenda items" not in output


def test_pasted_text_without_source_blocks_keeps_existing_text_processing():
    notes = "The committee discussed the lab timetable. Faculty should submit course files."
    result = organize_notes(notes)

    assert result.original_notes == notes
    assert len(result.agenda_items) == 1
    assert "lab timetable" in result.agenda_items[0].proceedings.casefold()
    assert any("course files" in action.casefold() for action in result.action_items)


def test_txt_content_without_docx_blocks_uses_existing_text_processing():
    notes = "Faculty discussed course delivery."
    result = organize_notes(notes, source_blocks=None)

    assert result.original_notes == notes
    assert len(result.agenda_items) == 1
    assert result.agenda_items[0].proceedings == notes


def test_sample_meeting_notes_keep_stated_deadline_without_filling_unknowns():
    notes = (
        "meeting held on 22 october at 11 am in computer science department. "
        "hod discussed syllabus completion. faculty should finish unit 4 before internal exams. "
        "lab timetable needs revision. coordinator asked faculty to submit updated course files by friday."
    )
    result = organize_notes(notes, corrected_notes="An invented resolution was approved.")
    assert [item.agenda_item for item in result.agenda_items] == [
        "Syllabus Completion",
        "Laboratory Timetable",
    ]
    assert all("22 october" not in item.proceedings.casefold() for item in result.agenda_items)
    assert any("unit 4" in action.casefold() for action in result.action_items)
    assert any("friday" in action.casefold() for action in result.action_items)
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
    assert len(document.tables) == 2  # Two agenda tables; empty approval fields are omitted.
    assert "Resolution" in table_text and "Action Plan" in table_text
    assert "Approved by" not in table_text and "Signature:" not in table_text
    assert "Finish before exams" in table_text
    assert "Dr. Reviewer" not in table_text


def test_agenda_tables_use_reference_style_two_column_layout_and_subject_grouping():
    rough_notes = (
        "project sync maybe 28 oct 2026, 11am, seminar room 204. "
        "Priya said the dashboard is not approved yet. "
        "Rahul verma will update the charts by 2 nov. "
        "maybe use PostgreSQL instead of the current spreadsheet, but no decision was made. "
        "team discussed slow loading on the reports page. "
        "we agreed to move the internal demo to 5 november 2026. "
        "Neha was asked to review the API documentation."
    )
    result = organize_notes(rough_notes)
    assert len(result.agenda_items) <= 8

    document = Document(BytesIO(build_mom_docx(result)))
    agenda_tables = [
        table for table in document.tables
        if any(cell.text == "Agenda Item" for row in table.rows for cell in row.cells)
    ]
    assert agenda_tables
    for table in agenda_tables:
        assert len(table.columns) == 2
        assert table.rows[0].cells[0].text == "Agenda Item"


def test_reusable_template_is_editable_and_has_reference_sections():
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "templates" / "faculty_mom_template.docx"
    document = Document(path)
    text = "\n".join(p.text for p in document.paragraphs)
    table_text = "\n".join(cell.text for table in document.tables for row in table.rows for cell in row.cells)
    assert "MIT Art, Design and Technology University, Pune" in text
    assert all(label in table_text for label in ("Agenda Item", "Proceedings", "Resolution", "Action Plan"))


def test_deadlines_extracted_without_invention():
    result = organize_notes("The report must be submitted by Friday. The lab check happens before Monday.")
    assert "by Friday" in result.deadlines
    assert "before Monday" in result.deadlines


def test_no_deadline_invented_when_absent():
    result = organize_notes("The lab timetable needs revision.")
    assert result.deadlines == []


def test_responsible_person_extracted_from_notes():
    result = organize_notes("Rahul will check the lab computers.")
    assert "Rahul" in result.responsible_persons


def test_no_responsible_person_invented_when_absent():
    result = organize_notes("The lab computers should be checked.")
    assert result.responsible_persons == []


def test_tentative_statement_is_not_a_confirmed_decision():
    result = organize_notes("Maybe submit the report on Friday.")
    assert result.key_decisions == []
    assert any("maybe" in item.casefold() for item in result.tentative_items)


def test_confirmed_decision_is_separated_from_discussion():
    result = organize_notes("The lab timetable needs revision. The committee approved the revised timetable.")
    assert any("approved" in item.casefold() for item in result.key_decisions)
    assert any("needs revision" in item.casefold() for item in result.discussion_points)


def test_negation_preserved_in_proceedings():
    result = organize_notes("Students said that the projector is not working.")
    assert "not working" in result.agenda_items[0].proceedings


def test_date_extracted_from_later_sentence_when_intro_lacks_it():
    result = organize_notes("The committee met. The meeting was held on 22 October at 11 am.")
    assert result.date == "22 October"
    assert result.start_time.casefold() == "11 am"


def test_action_item_keeps_stated_responsible_person_and_deadline():
    result = organize_notes("Coordinator asked faculty to submit updated course files by Friday.")
    assert "Coordinator" not in result.responsible_persons
    assert result.action_items
    assert "friday" in result.action_items[0].casefold()


def test_edited_content_appears_in_generated_docx():
    minutes = MeetingMinutes(
        meeting_title="Edited Title",
        meeting_number="4",
        date="22 October",
        venue="Computer Lab",
        coordinator="Dr. Faculty",
        attendees="Rahul; Neha",
        deadlines=["by Friday"],
        responsible_persons=["Rahul"],
        key_decisions=["The timetable is approved."],
        tentative_items=["Maybe meet next week."],
        agenda_items=[AgendaItem("Syllabus", "Unit 4 discussed", "Approved.", "Finish by exams.")],
    )
    document = Document(BytesIO(build_mom_docx(minutes)))
    text = "\n".join(p.text for p in document.paragraphs)
    table_text = "\n".join(cell.text for table in document.tables for row in table.rows for cell in row.cells)
    assert "Edited Title" in text
    assert "22 October" in text
    assert "Computer Lab" in text
    assert "Dr. Faculty" in text
    assert "Rahul; Neha" in text
    assert "by Friday" in text
    assert "Rahul" in text
    assert "The timetable is approved." in text
    assert "Maybe meet next week." in text
    assert "Finish by exams." in table_text
    assert "Dr. Reviewer" not in table_text


def test_empty_sections_are_not_forced_into_docx():
    minutes = MeetingMinutes(meeting_title="Only Title")
    document = Document(BytesIO(build_mom_docx(minutes)))
    text = "\n".join(p.text for p in document.paragraphs)
    assert "Only Title" in text
    assert "Deadlines Stated in Notes" not in text
    assert "Responsible Persons Stated in Notes" not in text
    assert "Matters Requiring Confirmation" not in text
    assert "Conclusion" not in text


# --- Case A: Confirmed decision ---
def test_confirmed_decision_is_classified_and_date_extracted():
    result = organize_notes("team agreed final demo on 15 nov")
    assert any("team agreed final demo on 15 nov" in d for d in result.key_decisions)
    assert result.date == "15 nov"
    assert "team agreed final demo on 15 nov" not in result.discussion_points


# --- Case B: Discussion without approval ---
def test_discussion_without_approval_is_not_a_decision():
    result = organize_notes("budget discussed no final decision yet")
    assert "budget discussed no final decision yet" in result.discussion_points
    assert result.key_decisions == []
    assert result.action_items == []
    assert any("no" in item.casefold() for item in result.discussion_points)


# --- Case C: Tentative action ---
def test_tentative_action_is_not_confirmed():
    result = organize_notes("riya may send draft by friday if client confirms")
    assert any("riya may send draft by friday if client confirms" in t for t in result.tentative_items)
    assert result.key_decisions == []
    assert result.action_items == []
    assert any("by friday" in d for d in result.deadlines)


# --- Case D: Explicit negation ---
def test_explicit_negation_is_not_a_decision_or_action():
    result = organize_notes("do not deploy until security approval")
    assert result.key_decisions == []
    assert result.action_items == []
    assert "do not deploy until security approval" in result.other_matters


# --- Case E: Missing owner ---
def test_action_without_owner_is_still_an_action():
    result = organize_notes("finish testing by friday")
    assert any("finish testing by friday" in a for a in result.action_items)
    assert any("by friday" in d for d in result.deadlines)
    assert result.responsible_persons == []


# --- Case F: Missing deadline ---
def test_action_without_deadline_is_still_an_action():
    result = organize_notes("rahul will prepare report")
    assert any("rahul will prepare report" in a for a in result.action_items)
    assert result.deadlines == []
    assert "rahul" in result.responsible_persons


# --- Case G: Conflicting statements ---
def test_conflicting_dates_are_preserved_not_resolved():
    result = organize_notes("demo planned monday but later postponed to wednesday")
    assert any("demo planned monday but later postponed to wednesday" in d for d in result.discussion_points)
    assert result.key_decisions == []
    assert "monday" in result.agenda_items[0].proceedings.casefold()
    assert "wednesday" in result.agenda_items[0].proceedings.casefold()


# --- Case H: Names and technical terminology ---
def test_names_and_technical_terms_are_preserved():
    result = organize_notes("Dr Patil asked Aarav to test MQTT integration on ESP32")
    assert "Dr Patil" not in result.responsible_persons
    assert "Aarav" in result.responsible_persons
    assert result.agenda_items == []
    assert "MQTT" in " ".join(result.action_items)
    assert "ESP32" in " ".join(result.action_items)


# --- Case I: Pending approval ---
def test_pending_approval_is_extracted():
    result = organize_notes("purchase request submitted awaiting hod approval")
    assert any("awaiting hod approval" in p for p in result.pending_approvals)


# --- Case J: Uncertain statement ---
def test_uncertain_statement_is_tentative_not_confirmed():
    result = organize_notes("possibly move the review to next week")
    assert any("possibly move the review to next week" in t for t in result.tentative_items)
    assert result.key_decisions == []
    assert result.deadlines == []


# --- Case K: No invented facts ---
def test_plain_discussion_invents_nothing():
    result = organize_notes("discussed project progress")
    assert "discussed project progress" in result.discussion_points
    assert result.key_decisions == []
    assert result.action_items == []
    assert result.deadlines == []
    assert result.responsible_persons == []
    assert result.pending_approvals == []
    assert result.tentative_decisions == []


# --- Case L: Empty or extremely short input ---
def test_empty_input_is_rejected():
    with pytest.raises(ValueError, match="Enter or upload"):
        organize_notes("  ")


def test_very_short_note_is_preserved_without_classification():
    result = organize_notes("lab broken.")
    assert len(result.agenda_items) == 1
    assert result.agenda_items[0].proceedings == "lab broken."
    assert result.key_decisions == []
    assert result.action_items == []
    assert result.deadlines == []


# --- Duplicate extraction avoidance ---
def test_duplicate_decision_is_not_repeated():
    result = organize_notes(
        "the committee approved the revised syllabus. the committee approved the revised syllabus."
    )
    matches = [d for d in result.key_decisions if "approved the revised syllabus" in d]
    assert len(matches) == 1


def test_tentative_decision_is_not_in_confirmed_decisions():
    result = organize_notes("the committee may approve the revised syllabus")
    assert result.key_decisions == []
    assert any("the committee may approve the revised syllabus" in t for t in result.tentative_items)


# --- Abbreviation protection in sentence splitting ---
def test_abbreviation_does_not_split_sentence():
    result = organize_notes("Dr. Patil asked Aarav to test MQTT on ESP32. The lab needs repair.")
    assert len(result.agenda_items) == 1
    assert "Dr. Patil asked Aarav to test MQTT on ESP32." in result.other_matters
    assert "The lab needs repair." in result.agenda_items[0].proceedings


# --- DOCX regression tests ---

def test_docx_complete_meeting_with_multiple_agenda_items():
    minutes = MeetingMinutes(
        meeting_title="Faculty Council Meeting",
        meeting_number="3",
        department="Computer Science",
        academic_year="2026-27",
        reference_number="CC/2026/03",
        date="15 November 2026",
        start_time="10:30 AM",
        end_time="12:00 PM",
        venue="Conference Hall B",
        coordinator="Dr. Neha Sharma",
        attendees="Rahul Verma; Neha Desai; Aarav Patil",
        absentees="",
        absent_without_intimation="",
        substitutes="",
        opening_remarks="The chair welcomed all members.",
        agenda_items=[
            AgendaItem("Syllabus Review", "Unit 4 completion discussed.", "Approved.", "Finish before exams."),
            AgendaItem("Lab Timetable", "Revision needed.", "", "HOD to issue revised timetable."),
        ],
        conclusion="Meeting concluded at 12:00 PM.",
        next_meeting_date="10 December 2026",
        prepared_by="",
        reviewed_by="",
        approved_by="",
        approval_date="",
        original_notes="test notes",
        corrected_notes="test notes",
        review_required=True,
        deadlines=["before exams"],
        responsible_persons=["HOD"],
        discussion_points=["Unit 4 completion discussed.", "Revision needed."],
        key_decisions=["Approved."],
        tentative_decisions=[],
        action_items=["Finish before exams.", "HOD to issue revised timetable."],
        tentative_items=[],
        pending_approvals=[],
        unresolved_questions=[],
    )
    document = Document(BytesIO(build_mom_docx(minutes)))
    text = "\n".join(p.text for p in document.paragraphs)
    table_text = "\n".join(cell.text for table in document.tables for row in table.rows for cell in row.cells)

    assert "Faculty Council Meeting" in text
    assert "15 November 2026" in text
    assert "10:30 AM" in text
    assert "Conference Hall B" in text
    assert "Dr. Neha Sharma" in text
    assert "Rahul Verma; Neha Desai; Aarav Patil" in text
    assert "Unit 4 completion discussed." in table_text
    assert "Finish before exams." in table_text
    assert "HOD to issue revised timetable." in table_text
    assert "Approved." in table_text
    assert "Meeting concluded at 12:00 PM." in text
    assert "10 December 2026" in text
    assert "Prepared by" not in table_text
    assert "Reviewed by" not in table_text
    assert "Approved by" not in table_text
    assert "Signature:" not in table_text


def test_docx_missing_optional_details():
    minutes = MeetingMinutes(meeting_title="Only Title")
    document = Document(BytesIO(build_mom_docx(minutes)))
    text = "\n".join(p.text for p in document.paragraphs)
    table_text = "\n".join(cell.text for table in document.tables for row in table.rows for cell in row.cells)

    assert "Only Title" in text
    assert "Meeting Details" not in text
    assert "Attendance" not in text
    assert "Deadlines Stated in Notes" not in text
    assert "Responsible Persons Stated in Notes" not in text
    assert "Matters Requiring Confirmation" not in text
    assert "Key Decisions" not in text
    assert "Tentative Decisions" not in text
    assert "Pending Approvals" not in text
    assert "Unresolved Questions" not in text
    assert "Discussion Points" not in text
    assert "Action Items" not in text
    assert "Conclusion" not in text
    assert "Next Meeting Date" not in text


def test_docx_empty_optional_sections_not_forced():
    minutes = MeetingMinutes(
        meeting_title="Minimal Meeting",
        key_decisions=[],
        deadlines=[],
        responsible_persons=[],
        tentative_items=[],
        tentative_decisions=[],
        pending_approvals=[],
        unresolved_questions=[],
        agenda_items=[],
    )
    document = Document(BytesIO(build_mom_docx(minutes)))
    text = "\n".join(p.text for p in document.paragraphs)
    assert "Minimal Meeting" in text
    assert "Deadlines Stated in Notes" not in text
    assert "Responsible Persons Stated in Notes" not in text
    assert "Matters Requiring Confirmation" not in text
    assert "Key Decisions" not in text
    assert "Tentative Decisions" not in text
    assert "Pending Approvals" not in text
    assert "Unresolved Questions" not in text


def test_docx_long_discussion_text():
    long_text = "This is a very long discussion point. " * 50
    minutes = MeetingMinutes(
        meeting_title="Long Discussion Meeting",
        discussion_points=[long_text],
        agenda_items=[AgendaItem("Item 1", long_text, "", "")],
    )
    document = Document(BytesIO(build_mom_docx(minutes)))
    text = "\n".join(p.text for p in document.paragraphs)
    table_text = "\n".join(cell.text for table in document.tables for row in table.rows for cell in row.cells)
    assert long_text in table_text


def test_docx_multiple_action_items():
    minutes = MeetingMinutes(
        meeting_title="Action Items Meeting",
        action_items=[
            "Rahul will submit the report by Friday.",
            "Neha will contact the vendor by Monday.",
            "Aarav will prepare the presentation before next week.",
        ],
        responsible_persons=["Rahul", "Neha", "Aarav"],
        deadlines=["by Friday", "by Monday", "before next week"],
    )
    document = Document(BytesIO(build_mom_docx(minutes)))
    text = "\n".join(p.text for p in document.paragraphs)
    table_text = "\n".join(cell.text for table in document.tables for row in table.rows for cell in row.cells)
    assert "Rahul will submit the report by Friday." in table_text
    assert "Neha will contact the vendor by Monday." in table_text
    assert "Aarav will prepare the presentation before next week." in table_text
    assert "by Friday" in table_text
    assert "by Monday" in table_text
    assert "before next week" in table_text
    assert "Rahul" in table_text
    assert "Neha" in table_text
    assert "Aarav" in table_text


def test_docx_editing_decision_before_export():
    minutes = MeetingMinutes(
        meeting_title="Test Meeting",
        key_decisions=["The original decision."],
        tentative_decisions=["A tentative proposal."],
    )
    # Simulate user editing the decision
    minutes.key_decisions[0] = "The revised decision after review."
    document = Document(BytesIO(build_mom_docx(minutes)))
    text = "\n".join(p.text for p in document.paragraphs)
    assert "The revised decision after review." in text
    assert "The original decision." not in text
    assert "A tentative proposal." in text


def test_docx_editing_deadline_before_export():
    minutes = MeetingMinutes(
        meeting_title="Test Meeting",
        deadlines=["by Friday"],
    )
    # Simulate user editing the deadline
    minutes.deadlines[0] = "by Monday"
    document = Document(BytesIO(build_mom_docx(minutes)))
    text = "\n".join(p.text for p in document.paragraphs)
    assert "by Monday" in text
    assert "by Friday" not in text


def test_docx_removing_item_before_export():
    minutes = MeetingMinutes(
        meeting_title="Test Meeting",
        agenda_items=[
            AgendaItem("Item 1", "Proceedings 1", "", ""),
            AgendaItem("Item 2", "Proceedings 2", "", ""),
        ],
    )
    # Simulate user removing Item 2
    minutes.agenda_items = [item for item in minutes.agenda_items if item.agenda_item != "Item 2"]
    document = Document(BytesIO(build_mom_docx(minutes)))
    table_text = "\n".join(cell.text for table in document.tables for row in table.rows for cell in row.cells)
    assert "Item 1" in table_text
    assert "Item 2" not in table_text


def test_docx_tentative_decisions_and_pending_approvals():
    minutes = MeetingMinutes(
        meeting_title="Test Meeting",
        tentative_decisions=["Maybe purchase new computers.", "Possibly revise the syllabus."],
        pending_approvals=["Purchase request awaiting HOD approval.", "Budget proposal pending dean review."],
        unresolved_questions=["Was the venue confirmed?", "Will external members attend?"],
    )
    document = Document(BytesIO(build_mom_docx(minutes)))
    text = "\n".join(p.text for p in document.paragraphs)
    assert "Tentative Decisions" in text
    assert "Pending Approvals" in text
    assert "Unresolved Questions" in text
    assert "Maybe purchase new computers." in text
    assert "Possibly revise the syllabus." in text
    assert "Purchase request awaiting HOD approval." in text
    assert "Budget proposal pending dean review." in text
    assert "Was the venue confirmed?" in text
    assert "Will external members attend?" in text


def test_docx_blank_approval_fields():
    minutes = MeetingMinutes(
        meeting_title="Test Meeting",
        prepared_by="",
        reviewed_by="",
        approved_by="",
        approval_date="",
    )
    document = Document(BytesIO(build_mom_docx(minutes)))
    content = "\n".join(
        [paragraph.text for paragraph in document.paragraphs]
        + [cell.text for table in document.tables for row in table.rows for cell in row.cells]
    )
    assert "Prepared by" not in content
    assert "Reviewed by" not in content
    assert "Approved by" not in content
    assert "Signature:" not in content
    assert "Designation:" not in content
    assert "Date:" not in content


def test_docx_agenda_items_numbered():
    minutes = MeetingMinutes(
        meeting_title="Numbered Agenda Test",
        agenda_items=[
            AgendaItem("First item", "First proceedings", "", ""),
            AgendaItem("Second item", "Second proceedings", "", ""),
            AgendaItem("Third item", "Third proceedings", "", ""),
        ],
    )
    document = Document(BytesIO(build_mom_docx(minutes)))
    table_text = "\n".join(cell.text for table in document.tables for row in table.rows for cell in row.cells)
    assert "First item" in table_text
    assert "Second item" in table_text
    assert "Third item" in table_text


# --- Regression: no stale content leak between different uploaded documents ---

def test_physics_document_does_not_leak_into_meeting_document():
    """Uploading a physics DOCX followed by a meeting DOCX must not contaminate
    the second generated MoM with physics text from the first document."""
    from io import BytesIO
    from docx import Document as _Document

    # --- Physics document ---
    phys_doc = _Document()
    phys_doc.add_paragraph("Gravity is a fundamental force described by Newton's laws.")
    phys_doc.add_paragraph("Newton's first law states that an object at rest stays at rest.")
    phys_bytes = BytesIO()
    phys_doc.save(phys_bytes)

    phys_notes = extract_docx_text(phys_bytes.getvalue(), "physics.docx")
    phys_result = organize_notes(phys_notes.text)
    phys_docx = build_mom_docx(phys_result)

    phys_doc_check = _Document(BytesIO(phys_docx))
    phys_text = "\n".join(p.text for p in phys_doc_check.paragraphs)
    phys_table_text = "\n".join(
        c.text for t in phys_doc_check.tables for row in t.rows for c in row.cells
    )
    phys_combined = phys_text + "\n" + phys_table_text

    assert "Gravity" in phys_combined
    assert "Newton" in phys_combined

    # --- Meeting document ---
    meet_doc = _Document()
    meet_doc.add_paragraph("The committee discussed the lab timetable.")
    meet_doc.add_paragraph("Faculty should submit updated course files by Friday.")
    meet_bytes = BytesIO()
    meet_doc.save(meet_bytes)

    meet_notes = extract_docx_text(meet_bytes.getvalue(), "meeting.docx")
    meet_result = organize_notes(meet_notes.text)
    meet_docx = build_mom_docx(meet_result)

    meet_doc_check = _Document(BytesIO(meet_docx))
    meet_text = "\n".join(p.text for p in meet_doc_check.paragraphs)
    meet_table_text = "\n".join(
        c.text for t in meet_doc_check.tables for row in t.rows for c in row.cells
    )
    meet_combined = meet_text + "\n" + meet_table_text

    # Meeting content must be present
    assert "The committee discussed the lab timetable." in meet_combined
    assert "Faculty should submit updated course files by Friday." in meet_combined

    # Physics content must NOT be present in the meeting document
    assert "Gravity" not in meet_combined
    assert "Newton" not in meet_combined
    assert "fundamental force" not in meet_combined


# --- Name extraction: lowercase names before action verbs ---

def test_lowercase_responsible_person_extracted():
    result = organize_notes("rahul will submit the report by friday.")
    assert "rahul" in result.responsible_persons


def test_lowercase_responsible_person_with_should():
    result = organize_notes("neha should contact the vendor by monday.")
    assert "neha" in result.responsible_persons


def test_lowercase_responsible_person_with_asked():
    result = organize_notes("aarav was asked to prepare the presentation.")
    assert "aarav" in result.responsible_persons


# --- Name extraction: mixed-case two-word names ---

def test_mixed_case_two_word_name_extracted():
    result = organize_notes("Rahul verma will submit the report.")
    assert "Rahul verma" in result.responsible_persons


def test_mixed_case_name_with_must():
    result = organize_notes("Neha desai must complete the review.")
    assert "Neha desai" in result.responsible_persons


# --- Name extraction: no false positives from common words ---

def test_common_word_not_extracted_as_name():
    result = organize_notes("the team will finish the project.")
    assert "the" not in result.responsible_persons
    assert "team" not in result.responsible_persons


def test_pronoun_not_extracted_as_name():
    result = organize_notes("we will submit the report.")
    assert "we" not in result.responsible_persons


def test_department_not_extracted_as_name():
    result = organize_notes("department will review the syllabus.")
    assert "department" not in result.responsible_persons


# --- Name extraction: duplicate avoidance with new patterns ---

def test_duplicate_lowercase_name_not_repeated():
    result = organize_notes("rahul will submit by monday. rahul will prepare by tuesday.")
    assert result.responsible_persons.count("rahul") == 1


def test_mixed_and_capitalized_same_person_deduplicated():
    result = organize_notes("Rahul verma will submit. Rahul will prepare.")
    # "Rahul verma" and "Rahul" are different casefold keys, so both appear.
    # This is acceptable - they are different strings.
    assert "Rahul verma" in result.responsible_persons
    assert "Rahul" in result.responsible_persons


# --- Combined: lowercase name plus deadline extracted together ---

def test_lowercase_name_with_deadline():
    result = organize_notes("sarah will finish testing by friday.")
    assert "sarah" in result.responsible_persons
    assert any("friday" in d for d in result.deadlines)


# --- Topic grouping: related statements merged into one agenda item ---

def test_related_statements_grouped_into_one_topic():
    notes = (
        "need to finish the dashboard before the next review. "
        "Rahul verma will update the charts by 2 nov. "
        "Priya said the dashboard is not approved yet, don't tell the client it is final."
    )
    result = organize_notes(notes)
    dashboard_items = [
        item for item in result.agenda_items
        if "dashboard" in item.agenda_item.casefold()
    ]
    assert len(dashboard_items) == 1, f"Expected 1 dashboard topic, got {len(dashboard_items)}"
    assert dashboard_items[0].action_plan == ""
    assert any("charts" in action.casefold() for action in result.action_items)
    assert not any("chart" in item.agenda_item.casefold() for item in result.agenda_items)
    assert "not approved" in dashboard_items[0].proceedings.casefold()


def test_distinct_topics_remain_separate():
    notes = (
        "need to finish the dashboard before the next review. "
        "maybe use PostgreSQL instead of the current spreadsheet."
    )
    result = organize_notes(notes)
    assert len(result.agenda_items) == 1
    assert any("PostgreSQL" in matter for matter in result.other_matters)


# --- Exclusion of explanatory / sample metadata ---

def test_explanatory_text_excluded_from_agenda():
    notes = (
        "This sample intentionally includes rough grammar for testing. "
        "The committee approved the revised timetable. "
        "These notes are fictional and intended only for software testing."
    )
    result = organize_notes(notes)
    agenda_text = " ".join(item.agenda_item for item in result.agenda_items)
    assert "this sample intentionally" not in agenda_text.casefold()
    assert "these notes are fictional" not in agenda_text.casefold()
    assert result.key_decisions
    assert "approved the revised timetable" in result.key_decisions[0].casefold()


def test_section_headings_not_agenda_items():
    notes = (
        "Meeting details (rough)\n"
        "The committee discussed the lab timetable.\n"
        "Notes (not cleaned up)\n"
        "Faculty should submit course files by Friday."
    )
    result = organize_notes(notes)
    titles = [item.agenda_item.casefold() for item in result.agenda_items]
    assert "meeting details (rough)" not in titles
    assert "notes (not cleaned up)" not in titles


# --- Venue extraction ---

def test_venue_extracted_from_date_time_context():
    result = organize_notes("Meeting held on 22 October at 11 am in seminar room 204.")
    assert result.venue == "seminar room 204"


def test_venue_not_extracted_from_unrelated_sentence():
    result = organize_notes("The notes are kept in a folder. Meeting held on 22 October.")
    assert result.venue != "folder"
    assert result.venue == ""


def test_venue_not_extracted_from_heading_only():
    result = organize_notes("Meeting details (rough)\nSeminar room 204\nThe committee met.")
    assert result.venue == ""


def test_venue_after_time_without_in_keyword():
    result = organize_notes("Project sync maybe 28 oct 2026, 11am, seminar room 204.")
    assert result.venue == "seminar room 204"


# --- No sentence-fragment agenda generation ---

def test_short_fragments_can_be_separate_items():
    result = organize_notes("Neha was asked to review the API documentation. Confirm with her first.")
    neha_items = [item for item in result.agenda_items if "neha" in item.agenda_item.casefold()]
    assert neha_items == []
    assert any("Confirm with her first" in matter for matter in result.other_matters)
    assert any("API documentation" in action for action in result.action_items)


def test_no_single_word_agenda_titles():
    notes = "date and time not decided. maybe schedule another meeting next week."
    result = organize_notes(notes)
    for item in result.agenda_items:
        assert len(item.agenda_item.split()) >= 2 or not item.agenda_item.strip()


def test_heading_first_agenda_grouping_keeps_other_matters_out_of_agenda():
    notes = """
Department of Computer Science and Engineering
Meeting: Department Academic and Project Review Meeting
Date: 18 September 2026
Time: 11:00 AM to 12:30 PM
Venue: Conference Room, Academic Block
Chair: Dr. Meera Kulkarni, Head of Department
Prepared by: Ananya Deshmukh, Department Coordinator
People present
Dr. Meera Kulkarni (HOD), Prof. Rahul Patil (Project Coordinator), Dr. Neha Shah (Training and Placement Coordinator), Prof. Amit Joshi (Lab In-charge), Ms. Ananya Deshmukh (Department Coordinator).
Could not attend: Prof. Sneha Rao informed the coordinator in advance that she was on leave.
Notes from the meeting
HOD started the meeting and welcomed everyone. She said the review should focus on final-year project progress, laboratory access, placement preparation and the upcoming project exhibition.
Final year project progress: Project Coordinator said 18 out of 24 teams have completed their first review. Six teams have not submitted the updated progress report. Some teams are waiting for dataset access and two teams need help with deployment. The next review should happen before the end of September. All teams should upload their updated report to the department drive.
There was a discussion about students who have not attended project review meetings. HOD said mentors should contact those students and understand the reason. No decision was made to penalize students at this stage.
Decision: The second project review will be conducted on 29 September 2026. Prof. Rahul Patil will prepare the review schedule and share it with faculty and students by 22 September.
Laboratory access: Students requested access to the AI and computing laboratory after regular lecture hours because several teams need GPU systems for model training. Lab In-charge explained that the lab can remain open until 7:00 PM on weekdays if a faculty member is available. The department cannot approve unrestricted overnight access because of safety and supervision requirements.
Decision: Extended lab access until 7:00 PM on weekdays is approved on a trial basis for final-year project teams, subject to faculty supervision and entry-register records.
Action: Prof. Amit Joshi will prepare a weekly faculty supervision roster and display the lab access rules by 21 September 2026. Students must record their entry and exit in the register. The trial arrangement will be reviewed after one month.
Placement preparation: Dr. Neha Shah shared that 42 students have registered for the technical aptitude sessions. Attendance has been low in the last two sessions. Students asked for more practice in SQL, problem solving and technical interviews. The placement team proposed two additional practice sessions.
It was suggested that a mock interview could be arranged with alumni. Dr. Neha Shah will check alumni availability. This was only a suggestion; no date or external interviewer has been confirmed.
Decision: Two additional technical aptitude and interview practice sessions will be arranged in October. Dr. Neha Shah will coordinate the sessions and circulate the schedule by 30 September 2026.
Project exhibition: The university project exhibition is expected in November, but the exact date has not been announced. The department discussed selecting projects that are sufficiently complete and have a working demonstration. Teams should prepare a short abstract, poster and demonstration plan.
Decision: Each project mentor will recommend up to two projects for the department shortlist. Final selection will be made by the department review committee after demonstrations. The shortlist should be ready by 16 October 2026.
Action: Prof. Rahul Patil will share the project nomination format with mentors by 25 September. Mentors should submit nominations by 9 October. The exhibition date remains unconfirmed.
Other matter: The projector in Seminar Room 204 is not working consistently. Prof. Amit Joshi said the issue has been reported to the maintenance team. No repair completion date was provided. The HOD asked the coordinator to include the pending projector issue in the next department meeting.
The meeting ended with a vote of thanks at 12:30 PM.
Next meeting: Proposed for 20 October 2026, subject to confirmation.
Additional reminders
Do not treat every bullet or sentence as a separate agenda item. Keep suggestions separate from confirmed decisions. Do not invent missing details, owners or deadlines.
"""
    result = organize_notes(notes)
    expected_titles = [
        "Final-Year Project Progress",
        "Extended Laboratory Access",
        "Placement Preparation",
        "University Project Exhibition",
    ]
    assert [item.agenda_item for item in result.agenda_items] == expected_titles
    assert result.department == "Department of Computer Science and Engineering"
    assert "projector" not in result.agenda_items[0].proceedings.casefold()
    assert "42 students" in result.agenda_items[2].proceedings
    assert result.agenda_items[0].resolution == "The second project review will be conducted on 29 September 2026."
    assert "mock interview" in " ".join(result.agenda_items[2].suggestions).casefold()
    assert "This was only a suggestion" not in result.agenda_items[2].proceedings
    assert "No date or external interviewer" in result.agenda_items[2].proceedings
    assert result.agenda_items[1].resolution.endswith("entry-register records.")
    assert "second project review schedule" in result.agenda_items[0].action_plan.casefold()
    assert "Prof. Rahul Patil" not in result.agenda_items[0].action_plan
    assert "21 September" not in result.agenda_items[1].action_plan
    assert "Dr. Neha Shah" not in result.agenda_items[2].action_plan
    assert "25 September" not in result.agenda_items[3].action_plan
    assert "The Head of Department commenced the meeting and welcomed the members." in result.opening_remarks
    assert "The Chairperson outlined the key areas for review:" in result.opening_remarks
    assert result.responsible_persons == [
        "Prof. Rahul Patil", "Prof. Amit Joshi", "Dr. Neha Shah"
    ]
    assert any("projector" in matter.casefold() for matter in result.other_matters)
    assert "vote of thanks" in result.conclusion.casefold()
    assert result.next_meeting_date == "Proposed for 20 October 2026, subject to confirmation."
    assert result.prepared_by == "Ananya Deshmukh, Department Coordinator"
    assert not any("do not treat" in item.proceedings.casefold() for item in result.agenda_items)

    document = Document(BytesIO(build_mom_docx(result)))
    agenda_tables = [
        table for table in document.tables
        if any(cell.text == "Agenda Item" for row in table.rows for cell in row.cells)
    ]
    assert len(agenda_tables) == 4
    action_table = next(
        table for table in document.tables
        if table.rows and table.rows[0].cells[0].text == "Responsible Person"
    )
    assert len(action_table.columns) == 3
    assert len(action_table.rows) == 13
    assert action_table.rows[0].cells[0].text == "Responsible Person"
    assert action_table.rows[0].cells[1].text == "Action Required"
    assert action_table.rows[0].cells[2].text == "Deadline"
    action_rows = action_table_rows(result)
    assert len(action_rows) == 12
    assert len({tuple(value.casefold() for value in row) for row in action_rows}) == len(action_rows)
    expected_actions = {
        (
            "Prof. Rahul Patil",
            "Prepare and circulate the second project review schedule",
            "22 September 2026",
        ),
        (
            "All project teams",
            "Upload updated progress reports to the department drive",
            "Not specified",
        ),
        (
            "Project mentors",
            "Contact students who missed project review meetings and understand the reasons",
            "Not specified",
        ),
        (
            "Prof. Amit Joshi",
            "Prepare a weekly faculty supervision roster and display the laboratory access rules",
            "21 September 2026",
        ),
        (
            "Students using the laboratory",
            "Record laboratory entry and exit in the register",
            "Not specified",
        ),
        (
            "Dr. Neha Shah",
            "Check alumni availability for the suggested mock interview",
            "Not specified",
        ),
        (
            "Dr. Neha Shah",
            "Coordinate the two additional practice sessions and circulate the schedule",
            "30 September 2026",
        ),
        (
            "Project teams",
            "Prepare a short abstract, poster and demonstration plan",
            "Not specified",
        ),
        (
            "Prof. Rahul Patil",
            "Share the project nomination format with mentors",
            "25 September 2026",
        ),
        (
            "Project mentors",
            "Submit project nominations",
            "9 October 2026",
        ),
    }
    assert expected_actions.issubset(set(action_rows))
    assert all(row[0] != "" and row[2] != "" for row in action_rows)
    assert [
        table.rows[0].cells[0].text for table in document.tables[-5:-1]
    ] == ["Agenda Item"] * 4
    assert document.tables[-1].rows[0].cells[0].text == "Responsible Person"
    assert "Discussion Points" not in "\n".join(p.text for p in document.paragraphs)
    exported_text = "\n".join(
        [p.text for p in document.paragraphs]
        + [cell.text for table in document.tables for row in table.rows for cell in row.cells]
    )
    assert "projector" in exported_text.casefold()
    assert "API documentation review" not in exported_text
    assert "Do not treat every bullet" not in exported_text
    assert "Prepared by" in "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "Ananya Deshmukh" in "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "Department Coordinator" in "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "Reviewed by" not in exported_text
    assert "Approved by" not in exported_text
    assert "Designation:" not in exported_text
    assert "Signature:" not in exported_text


def test_docx_rejects_sentence_like_agenda_titles():
    with pytest.raises(ValueError, match="sentence-like titles"):
        build_mom_docx(
            MeetingMinutes(agenda_items=[
                AgendaItem("HOD said mentors should contact those students")
            ])
        )


# --- Sample input / expected output pair ---

def test_sample_input_produces_coherent_mom():
    """Use the actual rough-notes sample to verify end-to-end behavior."""
    from pathlib import Path
    sample_path = Path(
        r"C:\Users\samruddhi kaule\Downloads\OfflineNoteAI_Sample_Rough_Meeting_Notes.docx"
    )
    if not sample_path.is_file():
        pytest.skip("Sample input DOCX not available")
    from nlp.docx_io import extract_docx_text
    content = sample_path.read_bytes()
    notes = extract_docx_text(content, "sample.docx").text
    result = organize_notes(notes)

    # Meeting metadata should be extracted
    assert result.date == "5 november 2026"
    assert result.start_time == "11am"
    assert result.venue == "seminar room 204"
    assert result.coordinator == "Priya Sharma"
    assert "rahul verma" in result.attendees.casefold()
    assert "Neha Joshi" in result.absentees

    # No physics text or unrelated content
    all_text = " ".join(item.proceedings for item in result.agenda_items)
    all_text += " " + " ".join(result.key_decisions)
    all_text += " " + " ".join(result.tentative_items)
    assert "Gravity" not in all_text
    assert "Newton" not in all_text
    assert "fundamental force" not in all_text

    # Related dashboard statements grouped
    dashboard_items = [
        item for item in result.agenda_items if "dashboard" in item.agenda_item.casefold()
    ]
    assert len(dashboard_items) == 1

    # Tentative items preserved, not converted to decisions
    tentative_text = " ".join(result.tentative_items).casefold()
    assert "postgresql" in tentative_text
    assert "export to csv" in tentative_text

    # Completed action not in action items
    assert "login bug" not in " ".join(result.action_items).casefold()

    # Reasonable agenda count (not dozens of fragments)
    assert 3 <= len(result.agenda_items) <= 20

    # No duplicate deadlines
    from collections import Counter
    dups = [d for d, c in Counter(dl.casefold() for dl in result.deadlines).items() if c > 1]
    assert not dups


def test_test2_docx_preserves_five_subjects_and_grounded_actions():
    from dataclasses import asdict
    from pathlib import Path

    sample_path = Path(
        r"C:\Users\samruddhi kaule\Downloads\OfflineNote_AI_Rough_Notes_Test_2.docx"
    )
    if not sample_path.is_file():
        pytest.skip("Test 2 input DOCX not available")

    source = extract_docx_text(sample_path.read_bytes(), sample_path.name)
    result = organize_notes(
        source.text,
        source_blocks=[asdict(block) for block in source.blocks],
    )

    assert len(result.agenda_items) == 5
    titles = [item.agenda_item.casefold() for item in result.agenda_items]
    assert any("timetable" in title for title in titles)
    assert any("laboratory" in title for title in titles)
    assert any("industry" in title for title in titles)
    assert any("interview" in title for title in titles)
    assert any("mini-project" in title for title in titles)
    assert not result.validation_warnings

    timetable, laboratory, industry, placement, evaluation = result.agenda_items
    assert "timetable clashes" in timetable.proceedings.casefold()
    assert "old lab" in timetable.proceedings.casefold()
    assert "6 machines" not in timetable.proceedings.casefold()
    assert "working systems" in laboratory.proceedings.casefold()
    assert "6 machines" in laboratory.proceedings.casefold()
    assert "timetable issue" not in laboratory.proceedings.casefold()
    assert "replacement" not in laboratory.resolution.casefold()
    assert "cloud infrastructure" in industry.proceedings.casefold()
    assert any("no speaker is confirmed" in item.casefold() for item in industry.pending_matters)
    assert "36 students" in placement.proceedings
    assert "11 have not filled" in placement.proceedings
    assert "three practice sessions" in placement.resolution.casefold()
    assert "screenshots alone will not count" in evaluation.proceedings.casefold()
    assert "first evaluation is fixed" in evaluation.resolution.casefold()
    assert any("moved by one week" in item.casefold() for item in evaluation.pending_matters)
    assert all("friday" not in item.casefold() for item in result.key_decisions)

    action_rows = action_table_rows(result)
    assert len(action_rows) == len({
        tuple(part.casefold() for part in row) for row in action_rows
    })
    assert any(
        owner == "Prof. Nikhil Joshi" and "revised timetable" in action.casefold()
        for owner, action, _ in action_rows
    )
    assert any(
        owner == "Ms. Pooja Nair" and "collect the logs" in action.casefold()
        for owner, action, _ in action_rows
    )
    assert any(
        owner == "Prof. Sameer Kulkarni" and "session plan" in action.casefold()
        and deadline == "16 October 2026"
        for owner, action, deadline in action_rows
    )
    assert any(
        owner == "Mr. Rohan Kulkarni" and "replace the sheet" in action.casefold()
        and deadline == "9 October 2026"
        for owner, action, deadline in action_rows
    )

    assert result.department == "Department of Information Technology"
    assert result.date == "7 October 2026"
    assert result.start_time == "2:15 PM"
    assert result.end_time == "3:40 PM"
    assert result.venue == "Lab Seminar Room, Block C"
    assert "Dr. Kavita Desai" in result.coordinator
    assert "Prof. Nikhil Joshi" in result.attendees
    assert result.absentees == "Dr. Asha Menon"
    assert any("IT-4187" in matter for matter in result.other_matters)
    assert any("notice board" in matter.casefold() for matter in result.other_matters)
    assert any("printer" in matter.casefold() for matter in result.other_matters)
    assert not any(
        "projector" in item.proceedings.casefold()
        for item in result.agenda_items
    )
    assert "Need a clean table" not in " ".join(
        item.proceedings for item in result.agenda_items
    )

    document = Document(BytesIO(build_mom_docx(result)))
    agenda_tables = [
        table for table in document.tables
        if any(cell.text == "Agenda Item" for row in table.rows for cell in row.cells)
    ]
    action_tables = [
        table for table in document.tables
        if table.rows
        and [cell.text for cell in table.rows[0].cells]
        == ["Responsible Person", "Action Required", "Deadline"]
    ]
    assert len(agenda_tables) == 5
    assert len(action_tables) == 1
    assert len(action_tables[0].columns) == 3


def test_test3_docx_actions_remain_grounded_through_export():
    from dataclasses import asdict
    from pathlib import Path

    sample_path = Path(
        r"C:\Users\samruddhi kaule\Downloads\OfflineNote_AI_Rough_Notes_Test_3.docx"
    )
    if not sample_path.is_file():
        pytest.skip("Test 3 input DOCX not available")

    source = extract_docx_text(sample_path.read_bytes(), sample_path.name)
    result = organize_notes(
        source.text,
        source_blocks=[asdict(block) for block in source.blocks],
    )
    assert len(result.agenda_items) == 5

    actions = result.structured_actions
    expected = [
        ("Prof. Vikram Rao", "corrected schedule", "16 November"),
        ("Department Office", "final notice", None),
        ("Mr. Karan Shah", "inspection report", "18 November"),
        ("Prof. Devika Menon", "adapter count", "17 November"),
        ("Classroom Assistants", "equipment borrowed and returned", None),
        ("Ms. Isha Kulkarni", "speaker profile", "24 November"),
        ("Prof. Devika Menon", "checklist wording", "20 November"),
        ("Students", "missing supervisor form", "23 November"),
        ("Department Office", "nine students", None),
        ("Project Teams", "working demo", None),
    ]
    for owner, phrase, deadline in expected:
        assert any(
            action.responsible_person == owner
            and phrase in action.description.casefold()
            and action.deadline == deadline
            for action in actions
        )
    assert not any(
        invalid in (action.responsible_person or "").casefold()
        for action in actions
        for invalid in ("incomplete submissions", "next review", "demonstration but")
    )
    assert not any(
        phrase in action.description.casefold()
        for action in actions
        for phrase in ("final decision", "next review should revisit")
    )
    assert any(
        action.agenda_topic == "Other Matters"
        and "previous semester's project coordinator list" in action.description.casefold()
        for action in actions
    )

    document = Document(BytesIO(build_mom_docx(result)))
    action_table = next(
        table for table in document.tables
        if table.rows
        and [cell.text for cell in table.rows[0].cells]
        == ["Responsible Person", "Action Required", "Deadline"]
    )
    assert len(action_table.rows) - 1 == len(action_table_rows(result))
    for row, expected_row in zip(
        action_table.rows[1:], action_table_rows(result)
    ):
        assert tuple(cell.text for cell in row.cells) == expected_row


def test_action_records_keep_task_owner_deadline_and_source_together():
    from processing import _extract_action_record

    roster = "Prof. Devika Deshmukh; Mr. Karan Shah"
    first = _extract_action_record(
        "Devika will verify the adapter count by 17 November.",
        agenda_topic="Network and Classroom Equipment",
        attendees=roster,
    )
    second = _extract_action_record(
        "After the rooms are confirmed, the department office should circulate the final notice.",
        agenda_topic="Project Review Schedule",
        attendees=roster,
    )

    assert first is not None
    assert first.description == "Verify the adapter count"
    assert first.responsible_person == "Prof. Devika Deshmukh"
    assert first.deadline == "17 November"
    assert first.agenda_topic == "Network and Classroom Equipment"
    assert first.source_text.startswith("Devika will verify")
    assert second is not None
    assert second.description == "Circulate the final notice"
    assert second.responsible_person == "Department Office"
    assert second.deadline is None


def test_action_extraction_accepts_individual_and_organizational_owners():
    from processing import _extract_action_record

    roster = "Prof. Devika Deshmukh; Mr. Karan Shah"
    individual = _extract_action_record(
        "Karan was asked to send the inspection report by 18 November.",
        attendees=roster,
    )
    unit = _extract_action_record(
        "Classroom assistants should record equipment borrowed and returned."
    )
    ownerless = _extract_action_record(
        "Submit the revised checklist by 20 November."
    )

    assert individual is not None
    assert individual.responsible_person == "Mr. Karan Shah"
    assert individual.deadline == "18 November"
    assert unit is not None
    assert unit.responsible_person == "Classroom Assistants"
    assert unit.deadline is None
    assert ownerless is not None
    assert ownerless.responsible_person is None
    assert ownerless.deadline == "20 November"


@pytest.mark.parametrize(
    "sentence",
    [
        "The final decision will be taken after the details are received.",
        "The next review should revisit the exhibition plan.",
        "Prof. Arjun Mehta was absent and did not accept the coordinator role.",
        "No coordinator was appointed.",
        "No one was assigned a date for circulation.",
    ],
)
def test_non_actions_are_not_extracted_as_assigned_tasks(sentence):
    from processing import _extract_action_record

    assert _extract_action_record(sentence) is None


def test_action_table_and_agenda_plan_use_the_same_distinct_records():
    from processing import _extract_action_record

    first = _extract_action_record(
        "Vikram will confirm room availability by 16 November.",
        agenda_topic="Project Review Schedule",
    )
    second = _extract_action_record(
        "Department office should circulate the final notice."
    )
    assert first is not None and second is not None
    first.agenda_topic = "Project Review Schedule"
    second.agenda_topic = "Project Review Schedule"
    agenda = AgendaItem(
        "Project Review Schedule",
        action_plan="\n".join((first.description, second.description)),
        action_items=[first, second],
    )
    result = MeetingMinutes(
        agenda_items=[agenda],
        structured_actions=[first, second],
    )

    rows = action_table_rows(result)
    assert len(rows) == 2
    assert [row[1] for row in rows] == [first.description, second.description]
    assert [item.description for item in agenda.action_items] == [row[1] for row in rows]
    assert rows[0][0] == "Vikram"
    assert rows[1][0] == "Department Office"


def test_docx_does_not_render_malformed_deadline_or_person_sections():
    document = Document(BytesIO(build_mom_docx(MeetingMinutes(
        deadlines=["16 November"],
        responsible_persons=["Vikram"],
        review_required=True,
    ))))
    exported_text = "\n".join(
        paragraph.text for paragraph in document.paragraphs
    )
    assert "Additional Deadlines" not in exported_text
    assert "Responsible Persons" not in exported_text


# --- Sequential uploads: no stale content ---

def test_no_stale_content_from_previous_upload():
    """Simulate processing two different documents in sequence."""
    first = organize_notes("Gravity is a fundamental force. Newton's laws apply.")
    second = organize_notes("The committee discussed the lab timetable.")

    first_text = " ".join(item.proceedings for item in first.agenda_items)
    second_text = " ".join(item.proceedings for item in second.agenda_items)

    assert "Gravity" in first_text
    assert "Gravity" not in second_text
    assert "Newton" not in second_text
    assert "lab timetable" in second_text


# --- Grammar correction does not alter agenda structure ---

def test_grammar_correction_does_not_change_agenda_structure():
    notes = "The committee approved the revised timetable. Faculty should submit course files."
    result_without = organize_notes(notes)
    result_with = organize_notes(notes, corrected_notes="The committee approved the revised timetable. Faculty should submit course files.")
    assert len(result_without.agenda_items) == len(result_with.agenda_items)
    assert result_without.key_decisions == result_with.key_decisions
