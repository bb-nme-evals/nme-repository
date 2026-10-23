"""
Validation module for NME JSON output.

Checks completeness, structure, and data integrity.
"""

import json
import logging
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path

from .config import KNOWN_ISOTOPES, MATRIX_ELEMENT_STRUCTURE

logger = logging.getLogger(__name__)


class JSONValidator:
    """
    Validate NME JSON files for completeness and correctness.
    """
    
    def __init__(self):
        """Initialize validator."""
        self.errors = []
        self.warnings = []
    
    def validate_file(self, filepath: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate a JSON file.
        
        Args:
            filepath: Path to JSON file to validate
        
        Returns:
            Tuple of (is_valid: bool, report: Dict)
        """
        self.errors = []
        self.warnings = []
        
        filepath = Path(filepath)
        
        if not filepath.exists():
            return False, {"error": f"File not found: {filepath}"}
        
        try:
            with open(filepath) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return False, {"error": f"Invalid JSON: {e}"}
        except Exception as e:
            return False, {"error": f"Failed to read file: {e}"}
        
        # Validate structure
        self._validate_structure(data)
        self._validate_entries(data.get("entries", []))
        
        is_valid = len(self.errors) == 0
        
        report = self._generate_report(data)
        return is_valid, report
    
    def validate_dict(self, data: Dict) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate a dictionary (already parsed JSON).
        
        Args:
            data: Dictionary to validate
        
        Returns:
            Tuple of (is_valid: bool, report: Dict)
        """
        self.errors = []
        self.warnings = []
        
        self._validate_structure(data)
        self._validate_entries(data.get("entries", []))
        
        is_valid = len(self.errors) == 0
        report = self._generate_report(data)
        
        return is_valid, report
    
    def _validate_structure(self, data: Dict) -> None:
        """Validate top-level structure."""
        required_fields = ["Reference", "URL", "bibtex", "entries"]
        
        for field in required_fields:
            if field not in data:
                self.errors.append(f"Missing required top-level field: {field}")
            elif field != "entries" and not isinstance(data[field], str):
                self.warnings.append(f"Field '{field}' is not a string")
        
        if "entries" in data and not isinstance(data["entries"], list):
            self.errors.append("Field 'entries' must be a list")
    
    def _validate_entries(self, entries: List[Dict]) -> None:
        """Validate all entries."""
        if not entries:
            self.warnings.append("No entries found in JSON")
            return
        
        for idx, entry in enumerate(entries):
            self._validate_entry(entry, idx)
    
    def _validate_entry(self, entry: Dict, entry_idx: int) -> None:
        """Validate a single entry."""
        prefix = f"Entry {entry_idx}:"
        
        # Required fields
        required = ["Model class", "Model", "Isotope", "g_A", "matrix_elements"]
        for field in required:
            if field not in entry:
                self.errors.append(f"{prefix} Missing field '{field}'")
            elif field != "matrix_elements" and not entry[field]:
                self.warnings.append(f"{prefix} Field '{field}' is empty")
        
        # Validate isotope
        isotope = entry.get("Isotope")
        if isotope and isotope not in KNOWN_ISOTOPES:
            self.warnings.append(f"{prefix} Unknown isotope '{isotope}'")
        
        # Validate g_A
        g_a = entry.get("g_A")
        if g_a:
            try:
                g_a_float = float(g_a)
                if not (0.8 <= g_a_float <= 1.5):
                    self.warnings.append(
                        f"{prefix} Unusual g_A value: {g_a} (expected 0.8-1.5)"
                    )
            except ValueError:
                self.errors.append(f"{prefix} g_A '{g_a}' is not numeric")
        
        # Validate matrix_elements structure
        self._validate_matrix_elements(entry.get("matrix_elements", {}), prefix)
    
    def _validate_matrix_elements(self, mat_elems: Dict, prefix: str) -> None:
        """Validate matrix_elements substructure."""
        if not isinstance(mat_elems, dict):
            self.errors.append(f"{prefix} matrix_elements must be a dict")
            return
        
        # Check expected top-level keys
        expected_keys = ["M_{total}", r"M_{long\,range}", r"M_{short\,range}", "M_summed", "M_subcomponents"]
        for key in expected_keys:
            if key not in mat_elems:
                self.warnings.append(f"{prefix} Missing matrix_elements key: {key}")
        
        # Validate value/error pairs
        for key, value in mat_elems.items():
            if key in ["M_summed", "M_subcomponents"]:
                # These are branches with sub-fields
                if not isinstance(value, dict):
                    self.errors.append(f"{prefix} {key} must be a dict")
                else:
                    for sub_key, sub_value in value.items():
                        self._validate_value_error_pair(sub_value, f"{prefix} {key}.{sub_key}")
            else:
                # These are leaf nodes
                self._validate_value_error_pair(value, f"{prefix} {key}")
    
    def _validate_value_error_pair(self, obj: Any, location: str) -> None:
        """Validate a {value, error} pair."""
        if not isinstance(obj, dict):
            self.errors.append(f"{location}: Expected dict with 'value' and 'error' keys")
            return
        
        if "value" not in obj or "error" not in obj:
            self.errors.append(f"{location}: Missing 'value' or 'error' key")
            return
        
        value = obj["value"]
        error = obj["error"]
        
        # Value can be empty string or numeric
        if value and value != "":
            try:
                float(value)
            except ValueError:
                self.errors.append(f"{location}: value '{value}' is not numeric")
        
        # Error can be empty string or numeric
        if error and error != "":
            try:
                float(error)
            except ValueError:
                self.errors.append(f"{location}: error '{error}' is not numeric")
        
        # If value exists, error should exist or be empty
        if value and not error:
            pass  # OK - empty error means no uncertainty reported
    
    def _generate_report(self, data: Dict) -> Dict[str, Any]:
        """Generate validation report."""
        entries = data.get("entries", [])
        
        # Count matrix elements
        element_counts = {}
        isotope_counts = {}
        model_counts = {}
        
        for entry in entries:
            isotope = entry.get("Isotope")
            if isotope:
                isotope_counts[isotope] = isotope_counts.get(isotope, 0) + 1
            
            model = entry.get("Model class")
            if model:
                model_counts[model] = model_counts.get(model, 0) + 1
            
            for elem in entry.get("matrix_elements", {}):
                if elem in ["M_summed", "M_subcomponents"]:
                    for sub_elem in entry["matrix_elements"][elem]:
                        full_name = f"{elem}.{sub_elem}"
                        element_counts[full_name] = element_counts.get(full_name, 0) + 1
                else:
                    element_counts[elem] = element_counts.get(elem, 0) + 1
        
        report = {
            "is_valid": len(self.errors) == 0,
            "entry_count": len(entries),
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings,
            "isotope_counts": dict(sorted(isotope_counts.items())),
            "model_counts": dict(sorted(model_counts.items())),
            "element_counts": dict(sorted(element_counts.items())),
        }
        
        return report
    
    def print_report(self, report: Dict) -> None:
        """Print validation report to logger."""
        logger.info("=" * 60)
        logger.info("VALIDATION REPORT")
        logger.info("=" * 60)
        logger.info(f"Valid: {report['is_valid']}")
        logger.info(f"Entries: {report['entry_count']}")
        logger.info(f"Errors: {report['error_count']}")
        logger.info(f"Warnings: {report['warning_count']}")
        
        if report["errors"]:
            logger.error("ERRORS:")
            for err in report["errors"]:
                logger.error(f"  - {err}")
        
        if report["warnings"]:
            logger.warning("WARNINGS:")
            for warn in report["warnings"]:
                logger.warning(f"  - {warn}")
        
        logger.info("\nIsotopes:")
        for iso, count in sorted(report["isotope_counts"].items()):
            logger.info(f"  {iso}: {count}")
        
        logger.info("\nModel classes:")
        for model, count in sorted(report["model_counts"].items()):
            logger.info(f"  {model}: {count}")
        
        logger.info("\nMatrix elements found:")
        for elem, count in sorted(report["element_counts"].items()):
            logger.info(f"  {elem}: {count}")
        
        logger.info("=" * 60)
