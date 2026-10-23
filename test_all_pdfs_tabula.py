#!/usr/bin/env python3
"""
Test tabula extraction on various PDFs to find usable NME tables.
"""

import sys
import logging
from pathlib import Path
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_pdf_with_tabula(pdf_path: str) -> list:
    """Extract and display tables from PDF using tabula."""
    try:
        import tabula
        
        pdf_name = Path(pdf_path).name
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {pdf_name}")
        logger.info(f"{'='*60}")
        
        tables = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True, stream=True)
        logger.info(f"✓ Found {len(tables)} tables")
        
        # Filter and display NME-relevant ones
        nme_tables = []
        for i, table in enumerate(tables):
            text = ' '.join(str(table.columns)) + ' ' + table.to_string()
            text_lower = text.lower()
            
            # Check for NME-related keywords
            has_nme_keyword = any(
                keyword in text_lower 
                for keyword in ['nme', 'matrix', 'decay', 'm_', 'ge', 'mo', 'xe', 'te', 'zr', 'se', '76', '100', '130', '136', '82']
            )
            
            if has_nme_keyword:
                nme_tables.append((i, table))
                logger.info(f"\n  Table {i}: Shape {table.shape}")
                logger.info(f"  Columns: {list(table.columns)[:5]}...")  # Show first 5 cols
                logger.info(f"  Preview:\n{table.iloc[:2].to_string()}\n")
        
        if not nme_tables:
            logger.warning(f"  No NME-relevant tables found")
        
        return nme_tables
    except Exception as e:
        logger.error(f"  Failed: {e}")
        return []

def main():
    pdfs = [
        'references/Menéndez_2018_J._Phys._G__Nucl._Part._Phys._45_014003.pdf',
        'references/PhysRevC.101.044315.pdf',
        'references/PhysRevC.78.064316.pdf',
        'references/PhysRevC.84.014332.pdf',
        'references/PhysRevLett.111.142501.pdf',
    ]
    
    results = {}
    for pdf_path in pdfs:
        if Path(pdf_path).exists():
            tables = test_pdf_with_tabula(pdf_path)
            results[Path(pdf_path).name] = tables
        else:
            logger.warning(f"Not found: {pdf_path}")
    
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    for name, tables in results.items():
        logger.info(f"{name}: {len(tables)} NME-relevant tables")

if __name__ == '__main__':
    main()
