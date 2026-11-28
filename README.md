# OfflineNote AI — Faculty Minutes of Meeting Generator

## Purpose

OfflineNote AI helps a faculty member convert rough, informal meeting notes into structured, professional Minutes of Meeting (MoM). The user enters rough notes and meeting details, reviews an organized draft, edits it, and downloads an editable DOCX document. The application organizes notes; it does not record, transcribe, or summarize meetings automatically, and it is not a cloud collaboration platform.

## Project objectives

- Reduce the manual effort of converting faculty meeting notes into formal minutes.
- Preserve information from the notes (names, dates, deadlines, responsibilities, negations, uncertain statements) while keeping discussion, explicit resolutions, and supported follow-up tasks distinct.
- Never invent attendees, decisions, deadlines, or responsible persons that were not in the source notes.
- Provide an editable document based on the supplied MIT-ADT IQAC minutes structure.
- Run entirely on the local computer using locally bundled model files.

## Features

- Single-page Streamlit workflow: meeting details, editable rough notes, and TXT/DOCX upload (UTF-8 TXT or .docx, up to 10 MB).
- DOCX notes are processed in source order using paragraph styles, heading levels, list markers, and table cells; labeled metadata, attendance, agenda sections, supporting tables, other matters, closing details, and explicitly excluded private notes are routed separately.
- Optional local grammar correction using the bundled pretrained `vennify/t5-base-grammar-correction` T5 model. The project does not train or download a model automatically.
- Original notes remain available beside corrected wording for comparison.
- Agenda drafts keep proceedings, resolutions, and action plans separate. For structured DOCX input, each action is stored as one record with its source statement, optional owner, optional deadline, and agenda topic; the same record supplies the agenda plan and consolidated Action Items table.
- Action owners are resolved from an unambiguous attendance-roster match or an explicitly named organizational unit. Missing owners and deadlines remain unspecified, and future decisions or review points are not promoted to assigned actions.
- Editable review step: meeting details, attendance, agenda tables, corrected notes, extracted facts (deadlines, responsible persons, decisions, action items, discussion points, tentative items), and blank approval/signature fields.
- User edits are reflected in the downloaded DOCX.
- DOCX export with meeting details, attendance, agenda/proceedings tables, a consolidated Action Items table, tentative matters, conclusion, next meeting, and approval/signature table. Extracted deadlines and owners appear with their action records rather than as standalone fact sections.
- Live HTML preview of the minutes.

## Technologies

Python, Streamlit, PyTorch (CPU), Hugging Face Transformers, spaCy, SentencePiece, `python-docx`, and `lxml`.

The bundled model is `vennify/t5-base-grammar-correction` (revision `9e4a09d...`). Its model card identifies the license as CC-BY-NC-SA-4.0 (non-commercial, share-alike). Review the model card and license before redistribution or any non-academic/commercial use. Local execution does not remove license obligations.

## Requirements and setup

Python 3.11 is recommended (tested with Python 3.11.8). Existing model weights are kept in `models/vennify-t5-base-grammar-correction/` and are not downloaded by the app. The spaCy English pipeline `en_core_web_sm` must be installed for grammar correction.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

For grammar correction, install the spaCy English model while online:

```powershell
python -m spacy download en_core_web_sm
```

If the bundled model files are absent, download them once while online with:

```powershell
python scripts/download_models.py
```

The application itself loads only local model files (`local_files_only=True`) and sets `HF_HUB_OFFLINE` and `TRANSFORMERS_OFFLINE` by default, so it does not call the Hugging Face Hub during normal operation. Missing model dependencies do not prevent using the conservative organizer: turn off the local correction option.

The optional grammar-quality reference check is `python -m scripts.evaluate`. The optional meeting-notes meaning-preservation check is `python -m scripts.evaluate_meeting_notes`.

## Use

1. Enter known meeting fields (title, department, date, time, venue, chair, etc.).
2. Paste rough notes into the text area, or upload a UTF-8 TXT / DOCX file to replace them.
3. Choose whether to apply local grammar correction (slower; cleans spelling before organizing).
4. Click "Generate minutes". Review the original and corrected notes.
5. Edit meeting details, attendance, each agenda table, corrected notes, and the extracted facts (deadlines, responsible persons, decisions, action items, discussion points, tentative items).
6. Add or remove agenda items as needed.
7. Click "Preview" for a live HTML preview, then click "Download DOCX" to export the reviewed, edited document.

Unknown details remain blank ("Not specified" where the template shows a field) rather than being invented. Approval and signature areas are blank unless supplied by an authorized person.

## Project structure

```text
app.py                          Streamlit interface
processing.py                   Conservative notes-to-agenda organization
documents.py                    Editable DOCX generation
nlp/                            Local T5 inference, preprocessing, and DOCX input
models/                         Bundled pretrained model files (not downloaded by app)
templates/                      Reusable faculty MoM template
reference_materials/            Supplied nine-page IQAC reference PDF
evaluation/                     Reference sets (sample_notes.json, meeting_notes.json) and metrics
tests/                          Processing, document, app, pipeline, preprocessing, and model tests
tests/integration/              Local-model offline integration test
scripts/                        Model setup and optional quality-evaluation commands
```

## Tests

Run the unit tests:

```powershell
python -m pytest -q
```

Run the integration test (requires the bundled model and spaCy pipeline; skipped otherwise):

```powershell
python -m pytest tests/integration -q
```

Test results are reported honestly: integration tests are excluded from the default `pytest` run by `pytest.ini` and are run separately. Tests do not establish the quality of arbitrary model outputs or visual matching to the scanned institutional reference.

## Evaluation

A meaning-preservation dataset is at `evaluation/meeting_notes.json` with 8 realistic rough-note samples covering grammar errors, missing punctuation, abbreviations, names, deadlines, dates, tentative and confirmed decisions, negations, incomplete information, repeated items, ambiguous statements, and very short notes.

Run the meaning-preservation check:

```powershell
python -m scripts.evaluate_meeting_notes
```

Results are factual checks against the source notes (names, dates, deadlines, responsible persons, decisions, negations preserved; nothing invented). They are not a claim of overall grammatical or semantic accuracy.

## Offline operation and limitations

The T5 checkpoint is loaded from local model files only; `scripts/download_models.py` is the only code that downloads anything, and only when you run it yourself while online. The app sets `HF_HUB_OFFLINE` and `TRANSFORMERS_OFFLINE` by default. When the bundled model and the locally installed `en_core_web_sm` spaCy pipeline are available, processing does not require the Hugging Face Hub or any external API.

This README does not claim a fully offline installation verified with all network access disabled, because a true network-disconnected test could not be performed in this environment. Offline readiness is verified by code inspection and by the integration test, which runs with offline flags enabled. Grammar correction may alter meaning; review all output. Sentence splitting and cue-based classification are heuristic and may misclassify or miss decisions and tasks. The responsible-person extractor only catches capitalized names directly before action verbs; lowercase names are preserved in the text but not listed as extracted responsible persons. Negated statements are not treated as confirmed decisions or actions.

## Model license

The bundled model card (`models/vennify-t5-base-grammar-correction/README.md`) states `license: cc-by-nc-sa-4.0`. This is a non-commercial, share-alike license. Academic use is consistent with this, but redistribution or commercial use may be affected. Do not treat local execution as removing license obligations. The license notice is preserved and is not removed.

## Deployment

This is a local-first desktop/classroom application intended to run on the user's computer. It has not been deployed to a cloud platform, and no public deployment URL exists. Cloud hosting would require the model and dependencies to be hosted there, could expose uploaded notes, and would compromise the offline-first design. Local execution is the intended delivery method.

## Known limitations

- Grammar correction is optional and may alter meaning; always compare with the source notes.
- Cue-based classification is heuristic; decisions, actions, deadlines, and responsible persons may be missed or misclassified.
- Responsible-person extraction only catches capitalized names immediately before action verbs.
- Dates/times/venues are extracted by regex from the source sentences.
- DOCX section and standalone agenda-heading recognition uses structural and contextual cues; unstructured TXT and pasted notes continue through the sentence-level organizer.
- Empty optional sections are omitted from the DOCX; missing information is not fabricated.
- No database, login, payment, speech-to-text, recording, or cloud features are present (not part of this project).
- The integration test requires the bundled model and spaCy pipeline and is excluded from the default pytest run.
