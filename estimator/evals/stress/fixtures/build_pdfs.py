"""Generate deterministic stress-test PDF fixtures at target file sizes."""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

FIXTURES_DIR = Path(__file__).resolve().parent

ATTACHMENT_SIZES_KB: tuple[int, ...] = (5, 20, 50, 100)

RECALL_TOKENS: dict[int, str] = {
    5: "STRESS_TOKEN_5KB",
    20: "STRESS_TOKEN_20KB",
    50: "STRESS_TOKEN_50KB",
    100: "STRESS_TOKEN_100KB",
}

LOREM_PARAGRAPH = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod "
    "tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, "
    "quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. "
    "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu "
    "fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in "
    "culpa qui officia deserunt mollit anim id est laborum."
)


def attachment_pdf_path(size_kb: int) -> Path:
    """Return the on-disk path for a stress attachment of ``size_kb`` kilobytes."""
    if size_kb not in RECALL_TOKENS:
        available = ", ".join(str(size) for size in ATTACHMENT_SIZES_KB)
        raise KeyError(f"Unknown attachment size {size_kb}kb; choose from: {available}")
    return FIXTURES_DIR / f"attach_{size_kb}kb.pdf"


def recall_token(size_kb: int) -> str:
    """Return the unique recall token embedded in the ``size_kb`` fixture."""
    return RECALL_TOKENS[size_kb]


def build_pdfs(*, force: bool = False) -> list[Path]:
    """Ensure all stress-test PDF fixtures exist; generate any that are missing."""
    paths: list[Path] = []
    for size_kb in ATTACHMENT_SIZES_KB:
        path = attachment_pdf_path(size_kb)
        if path.exists() and not force:
            paths.append(path)
            continue
        path.write_bytes(_render_pdf(size_kb, RECALL_TOKENS[size_kb]))
        paths.append(path)
    return paths


def _render_pdf(target_kb: int, token: str) -> bytes:
    """Build a PDF whose file size is at least ``target_kb`` KiB with embedded ``token``."""
    target_bytes = target_kb * 1024
    filler_unit = f"{LOREM_PARAGRAPH}\n\n"
    repeat = 1

    while True:
        pdf_bytes = _pdf_bytes(token, filler_unit, repeat)
        if len(pdf_bytes) >= target_bytes:
            return pdf_bytes
        repeat = max(repeat + 1, int(repeat * target_bytes / max(len(pdf_bytes), 1)))


def _pdf_bytes(token: str, filler_unit: str, repeat: int) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(0, 5, token)
    pdf.ln(3)
    pdf.multi_cell(0, 5, filler_unit * repeat)
    return bytes(pdf.output())


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate stress-test PDF fixtures.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate fixtures even when files already exist.",
    )
    args = parser.parse_args()
    paths = build_pdfs(force=args.force)
    for path in paths:
        size_kb = path.stat().st_size / 1024
        print(f"wrote {path.name} ({size_kb:.1f} KiB)")


if __name__ == "__main__":
    main()
