# Nuclear matrix element repository

This repository provides Python scripts for scraping tables from research papers,
extracting nuclear matrix elements (NMEs) for neutrinoless double-beta decay,
and storing the results in a standardized JSON format. The datasets retain
publication references, nuclear-model details, isotope identities, axial couplings,
and reported uncertainties so they can be compared and rendered as LaTeX tables.

Extraction is assisted, not guaranteed: scientific PDF layouts require review
against the original paper before an output can be treated as curated data.

## Repository layout

- [nme_values/](nme_values/): publication datasets and legacy/test compilations.
- [nme_extractor/](nme_extractor/): PDF detection, semantic parsing, JSON formatting,
  validation, and canonical key definitions.
- [scripts/extract_from_pdf.py](scripts/extract_from_pdf.py): general PDF pipeline.
- [scripts/extract_table_i_mr_cdft.py](scripts/extract_table_i_mr_cdft.py): targeted
  Table I extraction for Ding, Li, and Yao (2024).
- [scripts/json_to_latex_table.py](scripts/json_to_latex_table.py): JSON-to-LaTeX export.
- [tests/test_parser.py](tests/test_parser.py): parser, formatter, and validator tests.
- [.github/skills/extract-nme/SKILL.md](.github/skills/extract-nme/SKILL.md):
  extraction and schema instructions for future agents.

## Installation

Use Python 3.10 or newer (some scripts use modern type annotations).
From the repository root:

```sh
python -m venv .venv
# Activate the environment using your platform's activation command.
python -m pip install -r requirements.txt
```

[requirements.txt](requirements.txt) provides the core extraction dependencies.
Exploratory Docling/Tabula scripts require optional dependencies and are not the
validated default pipeline.

## Data and bibliography policy

Raw paper PDFs, extracted text, and PNG page images stay local. Git ignores
these extensions, case-insensitively; the dependency manifest is an explicit
exception to the text-file rule. Do not commit paper transcriptions in other
formats simply to bypass the rules. Only reviewed numeric data and necessary
code/documentation should be published.

Store each paper's **full BibTeX entry inside its JSON document**, in the
top-level `bibtex` string, alongside `Reference` and a stable DOI/publisher URL.
No separate bibliography file is required. Preserve bibliography metadata when
regenerating datasets. Use a JSON serializer: literal newlines inside a JSON
string are invalid; escaped `\n` characters are valid.

Prefer publication-first names such as
[nme_values/PhysLettB.856.138896_Table_I.json](nme_values/PhysLettB.856.138896_Table_I.json).
Choose one reviewed dataset per publication/table and avoid counting alternate
test extractions as independent calculations. Existing compilation and test
files are retained for context; their presence does not imply independent data.

## Standard JSON format

Each document describes one publication and contains an `entries` list. One entry
represents one isotope/model/parameter combination; distinct calculations may
share the same isotope. Field names and capitalization are significant.

| Field | Meaning |
| --- | --- |
| `Reference` | Human-readable author/year citation |
| `URL` | Stable publication link, preferably DOI |
| `bibtex` | Complete BibTeX entry as a JSON string |
| `entries` | List of calculation records |
| `Model class` | Broad method, e.g. `QRPA`, `EDF`, `Shell Model`, `IBM` |
| `Model` | Specific variant, e.g. `MR-CDFT`, basis/model identifier |
| `Isotope` | Parent isotope as mass plus symbol, e.g. `76Ge` |
| `g_A` | Axial coupling as a string, preserving reported precision |
| `matrix_elements` | The nested structure illustrated below |

Example record with all 21 matrix-element slots (illustrative, not a new dataset):

```json
{
  "Reference": "Example author 2024",
  "URL": "https://example.org/publication",
  "bibtex": "@article{example2024, author={Example Author}, title={Example study}, year={2024}}",
  "entries": [
    {
      "Model class": "QRPA",
      "Model": "Example variant",
      "Isotope": "76Ge",
      "g_A": "1.00",
      "matrix_elements": {
        "M_{total}": {"value": "6.8", "error": "0.3"},
        "M_{long\\,range}": {"value": "", "error": ""},
        "M_{short\\,range}": {"value": "", "error": ""},
        "M_summed": {
          "M_{GT}": {"value": "", "error": ""},
          "M_F": {"value": "", "error": ""},
          "M_T": {"value": "", "error": ""}
        },
        "M_subcomponents": {
          "M_F": {"value": "", "error": ""},
          "M_{GT}^{AA}": {"value": "", "error": ""},
          "M_{GT}^{AP}": {"value": "", "error": ""},
          "M_{GT}^{PP}": {"value": "", "error": ""},
          "M_{GT}^{MM}": {"value": "", "error": ""},
          "M_{T}^{AA}": {"value": "", "error": ""},
          "M_{T}^{AP}": {"value": "", "error": ""},
          "M_{T}^{PP}": {"value": "", "error": ""},
          "M_{T}^{MM}": {"value": "", "error": ""},
          "M_{Fsd}": {"value": "", "error": ""},
          "M_{GTsd}^{AA}": {"value": "", "error": ""},
          "M_{GTsd}^{AP}": {"value": "", "error": ""},
          "M_{GTsd}^{PP}": {"value": "", "error": ""},
          "M_{Tsd}^{AP}": {"value": "", "error": ""},
          "M_{Tsd}^{PP}": {"value": "", "error": ""}
        }
      }
    }
  ]
}
```

- All `value` and `error` leaves are **strings**, including numeric values.
  Preserve signs, trailing zeros, and reported precision.
- Unreported values and uncertainties are `""`, not zero. A missing error does
  not mean an exact value. Source dashes must not automatically become zero.
- `6.8(3)` becomes `{"value": "6.8", "error": "0.3"}`;
  `5.54(10)` becomes `{"value": "5.54", "error": "0.10"}`.
- Matrix-element leaf keys are LaTeX-ready **math fragments**, without `$`.
  JSON encodes the backslash in `M_{long\,range}` as `\\`.
  `M_summed` and `M_subcomponents` are structural keys, not math labels.
- There are 3 combined, 3 summed, and **15 subcomponent** slots.
  `M_F` appears in both branches: preserve the full path and never collapse them
  into a single table column. Do not populate one branch just because another
  contains a similarly named quantity without checking the paper's definitions.
- The canonical structure and aliases live in
  [nme_extractor/config.py](nme_extractor/config.py).

## Extraction workflow

1. Obtain the PDF locally and record the citation, DOI, relevant table/page,
   definitions, model variants, and coupling conventions.
2. Inspect the actual table. Try the general pipeline:

   ```sh
   python scripts/extract_from_pdf.py references/paper.pdf --output nme_values/Journal.Volume.Article.json --review
   ```

3. Review row/column assignments, numerical signs, precision, and error notation
   against the PDF. The review CSV is an inspection aid: edits to it are **not**
   automatically read back into the pipeline.
4. If table detection fails, inspect cropped text and coordinates. Captions can
   be fragmented, use Roman numerals, or be mixed with another column. Zero
   detected tables is not proof that the paper has no numerical tables.
   A targeted example is:

   ```sh
   python scripts/extract_table_i_mr_cdft.py references/1-s2.0-S0370269324004544-main.pdf
   ```

   This script is specific to the source layout, checks for five isotope columns
   and 15 rows, and preserves reported missing cells. It is not a universal parser.
5. Verify model and `g_A` from the paper; existing scripts contain assumptions or
   defaults that must not be generalized. Do not derive missing combined NMEs
   without explicitly verifying the paper's formula and conventions.
6. Supply/verify the full top-level BibTeX. The general pipeline's PDF metadata
   does not guarantee a complete citation. Validate both JSON syntax and values;
   inspect warnings, non-empty entry count, and spot-check every column.
7. Publish only reviewed JSON and code. Stage explicit files and inspect the
   staged diff, including whether any existing citation was overwritten.

### Known limitations

Generic table and fuzzy-header recognition can misclassify prose, miss tables,
or fail on unfamiliar headers. The exploratory semantic CSV script currently
does not recognize all sample-table headers and may yield zero entries; the
direct CSV script is a separate workaround requiring its local input CSV.
Figures and scanned PDFs need a separate, reviewed workflow. Validation checks
structure and plausible values, not scientific correctness or source fidelity.

## LaTeX tables

```sh
python scripts/json_to_latex_table.py nme_values --sort --output nme_values/nme_table.tex
```

By default the table contains 5 metadata columns plus all 21 NME slots, including
missing cells (`--`), with grouped Combined, Summed, and Subcomponents headings.
Uncertainties render with `\pm`; the axial-coupling header is `$g_A$`.
Load `amsmath` and `graphicx` in the enclosing LaTeX document. `--longtable`
requires the `longtable` package and may need landscape layout for the wide table.

Options include `--caption`, `--label`, `--sort`, `--longtable`, and opt-in
`--drop-empty`. Directory scans normally include only publication-named JSON;
`--all-files` includes compilations too. This is a filename filter, **not**
deduplication between two publication-named test outputs. Pass explicit reviewed
files if multiple extraction versions exist.

## Validation and tests

```sh
python -m unittest tests.test_parser
```

For programmatic validation, use `JSONValidator.validate_file(path)` or
`validate_dict(data)` from `nme_extractor`. A successful report does not establish
that rows correspond to the source paper or that the bibliography is complete;
those checks remain part of review.