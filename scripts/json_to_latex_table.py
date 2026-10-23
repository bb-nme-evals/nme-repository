"""Build a LaTeX-ready table of NME values from the nme_values JSON files."""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nme_extractor.config import MATRIX_ELEMENT_STRUCTURE

META_COLUMNS = ("Model", "Model class", "Reference", "Isotope", "g_A")
META_HEADERS = {"g_A": "$g_A$"}
MISSING = "--"

# M_F appears under both branches, so columns are keyed by (group, name).
GROUPS = {"M_summed": "summed", "M_subcomponents": "sub"}
GROUP_TITLES = {"top": "Combined", "summed": "Summed", "sub": "Subcomponents"}

# Directory scans take only publication-named files (e.g. PhysRevC.98.024608_*.json),
# skipping the hand-curated compilations that restate the same papers.
PUBLICATION_FILE = re.compile(r"^[A-Za-z]+\.\d")

# Subscript rendering for the canonical matrix-element names.
SUBSCRIPTS = {
    "total": r"\text{tot}",
    "long_range": r"\text{LR}",
    "short_range": r"\text{SR}",
    "GT": r"\text{GT}",
    "F": r"\text{F}",
    "T": r"\text{T}",
    "Fsd": r"\text{F,sd}",
    "GTsd": r"\text{GT,sd}",
    "Tsd": r"\text{T,sd}",
}

LATEX_SPECIALS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def canonical_name(name: str) -> str:
    """Collapse the differing brace/spacing conventions onto one key."""
    return name.replace(r"\,", "_").replace(" ", "_").replace("{", "").replace("}", "")


def schema_columns() -> list[tuple[str, str]]:
    columns: list[tuple[str, str]] = []
    for name, child in MATRIX_ELEMENT_STRUCTURE.items():
        if child is None:
            columns.append(("top", canonical_name(name)))
        else:
            columns.extend((GROUPS[name], canonical_name(key)) for key in child)
    return columns


def latex_header(column: str) -> str:
    base, _, superscript = column.partition("^")
    subscript = SUBSCRIPTS.get(base[2:], rf"\text{{{base[2:]}}}") if base.startswith("M_") else base
    header = rf"$M_{{{subscript}}}"
    if superscript:
        header += rf"^{{{superscript}}}"
    return header + "$"


def escape(text: str) -> str:
    return "".join(LATEX_SPECIALS.get(character, character) for character in str(text))


def flatten_elements(elements: dict, group: str = "top") -> dict[tuple[str, str], dict[str, str]]:
    """Flatten the nested matrix_elements tree, keyed by (group, canonical name)."""
    flat: dict[tuple[str, str], dict[str, str]] = {}
    for name, node in elements.items():
        if not isinstance(node, dict):
            continue
        if "value" in node:
            flat[(group, canonical_name(name))] = node
        else:
            flat.update(flatten_elements(node, GROUPS.get(name, group)))
    return flat


def format_value(cell: dict[str, str] | None) -> str:
    if not cell:
        return MISSING
    value = str(cell.get("value", "")).strip()
    error = str(cell.get("error", "")).strip()
    if value in ("", "-", "--"):
        return MISSING
    value = value.replace("−", "-")
    return rf"${value} \pm {error}$" if error else f"${value}$"


def load_rows(paths: list[Path]) -> list[dict]:
    rows = []
    for path in paths:
        # utf-8-sig: some files were written by PowerShell and carry a BOM.
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        reference = data.get("Reference", "")
        for entry in data.get("entries", []):
            row = {field: entry.get(field, "") for field in META_COLUMNS}
            row["Reference"] = reference
            row["elements"] = flatten_elements(entry.get("matrix_elements", {}))
            rows.append(row)
    return rows


def build_table(rows: list[dict], drop_empty: bool, caption: str, label: str, longtable: bool) -> str:
    columns = schema_columns()
    if drop_empty:
        columns = [c for c in columns if any(format_value(r["elements"].get(c)) != MISSING for r in rows)]

    alignment = "l" * len(META_COLUMNS) + "c" * len(columns)

    group_cells = [rf"\multicolumn{{{len(META_COLUMNS)}}}{{c}}{{}}"]
    for group in dict.fromkeys(group for group, _ in columns):
        width = sum(1 for other, _ in columns if other == group)
        group_cells.append(rf"\multicolumn{{{width}}}{{c}}{{{GROUP_TITLES[group]}}}")
    group_line = " & ".join(group_cells) + r" \\"

    headers = [META_HEADERS.get(name, escape(name)) for name in META_COLUMNS]
    headers += [latex_header(name) for _, name in columns]
    header_line = " & ".join(headers) + r" \\"

    body = []
    for row in rows:
        cells = [escape(row[field]) for field in META_COLUMNS]
        cells += [format_value(row["elements"].get(column)) for column in columns]
        body.append(" & ".join(cells) + r" \\")

    head = [r"\hline", group_line, header_line, r"\hline"]
    if longtable:
        lines = [
            rf"\begin{{longtable}}{{{alignment}}}",
            rf"\caption{{{caption}}}\label{{{label}}}\\",
            *head, r"\endfirsthead",
            *head, r"\endhead",
            *body,
            r"\hline",
            r"\end{longtable}",
        ]
    else:
        lines = [
            r"\begin{table}[htbp]", r"\centering", rf"\caption{{{caption}}}", rf"\label{{{label}}}",
            r"\resizebox{\textwidth}{!}{%",
            rf"\begin{{tabular}}{{{alignment}}}",
            *head,
            *body,
            r"\hline",
            r"\end{tabular}}",
            r"\end{table}",
        ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Write a LaTeX table from NME JSON files.")
    parser.add_argument("inputs", nargs="+", type=Path, help="JSON files or directories")
    parser.add_argument("--output", type=Path, help="Output .tex file (default: stdout)")
    parser.add_argument("--caption", default="Nuclear matrix elements for $0\\nu\\beta\\beta$ decay.")
    parser.add_argument("--label", default="tab:nme")
    parser.add_argument("--longtable", action="store_true", help="Emit a longtable environment")
    parser.add_argument("--drop-empty", action="store_true", help="Omit columns that are empty for every row")
    parser.add_argument("--sort", action="store_true", help="Sort rows by isotope, then reference")
    parser.add_argument("--all-files", action="store_true", help="Include non-publication-named files in directory scans")
    args = parser.parse_args()

    paths: list[Path] = []
    for item in args.inputs:
        if not item.is_dir():
            paths.append(item)
            continue
        found = sorted(item.glob("*.json"))
        if not args.all_files:
            found = [p for p in found if PUBLICATION_FILE.match(p.stem)]
        paths.extend(found)
    if not paths:
        raise SystemExit("No JSON files found")

    rows = load_rows(paths)
    if not rows:
        raise SystemExit("No entries found in the provided JSON files")
    if args.sort:
        rows.sort(key=lambda r: (int(re.match(r"\d+", r["Isotope"] or "0").group()), r["Reference"]))

    table = build_table(rows, args.drop_empty, args.caption, args.label, args.longtable)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(table, encoding="utf-8")
        print(f"Wrote {len(rows)} rows to {args.output}")
    else:
        print(table)


if __name__ == "__main__":
    main()
