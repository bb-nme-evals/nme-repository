"""
JSON formatter module.

Formats extracted NME data into the canonical JSON schema.
Handles metadata assembly and entry structuring.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from .config import ENTRY_FIELD_ORDER, MATRIX_ELEMENT_STRUCTURE

logger = logging.getLogger(__name__)


class JSONFormatter:
    """
    Format extracted NME entries into canonical JSON schema.
    
    Produces output compatible with the reference NME JSON schema
    (Unified NME values - PhysRevC.98.024608.json)
    """
    
    def __init__(self):
        """Initialize JSON formatter."""
        self.entries = []
        self.metadata = {
            "Reference": "",
            "URL": "",
            "bibtex": "",
        }
    
    def set_metadata(
        self,
        reference: str = "",
        url: str = "",
        bibtex: str = "",
    ):
        """
        Set top-level metadata for the JSON output.
        
        Args:
            reference: Publication citation (e.g., "Author Year")
            url: URL to publication
            bibtex: Full BibTeX entry
        """
        self.metadata["Reference"] = reference.strip()
        self.metadata["URL"] = url.strip()
        self.metadata["bibtex"] = bibtex.strip()
    
    def add_entry(self, entry: Dict[str, Any]) -> bool:
        """
        Add a parsed entry to the output.
        
        Args:
            entry: Parsed NME entry dictionary
        
        Returns:
            True if entry was added, False if rejected
        """
        # Validate entry structure
        if not self._validate_entry(entry):
            logger.warning(f"Skipping invalid entry: {entry}")
            return False
        
        # Structure entry according to schema
        structured_entry = self._structure_entry(entry)
        self.entries.append(structured_entry)
        
        return True
    
    def add_entries_batch(self, entries: List[Dict[str, Any]]) -> int:
        """
        Add multiple entries at once.
        
        Args:
            entries: List of parsed entry dictionaries
        
        Returns:
            Number of entries successfully added
        """
        count = 0
        for entry in entries:
            if self.add_entry(entry):
                count += 1
        
        logger.info(f"Added {count}/{len(entries)} entries")
        return count
    
    def _validate_entry(self, entry: Dict[str, Any]) -> bool:
        """
        Validate entry structure.
        
        Args:
            entry: Entry to validate
        
        Returns:
            True if valid, False otherwise
        """
        # Required fields
        required = ["Isotope", "Model class", "Model", "g_A"]
        for field in required:
            if not entry.get(field):
                logger.debug(f"Missing required field: {field}")
                return False
        
        # Must have at least one matrix element
        if not entry.get("matrix_elements"):
            logger.debug("No matrix elements in entry")
            return False
        
        return True
    
    def _structure_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Structure an entry according to the canonical schema.
        
        Args:
            entry: Raw parsed entry
        
        Returns:
            Entry structured per schema (with proper key ordering)
        """
        structured = {}
        
        # Add fields in canonical order
        for field in ENTRY_FIELD_ORDER:
            if field == "matrix_elements":
                # Build matrix_elements substructure
                structured["matrix_elements"] = self._structure_matrix_elements(
                    entry.get("matrix_elements", {})
                )
            else:
                structured[field] = entry.get(field)
        
        return structured
    
    def _structure_matrix_elements(
        self,
        raw_elements: Dict[str, Dict[str, str]]
    ) -> Dict[str, Any]:
        r"""
        Structure matrix_elements according to schema.
        
        Organizes elements into:
        - M_{total}, M_{long\,range}, M_{short\,range} (leaves)
        - M_summed (branch with M_{GT}, M_F, M_T)
        - M_subcomponents (branch with all subcomponents)
        
        Args:
            raw_elements: Dictionary of field -> {value, error}
        
        Returns:
            Structured matrix_elements dictionary
        """
        structured = {}
        
        # Top-level leaves
        for leaf in ["M_{total}", r"M_{long\,range}", r"M_{short\,range}"]:
            if leaf in raw_elements:
                structured[leaf] = raw_elements[leaf]
            else:
                structured[leaf] = {"value": "", "error": ""}
        
        # M_summed branch
        structured["M_summed"] = {}
        for field in ["M_{GT}", "M_F", "M_T"]:
            if field in raw_elements:
                structured["M_summed"][field] = raw_elements[field]
            else:
                structured["M_summed"][field] = {"value": "", "error": ""}
        
        # M_subcomponents branch (all remaining fields)
        structured["M_subcomponents"] = {}
        subcomponent_fields = [
            "M_F",  # Note: second M_F occurs here
            "M_{GT}^{AA}", "M_{GT}^{AP}", "M_{GT}^{PP}", "M_{GT}^{MM}",
            "M_{T}^{AA}", "M_{T}^{AP}", "M_{T}^{PP}", "M_{T}^{MM}",
            "M_{Fsd}",
            "M_{GTsd}^{AA}", "M_{GTsd}^{AP}", "M_{GTsd}^{PP}",
            "M_{Tsd}^{AP}", "M_{Tsd}^{PP}",
        ]
        
        for field in subcomponent_fields:
            if field in raw_elements:
                structured["M_subcomponents"][field] = raw_elements[field]
            else:
                structured["M_subcomponents"][field] = {"value": "", "error": ""}
        
        return structured
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Get output as Python dictionary.
        
        Returns:
            Dictionary ready for JSON serialization
        """
        output = {
            "Reference": self.metadata["Reference"],
            "URL": self.metadata["URL"],
            "bibtex": self.metadata["bibtex"],
            "entries": self.entries,
        }
        return output
    
    def to_json(self, indent: int = 2) -> str:
        """
        Get output as JSON string.
        
        Args:
            indent: JSON indentation level
        
        Returns:
            JSON string
        """
        output_dict = self.to_dict()
        return json.dumps(output_dict, indent=indent)
    
    def write_to_file(self, filepath: str, indent: int = 2) -> bool:
        """
        Write output to JSON file.
        
        Args:
            filepath: Output file path
            indent: JSON indentation level
        
        Returns:
            True if successful, False otherwise
        """
        try:
            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, 'w') as f:
                json.dump(self.to_dict(), f, indent=indent)
            
            logger.info(f"Wrote {len(self.entries)} entries to {filepath}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to write JSON file: {e}")
            return False
    
    def write_review_csv(self, filepath: str) -> bool:
        """
        Write entries to CSV for manual review.
        
        Args:
            filepath: Output CSV file path
        
        Returns:
            True if successful, False otherwise
        """
        try:
            import pandas as pd
            
            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Flatten entries for CSV
            rows = []
            for entry in self.entries:
                row = {
                    "Isotope": entry.get("Isotope"),
                    "Model class": entry.get("Model class"),
                    "Model": entry.get("Model"),
                    "g_A": entry.get("g_A"),
                }
                
                # Add all matrix elements as columns
                for elem_name, elem_data in entry.get("matrix_elements", {}).items():
                    row[f"{elem_name}_value"] = elem_data.get("value", "")
                    row[f"{elem_name}_error"] = elem_data.get("error", "")
                
                rows.append(row)
            
            df = pd.DataFrame(rows)
            df.to_csv(filepath, index=False)
            
            logger.info(f"Wrote {len(rows)} entries to review CSV: {filepath}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to write review CSV: {e}")
            return False
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics of formatted output.
        
        Returns:
            Dictionary with:
            {
                'entry_count': int,
                'isotopes': Set[str],
                'model_classes': Set[str],
                'models': Set[str],
                'element_counts': Dict[str, int],
            }
        """
        isotopes = set()
        model_classes = set()
        models = set()
        element_counts = {}
        
        for entry in self.entries:
            isotopes.add(entry.get("Isotope"))
            model_classes.add(entry.get("Model class"))
            models.add(entry.get("Model"))
            
            for elem in entry.get("matrix_elements", {}):
                element_counts[elem] = element_counts.get(elem, 0) + 1
        
        return {
            'entry_count': len(self.entries),
            'isotopes': sorted(list(isotopes)),
            'model_classes': sorted(list(model_classes)),
            'models': sorted(list(models)),
            'element_counts': dict(sorted(element_counts.items())),
        }
