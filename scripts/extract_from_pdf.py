#!/usr/bin/env python3
"""
CLI script for extracting NME values from PDFs.

Usage:
    python extract_from_pdf.py <pdf_path> [--output <json_path>] [--review]
    
Examples:
    # Extract and save directly
    python extract_from_pdf.py paper.pdf --output output.json
    
    # Extract with review step (generates CSV for inspection)
    python extract_from_pdf.py paper.pdf --output output.json --review
    
    # Just export tables to CSV without JSON conversion
    python extract_from_pdf.py paper.pdf --tables-only
"""

import argparse
import sys
import logging
from pathlib import Path

# Add parent directory to path to import nme_extractor
sys.path.insert(0, str(Path(__file__).parent.parent))

from nme_extractor import PDFParser, SemanticParser, JSONFormatter, JSONValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_and_format(
    pdf_path: str,
    output_json: str = None,
    review: bool = False,
    output_dir: str = None,
) -> bool:
    """
    Full pipeline: extract tables -> parse -> format -> validate -> write.
    
    Args:
        pdf_path: Path to input PDF
        output_json: Path to output JSON file
        review: If True, generate CSV for manual review
        output_dir: Directory for intermediate files
    
    Returns:
        True if successful, False otherwise
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        logger.error(f"PDF file not found: {pdf_path}")
        return False
    
    # Create output directory if needed
    if output_dir is None:
        output_dir = pdf_path.parent / f".nme_extraction_{pdf_path.stem}"
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Using output directory: {output_dir}")
    
    # If output JSON path not specified, use default
    if output_json is None:
        output_json = pdf_path.with_stem(f"{pdf_path.stem}_extracted").with_suffix(".json")
    
    output_json = Path(output_json)
    
    # ========== STAGE 1: PDF Parsing ==========
    logger.info("\n" + "="*60)
    logger.info("STAGE 1: PDF Parsing")
    logger.info("="*60)
    
    try:
        parser = PDFParser(str(pdf_path))
        nme_tables = parser.extract_all_tables()
        
        logger.info(f"Found {len(nme_tables)} NME-relevant tables")
        
        # Export all tables to CSV for inspection
        csv_dir = output_dir / "tables"
        csv_files = parser.export_tables_to_csv(str(csv_dir))
        logger.info(f"Exported {len(csv_files)} tables to CSV for review")
        
        if not nme_tables:
            logger.warning("No NME-relevant tables found. Exiting.")
            return False
        
        # Get PDF metadata
        metadata = parser.get_pdf_metadata()
        logger.info(f"PDF metadata: {metadata}")
    
    except Exception as e:
        logger.error(f"Failed to parse PDF: {e}")
        return False
    
    # ========== STAGE 2: Semantic Parsing ==========
    logger.info("\n" + "="*60)
    logger.info("STAGE 2: Semantic Parsing")
    logger.info("="*60)
    
    semantic_parser = SemanticParser()
    all_entries = []
    all_warnings = []
    
    for table_idx, table_dict in enumerate(nme_tables):
        df = table_dict['data']
        logger.info(f"\nParsing table {table_idx + 1}/{len(nme_tables)} (page {table_dict['page']})")
        
        try:
            result = semantic_parser.parse_table(df)
            all_entries.extend(result['entries'])
            all_warnings.extend(result['warnings'])
        except Exception as e:
            logger.error(f"Error parsing table {table_idx}: {e}")
            continue
    
    logger.info(f"\nTotal entries parsed: {len(all_entries)}")
    
    if all_warnings:
        logger.warning(f"Encountered {len(all_warnings)} warnings during parsing")
        for warning in all_warnings[:5]:  # Show first 5
            logger.warning(f"  - {warning}")
        if len(all_warnings) > 5:
            logger.warning(f"  ... and {len(all_warnings) - 5} more")
    
    if not all_entries:
        logger.error("No entries extracted from tables. Cannot continue.")
        return False
    
    # ========== STAGE 3: JSON Formatting ==========
    logger.info("\n" + "="*60)
    logger.info("STAGE 3: JSON Formatting")
    logger.info("="*60)
    
    formatter = JSONFormatter()
    
    # Set metadata from PDF or prompt user
    reference = metadata.get('Author', '') or input("Enter reference/citation: ")
    url = metadata.get('Title', '') or ""
    formatter.set_metadata(
        reference=reference,
        url=url,
        bibtex=""  # Would need to extract from PDF or prompt
    )
    
    # Add entries
    added_count = formatter.add_entries_batch(all_entries)
    logger.info(f"Added {added_count}/{len(all_entries)} entries to output")
    
    # Get summary
    summary = formatter.get_summary()
    logger.info("\nFormatted data summary:")
    logger.info(f"  Entries: {summary['entry_count']}")
    logger.info(f"  Isotopes: {', '.join(summary['isotopes'])}")
    logger.info(f"  Model classes: {', '.join(summary['model_classes'])}")
    logger.info(f"  Unique matrix elements: {len(summary['element_counts'])}")
    
    # ========== STAGE 4: Review (Optional) ==========
    if review:
        logger.info("\n" + "="*60)
        logger.info("STAGE 4: Review")
        logger.info("="*60)
        
        review_csv = output_dir / "entries_review.csv"
        if formatter.write_review_csv(str(review_csv)):
            logger.info(f"Review CSV written to: {review_csv}")
            logger.info("Please review this file before running final write.")
            
            response = input("\nContinue to write JSON? [y/N]: ").strip().lower()
            if response != 'y':
                logger.info("Aborted by user.")
                return False
    
    # ========== STAGE 5: Validation ==========
    logger.info("\n" + "="*60)
    logger.info("STAGE 5: Validation")
    logger.info("="*60)
    
    validator = JSONValidator()
    is_valid, validation_report = validator.validate_dict(formatter.to_dict())
    validator.print_report(validation_report)
    
    if not is_valid:
        logger.error("Validation failed. Not writing output.")
        return False
    
    # ========== STAGE 6: Write Output ==========
    logger.info("\n" + "="*60)
    logger.info("STAGE 6: Write Output")
    logger.info("="*60)
    
    output_json.parent.mkdir(parents=True, exist_ok=True)
    if formatter.write_to_file(str(output_json)):
        logger.info(f"Successfully wrote JSON to: {output_json}")
    else:
        logger.error("Failed to write JSON file.")
        return False
    
    logger.info("\n" + "="*60)
    logger.info("EXTRACTION COMPLETE")
    logger.info("="*60)
    logger.info(f"Output: {output_json}")
    logger.info(f"Review files: {output_dir}")
    
    return True


def export_tables_only(pdf_path: str, output_dir: str = None) -> bool:
    """
    Export PDF tables to CSV only (no JSON conversion).
    
    Args:
        pdf_path: Path to input PDF
        output_dir: Directory for output CSV files
    
    Returns:
        True if successful
    """
    pdf_path = Path(pdf_path)
    
    if output_dir is None:
        output_dir = pdf_path.parent / f".nme_tables_{pdf_path.stem}"
    
    output_dir = Path(output_dir)
    
    try:
        parser = PDFParser(str(pdf_path))
        tables = parser.extract_all_tables()
        
        logger.info(f"Found {len(tables)} NME-relevant tables")
        
        csv_files = parser.export_tables_to_csv(str(output_dir))
        logger.info(f"Exported {len(csv_files)} tables to {output_dir}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Extract NME values from PDF tables and format as JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "pdf_path",
        help="Path to input PDF file"
    )
    
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Path to output JSON file (default: <pdf_stem>_extracted.json)"
    )
    
    parser.add_argument(
        "-r", "--review",
        action="store_true",
        help="Generate CSV for manual review before writing JSON"
    )
    
    parser.add_argument(
        "--tables-only",
        action="store_true",
        help="Export tables to CSV only (skip JSON conversion)"
    )
    
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for intermediate/output files"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose logging output"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run extraction
    if args.tables_only:
        success = export_tables_only(args.pdf_path, args.output_dir)
    else:
        success = extract_and_format(
            args.pdf_path,
            output_json=args.output,
            review=args.review,
            output_dir=args.output_dir,
        )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
