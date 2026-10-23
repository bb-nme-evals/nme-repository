"""
PDF table extraction module.

Uses pdfplumber to detect and extract tables from academic PDFs.
Provides filtering and preprocessing for NME-relevant tables.
"""

import logging
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import pandas as pd

try:
    import pdfplumber
except ImportError:
    raise ImportError(
        "pdfplumber not installed. Install with: pip install pdfplumber"
    )

from .config import TABLE_DETECTION

logger = logging.getLogger(__name__)


class PDFParser:
    """
    Extract tables from academic PDFs.
    
    Attributes:
        pdf_path: Path to input PDF file
        pdf_object: pdfplumber.PDF object
        tables: List of extracted tables with metadata
        detected_tables: List of raw tables for review
    """
    
    def __init__(self, pdf_path: str):
        """
        Initialize PDF parser.
        
        Args:
            pdf_path: Path to PDF file
            
        Raises:
            FileNotFoundError: If PDF file does not exist
            Exception: If PDF cannot be opened
        """
        self.pdf_path = Path(pdf_path)
        
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            self.pdf_object = pdfplumber.open(str(self.pdf_path))
        except Exception as e:
            raise Exception(f"Failed to open PDF {pdf_path}: {e}")
        
        self.tables = []
        self.detected_tables = []
        logger.info(f"Initialized PDF parser for {self.pdf_path.name}")
    
    def __del__(self):
        """Close PDF on cleanup."""
        if hasattr(self, 'pdf_object'):
            self.pdf_object.close()
    
    def extract_all_tables(self) -> List[Dict]:
        """
        Extract all tables from the PDF.
        
        Returns:
            List of table dictionaries with metadata:
            {
                'page': int,
                'table_index': int,
                'data': pd.DataFrame,
                'is_nme_relevant': bool,
                'keywords_found': List[str],
            }
        """
        logger.info("Extracting all tables from PDF...")
        self.detected_tables = []
        
        for page_num, page in enumerate(self.pdf_object.pages, start=1):
            try:
                raw_tables = page.extract_tables()
                if not raw_tables:
                    continue
                
                for table_idx, raw_table in enumerate(raw_tables):
                    df = pd.DataFrame(raw_table[1:], columns=raw_table[0])
                    
                    # Filter out empty or trivial tables
                    if df.empty or len(df) < TABLE_DETECTION["min_rows"]:
                        continue
                    
                    if len(df.columns) < TABLE_DETECTION["min_cols"]:
                        continue
                    
                    # Check if table is NME-relevant
                    is_relevant, keywords = self._check_nme_relevance(df, page)
                    
                    table_entry = {
                        'page': page_num,
                        'table_index': table_idx,
                        'data': df,
                        'is_nme_relevant': is_relevant,
                        'keywords_found': keywords,
                    }
                    
                    self.detected_tables.append(table_entry)
                    
                    if is_relevant:
                        self.tables.append(table_entry)
                        logger.info(
                            f"  Found NME-relevant table on page {page_num}, "
                            f"table {table_idx} (keywords: {', '.join(keywords)})"
                        )
            
            except Exception as e:
                logger.warning(f"Error processing page {page_num}: {e}")
        
        logger.info(f"Extracted {len(self.tables)} NME-relevant tables from PDF")
        return self.tables
    
    def _check_nme_relevance(self, df: pd.DataFrame, page) -> Tuple[bool, List[str]]:
        """
        Check if a table is likely to contain NME data.
        
        Args:
            df: DataFrame to check
            page: pdfplumber page object (for text extraction)
        
        Returns:
            Tuple of (is_relevant: bool, keywords_found: List[str])
        """
        keywords_found = []
        
        # Check column headers
        headers_text = " ".join(str(col).lower() for col in df.columns)
        
        for keyword in TABLE_DETECTION["keywords"]:
            if keyword.lower() in headers_text:
                keywords_found.append(keyword)
        
        # Check cell content
        content_text = " ".join(
            str(val).lower() 
            for col in df.columns 
            for val in df[col].head(5)  # Check first few rows
        )
        
        for keyword in TABLE_DETECTION["keywords"]:
            if keyword.lower() in content_text and keyword not in keywords_found:
                keywords_found.append(keyword)
        
        # Check page text for context
        try:
            page_text = page.extract_text().lower()
            for keyword in TABLE_DETECTION["keywords"]:
                if keyword.lower() in page_text and keyword not in keywords_found:
                    keywords_found.append(keyword)
        except:
            pass
        
        is_relevant = len(keywords_found) > 0
        return is_relevant, keywords_found
    
    def get_all_tables(self) -> List[pd.DataFrame]:
        """
        Get all detected tables as DataFrames (including non-NME).
        
        Returns:
            List of DataFrames
        """
        return [t['data'] for t in self.detected_tables]
    
    def get_nme_tables(self) -> List[pd.DataFrame]:
        """
        Get only NME-relevant tables.
        
        Returns:
            List of DataFrames identified as NME-relevant
        """
        return [t['data'] for t in self.tables]
    
    def export_tables_to_csv(self, output_dir: str) -> List[str]:
        """
        Export all detected tables to CSV for review.
        
        Args:
            output_dir: Directory to write CSV files
        
        Returns:
            List of output file paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_files = []
        
        for table_entry in self.detected_tables:
            page = table_entry['page']
            idx = table_entry['table_index']
            relevance = "NME" if table_entry['is_nme_relevant'] else "OTHER"
            
            filename = f"table_p{page:03d}_t{idx}__{relevance}.csv"
            filepath = output_dir / filename
            
            table_entry['data'].to_csv(filepath, index=False)
            output_files.append(str(filepath))
            
            logger.info(f"Exported table to {filepath}")
        
        return output_files
    
    def get_pdf_metadata(self) -> Dict:
        """
        Extract metadata from PDF.
        
        Returns:
            Dictionary with 'title', 'author', 'subject', 'creator'
        """
        metadata = self.pdf_object.metadata or {}
        return {
            'title': metadata.get('Title', ''),
            'author': metadata.get('Author', ''),
            'subject': metadata.get('Subject', ''),
            'creator': metadata.get('Creator', ''),
        }
    
    def get_page_count(self) -> int:
        """Get total number of pages in PDF."""
        return len(self.pdf_object.pages)
