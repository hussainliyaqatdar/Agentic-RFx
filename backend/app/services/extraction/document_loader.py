from pathlib import Path

from docx import Document
from google.genai import types
from openpyxl import load_workbook

_MIME_BY_SUFFIX = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def _xlsx_to_text(path: Path) -> str:
    wb = load_workbook(path, data_only=True)
    lines = []
    for sheet in wb.worksheets:
        lines.append(f"[sheet: {sheet.title}]")
        for row in sheet.iter_rows(values_only=True):
            if any(cell is not None for cell in row):
                lines.append(" | ".join("" if cell is None else str(cell) for cell in row))
    return "\n".join(lines)


def _docx_to_text(path: Path) -> str:
    doc = Document(path)
    lines = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            lines.append(" | ".join(cell.text for cell in row.cells))
    return "\n".join(lines)


def load_vendor_documents(vendor_dir: Path) -> list:
    """Reads every file in a vendor's response folder and returns a list of Gemini
    `contents` parts (plain strings for text-derived documents, `types.Part` for
    anything sent to the model natively - PDF and image). Order matches the files
    on disk, so a follow-up email sorts after the document it follows up on."""
    parts: list = []
    # A plain-text email is treated as later/supplementary commentary rather than the primary
    # submission (e.g. a follow-up clarifying or overriding an earlier formal quote/photo), so
    # it's sorted after other files rather than by filename alone.
    candidates = [p for p in vendor_dir.iterdir() if not p.name.startswith(("~$", "."))]
    for path in sorted(candidates, key=lambda p: (p.suffix.lower() == ".txt", p.name)):
        suffix = path.suffix.lower()
        if suffix in _MIME_BY_SUFFIX:
            parts.append(f"--- Document: {path.name} ---")
            parts.append(types.Part.from_bytes(data=path.read_bytes(), mime_type=_MIME_BY_SUFFIX[suffix]))
        elif suffix == ".xlsx":
            parts.append(f"--- Document: {path.name} (spreadsheet, converted to text) ---\n{_xlsx_to_text(path)}")
        elif suffix == ".docx":
            parts.append(f"--- Document: {path.name} (Word document, converted to text) ---\n{_docx_to_text(path)}")
        elif suffix == ".txt":
            parts.append(f"--- Document: {path.name} (email) ---\n{path.read_text(encoding='utf-8')}")
    if not parts:
        raise ValueError(f"No readable vendor documents found in {vendor_dir}")
    return parts
