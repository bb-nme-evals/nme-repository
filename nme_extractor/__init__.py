"""
NME Extractor: Automated extraction of nuclear matrix elements from PDFs.

This package provides tools to:
1. Extract tables from academic PDFs
2. Parse semantic content (isotopes, models, matrix elements)
3. Format data into the canonical NME JSON schema
4. Validate completeness and integrity
"""

__version__ = "0.1.0"
__author__ = "NME Research"

from .pdf_parser import PDFParser
from .semantic_parser import SemanticParser
from .json_formatter import JSONFormatter
from .validator import JSONValidator

__all__ = [
    "PDFParser",
    "SemanticParser",
    "JSONFormatter",
    "JSONValidator",
]
