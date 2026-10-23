#!/usr/bin/env python3
"""
Direct NME CSV processor - for tables with isotope info in the first column.
"""

import pandas as pd
import re
import sys
sys.path.insert(0, '.')

from nme_extractor import JSONFormatter, JSONValidator

# Load CSV
df = pd.read_csv('references/PhysRevC.98.024608_Table_V_sample.csv')

# Parse rows manually
entries = []

for idx, row in df.iterrows():
    nuclear_transition = row['Nuclear transition']
    basis = row['Basis']
    model = row['Model']
    
    # Extract isotope from transition (e.g., "76Ge -> 76Se" -> "76Ge")
    match = re.match(r'(\d+[A-Z][a-z]?)\s*->', nuclear_transition)
    if not match:
        continue
    isotope = match.group(1)
    
    # Parse model class from basis
    model_class = "QRPA" if "WS" in basis or "sp" in basis else "Shell Model"
    
    # Build matrix element dictionary
    matrix_elements = {}
    
    # Map column names to canonical matrix element names
    column_mapping = {
        'M_F^(0nubb)': 'M_F',
        'M_GT^(0nubb)': 'M_{GT}',
        'M_T^(0nubb)': 'M_T',
        'M^(0nubb)': 'M_{total}',
    }
    
    for col, canonical_name in column_mapping.items():
        value = row[col]
        if pd.isna(value) or value == "":
            continue
        
        # Parse value and error from string
        value_str = str(value).strip()
        
        # Handle +/- format: "value +/- error"
        if '+/-' in value_str or '±' in value_str:
            # Split on +/- or ±
            match = re.match(r'([-\d.]+)\s*[±+/-]+\s*([\d.]+)', value_str)
            if match:
                val = match.group(1)
                err = match.group(2)
            else:
                val = value_str
                err = ""
        else:
            val = value_str
            err = ""
        
        matrix_elements[canonical_name] = {
            "value": val,
            "error": err,
        }
    
    # Add g_A (assume 1.00 if not specified)
    g_a = "1.00"
    
    # Create entry
    entry = {
        "Model class": model_class,
        "Model": basis,
        "Isotope": isotope,
        "g_A": g_a,
        "matrix_elements": matrix_elements,
    }
    
    entries.append(entry)
    print(f"Parsed: {isotope} / {basis} / Model {model} -> {len(matrix_elements)} matrix elements")

print(f"\nTotal entries: {len(entries)}\n")

# Format as JSON
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

count = formatter.add_entries_batch(entries)
print(f"Added {count} entries to formatter\n")

# Summary
summary = formatter.get_summary()
print("Summary:")
print(f"  Entries: {summary['entry_count']}")
print(f"  Isotopes: {', '.join(summary['isotopes'])}")
print(f"  Model classes: {', '.join(summary['model_classes'])}")
print(f"  Matrix elements found:")
for elem, cnt in sorted(summary['element_counts'].items()):
    print(f"    {elem}: {cnt}")

# Validate
print("\nValidating...")
validator = JSONValidator()
is_valid, report = validator.validate_dict(formatter.to_dict())

if is_valid:
    print("✓ Validation PASSED")
else:
    print("✗ Validation FAILED")

# Write output
output_path = 'nme_values/PhysRevC.98.024608_extracted_direct.json'
formatter.write_to_file(output_path)
print(f"\nJSON written to: {output_path}")
