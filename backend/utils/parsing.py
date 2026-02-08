"""
File parsing utilities for OpenRecords.
Extracts text from PDF, DOCX, MD, and TXT files.
"""
import io
from typing import List, Tuple


def extract_text_from_pdf(data: bytes) -> List[Tuple[int, str]]:
    """
    Extract text from PDF bytes.
    Returns list of (page_number, text) tuples.
    """
    import fitz  # PyMuPDF

    pages: List[Tuple[int, str]] = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")
            if text and text.strip():
                pages.append((page_num, text.strip()))
    return pages


def extract_text_from_docx(data: bytes) -> List[Tuple[int, str]]:
    """
    Extract text from DOCX bytes.
    Returns list of (paragraph_index, text) tuples.
    """
    from docx import Document

    doc = Document(io.BytesIO(data))
    paragraphs: List[Tuple[int, str]] = []
    for idx, para in enumerate(doc.paragraphs, start=1):
        text = para.text.strip()
        if text:
            paragraphs.append((idx, text))
    return paragraphs


def extract_text_from_markdown(data: bytes) -> str:
    """
    Extract raw text from Markdown bytes.
    Returns the plain text content (markdown is already text).
    """
    return data.decode("utf-8", errors="ignore").strip()


def extract_text_from_txt(data: bytes) -> str:
    """
    Extract text from TXT bytes.
    """
    return data.decode("utf-8", errors="ignore").strip()


# Map of MIME type / extension patterns to extractors
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}

MIME_TO_EXT = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/x-markdown": ".md",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}


def detect_extension(filename: str, content_type: str | None) -> str | None:
    """Detect file extension from filename or MIME type."""
    from pathlib import Path

    ext = Path(filename).suffix.lower()
    if ext in SUPPORTED_EXTENSIONS:
        return ext

    if content_type and content_type in MIME_TO_EXT:
        return MIME_TO_EXT[content_type]

    return None


def extract_text(data: bytes, extension: str) -> List[Tuple[int, str]]:
    """
    Unified text extraction.
    Returns list of (page_or_section_number, text) tuples.
    """
    ext = extension.lower()

    if ext == ".pdf":
        return extract_text_from_pdf(data)

    if ext == ".docx":
        return extract_text_from_docx(data)

    if ext in (".md", ".txt"):
        text = extract_text_from_txt(data) if ext == ".txt" else extract_text_from_markdown(data)
        if not text:
            return []
        # Split into page-like sections (one section = whole file)
        return [(1, text)]

    return []
