# OfflineNote AI — Faculty Minutes of Meeting Generator

## Purpose

Faculty can enter rough notes and meeting details, review a structured draft, and download an editable DOCX. The application organizes notes; it does not record or transcribe meetings and is not an automatic meeting summarizer.

## Project objectives

- Reduce the manual effort of converting faculty meeting notes into formal minutes.
- Preserve information from the notes while keeping discussion, explicit resolutions, and supported follow-up tasks distinct.
- Provide an editable document based on the supplied MIT-ADT IQAC minutes structure.

## Features

- Single-page Streamlit workflow with meeting details, editable rough notes, and TXT/DOCX upload.
- Optional local grammar correction using the existing pretrained `vennify/t5-base-grammar-correction` T5 model. The project does not train a model.
- Original notes remain available beside corrected wording.
- Conservative sentence-level agenda draft with separate proceedings, resolution, and action-plan fields. Only explicit wording cues populate resolution/action fields; inspect and edit every result.
- Repeatable agenda-item tables, attendance and meeting details, conclusion, next-meeting field, and blank approval/signature fields in the DOCX.

## Technologies

Python, Streamlit, PyTorch, Hugging Face Transformers, spaCy, SentencePiece, and `python-docx`.

The upstream model card identifies the checkpoint as CC-BY-NC-SA-4.0 (non-commercial, share-alike). Review its [model card](https://huggingface.co/vennify/t5-base-grammar-correction) and license before redistribution or use.

## Requirements and setup

Python 3.11 is recommended. Existing model weights are kept in `models/vennify-t5-base-grammar-correction/` and are not downloaded by the app.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

For grammar correction, the local model files and spaCy English pipeline `en_core_web_sm` must be installed. If spaCy's model is missing, install it while online with `python -m spacy download en_core_web_sm`. Missing model dependencies do not prevent using the app's conservative organizer: turn off the local correction option.

If the bundled model files are absent, download them once while online with `python scripts/download_models.py`. The application itself loads only local model files. The optional grammar-quality dataset check is `python -m scripts.evaluate`.

## Use

Enter any known meeting fields and paste rough notes, or upload a UTF-8 TXT / DOCX file. Choose whether to apply local grammar correction and generate minutes. Review the original and corrected notes, edit details and each agenda table, add or remove agenda items, then download the DOCX. Unknown details remain blank. Approval and signature areas are blank unless supplied by the user.

## Project structure

```text
app.py                 Streamlit interface
processing.py          Conservative notes-to-agenda organization
documents.py           Editable DOCX generation
nlp/                   Existing local T5 inference, preprocessing, and DOCX input
models/                 Existing pretrained model files
templates/              Reusable faculty MoM template
reference_materials/      Supplied nine-page IQAC reference PDF
evaluation/              Small grammar-correction reference set and lexical metrics
tests/                  Processing, document, and existing NLP tests
scripts/                 Model setup and optional quality-evaluation commands
```

## Tests

Run `python -m pytest -q`. The local-model integration test runs only when the bundled model and runtime dependencies are available; pytest reports it as skipped otherwise. Tests do not establish the quality of arbitrary model outputs or visual matching to the scanned institutional reference.

## Offline operation and limitations

Inference loads the T5 checkpoint from local files only. The complete app workflow has not been verified with all network access disabled, and the optional spaCy package model must also be available locally; therefore this README does not claim a fully offline installation. Grammar correction may alter meaning. Sentence splitting and explicit-wording cues are heuristic, may misclassify or miss decisions and tasks, and do not infer a complete agenda from arbitrary notes. Review the source, all generated fields, and the final document before use.

The reusable template is based on the supplied `reference_materials/Minutes of 4th IQAC Meeting_2022-23.pdf`. The scanned reference has a university/committee header, meeting details, separate attendance status, opening proceedings, repeated two-column agenda/proceedings/resolution/action-plan blocks, conclusion and next-meeting date, and approval/signature areas. The template follows that structure without copying the historical attendees, reference number, stamps, or signatures. It is a clean editable recreation, not a pixel-perfect copy of the scan.
