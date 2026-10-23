#!/usr/bin/env python3
"""
Test script to extract and format NME data from CSV.
This tests the pipeline independently of PDF parsing.
"""

import pandas as pd
import sys
sys.path.insert(0, '.')

from nme_extractor import SemanticParser, JSONFormatter, JSONValidator

# Load CSV
print("Loading CSV data...")
df = pd.read_csv('references/PhysRevC.98.024608_Table_V_sample.csv')

print(f"Loaded {len(df)} rows with columns: {list(df.columns)}")
print()

# Parse with semantic parser
print("Parsing semantic content...")
parser = SemanticParser()
result = parser.parse_table(df)

entries = result['entries']
warnings = result['warnings']

print(f"Parsed {len(entries)} entries")
if warnings:
    print(f"Warnings:")
    for w in warnings[:3]:
        print(f"  - {w}")

print()

# Format as JSON
print("Formatting as JSON...")
formatter = JSONFormatter()
formatter.set_metadata(
    reference="Jokiniemi et al. 2018",
    url="https://journals.aps.org/prc/abstract/10.1103/PhysRevC.98.024608",
    bibtex="""@article{Jokiniemi:2018sxd,
  author = "Jokiniemi, L. and Ejiri, H. and Frekers, D. and Suhonen, J.",
  title = "{Neutrinoless $\\beta \\beta$ nuclear matrix elements using isovector spin-dipole $J^\\pi=2^−$ data}",
  doi = "10.1103/PhysRevC.98.024608",
  journal = "Phys. Rev. C",
  volume = "98",
  number = "2",
  pages = "024608",
  year = "2018"
}"""
)

formatter.add_entries_batch(entries)

# Print summary
summary = formatter.get_summary()
print(f"\nSummary:")
print(f"  Entries: {summary['entry_count']}")
print(f"  Isotopes: {summary['isotopes']}")
print(f"  Model classes: {summary['model_classes']}")
print(f"  Models: {summary['models']}")

# Validate
print("\nValidating...")
validator = JSONValidator()
is_valid, report = validator.validate_dict(formatter.to_dict())
validator.print_report(report)

# Write output
output_path = 'nme_values/PhysRevC.98.024608_extracted_from_csv.json'
formatter.write_to_file(output_path)

print(f"\nOutput written to: {output_path}")
