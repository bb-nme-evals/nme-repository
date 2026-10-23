#!/usr/bin/env python3
"""
Alternative PDF extraction strategies for complex PDFs.
Tries multiple approaches: docling, tabula, text extraction with regex.
"""

import sys
import logging
from pathlib import Path
import pandas as pd

sys.path.insert(0, '.')

from nme_extractor import SemanticParser, JSONFormatter, JSONValidator

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def extract_with_tabula(pdf_path: str) -> list:
    """Extract tables using tabula-py (optimized for PDF tables)."""
    try:
        import tabula
        logger.info("Attempting extraction with tabula-py...")
        
        tables = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True, stream=True)
        logger.info(f"Found {len(tables)} tables with tabula")
        
        # Filter for NME-relevant tables
        nme_tables = []
        for table in tables:
            text = ' '.join(table.columns.astype(str)) + ' ' + table.to_string()
            if any(keyword in text.lower() for keyword in ['nme', 'matrix', 'beta', 'm_', 'ge', 'mo', 'xe']):
                nme_tables.append(table)
        
        logger.info(f"Found {len(nme_tables)} NME-relevant tables")
        return nme_tables
    except Exception as e:
        logger.warning(f"Tabula extraction failed: {e}")
        return []

def extract_with_docling(pdf_path: str) -> list:
    """Extract tables using docling (modern document parsing)."""
    try:
        from docling.document_converter import DocumentConverter
        from docling.datamodel.base_models import ConversionStatus
        
        logger.info("Attempting extraction with docling...")
        
        converter = DocumentConverter()
        result = converter.convert_single(pdf_path)
        
        if result.status != ConversionStatus.SUCCESS:
            logger.warning(f"Docling conversion failed: {result.status}")
            return []
        
        # Extract markdown tables from document
        doc = result.document
        tables = []
        
        # Docling stores tables in structured format
        # Extract them from the markdown representation
        md_text = doc.export_to_markdown()
        
        # Split by table markers and parse each
        import re
        table_blocks = re.split(r'\n\n(?=\|)', md_text)
        
        for block in table_blocks:
            if '|' in block and any(keyword in block.lower() for keyword in ['nme', 'matrix', 'beta', 'ge', 'mo', 'xe']):
                # Parse markdown table to DataFrame
                try:
                    lines = block.strip().split('\n')
                    if len(lines) >= 3:  # At least header, separator, one row
                        headers = [h.strip() for h in lines[0].split('|')[1:-1]]
                        rows = []
                        for line in lines[2:]:  # Skip separator line
                            row = [c.strip() for c in line.split('|')[1:-1]]
                            if len(row) == len(headers):
                                rows.append(row)
                        
                        if rows:
                            df = pd.DataFrame(rows, columns=headers)
                            tables.append(df)
                except Exception as e:
                    logger.debug(f"Failed to parse table block: {e}")
        
        logger.info(f"Found {len(tables)} NME-relevant tables with docling")
        return tables
    except Exception as e:
        logger.warning(f"Docling extraction failed: {e}")
        return []

def extract_with_text_parsing(pdf_path: str) -> list:
    """Last resort: extract text and parse with regex."""
    try:
        import pdfplumber
        import re
        
        logger.info("Attempting extraction with text parsing...")
        
        with pdfplumber.open(pdf_path) as pdf:
            text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
        
        # Look for table patterns
        # Pattern: lines with isotope names, model names, and numeric values
        lines = text.split('\n')
        table_data = []
        
        for i, line in enumerate(lines):
            # Check if line contains known isotopes
            if any(iso in line for iso in ['76Ge', '96Zr', '100Mo', '116Cd', '128Te', '130Te', '136Xe', '82Se']):
                table_data.append(line)
        
        if table_data:
            logger.info(f"Found {len(table_data)} lines with NME data")
            # Would need more sophisticated parsing here
            # For now, just return empty to indicate partial success
        
        return []
    except Exception as e:
        logger.warning(f"Text parsing failed: {e}")
        return []

def main():
    pdf_path = 'references/1-s2.0-S0370269324004544-main.pdf'
    
    if not Path(pdf_path).exists():
        logger.error(f"PDF not found: {pdf_path}")
        return
    
    logger.info(f"Extracting from: {pdf_path}\n")
    
    # Try different extraction methods
    tables = []
    
    # Try 1: Docling (modern, handles complex layouts)
    tables = extract_with_docling(pdf_path)
    if tables:
        logger.info(f"\n✓ Docling successful: {len(tables)} tables found")
    else:
        # Try 2: Tabula (specialized for PDF tables)
        tables = extract_with_tabula(pdf_path)
        if tables:
            logger.info(f"\n✓ Tabula successful: {len(tables)} tables found")
        else:
            # Try 3: Text parsing
            tables = extract_with_text_parsing(pdf_path)
            if tables:
                logger.info(f"\n✓ Text parsing found some data")
            else:
                logger.error("\n✗ All extraction methods failed")
                return
    
    # Now format extracted tables
    if not tables:
        logger.error("No tables extracted!")
        return
    
    logger.info(f"\nProcessing {len(tables)} extracted tables...")
    
    # For demo, just show structure of first table
    if isinstance(tables[0], pd.DataFrame):
        df = tables[0]
        logger.info(f"First table shape: {df.shape}")
        logger.info(f"Columns: {list(df.columns)}")
        logger.info(f"\nFirst few rows:")
        print(df.head(3).to_string())
    else:
        logger.info(f"Extracted data type: {type(tables[0])}")

if __name__ == '__main__':
    main()
