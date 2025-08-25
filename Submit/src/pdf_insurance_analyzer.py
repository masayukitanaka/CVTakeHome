#!/usr/bin/env python3
"""
PDF Insurance Document Analyzer using OpenAI API

This script directly analyzes PDF files page by page to extract Location * Building information
for insurance documents. It extracts key insurance information including:

- Location/Building identifiers
- Addresses  
- Building Limits
- Personal Property Limits
- Business Income
- Deductibles
- Valuation methods

The script processes PDFs page by page to ensure thorough analysis of all content.
"""

import os
import sys
import argparse
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv
from openai import OpenAI
import pdfplumber

load_dotenv()


class PDFInsuranceAnalyzer:
    """PDF Insurance document analyzer using OpenAI API"""
    
    def __init__(self, enable_logging=True):
        """Initialize the analyzer"""
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in .env file")
        
        self.client = OpenAI(api_key=self.api_key)
        self.extracted_buildings = []
        self.extracted_dynamic_terms = []
        
        # Setup logging
        if enable_logging:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler('pdf_insurance_analysis.log'),
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
    
    def get_pdf_page_count(self, pdf_path):
        """Get total number of pages in PDF"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                return len(pdf.pages)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting page count: {str(e)}")
            return 0
    
    def analyze_page_for_locations(self, page_text, page_number):
        """Analyze a single page for location and building information"""
        if not page_text.strip():
            return [], []
        
        prompt = f"""Analyze this page from an insurance document and extract Location/Building information.

TASK: Extract property insurance information for any locations/buildings mentioned on this page.

Look for:
- Location numbers/identifiers (Location 1, Premises 001, etc.)
- Building information and identifiers  
- Property addresses
- Coverage limits and details
- Deductibles
- Valuation methods

Extract the following for EACH building/property found:
1. Location/Building identifier: Format as "Location X Building Y" or similar
2. Address: Complete physical address if available
3. Building Limit: Building coverage limit amount (property coverage, not liability)
4. Personal Property Limit: Business Personal Property coverage limit
5. Business Income: Business Income and Extra Expense coverage limit
6. Deductible: Property coverage deductible amount
7. Valuation: RC (Replacement Cost), ACV (Actual Cash Value), etc.

IMPORTANT GUIDELINES:
- Only extract information actually present on this page
- Distinguish between PROPERTY coverage and LIABILITY coverage
- Use $ symbol for amounts (e.g., $500,000)
- Use empty string "" for missing information
- Return empty array if no location/building information is found

PAGE {page_number} CONTENT:
{page_text}

Return JSON with buildings found on this page:
{{
  "buildings": [
    {{
      "location_building": "Location 1 Building 1",
      "address": "complete address or empty string",
      "building_limit": "$amount or empty string", 
      "personal_property_limit": "$amount or empty string",
      "business_income": "$amount or empty string",
      "deductible": "$amount or empty string",
      "valuation": "RC/ACV/etc or empty string"
    }}
  ]
}}

Return only valid JSON. If no buildings found, return {{"buildings": []}}."""

        # Get basic location info
        buildings = self._analyze_page_basic(page_text, page_number)
        
        # Get additional terms
        dynamic_terms = self._analyze_page_dynamic_terms(page_text, page_number)
        
        return buildings, dynamic_terms
    
    def _analyze_page_basic(self, page_text, page_number):
        """Extract basic location/building information from a page"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an insurance document analyst. Extract property insurance information accurately from document pages and return valid JSON."
                    },
                    {"role": "user", "content": f"""Analyze this page from an insurance document and extract Location/Building information.

TASK: Extract property insurance information for any locations/buildings mentioned on this page.

Look for:
- Location numbers/identifiers (Location 1, Premises 001, etc.)
- Building information and identifiers  
- Property addresses
- Coverage limits and details
- Deductibles
- Valuation methods

Extract the following for EACH building/property found:
1. Location/Building identifier: Format as "Location X Building Y" or similar
2. Address: Complete physical address if available
3. Building Limit: Building coverage limit amount (property coverage, not liability)
4. Personal Property Limit: Business Personal Property coverage limit
5. Business Income: Business Income and Extra Expense coverage limit
6. Deductible: Property coverage deductible amount
7. Valuation: RC (Replacement Cost), ACV (Actual Cash Value), etc.

IMPORTANT GUIDELINES:
- Only extract information actually present on this page
- Distinguish between PROPERTY coverage and LIABILITY coverage
- Use $ symbol for amounts (e.g., $500,000)
- Use empty string "" for missing information
- Return empty array if no location/building information is found

PAGE {page_number} CONTENT:
{page_text}

Return JSON with buildings found on this page:
{{
  "buildings": [
    {{
      "location_building": "Location 1 Building 1",
      "address": "complete address or empty string",
      "building_limit": "$amount or empty string", 
      "personal_property_limit": "$amount or empty string",
      "business_income": "$amount or empty string",
      "deductible": "$amount or empty string",
      "valuation": "RC/ACV/etc or empty string"
    }}
  ]
}}

Return only valid JSON. If no buildings found, return {{"buildings": []}}."""}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=4000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            if self.logger:
                self.logger.info(f"Page {page_number} basic analysis response: {result_text[:200]}...")
            
            # Parse JSON response
            try:
                result = json.loads(result_text)
                buildings = result.get('buildings', [])
                
                if self.logger:
                    self.logger.info(f"Page {page_number}: Found {len(buildings)} buildings")
                
                return buildings
                
            except json.JSONDecodeError as e:
                if self.logger:
                    self.logger.error(f"Page {page_number} JSON parsing error: {e}")
                return []
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Page {page_number} basic analysis error: {e}")
            return []
    
    def _analyze_page_dynamic_terms(self, page_text, page_number):
        """Extract additional insurance terms and conditions from a page"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an insurance document analyst specialized in discovering additional terms, conditions, and coverage details."
                    },
                    {"role": "user", "content": f"""Analyze this page from an insurance document and extract ADDITIONAL terms, conditions, and coverage details.

TASK: Find any additional insurance terms, conditions, endorsements, or coverage details NOT covered by standard property insurance fields.

Look for:
- Additional coverages (Equipment Breakdown, Ordinance & Law, Terrorism, etc.)
- Special conditions or endorsements
- Policy forms and numbers
- Coverage extensions or modifications
- Additional financial terms (Coinsurance, Aggregate limits, etc.)
- Territory or protection class information
- Construction details
- Occupancy classifications
- Any other insurance-specific terms with associated values

EXCLUDE these standard fields (covered elsewhere):
- Basic building limits
- Basic personal property limits  
- Basic business income
- Basic deductibles
- Basic address information

PAGE {page_number} CONTENT:
{page_text}

Return JSON with additional terms found:
{{
  "additional_terms": [
    {{
      "term": "Equipment Breakdown",
      "value": "$50,000",
      "location": "All Locations" 
    }},
    {{
      "term": "Ordinance and Law",
      "value": "10% of Building Limit",
      "location": "Location 1"
    }}
  ]
}}

Return only valid JSON. If no additional terms found, return {{"additional_terms": []}}."""}  
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=4000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            if self.logger:
                self.logger.info(f"Page {page_number} dynamic terms response: {result_text[:200]}...")
            
            # Parse JSON response
            try:
                result = json.loads(result_text)
                terms = result.get('additional_terms', [])
                
                if self.logger:
                    self.logger.info(f"Page {page_number}: Found {len(terms)} additional terms")
                
                return terms
                
            except json.JSONDecodeError as e:
                if self.logger:
                    self.logger.error(f"Page {page_number} dynamic terms JSON parsing error: {e}")
                return []
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Page {page_number} dynamic terms analysis error: {e}")
            return []
    
    def consolidate_buildings(self, all_buildings):
        """Consolidate buildings from multiple pages and properly assign Location/Building IDs"""
        # First, group by address to identify premises (locations)
        address_groups = {}
        
        for building in all_buildings:
            address = building.get('address', '').strip()
            if address:
                # Normalize address for grouping
                normalized_address = self._normalize_address(address)
                if normalized_address not in address_groups:
                    address_groups[normalized_address] = []
                address_groups[normalized_address].append(building)
        
        # Assign proper Location/Building identifiers
        consolidated = {}
        location_counter = 1
        
        for normalized_address, buildings in address_groups.items():
            building_counter = 1
            
            for building in buildings:
                # Create proper location_building identifier
                location_building_id = f"Location {location_counter} Building {building_counter}"
                
                # Update building data
                updated_building = building.copy()
                updated_building['location_building'] = location_building_id
                
                # Use the new ID as consolidation key
                key = location_building_id
                
                if key in consolidated:
                    # Merge information, preferring non-empty values
                    existing = consolidated[key]
                    merged = {}
                    
                    for field in ['location_building', 'address', 'building_limit', 
                                'personal_property_limit', 'business_income', 'deductible', 'valuation']:
                        existing_val = existing.get(field, '')
                        new_val = updated_building.get(field, '')
                        
                        # Prefer non-empty values, or longer values if both non-empty
                        if not existing_val:
                            merged[field] = new_val
                        elif not new_val:
                            merged[field] = existing_val
                        else:
                            # Both have values, prefer longer/more detailed one
                            merged[field] = new_val if len(new_val) > len(existing_val) else existing_val
                    
                    consolidated[key] = merged
                else:
                    consolidated[key] = updated_building
                
                building_counter += 1
            
            location_counter += 1
        
        return list(consolidated.values())
    
    def _normalize_address(self, address):
        """Normalize address for proper grouping"""
        # Basic address normalization
        normalized = address.lower().strip()
        
        # Remove common variations
        normalized = normalized.replace(',', ' ')
        normalized = ' '.join(normalized.split())  # Remove extra spaces
        
        # Remove suite, apt, unit numbers for premise grouping
        import re
        # Remove patterns like "Suite 100", "Apt 2A", "Unit B", etc.
        patterns = [
            r'\bsuite?\s*\w+',
            r'\bapt\.?\s*\w+', 
            r'\bunit\s*\w+',
            r'\b#\s*\w+',
            r'\broom\s*\w+'
        ]
        
        for pattern in patterns:
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
        
        # Clean up extra spaces
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def consolidate_dynamic_terms(self, all_terms):
        """Consolidate dynamic terms from multiple pages to avoid duplicates"""
        consolidated = {}
        
        for term_entry in all_terms:
            # Create unique key from term and location
            term = term_entry.get('term', '')
            location = term_entry.get('location', '')
            value = term_entry.get('value', '')
            
            key = f"{term}|{location}"
            
            if key in consolidated:
                # If we have the same term+location, prefer non-empty value or longer value
                existing_value = consolidated[key].get('value', '')
                if not existing_value or (value and len(value) > len(existing_value)):
                    consolidated[key] = term_entry
            else:
                consolidated[key] = term_entry
        
        return list(consolidated.values())
    
    def analyze_pdf(self, pdf_path, start_page=1, end_page=None):
        """Analyze entire PDF for insurance location and building information"""
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
        
        print(f"📄 Analyzing PDF: {pdf_path}")
        print(f"📊 Page range: {start_page}-{end_page} (total: {total_pages} pages)")
        
        if self.logger:
            self.logger.info(f"Starting PDF analysis: {pdf_path}")
            self.logger.info(f"Page range: {start_page}-{end_page} ({end_page - start_page + 1} pages)")
        
        # Analyze each page
        all_buildings = []
        all_dynamic_terms = []
        
        for page_num in range(start_page, end_page + 1):
            print(f"🔍 Processing page {page_num}...")
            
            # Extract text from page
            page_text = self.extract_text_from_pdf_page(pdf_path, page_num)
            
            # Analyze page for location/building information and dynamic terms
            page_buildings, page_dynamic_terms = self.analyze_page_for_locations(page_text, page_num)
            
            building_count = len(page_buildings)
            terms_count = len(page_dynamic_terms)
            
            if building_count > 0 or terms_count > 0:
                print(f"✅ Page {page_num}: Found {building_count} building(s), {terms_count} additional term(s)")
                all_buildings.extend(page_buildings)
                all_dynamic_terms.extend(page_dynamic_terms)
            else:
                print(f"📭 Page {page_num}: No building or additional term information found")
        
        # Consolidate results to avoid duplicates
        print(f"\n🔄 Consolidating {len(all_buildings)} building records...")
        consolidated_buildings = self.consolidate_buildings(all_buildings)
        
        print(f"🔄 Consolidating {len(all_dynamic_terms)} additional terms...")
        consolidated_terms = self.consolidate_dynamic_terms(all_dynamic_terms)
        
        self.extracted_buildings = consolidated_buildings
        self.extracted_dynamic_terms = consolidated_terms
        
        print(f"✅ Analysis complete!")
        print(f"📊 Final results: {len(consolidated_buildings)} unique buildings, {len(consolidated_terms)} additional terms found")
        
        if self.logger:
            self.logger.info(f"Analysis complete: {len(consolidated_buildings)} unique buildings, {len(consolidated_terms)} additional terms")
        
        return consolidated_buildings
    
    def display_results_as_table(self):
        """Display extraction results as Markdown table"""
        results = self.extracted_buildings
        
        # Display table header
        print("| Location/ Premises Number, Building Number | Addresses | Building | Personal Property | Business Income | Deductible | Valuation |")
        print("|--------------------------------------------|-----------|---------:| -----------------:| ---------------:| ----------:| ---------:|")
        
        if not results:
            print("| No buildings found | | | | | | |")
            return results
        
        # Display information for each building
        for building in results:
            location = building.get('location_building', '')
            address = building.get('address', '')
            building_limit = building.get('building_limit', '')
            personal_property = building.get('personal_property_limit', '')
            business_income = building.get('business_income', '')
            deductible = building.get('deductible', '')
            valuation = building.get('valuation', '')
            
            print(f"| {location:<42} | {address:<9} | {building_limit:>8} | {personal_property:>17} | {business_income:>15} | {deductible:>10} | {valuation:>9} |")
        
        return results
    
    def export_to_markdown(self, output_file=None, pdf_path=None, output_dir="../output"):
        """Export results to Markdown file"""
        results = self.extracted_buildings
        
        if output_file is None:
            # Generate default filename from PDF name
            if pdf_path:
                pdf_name = Path(pdf_path).stem
                output_file = f"{pdf_name}.md"
            else:
                output_file = "pdf_insurance_analysis.md"
        
        # Add output directory if not absolute path
        if not Path(output_file).is_absolute():
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            output_file = str(output_path / output_file)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write table directly without header (like example.md)
            f.write("\n| Location/ Premises Number, Building Number | Addresses | Building | Personal Property | Business Income | Deductible | Valuation |\n")
            f.write("|--------------------------------------------|-----------|---------:| -----------------:| ---------------:| ----------:| ---------:|\n")
            
            if not results:
                f.write("| No buildings found | | | | | | |\n")
            else:
                for building in results:
                    location = building.get('location_building', '')
                    address = building.get('address', '')
                    building_limit = building.get('building_limit', '')
                    personal_property = building.get('personal_property_limit', '')
                    business_income = building.get('business_income', '')
                    deductible = building.get('deductible', '')
                    valuation = building.get('valuation', '')
                    
                    f.write(f"| {location} | {address} | {building_limit} | {personal_property} | {business_income} | {deductible} | {valuation} |\n")
        
        print(f"📁 Results exported to: {output_file}")
        return output_file
    
    def export_to_json(self, output_file=None, pdf_path=None, output_dir="output"):
        """Export results to JSON file"""
        results = self.extracted_buildings
        
        if output_file is None:
            # Generate default filename from PDF name
            if pdf_path:
                pdf_name = Path(pdf_path).stem
                output_file = f"{pdf_name}.json"
            else:
                output_file = "pdf_insurance_analysis.json"
        
        # Add output directory if not absolute path
        if not Path(output_file).is_absolute():
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            output_file = str(output_path / output_file)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "total_buildings": len(results),
                "buildings": results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"📁 JSON results exported to: {output_file}")
        return output_file
    
    def export_dynamic_terms_to_markdown(self, output_file=None, pdf_path=None, output_dir="output"):
        """Export dynamic terms to separate Markdown file"""
        terms = getattr(self, 'extracted_dynamic_terms', [])
        
        if output_file is None:
            # Generate default filename from PDF name
            if pdf_path:
                pdf_name = Path(pdf_path).stem
                output_file = f"{pdf_name}_dynamic_terms.md"
            else:
                output_file = "pdf_dynamic_terms.md"
        
        # Add output directory if not absolute path
        if not Path(output_file).is_absolute():
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            output_file = str(output_path / output_file)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write table directly without header (like example.md format)
            f.write("\n| Term | Value |\n")
            f.write("|------|-------|\n")
            
            if not terms:
                f.write("| No additional terms found | |\n")
            else:
                for term_entry in terms:
                    term = term_entry.get('term', '')
                    value = term_entry.get('value', '')
                    location = term_entry.get('location', '')
                    
                    # Include location in term name if specified
                    if location and location.lower() != 'all locations':
                        display_term = f"{term} ({location})"
                    else:
                        display_term = term
                    
                    f.write(f"| {display_term} | {value} |\n")
        
        print(f"📁 Dynamic terms exported to: {output_file}")
        return output_file


def main():
    parser = argparse.ArgumentParser(
        description='Analyze PDF insurance documents for Location/Building information using OpenAI API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pdf_insurance_analyzer.py document.pdf
  python pdf_insurance_analyzer.py document.pdf --start-page 1 --end-page 10
  python pdf_insurance_analyzer.py document.pdf --output results.md --json results.json
  
The program will:
- Extract text from each PDF page using pdfplumber
- Analyze each page for location/building insurance information using OpenAI
- Consolidate results across pages to avoid duplicates
- Export results in Markdown table format and optionally JSON
        """
    )
    
    parser.add_argument('pdf_path', type=str, help='Path to the PDF file to analyze')
    parser.add_argument('--start-page', type=int, default=1,
                       help='Start analysis from this page (default: 1)')
    parser.add_argument('--end-page', type=int,
                       help='End analysis at this page (default: last page)')
    parser.add_argument('--output', '-o', type=str,
                       help='Output Markdown file path (default: pdf_insurance_analysis.md)')
    parser.add_argument('--json', type=str,
                       help='Output JSON file path (optional)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--output-dir', type=str, default='output',
                       help='Output directory for results (default: output)')
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.exists(args.pdf_path):
        print(f"❌ Error: PDF file not found: {args.pdf_path}")
        sys.exit(1)
    
    # Check environment variable
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ Error: OPENAI_API_KEY environment variable is not set")
        print("Please run: export OPENAI_API_KEY='your-api-key'")
        sys.exit(1)
    
    try:
        # Create analyzer
        analyzer = PDFInsuranceAnalyzer(enable_logging=args.verbose)
        
        if args.verbose:
            print(f"🔧 Configuration:")
            print(f"  PDF file: {args.pdf_path}")
            print(f"  Start page: {args.start_page}")
            print(f"  End page: {args.end_page or 'last'}")
            print(f"  Output file: {args.output or 'pdf_insurance_analysis.md'}")
            print(f"  JSON output: {args.json or 'disabled'}")
            print(f"  Output directory: {args.output_dir}")
            print(f"  Verbose logging: {args.verbose}")
            print()
        
        # Analyze PDF
        results = analyzer.analyze_pdf(
            pdf_path=args.pdf_path,
            start_page=args.start_page,
            end_page=args.end_page
        )
        
        # Display results
        print("\n" + "="*100)
        print("ANALYSIS RESULTS")
        print("="*100)
        analyzer.display_results_as_table()
        
        # Export results
        markdown_file = analyzer.export_to_markdown(args.output, args.pdf_path, args.output_dir)
        
        # Export dynamic terms to separate file
        dynamic_terms_file = analyzer.export_dynamic_terms_to_markdown(None, args.pdf_path, args.output_dir)
        
        if args.json:
            json_file = analyzer.export_to_json(args.json, args.pdf_path, args.output_dir)
        
        print(f"\n🎉 Success! Found {len(results)} buildings/locations")
        print(f"📁 Markdown results: {markdown_file}")
        print(f"📁 Dynamic terms: {dynamic_terms_file}")
        if args.json:
            print(f"📁 JSON results: {json_file}")
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()