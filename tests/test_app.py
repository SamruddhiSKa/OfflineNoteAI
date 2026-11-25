from pathlib import Path

from streamlit.testing.v1 import AppTest


def _widget(collection, key):
    return next(item for item in collection if item.key == key)


def test_app_starts_as_single_streamlit_page():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=30)
    assert not app.exception
    assert any(title.value == "Minutes of Meeting," for title in app.title)


def test_generate_edit_and_docx_export_workflow_without_grammar_model():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=30)

    _widget(app.text_input, "meeting_title").set_value("Faculty Review")
    _widget(app.text_input, "department").set_value("Computer Science")
    _widget(app.text_area, "source_notes").set_value(
        "The committee discussed the lab timetable. The coordinator asked faculty "
        "to submit updated course files by Friday."
    )
    _widget(app.toggle, "use_local_grammar").set_value(False)
    _widget(app.button, "generate_minutes").click()
    app.run(timeout=60)

    assert not app.exception
    assert app.session_state["mom"]["original_notes"].startswith("The committee discussed")
    assert len(app.session_state["mom"]["agenda_items"]) == 1
    assert "course files" in " ".join(app.session_state["mom"]["action_items"]).casefold()
    assert app.get("download_button")
    preview = "\n".join(element.value for element in app.markdown)
    assert preview.count('class="paper-agenda-table"') == 1
    assert "Agenda Item" in preview and "Action Plan" in preview

    _widget(app.text_input, "edit_meeting_title").set_value("Faculty Review — edited")
    app.run(timeout=30)
    assert not app.exception
    assert app.session_state["mom"]["meeting_title"] == "Faculty Review — edited"


def test_invalid_input_clears_previous_generated_state():
    """Empty input after a generation must clear the stale mom state."""
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=30)

    # First generate a valid meeting
    _widget(app.text_input, "meeting_title").set_value("First Meeting")
    _widget(app.text_area, "source_notes").set_value("rahul will submit by friday.")
    _widget(app.toggle, "use_local_grammar").set_value(False)
    app.run(timeout=30)
    _widget(app.button, "generate_minutes").click()
    app.run(timeout=60)
    assert not app.exception
    assert "mom" in app.session_state
    assert app.session_state["mom"]["meeting_title"] == "First Meeting"

    # Now clear notes and try to generate again
    app.session_state["source_notes"] = "   "
    _widget(app.toggle, "use_local_grammar").set_value(False)
    _widget(app.button, "generate_minutes").click()
    app.run(timeout=60)
    assert not app.exception
    # The old mom should have been cleared; the error path should not retain it.
    assert "mom" not in app.session_state


def test_invalid_input_clears_previous_generated_state():
    """Empty input after a generation must clear the stale mom state."""
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=30)

    # First generate a valid meeting
    _widget(app.text_input, "meeting_title").set_value("First Meeting")
    _widget(app.text_area, "source_notes").set_value("rahul will submit by friday.")
    _widget(app.toggle, "use_local_grammar").set_value(False)
    _widget(app.button, "generate_minutes").click()
    app.run(timeout=60)
    assert not app.exception
    assert "mom" in app.session_state

    # Now clear notes and try to generate again
    _widget(app.text_area, "source_notes").set_value("   ")
    _widget(app.button, "generate_minutes").click()
    app.run(timeout=60)
    assert not app.exception
    # The old mom should have been cleared; the error path should not retain it.
    assert "mom" not in app.session_state
    assert len(app.exception) == 0 or app.exception is None


def test_second_meeting_replaces_prior_content_and_keeps_source_metadata():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=30)
    first_notes = (
        "Department of Computer Science and Engineering\n"
        "Meeting: First Project Review\n"
        "Date: 18 September 2026\n"
        "Chair: Dr. Meera Kulkarni\n"
        "People present\n"
        "Prof. Rahul Patil\n"
        "Notes from the meeting\n"
        "Project review: Teams discussed dataset access and deployment progress."
    )
    _widget(app.text_area, "source_notes").set_value(first_notes)
    _widget(app.toggle, "use_local_grammar").set_value(False)
    _widget(app.button, "generate_minutes").click()
    app.run(timeout=60)

    first = app.session_state["mom"]
    assert first["department"] == "Department of Computer Science and Engineering"
    assert first["meeting_title"] == "First Project Review"
    assert "Dr. Meera Kulkarni" in first["coordinator"]
    assert "Prof. Rahul Patil" in first["attendees"]

    second_notes = "Laboratory timetable: The laboratory timetable needs revision."
    _widget(app.text_area, "source_notes").set_value(second_notes)
    _widget(app.button, "generate_minutes").click()
    app.run(timeout=60)

    second = app.session_state["mom"]
    assert second["original_notes"] == second_notes
    assert second["agenda_items"]
    assert all("laboratory timetable" in item["agenda_item"].casefold() for item in second["agenda_items"])
    assert "dataset access" not in str(second)
