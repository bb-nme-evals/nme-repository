"""
Semantic parsing module.

Interprets table column headers and row content to extract:
- Isotope names
- Model class and variant
- g_A values
- Matrix element values and errors
"""

import logging
import re
from typing import List, Dict, Tuple, Optional, Any
import pandas as pd
from difflib import SequenceMatcher

try:
    from fuzzywuzzy import fuzz
except ImportError:
    fuzz = None
    logging.warning("fuzzywuzzy not installed. Fuzzy matching disabled.")

from .config import (
    KNOWN_ISOTOPES,
    MODEL_CLASSES,
    MODEL_VARIANTS,
    ALIAS_TO_CANONICAL,
    FUZZY_MATCH_THRESHOLD,
    ISOTOPE_PATTERN,
    ERROR_PATTERNS,
)

logger = logging.getLogger(__name__)


class SemanticParser:
    """
    Parse semantic content from extracted tables.
    
    Identifies columns and their meanings, parses values with errors,
    and extracts nuclear physics data.
    """
    
    def __init__(self):
        """Initialize semantic parser."""
        self.column_map = {}  # Maps column header -> canonical field name
        self.uncertainties = []  # List of parsed uncertainties
    
    def parse_table(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Parse an entire table and extract NME entries.
        
        Args:
            df: DataFrame to parse
        
        Returns:
            Dictionary with:
            {
                'entries': List[Dict],  # Parsed entries
                'column_map': Dict,     # Column name mappings
                'warnings': List[str],  # Parsing warnings/ambiguities
            }
        """
        logger.info(f"Parsing table with shape {df.shape}")
        
        self.column_map = self._identify_columns(df)
        entries = []
        warnings = []
        
        # Normalize column headers
        df_normalized = df.rename(columns=str.strip)
        
        # Parse each row
        for idx, row in df_normalized.iterrows():
            try:
                entry = self._parse_row(row, self.column_map)
                if entry:
                    entries.append(entry)
            except Exception as e:
                warning = f"Row {idx}: Failed to parse - {e}"
                logger.warning(warning)
                warnings.append(warning)
        
        logger.info(f"Parsed {len(entries)} entries from table")
        
        return {
            'entries': entries,
            'column_map': self.column_map,
            'warnings': warnings,
        }
    
    def _identify_columns(self, df: pd.DataFrame) -> Dict[str, Optional[str]]:
        """
        Identify what each column represents.
        
        Args:
            df: DataFrame with headers to identify
        
        Returns:
            Dictionary mapping column header -> canonical field name
            (or None if unidentified)
        """
        column_map = {}
        
        for col in df.columns:
            col_clean = str(col).strip().lower()
            
            # Try exact and fuzzy matching to canonical names
            canonical = self._match_column_name(col_clean)
            column_map[col] = canonical
            
            if canonical:
                logger.debug(f"Column '{col}' -> '{canonical}'")
            else:
                logger.debug(f"Column '{col}' -> UNKNOWN")
        
        return column_map
    
    def _match_column_name(self, col_text: str) -> Optional[str]:
        """
        Match a column header to a canonical field name.
        
        Args:
            col_text: Column header text (cleaned, lowercase)
        
        Returns:
            Canonical field name or None if no match
        """
        # Direct match in alias dictionary
        if col_text in ALIAS_TO_CANONICAL:
            return ALIAS_TO_CANONICAL[col_text]
        
        # Check for isotope/model/g_A patterns
        if any(iso in col_text for iso in KNOWN_ISOTOPES):
            return "Isotope"
        if any(cls in col_text.lower() for cls in MODEL_CLASSES):
            return "Model class"
        if any(var in col_text for var in MODEL_VARIANTS):
            return "Model"
        if "g_a" in col_text or "g_A" in col_text or "gA" in col_text:
            return "g_A"
        
        # Fuzzy matching for matrix element fields
        if fuzz:
            best_match = None
            best_score = 0
            
            for alias in ALIAS_TO_CANONICAL.keys():
                score = fuzz.token_sort_ratio(col_text, alias)
                if score > best_score:
                    best_score = score
                    best_match = ALIAS_TO_CANONICAL[alias]
            
            if best_score >= FUZZY_MATCH_THRESHOLD:
                logger.debug(f"Fuzzy match '{col_text}' -> '{best_match}' ({best_score}%)")
                return best_match
        
        return None
    
    def _parse_row(self, row: pd.Series, column_map: Dict) -> Optional[Dict]:
        """
        Parse a single row into an NME entry.
        
        Args:
            row: Pandas Series representing one row
            column_map: Mapping from column header to field name
        
        Returns:
            Dictionary with parsed entry, or None if invalid
        """
        entry = {
            "Model class": None,
            "Model": None,
            "Isotope": None,
            "g_A": None,
            "matrix_elements": {},
        }
        
        matrix_elements = {}
        
        for col, field_name in column_map.items():
            if field_name is None:
                continue
            
            value = row[col]
            if pd.isna(value) or value == "":
                continue
            
            # Ensure value is converted to string
            value_str = str(value).strip() if value is not None else ""
            
            if not value_str:
                continue
            
            # Parse different field types
            if field_name == "Isotope":
                entry["Isotope"] = self._parse_isotope(value_str)
            elif field_name == "Model class":
                entry["Model class"] = self._parse_model_class(value_str)
            elif field_name == "Model":
                entry["Model"] = self._parse_model_variant(value_str)
            elif field_name == "g_A":
                entry["g_A"] = self._parse_g_a(value_str)
            else:
                # It's a matrix element
                val, err = self._parse_value_with_error(value_str)
                if val is not None:
                    matrix_elements[field_name] = {
                        "value": val,
                        "error": err,
                    }
        
        # Check if entry is valid
        if not entry["Isotope"]:
            return None
        
        entry["matrix_elements"] = matrix_elements
        return entry if matrix_elements else None
    
    def _parse_isotope(self, text: str) -> Optional[str]:
        """
        Parse isotope name from text.
        
        Args:
            text: Raw text from PDF
        
        Returns:
            Canonical isotope name (e.g., "76Ge") or None
        """
        # Try regex pattern
        match = re.search(ISOTOPE_PATTERN, text)
        if match:
            mass_num, element = match.groups()
            isotope = f"{mass_num}{element}"
            if isotope in KNOWN_ISOTOPES:
                return isotope
        
        # Check if any known isotope is in the text
        for iso in KNOWN_ISOTOPES:
            if iso.lower() in text.lower():
                return iso
        
        return None
    
    def _parse_model_class(self, text: str) -> Optional[str]:
        """Parse model class (QRPA, Shell Model, etc.)."""
        text_lower = text.lower()
        for cls in MODEL_CLASSES:
            if cls.lower() in text_lower:
                return cls
        return None
    
    def _parse_model_variant(self, text: str) -> Optional[str]:
        """Parse model variant (WS, sp, etc.)."""
        # Check for known variants
        for variant in MODEL_VARIANTS:
            if variant.lower() in text.lower():
                return text.strip()  # Return original formatting
        return text.strip() if text else None
    
    def _parse_g_a(self, text: str) -> Optional[str]:
        """Parse g_A value."""
        # Extract numeric value
        match = re.search(r"[\d\.]+", text)
        if match:
            return match.group()
        return None
    
    def _parse_value_with_error(self, text: str) -> Tuple[Optional[str], str]:
        """
        Parse numeric value and uncertainty from text.
        
        Handles formats:
        - "6.8(3)" -> value="6.8", error="0.3"
        - "6.8 ± 0.3" -> value="6.8", error="0.3"
        - "6.8 +/- 0.3" -> value="6.8", error="0.3"
        - "6.8" -> value="6.8", error=""
        
        Args:
            text: Text containing value and optional error
        
        Returns:
            Tuple of (value: str, error: str)
        """
        text = text.strip()
        
        # Format: value(error) e.g., 6.8(3)
        match = re.match(r"([\d\.]+)\((\d+)\)", text)
        if match:
            value = match.group(1)
            error_digits = match.group(2)
            # Convert (3) to 0.3 or (30) to 0.30 depending on decimal places
            error = self._convert_parenthesis_error(value, error_digits)
            return value, error
        
        # Format: value ± error or value +/- error
        match = re.match(r"([\d\.]+)\s*[±+/-]+\s*([\d\.]+)", text)
        if match:
            value = match.group(1)
            error = match.group(2)
            return value, error
        
        # Just a value
        match = re.match(r"([\d\.]+)", text)
        if match:
            return match.group(1), ""
        
        return None, ""
    
    @staticmethod
    def _convert_parenthesis_error(value: str, error_digits: str) -> str:
        """
        Convert parenthesis error notation to decimal.
        
        E.g., 6.8(3) -> error="0.3" (one digit matches last decimal place)
              5.54(10) -> error="0.10" (two digits)
        
        Args:
            value: Main value string
            error_digits: Digits in parentheses
        
        Returns:
            Error as decimal string
        """
        # Count decimal places in value
        if '.' in value:
            decimal_places = len(value.split('.')[1])
        else:
            decimal_places = 0
        
        # If no decimal places in value, return error_digits as is
        if decimal_places == 0:
            return error_digits
        
        # Pad error_digits to match decimal places
        # For 6.8(3): decimal_places=1, error_digits="3" -> "03" -> "0.3"
        # For 5.54(10): decimal_places=2, error_digits="10" -> "10" -> "0.10"
        error_padded = error_digits.zfill(decimal_places)
        
        # Insert decimal point
        if len(error_padded) > decimal_places:
            # Insert decimal before last decimal_places digits
            int_part = error_padded[:-decimal_places]
            dec_part = error_padded[-decimal_places:]
            error_str = int_part + '.' + dec_part
        else:
            # All digits are decimal part, prepend 0
            error_str = '0.' + error_padded
        
        return error_str
