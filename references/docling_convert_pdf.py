import argparse
from pathlib import Path

from docling.document_converter import DocumentConverter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a PDF to Docling markdown and plain text outputs."
    )
    parser.add_argument("pdf", type=Path, help="Path to input PDF")
    parser.add_argument(
        "--md-out",
        type=Path,
        default=None,
        help="Optional markdown output path (default: <pdf>.docling.md)",
    )
    parser.add_argument(
        "--txt-out",
        type=Path,
        default=None,
        help="Optional text output path (default: <pdf>.docling.txt)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pdf_path = args.pdf.resolve()

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    md_out = args.md_out or pdf_path.with_suffix(".docling.md")
    txt_out = args.txt_out or pdf_path.with_suffix(".docling.txt")

    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    doc = result.document

    md_text = doc.export_to_markdown()
    txt_text = doc.export_to_text()

    md_out.write_text(md_text, encoding="utf-8")
    txt_out.write_text(txt_text, encoding="utf-8")

    print(f"Wrote markdown: {md_out}")
    print(f"Wrote text: {txt_out}")


if __name__ == "__main__":
    main()
