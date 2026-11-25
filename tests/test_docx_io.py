from io import BytesIO
import zipfile

from docx import Document
import pytest

import nlp.docx_io as docx_io
from nlp.docx_io import (
    MAX_DOCX_SIZE_BYTES,
    DocxInputError,
    build_improved_docx,
    extract_docx_text,
)


def make_docx_bytes() -> bytes:
    document = Document()
    document.add_heading("biology notes", level=1)
    document.add_paragraph("cells is the basic unit of life.")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Term"
    table.cell(0, 1).text = "Definition"
    table.add_row().cells[0].text = "osmosis"
    table.rows[1].cells[1].text = "water move across a membrane."
    output = BytesIO()
    document.save(output)
    return output.getvalue()


def test_extracts_body_headings_and_table_cell_text_in_order():
    notes = extract_docx_text(make_docx_bytes(), "lecture.docx")

    assert notes.text == (
        "biology notes\n\n"
        "cells is the basic unit of life.\n\n"
        "Term\n\n"
        "Definition\n\n"
        "osmosis\n\n"
        "water move across a membrane."
    )
    assert notes.paragraphs[0].style.name == "Heading 1"


def test_generates_updated_docx_preserving_heading_and_table():
    original_bytes = make_docx_bytes()
    notes = extract_docx_text(original_bytes)
    original_text = notes.text
    improved = tuple(f"Revised: {paragraph.text.strip()}" for paragraph in notes.paragraphs)

    output_bytes = build_improved_docx(notes, improved)

    assert extract_docx_text(original_bytes).text == original_text
    output = Document(BytesIO(output_bytes))
    assert output.paragraphs[0].text == "Revised: biology notes"
    assert output.paragraphs[0].style.name == "Heading 1"
    assert output.paragraphs[1].text == "Revised: cells is the basic unit of life."
    assert output.tables[0].cell(0, 0).text == "Revised: Term"
    assert output.tables[0].cell(1, 1).text == "Revised: water move across a membrane."


@pytest.mark.parametrize(
    ("content", "filename", "message"),
    [
        (b"", "empty.docx", "empty"),
        (b"not a zip archive", "invalid.docx", "valid"),
        (b"ignored", "unsupported.pdf", "Unsupported"),
    ],
)
def test_rejects_empty_invalid_and_unsupported_inputs(content, filename, message):
    with pytest.raises(DocxInputError, match=message):
        extract_docx_text(content, filename)


def test_rejects_oversized_document_before_parsing():
    with pytest.raises(DocxInputError, match="exceeds"):
        extract_docx_text(b"x" * (MAX_DOCX_SIZE_BYTES + 1))


def test_rejects_excessive_expanded_docx_contents(monkeypatch):
    monkeypatch.setattr(docx_io, "MAX_DOCX_CONTENT_SIZE_BYTES", 100)
    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "types")
        archive.writestr("word/document.xml", "x" * 200)

    with pytest.raises(DocxInputError, match="expanded"):
        extract_docx_text(output.getvalue())


def test_rejects_document_with_no_readable_text():
    output = BytesIO()
    Document().save(output)

    with pytest.raises(DocxInputError, match="no readable"):
        extract_docx_text(output.getvalue())


def test_rejects_mismatched_rewrite_paragraph_count():
    notes = extract_docx_text(make_docx_bytes())

    with pytest.raises(ValueError, match="paragraph count"):
        build_improved_docx(notes, ("only one",))
