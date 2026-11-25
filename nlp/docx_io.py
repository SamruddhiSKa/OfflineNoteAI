"""Local DOCX text extraction and structure-preserving document generation."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import re
import zipfile

from docx import Document
from docx.document import Document as DocumentObject
from docx.oxml.ns import qn
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.text.paragraph import Paragraph
from docx.table import Table, _Cell
from docx.opc.exceptions import PackageNotFoundError
from lxml.etree import XMLSyntaxError

MAX_DOCX_SIZE_BYTES = 10 * 1024 * 1024
MAX_DOCX_CONTENT_SIZE_BYTES = 50 * 1024 * 1024
MAX_DOCX_ZIP_MEMBERS = 2_000


class DocxInputError(ValueError):
    """Raised when a DOCX upload is invalid, unsupported, or too large."""


@dataclass
class DocxBlock:
    """A top-level Word paragraph or table with its original structure."""

    kind: str
    text: str
    style: str = ""
    rows: tuple[tuple[str, ...], ...] = ()
    level: int = 0
    is_list: bool = False
    list_type: str = ""  # "bullet" or "numbered"


@dataclass
class DocxNotes:
    """Extracted non-empty paragraphs and the source document in memory."""

    document: DocumentObject
    paragraphs: tuple[Paragraph, ...]
    text: str
    blocks: tuple[DocxBlock, ...] = ()


def _iter_container_blocks(parent: DocumentObject | _Cell):
    element = parent.element.body if isinstance(parent, DocumentObject) else parent._tc
    for child in element.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def _iter_paragraphs(parent: DocumentObject | _Cell):
    for block in _iter_container_blocks(parent):
        if isinstance(block, Paragraph):
            yield block
        else:
            seen_cells: set[int] = set()
            for row in block.rows:
                for cell in row.cells:
                    cell_id = id(cell._tc)
                    if cell_id in seen_cells:
                        continue
                    seen_cells.add(cell_id)
                    yield from _iter_paragraphs(cell)


def _detect_list(paragraph: Paragraph) -> tuple[bool, str]:
    """Detect if a paragraph is a bulleted or numbered list item."""
    try:
        pPr = paragraph._p.find(qn("w:pPr"))
        if pPr is None:
            return False, ""
        numPr = pPr.find(qn("w:numPr"))
        if numPr is not None:
            ilvl = numPr.find(qn("w:ilvl"))
            numId = numPr.find(qn("w:numId"))
            if numId is not None and numId.text:
                # Check the numbering definition for bullet vs numbered
                return True, "numbered"
        # Fallback: check for manual bullet/number markers at start of text
        text = paragraph.text.strip()
        if re.match(r"^[\u2022\u2013\u2014\-•◦§]\s+", text):
            return True, "bullet"
        if re.match(r"^\d+[\.)]\s+", text):
            return True, "numbered"
    except Exception:  # noqa: BLE001 - defensive list detection
        pass
    return False, ""


def _validate_docx_bytes(content: bytes) -> None:
    if not content:
        raise DocxInputError("The uploaded Word document is empty.")
    if len(content) > MAX_DOCX_SIZE_BYTES:
        raise DocxInputError(
            f"The Word document exceeds the {MAX_DOCX_SIZE_BYTES // (1024 * 1024)} MB limit."
        )
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            members = archive.infolist()
            if len(members) > MAX_DOCX_ZIP_MEMBERS:
                raise DocxInputError("The Word document contains too many embedded files.")
            if "[Content_Types].xml" not in archive.namelist() or \
                    "word/document.xml" not in archive.namelist():
                raise DocxInputError("This file is not a supported Word .docx document.")
            if any(member.flag_bits & 0x1 for member in members):
                raise DocxInputError("Encrypted Word documents are not supported.")
            expanded_size = sum(member.file_size for member in members)
            if expanded_size > MAX_DOCX_CONTENT_SIZE_BYTES:
                raise DocxInputError(
                    "The expanded Word document exceeds the 50 MB processing limit."
                )
    except zipfile.BadZipFile as exc:
        raise DocxInputError(
            "The uploaded file is not a valid .docx document."
        ) from exc


def extract_docx_text(content: bytes, filename: str = "notes.docx") -> DocxNotes:
    """Extract body paragraphs and table-cell paragraphs in document order."""
    if Path(filename).suffix.casefold() != ".docx":
        raise DocxInputError("Unsupported document type. Upload a .docx file.")
    _validate_docx_bytes(content)
    try:
        document = Document(BytesIO(content))
    except (PackageNotFoundError, KeyError, ValueError, XMLSyntaxError) as exc:
        raise DocxInputError(
            "The Word document could not be read. Check that it is a valid .docx file."
        ) from exc

    paragraphs = tuple(paragraph for paragraph in _iter_paragraphs(document) if paragraph.text.strip())
    if not paragraphs:
        raise DocxInputError(
            "The Word document contains no readable paragraph or table text."
        )
    text = "\n\n".join(paragraph.text.strip() for paragraph in paragraphs)
    blocks: list[DocxBlock] = []
    for block in _iter_container_blocks(document):
        if isinstance(block, Paragraph):
            if block.text.strip():
                style_name = block.style.name if block.style else ""
                style_lower = style_name.casefold()
                level = 0
                if style_lower.startswith("heading"):
                    digits = "".join(ch for ch in style_name if ch.isdigit())
                    level = int(digits) if digits else 1
                is_list, list_type = _detect_list(block)
                blocks.append(
                    DocxBlock(
                        kind="paragraph",
                        text=block.text.strip(),
                        style=style_name,
                        level=level,
                        is_list=is_list,
                        list_type=list_type,
                    )
                )
            continue
        rows = tuple(
            tuple(cell.text.strip() for cell in row.cells)
            for row in block.rows
        )
        table_text = "\n".join(
            " | ".join(cell for cell in row if cell)
            for row in rows
            if any(cell for cell in row)
        )
        if table_text:
            blocks.append(
                DocxBlock(
                    kind="table",
                    text=table_text,
                    rows=rows,
                )
            )
    return DocxNotes(
        document=document,
        paragraphs=paragraphs,
        text=text,
        blocks=tuple(blocks),
    )


def _replace_paragraph_text(paragraph: Paragraph, text: str) -> None:
    """Replace text runs while leaving paragraph style and non-text XML in place."""
    text_nodes = paragraph._p.xpath(".//w:t")
    if not text_nodes:
        if text:
            paragraph.add_run(text)
        return

    text_nodes[0].text = text
    if text.startswith(" ") or text.endswith(" "):
        text_nodes[0].set(qn("xml:space"), "preserve")
    for text_node in text_nodes[1:]:
        text_node.text = ""


def build_improved_docx(
    notes: DocxNotes,
    improved_paragraphs: tuple[str, ...],
) -> bytes:
    """Serialize revised text to a new DOCX without modifying the uploaded bytes."""
    if len(notes.paragraphs) != len(improved_paragraphs):
        raise ValueError(
            "Improved paragraph count does not match the source document."
        )
    for paragraph, improved in zip(notes.paragraphs, improved_paragraphs):
        _replace_paragraph_text(paragraph, improved)

    output = BytesIO()
    notes.document.save(output)
    return output.getvalue()
