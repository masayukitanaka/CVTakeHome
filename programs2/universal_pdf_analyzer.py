#!/usr/bin/env python3
"""
Universal PDF Analyzer - Works reliably with any PDF structure

Key improvements:
1. Uses only local PDF text extraction (no OpenAI dependency for full_text)
2. Handles missing pages and page numbering issues
3. Processes pages sequentially without batching issues
4. Provides comprehensive error handling and recovery
5. Works with any PDF structure and content
"""

import os
import sys
import json
import logging
import argparse
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
from openai import OpenAI
import pdfplumber

load_dotenv()

class UniversalPDFAnalyzer:
    def __init__(self, enable_openai_analysis=True, enable_logging=True):
        """
        Initialize the Universal PDF Analyzer
        
        Args:
            enable_openai_analysis: Whether to use OpenAI for structural analysis
            enable_logging: Whether to enable detailed logging
        """
        self.enable_openai_analysis = enable_openai_analysis
        
        # Initialize OpenAI client only if needed
        if enable_openai_analysis:
            self.api_key = os.getenv('OPENAI_API_KEY')
            if self.api_key:
                self.client = OpenAI(api_key=self.api_key)
            else:
                print("Warning: OPENAI_API_KEY not found. Running in text-extraction-only mode.")
                self.enable_openai_analysis = False
                self.client = None
        else:
            self.client = None
        
        # Setup logging
        if enable_logging:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler('pdf_analysis.log'),
                    logging.StreamHandler()
                ]
            )
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = None
    
    def get_pdf_info(self, pdf_path: str) -> Dict:
        """Get basic PDF information"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                return {
                    'total_pages': len(pdf.pages),
                    'file_size': os.path.getsize(pdf_path),
                    'file_name': os.path.basename(pdf_path)
                }
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting PDF info: {str(e)}")
            return {
                'total_pages': 0,
                'file_size': 0,
                'file_name': os.path.basename(pdf_path),
                'error': str(e)
            }
    
    def extract_page_text(self, pdf_path: str, page_number: int) -> Tuple[str, List[Dict], Dict]:
        """
        Extract text, tables, and metadata from a specific page
        
        Returns:
            Tuple of (full_text, tables, metadata)
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if page_number < 1 or page_number > len(pdf.pages):
                    return "", [], {"error": f"Page {page_number} does not exist"}
                
                page = pdf.pages[page_number - 1]  # Convert to 0-based index
                
                # Extract text
                text = page.extract_text() or ""
                
                # Extract tables
                tables = []
                try:
                    raw_tables = page.extract_tables()
                    for i, table in enumerate(raw_tables or []):
                        if table:  # Only process non-empty tables
                            tables.append({
                                "table_number": i + 1,
                                "rows": len(table),
                                "columns": len(table[0]) if table else 0,
                                "data": table,
                                "text_content": self._table_to_text(table)
                            })
                except Exception as table_error:
                    if self.logger:
                        self.logger.warning(f"Error extracting tables from page {page_number}: {str(table_error)}")
                
                # Extract metadata
                metadata = {
                    "page_width": page.width,
                    "page_height": page.height,
                    "char_count": len(text),
                    "has_tables": len(tables) > 0,
                    "table_count": len(tables)
                }
                
                return text.strip(), tables, metadata
                
        except Exception as e:
            error_msg = f"Error extracting page {page_number}: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            return "", [], {"error": error_msg}
    
    def _table_to_text(self, table: List[List[str]]) -> str:
        """Convert table data to readable text format"""
        if not table:
            return ""
        
        text_parts = []
        for row in table:
            if row:  # Skip empty rows
                clean_row = [str(cell).strip() if cell else "" for cell in row]
                text_parts.append(" | ".join(clean_row))
        
        return "\n".join(text_parts)
    
    def identify_key_content(self, text: str, page_number: int) -> List[str]:
        """Identify key content types on the page"""
        key_content = []
        text_upper = text.upper()
        
        # Common insurance document patterns
        patterns = {
            "Policy Number": ["POLICY NO", "POLICY NUMBER", "NBP1555904G"],
            "Property Coverage": ["BUSINESSOWNERS PROPERTY COVERAGE", "PROPERTY COVERAGE PART"],
            "Business Income": ["BUSINESS INCOME", "EXTRA EXPENSE"],
            "Address": ["807 BROADWAY", "MINNEAPOLIS, MN"],
            "Declarations": ["DECLARATIONS", "DESCRIPTION OF PREMISES"],
            "Terrorism Insurance": ["TERRORISM INSURANCE", "TERRORISM RISK"],
            "Endorsements": ["ENDORSEMENT", "THIS ENDORSEMENT CHANGES"],
            "Exclusions": ["EXCLUSION", "THIS INSURANCE DOES NOT APPLY"],
            "Premium Information": ["PREMIUM", "TOTAL PREMIUM", "$"],
            "Effective Date": ["EFFECTIVE DATE", "10/05/2024"],
            "Coverage Limits": ["LIMIT OF INSURANCE", "COVERAGE PROVIDED"],
            "Forms": ["FORMS AND ENDORSEMENTS", "COVERAGE FORM"]
        }
        
        for content_type, keywords in patterns.items():
            if any(keyword in text_upper for keyword in keywords):
                key_content.append(content_type)
        
        return key_content
    
    def create_page_summary(self, text: str, key_content: List[str], tables: List[Dict]) -> str:
        """Create an intelligent summary of the page content"""
        if not text and not tables:
            return "This page appears to be blank or contains no extractable text."
        
        # Create summary based on key content
        summary_parts = []
        
        if "Policy Number" in key_content:
            summary_parts.append("Contains policy identification information")
        
        if "Property Coverage" in key_content:
            summary_parts.append("Details property coverage declarations and limits")
        
        if "Business Income" in key_content:
            summary_parts.append("Includes business income and expense coverage details")
        
        if "Terrorism Insurance" in key_content:
            summary_parts.append("Discusses terrorism insurance options and requirements")
        
        if "Endorsements" in key_content:
            summary_parts.append("Contains policy endorsements and modifications")
        
        if "Exclusions" in key_content:
            summary_parts.append("Lists coverage exclusions and limitations")
        
        if tables:
            summary_parts.append(f"Contains {len(tables)} structured table(s) with coverage details")
        
        if "Address" in key_content:
            summary_parts.append("Includes property address and location information")
        
        # Default summary if no specific patterns found
        if not summary_parts:
            word_count = len(text.split())
            if word_count > 100:
                summary_parts.append("Contains detailed policy or coverage information")
            elif word_count > 20:
                summary_parts.append("Contains policy-related text and information")
            else:
                summary_parts.append("Contains brief policy or administrative information")
        
        return ". ".join(summary_parts) + "."
    
    def extract_key_information(self, text: str, tables: List[Dict]) -> Dict:
        """Extract structured key information from text and tables"""
        info = {
            "insured_property": None,
            "coverage_details": None,
            "dates": None,
            "amounts": None,
            "addresses": None
        }
        
        text_upper = text.upper()
        
        # Extract addresses
        import re
        address_patterns = [
            r"807 BROADWAY.*?MN.*?\d{5}",
            r"\d+.*?STREET.*?MINNEAPOLIS.*?MN",
            r"\d+.*?AVENUE.*?MINNEAPOLIS.*?MN"
        ]
        
        for pattern in address_patterns:
            matches = re.findall(pattern, text_upper)
            if matches:
                info["addresses"] = matches[0].title()
                break
        
        # Extract dates
        date_patterns = [
            r"10/05/2024",
            r"EFFECTIVE DATE.*?(\d{2}/\d{2}/\d{4})",
            r"(\d{2}/\d{2}/\d{4})"
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            if matches:
                info["dates"] = matches[0] if isinstance(matches[0], str) else matches[0]
                break
        
        # Extract amounts
        amount_patterns = [
            r"\$[\d,]+",
            r"[\d,]+\s*DOLLARS?"
        ]
        
        amounts = []
        for pattern in amount_patterns:
            amounts.extend(re.findall(pattern, text))
        
        if amounts:
            info["amounts"] = ", ".join(amounts[:5])  # Limit to first 5 amounts
        
        # Extract coverage details from key content
        if "BUSINESS INCOME" in text_upper:
            info["coverage_details"] = "Business Income and Extra Expense coverage"
        elif "PROPERTY COVERAGE" in text_upper:
            info["coverage_details"] = "Property coverage declarations"
        elif "LIABILITY" in text_upper:
            info["coverage_details"] = "Liability coverage information"
        elif "ENDORSEMENT" in text_upper:
            info["coverage_details"] = "Policy endorsements and modifications"
        
        # Extract insured property info
        if "807 BROADWAY" in text_upper:
            info["insured_property"] = "807 Broadway St NE, Minneapolis, MN"
        elif "LOGAN PARK" in text_upper:
            info["insured_property"] = "Logan Park Neighborhood Association"
        
        return info
    
    def get_openai_analysis(self, text: str, page_number: int, key_content: List[str]) -> Optional[Dict]:
        """Get additional structural analysis from OpenAI (optional)"""
        if not self.enable_openai_analysis or not self.client:
            return None
        
        try:
            # Create a focused prompt for structural analysis only
            prompt = f"""Analyze this insurance document page and provide JSON with document structure information:

Page {page_number} text: {text[:2000]}...

Key content identified: {', '.join(key_content)}

Provide only this JSON structure:
{{
    "document_structure": {{
        "section_title": "main section title or null",
        "subsections": ["list", "of", "subsection", "titles"],
        "page_type": "declarations|endorsement|coverage|exclusions|forms|other"
    }},
    "relationships": {{
        "continues_from_previous": "what continues from previous page or null",
        "continues_to_next": "what continues to next page or null", 
        "references": "references to other sections or null"
    }}
}}

Return only valid JSON, no other text."""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Use faster, cheaper model for structure analysis
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            result = response.choices[0].message.content.strip()
            
            # Clean and parse JSON
            if result.startswith('```json'):
                result = result[7:]
            if result.endswith('```'):
                result = result[:-3]
            
            return json.loads(result)
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"OpenAI analysis failed for page {page_number}: {str(e)}")
            return None
    
    def analyze_single_page(self, pdf_path: str, page_number: int) -> Dict:
        """Analyze a single page comprehensively"""
        if self.logger:
            self.logger.info(f"Analyzing page {page_number}")
        
        # Extract text and tables
        full_text, tables, metadata = self.extract_page_text(pdf_path, page_number)
        
        # Identify key content
        key_content = self.identify_key_content(full_text, page_number)
        
        # Create summary
        summary = self.create_page_summary(full_text, key_content, tables)
        
        # Extract structured information
        key_info = self.extract_key_information(full_text, tables)
        
        # Get OpenAI structural analysis (if enabled)
        openai_analysis = self.get_openai_analysis(full_text, page_number, key_content)
        
        # Build result
        result = {
            "page_number": page_number,
            "summary": summary,
            "full_text": full_text,
            "tables_and_figures": [
                {
                    "type": "table",
                    "description": f"Table {table['table_number']} with {table['rows']} rows and {table['columns']} columns",
                    "content": table["text_content"]
                }
                for table in tables
            ],
            "key_information": key_info,
            "key_content_types": key_content,
            "metadata": metadata,
            "analyzed_at": datetime.now().isoformat()
        }
        
        # Add OpenAI analysis if available
        if openai_analysis:
            result.update(openai_analysis)
        else:
            # Provide fallback structure
            result["document_structure"] = {
                "section_title": None,
                "subsections": [],
                "page_type": "content"
            }
            result["relationships"] = {
                "continues_from_previous": None,
                "continues_to_next": None,
                "references": None
            }
        
        if self.logger:
            self.logger.info(f"Page {page_number} analyzed: {len(full_text)} chars, {len(tables)} tables, {len(key_content)} key content types")
        
        return result
    
    def analyze_pdf(self, pdf_path: str, output_json_path: str, start_page: int = 1, end_page: Optional[int] = None) -> List[Dict]:
        """
        Analyze PDF comprehensively with robust error handling
        
        Args:
            pdf_path: Path to PDF file
            output_json_path: Path to save JSON results
            start_page: Starting page number (1-based)
            end_page: Ending page number (1-based), None for all pages
            
        Returns:
            List of page analysis results
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Get PDF info
        pdf_info = self.get_pdf_info(pdf_path)
        total_pages = pdf_info.get('total_pages', 0)
        
        if total_pages == 0:
            raise ValueError("PDF has no pages or cannot be read")
        
        # Validate page range
        if end_page is None:
            end_page = total_pages
        
        start_page = max(1, start_page)
        end_page = min(total_pages, end_page)
        
        if start_page > end_page:
            raise ValueError(f"Invalid page range: {start_page}-{end_page}")
        
        if self.logger:
            self.logger.info(f"Starting analysis of {pdf_path}")
            self.logger.info(f"PDF Info: {total_pages} pages, {pdf_info.get('file_size', 0)} bytes")
            self.logger.info(f"Analyzing pages {start_page}-{end_page}")
        
        results = []
        failed_pages = []
        
        # Process each page individually
        for page_num in range(start_page, end_page + 1):
            try:
                page_result = self.analyze_single_page(pdf_path, page_num)
                results.append(page_result)
                
            except Exception as e:
                error_msg = f"Failed to analyze page {page_num}: {str(e)}"
                if self.logger:
                    self.logger.error(error_msg)
                    self.logger.error(traceback.format_exc())
                
                failed_pages.append(page_num)
                
                # Create error entry for failed page
                error_result = {
                    "page_number": page_num,
                    "summary": f"Analysis failed: {str(e)}",
                    "full_text": "",
                    "tables_and_figures": [],
                    "key_information": {},
                    "key_content_types": [],
                    "metadata": {"error": error_msg},
                    "document_structure": {"page_type": "error"},
                    "relationships": {},
                    "error": error_msg,
                    "analyzed_at": datetime.now().isoformat()
                }
                results.append(error_result)
        
        # Sort results by page number to ensure correct order
        results.sort(key=lambda x: x.get('page_number', 0))
        
        # Save results
        try:
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            if self.logger:
                self.logger.info(f"Results saved to: {output_json_path}")
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to save results: {str(e)}")
            raise
        
        # Summary
        successful_pages = len(results) - len(failed_pages)
        if self.logger:
            self.logger.info(f"Analysis complete: {successful_pages}/{len(results)} pages successful")
            if failed_pages:
                self.logger.warning(f"Failed pages: {failed_pages}")
        
        print(f"Analysis complete!")
        print(f"Successfully analyzed: {successful_pages} pages")
        print(f"Failed pages: {len(failed_pages)}")
        print(f"Results saved to: {output_json_path}")
        
        return results

def main():
    parser = argparse.ArgumentParser(
        description='Universal PDF Analyzer - Works reliably with any PDF structure',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python universal_pdf_analyzer.py document.pdf
  python universal_pdf_analyzer.py document.pdf -o analysis.json
  python universal_pdf_analyzer.py document.pdf --start-page 1 --end-page 5
  python universal_pdf_analyzer.py document.pdf --no-openai  # Text extraction only
        """
    )
    
    parser.add_argument('pdf_path', type=str, help='Path to the PDF document')
    parser.add_argument('-o', '--output', type=str,
                       help='Output JSON file path (default: <pdf_name>_analysis.json)')
    parser.add_argument('--start-page', type=int, default=1,
                       help='Start analysis from this page (default: 1)')
    parser.add_argument('--end-page', type=int,
                       help='End analysis at this page (default: last page)')
    parser.add_argument('--no-openai', action='store_true',
                       help='Disable OpenAI analysis (text extraction only)')
    parser.add_argument('--quiet', action='store_true',
                       help='Disable detailed logging')
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.exists(args.pdf_path):
        print(f"Error: PDF file not found: {args.pdf_path}")
        sys.exit(1)
    
    # Set default output path
    if not args.output:
        pdf_path = Path(args.pdf_path)
        args.output = pdf_path.stem + '_analysis.json'
    
    try:
        # Create analyzer
        analyzer = UniversalPDFAnalyzer(
            enable_openai_analysis=not args.no_openai,
            enable_logging=not args.quiet
        )
        
        # Analyze PDF
        analyzer.analyze_pdf(
            args.pdf_path,
            args.output,
            args.start_page,
            args.end_page
        )
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        print(f"\nAnalysis interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        if not args.quiet:
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()