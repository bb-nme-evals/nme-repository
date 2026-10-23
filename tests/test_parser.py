"""
Unit tests for NME extractor modules.
"""

import unittest
from pathlib import Path
import tempfile
import json

# Test imports
from nme_extractor.semantic_parser import SemanticParser
from nme_extractor.json_formatter import JSONFormatter
from nme_extractor.validator import JSONValidator


class TestSemanticParser(unittest.TestCase):
    """Test semantic parsing functionality."""
    
    def setUp(self):
        self.parser = SemanticParser()
    
    def test_parse_isotope(self):
        """Test isotope name parsing."""
        self.assertEqual(self.parser._parse_isotope("76Ge"), "76Ge")
        self.assertEqual(self.parser._parse_isotope("96Zr"), "96Zr")
        self.assertEqual(self.parser._parse_isotope("100Mo"), "100Mo")
        self.assertIsNone(self.parser._parse_isotope("invalid"))
    
    def test_parse_value_with_error_parenthesis(self):
        """Test parsing value(error) format."""
        val, err = self.parser._parse_value_with_error("6.8(3)")
        self.assertEqual(val, "6.8")
        self.assertEqual(err, "0.3")
        
        val, err = self.parser._parse_value_with_error("5.54(10)")
        self.assertEqual(val, "5.54")
        self.assertEqual(err, "0.10")
    
    def test_parse_value_with_error_plus_minus(self):
        """Test parsing value ± error format."""
        val, err = self.parser._parse_value_with_error("6.8 ± 0.3")
        self.assertEqual(val, "6.8")
        self.assertEqual(err, "0.3")
        
        val, err = self.parser._parse_value_with_error("5.54 +/- 0.10")
        self.assertEqual(val, "5.54")
        self.assertEqual(err, "0.10")
    
    def test_parse_value_without_error(self):
        """Test parsing value only."""
        val, err = self.parser._parse_value_with_error("6.8")
        self.assertEqual(val, "6.8")
        self.assertEqual(err, "")
    
    def test_parse_g_a(self):
        """Test g_A value parsing."""
        self.assertEqual(self.parser._parse_g_a("1.00"), "1.00")
        self.assertEqual(self.parser._parse_g_a("g_A=1.27"), "1.27")
        self.assertIsNone(self.parser._parse_g_a("invalid"))


class TestJSONFormatter(unittest.TestCase):
    """Test JSON formatting functionality."""
    
    def setUp(self):
        self.formatter = JSONFormatter()
        self.formatter.set_metadata(
            reference="Test Author 2024",
            url="http://example.com",
            bibtex="@article{test2024}"
        )
    
    def test_validate_entry_valid(self):
        """Test validation of valid entry."""
        entry = {
            "Model class": "QRPA",
            "Model": "WS, model 1",
            "Isotope": "76Ge",
            "g_A": "1.00",
            "matrix_elements": {
                "M_{total}": {"value": "6.8", "error": "0.3"}
            }
        }
        self.assertTrue(self.formatter._validate_entry(entry))
    
    def test_validate_entry_missing_isotope(self):
        """Test rejection of entry missing isotope."""
        entry = {
            "Model class": "QRPA",
            "Model": "WS, model 1",
            "Isotope": None,
            "g_A": "1.00",
            "matrix_elements": {"M_{total}": {"value": "6.8", "error": ""}}
        }
        self.assertFalse(self.formatter._validate_entry(entry))
    
    def test_add_entry(self):
        """Test adding a valid entry."""
        entry = {
            "Model class": "QRPA",
            "Model": "WS, model 1",
            "Isotope": "76Ge",
            "g_A": "1.00",
            "matrix_elements": {
                "M_{total}": {"value": "6.8", "error": "0.3"}
            }
        }
        success = self.formatter.add_entry(entry)
        self.assertTrue(success)
        self.assertEqual(len(self.formatter.entries), 1)
    
    def test_structure_matrix_elements(self):
        """Test matrix element structuring."""
        raw = {
            "M_{total}": {"value": "6.8", "error": "0.3"},
            "M_{GT}^{AA}": {"value": "2.5", "error": ""},
        }
        
        structured = self.formatter._structure_matrix_elements(raw)
        
        # Check that all top-level keys exist
        self.assertIn("M_{total}", structured)
        self.assertIn("M_summed", structured)
        self.assertIn("M_subcomponents", structured)
        
        # Check that we preserved provided values
        self.assertEqual(structured["M_{total}"]["value"], "6.8")
        self.assertEqual(structured["M_subcomponents"]["M_{GT}^{AA}"]["value"], "2.5")
    
    def test_to_json(self):
        """Test JSON serialization."""
        entry = {
            "Model class": "QRPA",
            "Model": "WS, model 1",
            "Isotope": "76Ge",
            "g_A": "1.00",
            "matrix_elements": {
                "M_{total}": {"value": "6.8", "error": "0.3"}
            }
        }
        self.formatter.add_entry(entry)
        
        json_str = self.formatter.to_json()
        parsed = json.loads(json_str)
        
        self.assertEqual(parsed["Reference"], "Test Author 2024")
        self.assertEqual(len(parsed["entries"]), 1)


class TestJSONValidator(unittest.TestCase):
    """Test JSON validation functionality."""
    
    def setUp(self):
        self.validator = JSONValidator()
    
    def test_validate_valid_dict(self):
        """Test validation of valid JSON structure."""
        data = {
            "Reference": "Test 2024",
            "URL": "http://example.com",
            "bibtex": "@article{test}",
            "entries": [
                {
                    "Model class": "QRPA",
                    "Model": "WS, model 1",
                    "Isotope": "76Ge",
                    "g_A": "1.00",
                    "matrix_elements": {
                        "M_{total}": {"value": "6.8", "error": "0.3"},
                        "M_summed": {"M_{GT}": {"value": "", "error": ""}},
                        "M_subcomponents": {
                            "M_F": {"value": "", "error": ""}
                        }
                    }
                }
            ]
        }
        
        is_valid, report = self.validator.validate_dict(data)
        self.assertTrue(is_valid)
        self.assertEqual(report["error_count"], 0)
    
    def test_validate_missing_required_field(self):
        """Test detection of missing required fields."""
        data = {
            "Reference": "Test 2024",
            "URL": "http://example.com",
            # Missing bibtex
            "entries": []
        }
        
        is_valid, report = self.validator.validate_dict(data)
        self.assertFalse(is_valid)
        self.assertGreater(report["error_count"], 0)
    
    def test_validate_unknown_isotope_warning(self):
        """Test warning for unknown isotope."""
        data = {
            "Reference": "Test 2024",
            "URL": "",
            "bibtex": "",
            "entries": [
                {
                    "Model class": "QRPA",
                    "Model": "WS, model 1",
                    "Isotope": "999Xx",  # Unknown isotope
                    "g_A": "1.00",
                    "matrix_elements": {
                        "M_{total}": {"value": "6.8", "error": ""},
                        "M_summed": {"M_{GT}": {"value": "", "error": ""}},
                        "M_subcomponents": {"M_F": {"value": "", "error": ""}}
                    }
                }
            ]
        }
        
        is_valid, report = self.validator.validate_dict(data)
        self.assertGreater(report["warning_count"], 0)


if __name__ == "__main__":
    unittest.main()
