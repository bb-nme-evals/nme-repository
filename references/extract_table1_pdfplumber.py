import argparse
import re
from pathlib import Path

import pdfplumber


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract full text, markdown, and Table 1 candidates from a PDF using pdfplumber."
    )
    parser.add_argument("pdf", type=Path, help="Path to input PDF file")
    parser.add_argument(
        "--txt-out",
        type=Path,
        default=None,
        help="Optional output .txt path (default: <pdf>.txt)",
    )
    parser.add_argument(
        "--md-out",
        type=Path,
        default=None,
        help="Optional output .md path (default: <pdf>.md)",
    )
    parser.add_argument(
        "--table-out",
        type=Path,
        default=None,
        help="Optional Table 1 extraction report path (default: <pdf>_Table1_extract.md)",
    )
    return parser.parse_args()


def normalize_cell(value: object) -> str:
    if value is None:
        return ""
    return str(value).replace("\n", " ").strip()


def main() -> None:
    args = parse_args()
    pdf_path = args.pdf.resolve()

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    txt_out = args.txt_out or pdf_path.with_suffix(".txt")
    md_out = args.md_out or pdf_path.with_suffix(".md")
    table_out = args.table_out or pdf_path.with_name(pdf_path.stem + "_Table1_extract.md")

    all_text_pages = []
    md_parts = [f"# Extracted Text: {pdf_path.name}", ""]
    table1_hits = []

    with pdfplumber.open(str(pdf_path)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            all_text_pages.append(text)

            md_parts.append(f"## Page {i}")
            md_parts.append("")
            md_parts.append("```text")
            md_parts.append(text)
            md_parts.append("```")
            md_parts.append("")

            if re.search(r"\bTable\s*1\b", text, flags=re.IGNORECASE):
                table1_hits.append(i)

    txt_out.write_text("\n\n".join(all_text_pages), encoding="utf-8")
    md_out.write_text("\n".join(md_parts), encoding="utf-8")

    report = [f"# Table 1 Extraction Report: {pdf_path.name}", ""]
    report.append(
        "Detected pages containing 'Table 1': "
        + (", ".join(map(str, table1_hits)) if table1_hits else "none")
    )
    report.append("")

    with pdfplumber.open(str(pdf_path)) as pdf:
        target_pages = table1_hits[:] if table1_hits else list(range(1, min(6, len(pdf.pages) + 1)))

        for pnum in target_pages:
            page = pdf.pages[pnum - 1]
            page_text = page.extract_text() or ""

            report.append(f"## Page {pnum}")
            report.append("")
            report.append("### Raw page text snippet")
            report.append("```text")
            report.append("\n".join(page_text.splitlines()[:80]))
            report.append("```")
            report.append("")

            table_settings = {
                "vertical_strategy": "text",
                "horizontal_strategy": "text",
                "intersection_tolerance": 5,
                "snap_tolerance": 3,
                "join_tolerance": 3,
                "edge_min_length": 3,
                "min_words_vertical": 2,
                "min_words_horizontal": 1,
                "text_tolerance": 3,
                "text_x_tolerance": 2,
                "text_y_tolerance": 2,
            }

            tables = page.extract_tables(table_settings=table_settings) or []
            report.append(f"### Detected tables on page: {len(tables)}")
            report.append("")

            for ti, tbl in enumerate(tables, start=1):
                report.append(f"#### Table candidate {ti}")
                report.append("")

                if not tbl:
                    report.append("(empty)")
                    report.append("")
                    continue

                max_cols = max(len(r) for r in tbl if r) if tbl else 0
                norm_rows = []
                for row in tbl:
                    row = (row or []) + [""] * (max_cols - len(row or []))
                    norm_rows.append([normalize_cell(c) for c in row])

                if norm_rows:
                    header = norm_rows[0]
                    report.append("| " + " | ".join(header) + " |")
                    report.append("| " + " | ".join(["---"] * len(header)) + " |")
                    for row in norm_rows[1:]:
                        report.append("| " + " | ".join(row) + " |")
                    report.append("")

    table_out.write_text("\n".join(report), encoding="utf-8")

    print(f"Wrote: {txt_out}")
    print(f"Wrote: {md_out}")
    print(f"Wrote: {table_out}")


if __name__ == "__main__":
    main()
