"""Extract Table I from Ding, Li, and Yao (Phys. Lett. B 856, 138896)."""

import argparse
import re
import sys
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nme_extractor import JSONFormatter, JSONValidator


ISOTOPES = ("76Ge", "82Se", "100Mo", "130Te", "136Xe")
ROW_FIELDS = (
    "M_F",
    "M_{GT}^{AA}", "M_{GT}^{AP}", "M_{GT}^{PP}", "M_{GT}^{MM}",
    "M_{T}^{AA}", "M_{T}^{AP}", "M_{T}^{PP}", "M_{T}^{MM}",
    "M_{Fsd}",
    "M_{GTsd}^{AA}", "M_{GTsd}^{AP}", "M_{GTsd}^{PP}",
    "M_{Tsd}^{AP}", "M_{Tsd}^{PP}",
)
VALUE = r"-?\d+\.\d+"


def find_table_i_page(pdf: pdfplumber.PDF) -> pdfplumber.page.Page:
    """Locate the Table I right-hand-column page from its isotope header."""
    for page in pdf.pages:
        text = page.crop((page.width / 2, 100, page.width - 10, 550)).extract_text(
            x_tolerance=1, y_tolerance=2, layout=True
        ) or ""
        decimal_count = len(re.findall(r"\d+\.\d+", text))
        if all(isotope in text for isotope in ISOTOPES) and "NME" in text and decimal_count >= 40:
            return page
    raise ValueError("Could not locate Table I by its header and numeric rows")


def extract_table_i_values(pdf_path: Path) -> dict[str, dict[str, str]]:
    """Return one matrix-element dictionary per isotope from the Table I crop."""
    with pdfplumber.open(pdf_path) as pdf:
        page = find_table_i_page(pdf)
        table_text = page.crop((page.width / 2, 120, page.width - 10, 520)).extract_text(
            x_tolerance=1, y_tolerance=2, layout=True
        ) or ""

    rows = []
    for line in table_text.splitlines():
        normalized_line = line.translate({0x2212: "-"})
        numbers = re.findall(VALUE, normalized_line)
        if len(numbers) == len(ISOTOPES):
            rows.append(numbers)
            continue
        if "AA" in normalized_line and normalized_line.count("-") == len(ISOTOPES):
            rows.append(["-"] * len(ISOTOPES))
    if len(rows) != len(ROW_FIELDS):
        raise ValueError(
            f"Expected {len(ROW_FIELDS)} numeric rows in Table I, found {len(rows)}"
        )

    values = {isotope: {} for isotope in ISOTOPES}
    for field, row in zip(ROW_FIELDS, rows):
        for isotope, value in zip(ISOTOPES, row):
            values[isotope][field] = {"value": "" if value == "-" else value, "error": ""}
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract MR-CDFT Table I NME values.")
    parser.add_argument("pdf", type=Path, help="Input paper PDF")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("nme_values/PhysLettB.856.138896_Table_I.json"),
        help="Output JSON path",
    )
    args = parser.parse_args()

    values = extract_table_i_values(args.pdf)
    formatter = JSONFormatter()
    formatter.set_metadata(
        reference="Ding, Li, and Yao 2024",
        url="https://doi.org/10.1016/j.physletb.2024.138896",
        bibtex='''@article{Ding:2024obt,
    author = "Ding, Chen-rong and Li, Gang and Yao, Jiang-ming",
    title = "{Nuclear matrix elements of neutrinoless double-beta decay in covariant density functional theory with different mechanisms}",
    eprint = "2403.17722",
    archivePrefix = "arXiv",
    primaryClass = "nucl-th",
    doi = "10.1016/j.physletb.2024.138896",
    journal = "Phys. Lett. B",
    volume = "856",
    pages = "138896",
    year = "2024"
}''',
    )
    for isotope in ISOTOPES:
        formatter.add_entry({
            "Model class": "EDF",
            "Model": "MR-CDFT",
            "Isotope": isotope,
            "g_A": "1.27",
            "matrix_elements": values[isotope],
        })

    data = formatter.to_dict()
    is_valid, report = JSONValidator().validate_dict(data)
    if not is_valid:
        raise ValueError("Output validation failed: " + "; ".join(report["errors"]))
    formatter.write_to_file(args.output)
    print(f"Extracted {len(formatter.entries)} entries to {args.output}")


if __name__ == "__main__":
    main()