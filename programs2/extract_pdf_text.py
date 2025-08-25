#!/usr/bin/env python3
"""
Simple PDF text extractor using pdfplumber
"""
import sys
import json
import pdfplumber
from pathlib import Path

def extract_pdf_pages(pdf_path, start_page=1, end_page=None, output_json=None):
    """
    Extract text from PDF pages using pdfplumber
    
    Args:
        pdf_path: Path to PDF file
        start_page: Starting page number (1-based)
        end_page: Ending page number (1-based), None for all pages
        output_json: Optional path to save JSON output
    """
    results = []
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        
        if end_page is None:
            end_page = total_pages
        
        # Validate page range
        start_page = max(1, min(start_page, total_pages))
        end_page = max(start_page, min(end_page, total_pages))
        
        print(f"Extracting pages {start_page} to {end_page} from {pdf_path}")
        
        for page_num in range(start_page - 1, end_page):
            page = pdf.pages[page_num]
            text = page.extract_text()
            
            # Extract tables if present
            tables = page.extract_tables()
            
            page_data = {
                "page_number": page_num + 1,
                "text_length": len(text) if text else 0,
                "full_text": text if text else "",
                "tables": []
            }
            
            # Add table data if found
            if tables:
                for i, table in enumerate(tables):
                    page_data["tables"].append({
                        "table_number": i + 1,
                        "rows": len(table),
                        "data": table
                    })
            
            # Check for key content
            key_content = []
            if text:
                if "BUSINESSOWNERS PROPERTY COVERAGE" in text:
                    key_content.append("Property Coverage Declarations")
                if "Business Income" in text and "Extra Expense" in text:
                    key_content.append("Business Income and Extra Expense")
                if "807 Broadway" in text:
                    key_content.append("807 Broadway Address")
                if "NBP1555904G" in text:
                    key_content.append("Policy Number NBP1555904G")
                if "DESCRIPTION OF PREMISES" in text:
                    key_content.append("Description of Premises")
                
            page_data["key_content"] = key_content
            
            results.append(page_data)
            
            print(f"Page {page_num + 1}: {len(text) if text else 0} characters extracted")
            if key_content:
                print(f"  Key content: {', '.join(key_content)}")
    
    # Save to JSON if output path provided
    if output_json:
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to {output_json}")
    
    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_pdf_text.py <pdf_file> [start_page] [end_page] [output.json]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    start_page = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    end_page = int(sys.argv[3]) if len(sys.argv) > 3 else None
    output_json = sys.argv[4] if len(sys.argv) > 4 else None
    
    if not Path(pdf_path).exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    extract_pdf_pages(pdf_path, start_page, end_page, output_json)

if __name__ == "__main__":
    main()