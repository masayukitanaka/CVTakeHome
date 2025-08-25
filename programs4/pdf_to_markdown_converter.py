#!/usr/bin/env python3
"""
PDF to Markdown Converter using OpenAI API

This script converts each page of a PDF document to Markdown format while preserving
the original content structure and formatting as much as possible.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import pdfplumber

load_dotenv()

class PDFToMarkdownConverter:
    def __init__(self, enable_logging=True):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in .env file")
        
        self.client = OpenAI(api_key=self.api_key)
        
        # Setup logging
        if enable_logging:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler('pdf_markdown_conversion.log'),
                    logging.StreamHandler()
                ]
            )
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = None
    
    def extract_text_from_pdf_page(self, pdf_path, page_number):
        """Extract text from a specific PDF page using pdfplumber"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if page_number <= len(pdf.pages):
                    page = pdf.pages[page_number - 1]  # Convert to 0-based index
                    text = page.extract_text()
                    
                    if self.logger:
                        self.logger.info(f"Extracted {len(text) if text else 0} characters from page {page_number}")
                    
                    return text or ""
                else:
                    if self.logger:
                        self.logger.warning(f"Page {page_number} does not exist in PDF")
                    return ""
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error extracting text from page {page_number}: {str(e)}")
            return ""
    
    def convert_page_to_markdown(self, text_content, page_number):
        """Convert page text content to Markdown using OpenAI"""
        try:
            if not text_content.strip():
                return f"# Page {page_number}\n\n*This page appears to be blank or contains minimal content.*\n\n"
            
            prompt = f"""Convert the following text content from page {page_number} of a PDF document to clean, well-structured Markdown format.

IMPORTANT REQUIREMENTS:
1. Preserve ALL original content - do not summarize or omit any information
2. Maintain the original document structure and hierarchy
3. Convert tables to proper Markdown table format
4. Use appropriate headers (# ## ###) for titles and sections
5. Preserve lists, bullet points, and numbered items
6. Keep all financial amounts, dates, addresses, and policy numbers exactly as written
7. Maintain line breaks and spacing where they convey meaning
8. Use **bold** for emphasis where appropriate
9. Use `code formatting` for policy numbers, form numbers, and codes
10. Convert any tabular data to proper Markdown tables

Text content from page {page_number}:
---
{text_content}
---

Convert to clean Markdown format while preserving ALL original information and structure:"""

            if self.logger:
                self.logger.info(f"Converting page {page_number} to Markdown using OpenAI...")
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert document formatter. Convert the provided text to clean, well-structured Markdown while preserving ALL original content and maintaining the document's structure and formatting. Never summarize or omit information."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=4000
            )
            
            markdown_content = response.choices[0].message.content.strip()
            
            if self.logger:
                self.logger.info(f"Successfully converted page {page_number} to Markdown ({len(markdown_content)} characters)")
            
            return markdown_content
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error converting page {page_number} to Markdown: {str(e)}")
            
            # Fallback: return basic Markdown with original text
            return f"# Page {page_number}\n\n```\n{text_content}\n```\n\n*Note: OpenAI conversion failed, showing original text*\n\n"
    
    def get_pdf_page_count(self, pdf_path):
        """Get total number of pages in PDF"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                return len(pdf.pages)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting page count: {str(e)}")
            return 0
    
    def convert_pdf_to_markdown(self, pdf_path, output_path=None, start_page=1, end_page=None):
        """Convert entire PDF or specified page range to Markdown"""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Get total pages and validate range
        total_pages = self.get_pdf_page_count(pdf_path)
        if total_pages == 0:
            raise ValueError("Could not read PDF or PDF has no pages")
        
        if end_page is None:
            end_page = total_pages
        
        # Validate page range
        start_page = max(1, start_page)
        end_page = min(total_pages, end_page)
        
        if start_page > end_page:
            raise ValueError(f"Invalid page range: {start_page}-{end_page}")
        
        # Set default output path
        if output_path is None:
            pdf_name = Path(pdf_path).stem
            output_path = f"{pdf_name}_converted.md"
        
        print(f"Converting PDF: {pdf_path}")
        print(f"Page range: {start_page}-{end_page} (total: {total_pages} pages)")
        print(f"Output file: {output_path}")
        
        if self.logger:
            self.logger.info(f"Starting PDF conversion: {pdf_path}")
            self.logger.info(f"Page range: {start_page}-{end_page} ({end_page - start_page + 1} pages)")
        
        # Convert each page
        markdown_content = []
        
        # Add document header
        pdf_name = Path(pdf_path).stem
        markdown_content.append(f"# {pdf_name.replace('_', ' ').title()}")
        markdown_content.append(f"\n*Converted from PDF using OpenAI API*")
        markdown_content.append(f"\n*Pages {start_page}-{end_page} of {total_pages}*")
        markdown_content.append("\n---\n")
        
        for page_num in range(start_page, end_page + 1):
            print(f"Processing page {page_num}...")
            
            # Extract text from page
            page_text = self.extract_text_from_pdf_page(pdf_path, page_num)
            
            # Convert to markdown
            page_markdown = self.convert_page_to_markdown(page_text, page_num)
            
            # Add page separator and content
            if page_num > start_page:
                markdown_content.append("\n\n---\n\n")
            
            markdown_content.append(page_markdown)
        
        # Write to output file
        final_markdown = "".join(markdown_content)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_markdown)
            
            print(f"\n✅ Conversion complete!")
            print(f"📄 {end_page - start_page + 1} pages converted")
            print(f"📁 Output saved to: {output_path}")
            print(f"📊 Total characters: {len(final_markdown)}")
            
            if self.logger:
                self.logger.info(f"Conversion complete: {output_path}")
                self.logger.info(f"Final markdown length: {len(final_markdown)} characters")
            
            return output_path
            
        except Exception as e:
            error_msg = f"Error writing output file: {str(e)}"
            print(f"❌ {error_msg}")
            if self.logger:
                self.logger.error(error_msg)
            raise

def main():
    parser = argparse.ArgumentParser(
        description='Convert PDF pages to Markdown format using OpenAI API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pdf_to_markdown_converter.py document.pdf
  python pdf_to_markdown_converter.py document.pdf -o document.md
  python pdf_to_markdown_converter.py document.pdf --start-page 1 --end-page 5
  
The program will:
- Extract text from each PDF page using pdfplumber
- Convert each page to clean Markdown using OpenAI GPT-4o
- Preserve all original content and structure
- Output a single Markdown file with all pages
        """
    )
    
    parser.add_argument('pdf_path', type=str, help='Path to the PDF file to convert')
    parser.add_argument('-o', '--output', type=str, 
                       help='Output Markdown file path (default: <pdf_name>_converted.md)')
    parser.add_argument('--start-page', type=int, default=1,
                       help='Start conversion from this page (default: 1)')
    parser.add_argument('--end-page', type=int,
                       help='End conversion at this page (default: last page)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.exists(args.pdf_path):
        print(f"❌ Error: PDF file not found: {args.pdf_path}")
        sys.exit(1)
    
    try:
        # Create converter
        converter = PDFToMarkdownConverter(enable_logging=args.verbose)
        
        if args.verbose:
            print(f"🔧 Configuration:")
            print(f"  PDF file: {args.pdf_path}")
            print(f"  Output file: {args.output or 'auto-generated'}")
            print(f"  Start page: {args.start_page}")
            print(f"  End page: {args.end_page or 'last'}")
            print(f"  Verbose logging: {args.verbose}")
            print()
        
        # Convert PDF to Markdown
        output_file = converter.convert_pdf_to_markdown(
            pdf_path=args.pdf_path,
            output_path=args.output,
            start_page=args.start_page,
            end_page=args.end_page
        )
        
        print(f"\n🎉 Success! Markdown file created: {output_file}")
        sys.exit(0)
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Conversion interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()