from io import BytesIO

import pytest
from docx import Document
from pypdf import PdfWriter

from app.services.attachments import (
    ATTACHMENT_SEPARATOR,
    UnsupportedAttachmentError,
    attachments_total_chars,
    collect_attachment_payloads,
    enrich_transcript,
    extract_attachment_text,
)
from tests.conftest import make_pdf_with_text


def _make_blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _make_docx(*paragraphs: str) -> bytes:
    document = Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_extract_pdf_reads_generated_text() -> None:
    text = extract_attachment_text("spec.pdf", make_pdf_with_text("PostgreSQL required"))
    assert "PostgreSQL required" in text


def test_extract_pdf_returns_empty_for_blank_page() -> None:
    text = extract_attachment_text("spec.pdf", _make_blank_pdf())
    assert text == ""


def test_extract_pdf_formats_non_empty_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakePage:
        def __init__(self, content: str) -> None:
            self._content = content

        def extract_text(self) -> str:
            return self._content

    class FakeReader:
        def __init__(self, _stream) -> None:
            self.pages = [FakePage("PostgreSQL required"), FakePage("")]

    monkeypatch.setattr("app.services.attachments.PdfReader", FakeReader)
    text = extract_attachment_text("spec.pdf", b"%PDF-1.4")
    assert "--- Page 1 ---" in text
    assert "PostgreSQL required" in text


def test_extract_docx_returns_paragraphs() -> None:
    text = extract_attachment_text("spec.docx", _make_docx("PostgreSQL required", "Redis cache"))
    assert "PostgreSQL required" in text
    assert "Redis cache" in text


def test_unsupported_extension_raises() -> None:
    with pytest.raises(UnsupportedAttachmentError, match="Unsupported attachment type"):
        extract_attachment_text("notes.txt", b"plain text")


def test_enrich_transcript_without_attachments() -> None:
    transcript = "We need a CRM with auth and roles."
    assert enrich_transcript(transcript, []) == transcript


def test_enrich_transcript_adds_separator_and_content() -> None:
    docx_bytes = _make_docx("Must use PostgreSQL for persistence.")
    enriched = enrich_transcript(
        "Base transcript for the project.",
        [("spec.docx", docx_bytes)],
    )
    assert "Base transcript for the project." in enriched
    assert ATTACHMENT_SEPARATOR.format(filename="spec.docx") in enriched
    assert "Must use PostgreSQL for persistence." in enriched


def test_enrich_transcript_truncates_attachment_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.attachments.get_settings",
        lambda: type("S", (), {"MAX_ATTACHMENT_CHARS": 10})(),
    )
    monkeypatch.setattr(
        "app.services.attachments.extract_attachment_text",
        lambda _filename, _content: "x" * 20,
    )
    enriched = enrich_transcript("Base transcript.", [("big.pdf", b"%PDF")])
    assert enriched.startswith("Base transcript.")
    assert "x" * 10 in enriched
    assert "x" * 11 not in enriched


def test_enrich_transcript_skips_attachment_when_budget_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.attachments.get_settings",
        lambda: type("S", (), {"MAX_ATTACHMENT_CHARS": 5})(),
    )
    monkeypatch.setattr(
        "app.services.attachments.extract_attachment_text",
        lambda _filename, _content: "abcdefghij",
    )
    enriched = enrich_transcript(
        "Base transcript.",
        [("first.pdf", b"1"), ("second.pdf", b"2")],
    )
    assert enriched.count(ATTACHMENT_SEPARATOR.format(filename="first.pdf")) == 1
    assert enriched.count(ATTACHMENT_SEPARATOR.format(filename="second.pdf")) == 1
    assert "abcde" in enriched
    assert "fghij" not in enriched


def test_attachments_total_chars_matches_enriched_attachment_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.attachments.get_settings",
        lambda: type("S", (), {"MAX_ATTACHMENT_CHARS": 10})(),
    )
    monkeypatch.setattr(
        "app.services.attachments.extract_attachment_text",
        lambda _filename, _content: "x" * 20,
    )
    files = [("big.pdf", b"%PDF")]
    assert attachments_total_chars(files) == 10
    enriched = enrich_transcript("Base transcript.", files)
    assert enriched.startswith("Base transcript.")
    assert "x" * 10 in enriched


def test_attachments_total_chars_zero_without_files() -> None:
    assert attachments_total_chars([]) == 0


@pytest.mark.asyncio
async def test_collect_attachment_payloads_reads_multiple_files() -> None:
    class FakeUpload:
        def __init__(self, filename: str | None, content: bytes) -> None:
            self.filename = filename
            self._content = content

        async def read(self) -> bytes:
            return self._content

    uploads = [
        FakeUpload("spec.pdf", b"%PDF"),
        FakeUpload("brief.docx", b"doc-bytes"),
    ]
    payloads = await collect_attachment_payloads(uploads)  # type: ignore[arg-type]
    assert payloads == [("spec.pdf", b"%PDF"), ("brief.docx", b"doc-bytes")]


@pytest.mark.asyncio
async def test_collect_attachment_payloads_skips_empty_filename() -> None:
    class FakeUpload:
        def __init__(self, filename: str | None, content: bytes) -> None:
            self.filename = filename
            self._content = content

        async def read(self) -> bytes:
            return self._content

    uploads = [
        FakeUpload("", b"ignored"),
        FakeUpload("spec.docx", b"doc-bytes"),
    ]
    payloads = await collect_attachment_payloads(uploads)  # type: ignore[arg-type]
    assert payloads == [("spec.docx", b"doc-bytes")]
