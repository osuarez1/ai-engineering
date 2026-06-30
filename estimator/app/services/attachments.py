"""Local text extraction for session attachments (Path B).

PDFs and Word documents are parsed in the AI service before the LLM call.
Extracted text is concatenated to the transcript with an explicit delimiter so
the model can treat attachments as supplementary context, not instructions.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from docx import Document
from fastapi import UploadFile
from pypdf import PdfReader

from app.config import get_settings

ATTACHMENT_SEPARATOR = "=== attachment: {filename} ==="

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


class UnsupportedAttachmentError(ValueError):
    """Raised when an uploaded file type cannot be processed locally."""


def extract_attachment_text(filename: str, content: bytes) -> str:
    """Extract plain text from a supported attachment."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(content)
    if suffix == ".docx":
        return _extract_docx(content)
    raise UnsupportedAttachmentError(
        f"Unsupported attachment type '{suffix or '(none)'}' for file '{filename}'. "
        f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
    )


def _attachment_blocks(files: list[tuple[str, bytes]]) -> tuple[list[str], int]:
    """Build separator + text blocks for attachments; return blocks and char count."""
    max_chars = get_settings().MAX_ATTACHMENT_CHARS
    blocks: list[str] = []
    attachment_chars = 0
    for filename, content in files:
        extracted = extract_attachment_text(filename, content)
        remaining = max_chars - attachment_chars
        if remaining <= 0:
            extracted = ""
        elif len(extracted) > remaining:
            extracted = extracted[:remaining]
        attachment_chars += len(extracted)
        blocks.append(ATTACHMENT_SEPARATOR.format(filename=filename))
        blocks.append(extracted)
    return blocks, attachment_chars


def attachments_total_chars(files: list[tuple[str, bytes]]) -> int:
    """Return the number of attachment characters included after truncation."""
    if not files:
        return 0
    _, count = _attachment_blocks(files)
    return count


def enrich_transcript(transcript: str, files: list[tuple[str, bytes]]) -> str:
    """Append extracted attachment text to the transcript with clear separators."""
    if not files:
        return transcript

    attachment_blocks, _ = _attachment_blocks(files)
    return "\n\n".join([transcript, *attachment_blocks])


def _extract_pdf(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    parts: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            parts.append(f"--- Page {index} ---\n{text}")
    return "\n\n".join(parts)


def _extract_docx(content: bytes) -> str:
    document = Document(BytesIO(content))
    paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
    return "\n".join(paragraphs)


async def collect_attachment_payloads(
    uploads: list[UploadFile],
) -> list[tuple[str, bytes]]:
    """Read uploaded files, skipping entries without a filename."""
    payloads: list[tuple[str, bytes]] = []
    for upload in uploads:
        if not upload.filename:
            continue
        content = await upload.read()
        payloads.append((upload.filename, content))
    return payloads
