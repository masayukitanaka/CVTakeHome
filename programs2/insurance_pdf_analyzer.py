#!/usr/bin/env python3
import os
import sys
import json
import base64
import argparse
import tempfile
import logging
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import PyPDF2
import pdfplumber

load_dotenv()

class InsurancePDFAnalyzer:
    def __init__(self, max_pages_per_batch=4, enable_logging=True):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in .env file")
        
        self.client = OpenAI(api_key=self.api_key)
        self.analysis_data = []
        self.max_pages_per_batch = max_pages_per_batch
        self.pdf_text_cache = {}  # Cache for extracted PDF text
        
        # Setup logging
        if enable_logging:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler('openai_responses.log'),
                    logging.StreamHandler()
                ]
            )
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = None
    
    def get_pdf_page_count(self, pdf_path):
        """Get total number of pages in PDF"""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            return len(reader.pages)
    
    def extract_text_from_pdf(self, pdf_path, start_page=1, end_page=None):
        """Extract text from PDF using pdfplumber"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                
                if end_page is None:
                    end_page = total_pages
                
                # Validate page range
                start_page = max(1, start_page)
                end_page = min(total_pages, end_page)
                
                extracted_text = {}
                
                for page_num in range(start_page - 1, end_page):
                    page = pdf.pages[page_num]
                    text = page.extract_text()
                    
                    # Clean up the text a bit
                    if text:
                        text = text.strip()
                    else:
                        text = ""
                    
                    # Store in cache with 1-based page numbering
                    extracted_text[page_num + 1] = text
                    self.pdf_text_cache[page_num + 1] = text
                    
                    if self.logger:
                        self.logger.info(f"Extracted {len(text)} characters from page {page_num + 1}")
                        # Log key content found
                        if text:
                            key_content = []
                            if "BUSINESSOWNERS PROPERTY COVERAGE" in text:
                                key_content.append("Property Coverage")
                            if "Business Income" in text and "Extra Expense" in text:
                                key_content.append("Business Income/Extra Expense")
                            if "807 Broadway" in text:
                                key_content.append("807 Broadway Address")
                            if key_content:
                                self.logger.info(f"  Key content found: {', '.join(key_content)}")
                
                return extracted_text
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error extracting text from PDF: {str(e)}")
            return {}
    
    def analyze_pdf(self, pdf_path, output_json_path, start_page=1, end_page=None):
        """
        Analyze PDF by uploading to OpenAI and save results to JSON.
        Automatically splits large page ranges into smaller batches.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Get total pages if end_page is not specified
        total_pages = self.get_pdf_page_count(pdf_path)
        if end_page is None:
            end_page = total_pages
        
        # Validate page range
        start_page = max(1, start_page)
        end_page = min(total_pages, end_page)
        
        if start_page > end_page:
            raise ValueError(f"Invalid page range: {start_page}-{end_page}")
        
        page_range = end_page - start_page + 1
        print(f"Starting analysis of: {pdf_path}")
        print(f"Total pages to analyze: {page_range} (pages {start_page}-{end_page})")
        
        # Check if we need to split into batches
        if page_range <= self.max_pages_per_batch:
            # Single batch processing
            print("Processing as single batch...")
            return self._analyze_single_batch(pdf_path, output_json_path, start_page, end_page)
        else:
            # Multi-batch processing
            print(f"Large page range detected. Splitting into batches of {self.max_pages_per_batch} pages...")
            return self._analyze_multi_batch(pdf_path, output_json_path, start_page, end_page)
    
    def _analyze_single_batch(self, pdf_path, output_json_path, start_page, end_page):
        """Analyze a single batch of pages"""
        # First extract text from PDF using PyPDF2
        print(f"Extracting text from PDF pages {start_page}-{end_page}...")
        extracted_text = self.extract_text_from_pdf(pdf_path, start_page, end_page)
        
        # Upload PDF to OpenAI
        file_obj = self.upload_pdf_to_openai(pdf_path)
        
        try:
            # Analyze the PDF using OpenAI
            analysis = self.analyze_pdf_with_openai(file_obj, self.analysis_data, start_page, end_page)
            
            # Replace OpenAI's full_text with our extracted text
            for page_data in analysis:
                if isinstance(page_data, dict) and 'page_number' in page_data:
                    page_num = page_data['page_number']
                    if page_num in extracted_text:
                        page_data['full_text'] = extracted_text[page_num]
                        if self.logger:
                            self.logger.info(f"Replaced full_text for page {page_num} with PyPDF2 extracted text ({len(extracted_text[page_num])} chars)")
            
            self.analysis_data = analysis
            
            # Save results
            self.save_json(output_json_path)
            
            print(f"Analysis complete. Results saved to: {output_json_path}")
            return self.analysis_data
            
        finally:
            # Clean up uploaded file
            try:
                self.client.files.delete(file_obj.id)
                print(f"Cleaned up: Deleted uploaded file {file_obj.id}")
            except:
                pass
    
    def _analyze_multi_batch(self, pdf_path, output_json_path, start_page, end_page):
        """Analyze multiple batches and merge results"""
        all_results = []
        batch_files = []
        
        try:
            current_page = start_page
            batch_num = 1
            
            while current_page <= end_page:
                batch_end = min(current_page + self.max_pages_per_batch - 1, end_page)
                
                print(f"\n--- Batch {batch_num}: Analyzing pages {current_page}-{batch_end} ---")
                
                # Create temporary file for this batch
                temp_output = f"{output_json_path.rsplit('.', 1)[0]}_batch_{batch_num}.json"
                batch_files.append(temp_output)
                
                # Analyze this batch
                batch_results = self._analyze_single_batch(pdf_path, temp_output, current_page, batch_end)
                
                # Update page numbers to be sequential from the original start
                page_offset = current_page - 1
                for i, result in enumerate(batch_results):
                    if isinstance(result, dict) and 'page_number' in result:
                        result['page_number'] = page_offset + i + 1
                
                all_results.extend(batch_results)
                
                current_page = batch_end + 1
                batch_num += 1
            
            # Merge all results into final file
            print(f"\n--- Merging {len(all_results)} pages from {len(batch_files)} batches ---")
            self.analysis_data = all_results
            self.save_json(output_json_path)
            
            print(f"Analysis complete! Total pages analyzed: {len(all_results)}")
            print(f"Final results saved to: {output_json_path}")
            
            return self.analysis_data
            
        finally:
            # Clean up batch files
            for batch_file in batch_files:
                try:
                    if os.path.exists(batch_file):
                        os.remove(batch_file)
                        print(f"Cleaned up batch file: {batch_file}")
                except:
                    pass
    
    
    def upload_pdf_to_openai(self, pdf_path):
        """
        Upload PDF file to OpenAI
        """
        try:
            with open(pdf_path, 'rb') as file:
                file_obj = self.client.files.create(
                    file=file,
                    purpose='assistants'
                )
            print(f"PDF uploaded successfully. File ID: {file_obj.id}")
            return file_obj
        except Exception as e:
            raise RuntimeError(f"Failed to upload PDF to OpenAI: {str(e)}")
    
    def analyze_pdf_with_openai(self, file_obj, previous_analysis, start_page=None, end_page=None):
        """
        Analyze PDF using OpenAI Assistant API
        """
        try:
            # Create assistant with file_search capability
            assistant = self.client.beta.assistants.create(
                name="Insurance PDF Page Analyzer",
                instructions="""You are an expert insurance document analyst. Your task is to analyze EVERY PAGE of the PDF document and provide comprehensive, detailed JSON-formatted results.

CRITICAL REQUIREMENTS:
1. Analyze ALL pages in the document - not just the first few pages
2. Focus on extracting structured information, tables, and key data
3. Identify relationships between pages and document structure

For each page, extract:
- Page number and comprehensive summary
- For full_text: Just provide a brief placeholder text (the actual text will be extracted separately)
- Detailed tables and figures descriptions with their structure and content
- Key insurance information (property, coverage, dates, amounts, addresses)
- Cross-page relationships and document structure

Return results as a comprehensive JSON array where each element represents one complete page analysis.

IMPORTANT: Return ONLY the JSON array. No explanations, comments, or code blocks. Start with [ and end with ].""",
                model="gpt-4o",
                tools=[{"type": "file_search"}]
            )
            
            print(f"Assistant created. Assistant ID: {assistant.id}")
            
            # Create thread and attach file
            thread = self.client.beta.threads.create()
            
            # Create page range message
            if start_page and end_page:
                page_range_instruction = f"Focus specifically on pages {start_page} to {end_page} of the document."
            else:
                page_range_instruction = "Extract ALL pages from the document, not just the first few pages."
            
            message = self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=f"""Please analyze this insurance PDF document page by page. {page_range_instruction}

IMPORTANT: 
- Focus on understanding the document structure and extracting key information
- For full_text field: just provide a brief placeholder (actual text will be extracted separately)
- Be comprehensive in identifying tables, figures, and relationships

For each page, provide detailed information in the following JSON format:

[
  {{
    "page_number": 1,
    "summary": "Brief summary of page content (2-3 sentences)",
    "full_text": "Text will be extracted separately",
    "tables_and_figures": [
      {{
        "type": "table or figure or chart",
        "description": "Description of the table/figure",
        "content": "Complete text content from the table/figure"
      }}
    ],
    "key_information": {{
      "insured_property": "Property information if found",
      "coverage_details": "Coverage information if found",
      "dates": "Important dates if found",
      "amounts": "Financial amounts if found",
      "addresses": "Any addresses mentioned"
    }},
    "relationships": {{
      "continues_from_previous": "What content continues from previous page",
      "continues_to_next": "What content appears to continue to next page",
      "references": "References to other pages or sections"
    }},
    "document_structure": {{
      "section_title": "Main section title if present",
      "subsections": ["List of subsection titles"],
      "page_type": "cover or content or table or appendix or other"
    }}
  }}
]

Please analyze ALL pages in the document and return the complete JSON array with every page included.

CRITICAL: Return ONLY valid JSON. No explanatory text, no comments, no code blocks. Just the raw JSON array starting with [ and ending with ]. Do not include any text before or after the JSON.""",
                attachments=[
                    {
                        "file_id": file_obj.id,
                        "tools": [{"type": "file_search"}]
                    }
                ]
            )
            
            # Run the assistant
            run = self.client.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=assistant.id
            )
            
            # If the first run didn't get all pages, send a follow-up message
            if run.status == 'completed':
                messages = self.client.beta.threads.messages.list(thread_id=thread.id)
                response_message = messages.data[0]
                analysis_text = response_message.content[0].text.value
                
                # Log the initial response
                if self.logger:
                    self.logger.info(f"Initial OpenAI response length: {len(analysis_text)} characters")
                    self.logger.info(f"Initial response preview: {analysis_text[:500]}...")
                    # Save full response to separate file
                    with open(f'openai_response_initial_{start_page}_{end_page}.txt', 'w', encoding='utf-8') as f:
                        f.write(analysis_text)
                    self.logger.info(f"Full initial response saved to openai_response_initial_{start_page}_{end_page}.txt")
                
                # Check if we got comprehensive results
                if "page" in analysis_text.lower() and len(analysis_text) < 5000:
                    print("Initial response seems incomplete. Requesting full analysis...")
                    
                    # Send follow-up message
                    followup_message = self.client.beta.threads.messages.create(
                        thread_id=thread.id,
                        role="user",
                        content="The previous response appears incomplete. Please ensure you analyze ALL pages in the document and include the complete full_text for each page with every single word, not summaries. Please provide the comprehensive analysis for all pages."
                    )
                    
                    # Run again
                    run = self.client.beta.threads.runs.create_and_poll(
                        thread_id=thread.id,
                        assistant_id=assistant.id
                    )
            
            print(f"Analysis completed with status: {run.status}")
            
            if run.status == 'completed':
                messages = self.client.beta.threads.messages.list(thread_id=thread.id)
                response_message = messages.data[0]
                analysis_text = response_message.content[0].text.value
                
                # Log the final response
                if self.logger:
                    self.logger.info(f"Final OpenAI response length: {len(analysis_text)} characters")
                    self.logger.info(f"Final response preview: {analysis_text[:500]}...")
                    # Save full response to separate file
                    with open(f'openai_response_final_{start_page}_{end_page}.txt', 'w', encoding='utf-8') as f:
                        f.write(analysis_text)
                    self.logger.info(f"Full final response saved to openai_response_final_{start_page}_{end_page}.txt")
                
                # Parse JSON response
                return self.parse_full_analysis_response(analysis_text, start_page, end_page)
            else:
                print(f"Analysis failed with status: {run.status}")
                return []
            
        except Exception as e:
            print(f"Error during OpenAI analysis: {str(e)}")
            return []
        finally:
            # Cleanup assistant
            try:
                if 'assistant' in locals():
                    self.client.beta.assistants.delete(assistant.id)
                    print(f"Cleaned up: Deleted assistant {assistant.id}")
            except:
                pass
    
    def parse_full_analysis_response(self, response_text, start_page=None, end_page=None):
        """
        Parse the complete analysis response from OpenAI
        """
        try:
            print("Raw response preview:", response_text[:200] + "..." if len(response_text) > 200 else response_text)
            
            # Log parsing attempt
            if self.logger:
                self.logger.info(f"Parsing JSON response for pages {start_page}-{end_page}")
            
            # Clean up response text - handle multiple code block formats
            response_text = response_text.strip()
            
            # Remove leading explanation text before JSON
            if "```json" in response_text:
                # Find the start of the JSON block
                json_start = response_text.find("```json")
                if json_start != -1:
                    response_text = response_text[json_start + 7:]  # Remove "```json"
                    
                    # Find the end of the JSON block
                    json_end = response_text.find("```")
                    if json_end != -1:
                        response_text = response_text[:json_end]
            
            # Alternative: look for JSON array start if no code blocks
            elif response_text.find("[") != -1:
                json_start = response_text.find("[")
                response_text = response_text[json_start:]
                
                # Find the last ] to close the array
                json_end = response_text.rfind("]")
                if json_end != -1:
                    response_text = response_text[:json_end + 1]
            
            response_text = response_text.strip()
            
            # Clean up common JSON syntax issues
            response_text = self.clean_json_syntax(response_text)
            
            # Try to fix common JSON issues
            if response_text and not response_text.startswith("["):
                # If it doesn't start with [, try to find the JSON part
                lines = response_text.split("\n")
                json_lines = []
                in_json = False
                for line in lines:
                    if line.strip().startswith("[") or in_json:
                        in_json = True
                        json_lines.append(line)
                        if line.strip().endswith("]") and line.strip() != "[":
                            break
                response_text = "\n".join(json_lines)
            
            print("Cleaned JSON preview:", response_text[:200] + "..." if len(response_text) > 200 else response_text)
            
            # Parse JSON array
            analysis_data = json.loads(response_text)
            
            # Ensure it's a list
            if not isinstance(analysis_data, list):
                analysis_data = [analysis_data]
            
            # Add timestamps to each page
            from datetime import datetime
            for page_data in analysis_data:
                if isinstance(page_data, dict):
                    page_data['analyzed_at'] = datetime.now().isoformat()
            
            print(f"Successfully parsed analysis for {len(analysis_data)} pages")
            
            # Log parsed data
            if self.logger:
                self.logger.info(f"Successfully parsed {len(analysis_data)} pages")
                for i, page in enumerate(analysis_data[:3]):  # Log first 3 pages
                    if isinstance(page, dict):
                        self.logger.info(f"Page {page.get('page_number', i+1)} summary: {page.get('summary', 'N/A')[:100]}...")
                        full_text_len = len(page.get('full_text', ''))
                        self.logger.info(f"Page {page.get('page_number', i+1)} full_text length: {full_text_len} chars")
            
            return analysis_data
            
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {str(e)}")
            print("Full raw response:", response_text[:1000] + "..." if len(response_text) > 1000 else response_text)
            
            # Try to extract any JSON-like content manually
            extracted_data = self.extract_json_manually(response_text)
            if extracted_data:
                return extracted_data
            
            # Create error response with the actual content
            from datetime import datetime
            return [{
                "page_number": 1,
                "summary": f"Analysis failed: JSON parse error - {str(e)}",
                "full_text": response_text,
                "tables_and_figures": [],
                "key_information": {},
                "relationships": {},
                "document_structure": {"page_type": "error"},
                "error": f"JSON parse error: {str(e)}",
                "analyzed_at": datetime.now().isoformat()
            }]
    
    def extract_json_manually(self, response_text):
        """
        Try to manually extract JSON content from response
        """
        try:
            # Look for JSON array patterns
            import re
            
            # Find JSON array pattern
            json_pattern = r'\[\s*\{.*?\}\s*\]'
            matches = re.findall(json_pattern, response_text, re.DOTALL)
            
            if matches:
                # Try to parse the largest match
                largest_match = max(matches, key=len)
                try:
                    data = json.loads(largest_match)
                    print(f"Successfully extracted JSON manually: {len(data)} pages")
                    
                    # Add timestamps
                    from datetime import datetime
                    for page_data in data:
                        if isinstance(page_data, dict):
                            page_data['analyzed_at'] = datetime.now().isoformat()
                    
                    return data
                except:
                    pass
                    
        except Exception as e:
            print(f"Manual extraction failed: {e}")
            
        return None
    
    def clean_json_syntax(self, json_text):
        """
        Clean up common JSON syntax issues
        """
        import re
        
        # Remove JavaScript-style comments
        json_text = re.sub(r'//.*$', '', json_text, flags=re.MULTILINE)
        
        # Remove C-style comments
        json_text = re.sub(r'/\*.*?\*/', '', json_text, flags=re.DOTALL)
        
        # Fix trailing commas in arrays/objects
        json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
        
        # Fix missing commas between objects in array
        json_text = re.sub(r'}\s*\n\s*{', '},\n  {', json_text)
        
        # Fix incomplete JSON arrays (if ends abruptly)
        if json_text.strip().endswith('}') and not json_text.strip().endswith('}]'):
            json_text = json_text.strip() + '\n]'
        
        # Remove any text after the final closing bracket
        last_bracket = json_text.rfind(']')
        if last_bracket != -1:
            json_text = json_text[:last_bracket + 1]
        
        return json_text
    
    def save_json(self, output_path):
        """
        Save analysis data to JSON file
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_data, f, ensure_ascii=False, indent=2)

def main():
    parser = argparse.ArgumentParser(
        description='Analyze insurance PDF documents page by page using OpenAI Vision API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python insurance_pdf_analyzer.py document.pdf
  python insurance_pdf_analyzer.py document.pdf -o analysis.json
  python insurance_pdf_analyzer.py document.pdf --start-page 1 --end-page 5

The program will create a detailed JSON analysis of each page including:
- Page summary and full text content
- Tables and figures descriptions  
- Key insurance information (property, coverage, dates, amounts)
- Cross-page relationships and document structure
        """
    )
    parser.add_argument('pdf_path', type=str, help='Path to the insurance PDF document')
    parser.add_argument('-o', '--output', type=str, 
                       help='Output JSON file path (default: <pdf_name>_analysis.json)')
    parser.add_argument('--start-page', type=int, default=1,
                       help='Start analysis from this page (default: 1)')
    parser.add_argument('--end-page', type=int, 
                       help='End analysis at this page (default: last page)')
    parser.add_argument('--resume', action='store_true',
                       help='Resume analysis from existing JSON file')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.exists(args.pdf_path):
        print(f"Error: PDF file not found: {args.pdf_path}")
        sys.exit(1)
    
    # Set default output path if not provided
    if not args.output:
        pdf_path = Path(args.pdf_path)
        args.output = pdf_path.stem + '_analysis.json'
    
    # Check if resuming from existing file
    if args.resume and os.path.exists(args.output):
        print(f"Resuming analysis from existing file: {args.output}")
    elif args.resume:
        print(f"Warning: Resume requested but output file not found: {args.output}")
        print("Starting fresh analysis...")
    
    try:
        analyzer = InsurancePDFAnalyzer()
        
        # Load existing data if resuming
        if args.resume and os.path.exists(args.output):
            with open(args.output, 'r', encoding='utf-8') as f:
                analyzer.analysis_data = json.load(f)
            print(f"Loaded {len(analyzer.analysis_data)} existing page analyses")
        
        # Set page range
        if args.verbose:
            print(f"Analysis parameters:")
            print(f"  PDF file: {args.pdf_path}")
            print(f"  Output file: {args.output}")
            print(f"  Start page: {args.start_page}")
            print(f"  End page: {args.end_page or 'last'}")
            print(f"  Resume mode: {args.resume}")
        
        analyzer.analyze_pdf(args.pdf_path, args.output, args.start_page, args.end_page)
        print(f"\nAnalysis completed successfully!")
        print(f"Results saved to: {args.output}")
        sys.exit(0)
        
    except KeyboardInterrupt:
        print(f"\nAnalysis interrupted by user. Partial results saved to: {args.output}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()