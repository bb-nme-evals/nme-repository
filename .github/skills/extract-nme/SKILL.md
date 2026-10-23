---
name: extract-nme
description: "Use when extracting nuclear matrix elements (NMEs) from PDF papers, reviewing NME tables, adding publication datasets or BibTeX, or modifying the standardized JSON schema and LaTeX export."
---

# Extract and review NME publication data

## Read before changing data

- Read [README.md](../../../README.md) for the complete JSON example and workflow.
- Read [config.py](../../../nme_extractor/config.py) for `MATRIX_ELEMENT_STRUCTURE`
  and aliases, and inspect the formatter and validator before changing key names.
- Existing datasets and passing tests are evidence of implementation behavior,
  not proof of scientific correctness. Do not rerun a writer over curated data
  until its output and metadata have been compared in a temporary local location.

## Procedure

1. Keep PDFs, text dumps, page PNGs, and intermediate extraction files local.
   Do not commit paper transcriptions under another extension to evade ignores.
2. Establish publication identity, DOI, complete BibTeX, table number, printed and
   PDF page numbers, parent isotopes, model variants, and stated `g_A` conventions.
   Do not infer a coupling solely from another paper or an extractor's default.
3. Visually inspect the table, units, definitions, signs, footnotes, and repeated
   row labels. Separate table values from nearby prose and figure annotations.
4. Try the general CLI in `scripts/extract_from_pdf.py` with `--review`. If it
   fails, inspect page text and word coordinates, crop the appropriate column,
   and implement a targeted parser with explicit header, row-count, and
   column-count checks. Detect the table itself, not just isotope names in an
   abstract. Captions may be fragmented or use `I` instead of `1`.
5. For the Ding 2024 layout, consult
   `scripts/extract_table_i_mr_cdft.py`: Table I is on PDF page 4, right column,
   five isotopes (`76Ge`, `82Se`, `100Mo`, `130Te`, `136Xe`) and 15 subcomponent
   rows. Coordinate bounds are layout-specific. Normalize U+2212 minus signs.
6. Parse to strings, retaining trailing zeros and signs. Interpret `6.8(3)` as
   value `6.8`, error `0.3`, and `5.54(10)` as `5.54`, error `0.10`. Missing
   uncertainties are empty strings. Dashes mean unreported unless the paper
   explicitly establishes zero. Do not invent values or error bars.
7. Preserve variant identifiers and one entry per distinct calculation. Check
   paper definitions before assigning a subcomponent to a summed field. Do not
   derive totals unless the formula/conventions and provenance are explicit.
8. Write UTF-8 JSON using a serializer, with complete top-level BibTeX. Never
   replace an existing citation with an empty string when regenerating outputs.
9. Check strict JSON parsing, non-empty entries, all expected isotope/variant
   combinations, every numeric column against the PDF, and validator warnings.
   The review CSV is not imported back automatically. Avoid the generic CSV
   script as a trusted writer when its column map or entry list is empty.
10. Prefer one reviewed publication-first dataset per table. Directory-based
    LaTeX export filters names, not duplicate publications. Use explicit inputs
    when alternate test extractions exist. Inspect diffs before staging/pushing;
    never stage raw paper files or environments.

## JSON contract

Top level: `Reference` (author/year), `URL` (stable publication/DOI link), `bibtex`
(full BibTeX string), and `entries` (list).

Entry: `Model class`, `Model`, `Isotope` (parent, e.g. `76Ge`), `g_A` (string),
and `matrix_elements` (object). Preserve case and exact spelling.

Each NME leaf is `{"value": "...", "error": "..."}`. Both fields are strings;
unreported fields are `""`. Do not use JSON null or numeric zeros for absence.

| Path/group | Required leaf slots |
| --- | --- |
| `matrix_elements` | `M_{total}`, `M_{long\,range}`, `M_{short\,range}` |
| `M_summed` | `M_{GT}`, `M_F`, `M_T` |
| `M_subcomponents` (15) | `M_F`, `M_{GT}^{AA}`, `M_{GT}^{AP}`, `M_{GT}^{PP}`, `M_{GT}^{MM}`, `M_{T}^{AA}`, `M_{T}^{AP}`, `M_{T}^{PP}`, `M_{T}^{MM}`, `M_{Fsd}`, `M_{GTsd}^{AA}`, `M_{GTsd}^{AP}`, `M_{GTsd}^{PP}`, `M_{Tsd}^{AP}`, `M_{Tsd}^{PP}` |

Leaf names are LaTeX math fragments without dollar signs; group names are not.
The in-memory backslash in `M_{long\,range}` must be escaped as `\\` in JSON.
BibTeX newlines must be escaped as `\n`, never literal line breaks in a string.

Keep `M_summed/M_F` distinct from `M_subcomponents/M_F`. The table generator uses
group/name pairs and must retain all 3 combined + 3 summed + 15 subcomponents
by default, even if entire columns are empty. Do not collapse repeated names.

## Verification

- Run `python -m unittest tests.test_parser` in the configured environment.
- Strict-parse changed JSON files and assert non-empty `bibtex` and entry lists
  for any newly curated publication dataset.
- Regenerate the LaTeX table with explicit curated inputs; confirm 26 columns
  (5 metadata + 21 NMEs), grouped headings, `$g_A$`, and missing-cell placeholders.
- Inspect the Git diff for unintended value changes, bibliography loss,
  duplicate datasets, and raw source material. Report limitations honestly.