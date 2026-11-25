import os
from io import BytesIO
from pathlib import Path

from docx import Document
import pytest

from nlp.docx_io import build_improved_docx, extract_docx_text
from nlp.model import load_local_rewriter
from nlp.pipeline import improve_notes
from nlp.preprocessing import load_spacy_pipeline

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models" / "vennify-t5-base-grammar-correction"


@pytest.mark.skipif(
    not (MODEL_DIR / "config.json").is_file(),
    reason="Download the local model to run the offline DOCX integration test.",
)
def test_docx_notes_run_through_local_pipeline_offline(monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    document = Document()
    document.add_heading("biology", level=1)
    document.add_paragraph("cells is the basic unit of life.")
    source = BytesIO()
    document.save(source)

    notes = extract_docx_text(source.getvalue(), "notes.docx")
    result = improve_notes(
        notes.text,
        load_spacy_pipeline(),
        load_local_rewriter(MODEL_DIR),
    )
    output = Document(BytesIO(
        build_improved_docx(notes, result.improved_paragraphs)
    ))

    assert len(result.improved_paragraphs) == len(notes.paragraphs)
    assert output.paragraphs[0].style.name == "Heading 1"
    assert output.paragraphs[1].text
    assert os.environ["HF_HUB_OFFLINE"] == "1"
    assert os.environ["TRANSFORMERS_OFFLINE"] == "1"
