#!/usr/bin/env python3
"""
Insurance certificate PDF analysis JSON parser using OpenAI API

Extracted items:
- Address
- Building Limit
- Personal Property Limit
- Business Income
- Primary Deductible
- Valuation (replacement cost, actual cash value, etc.)

Output format: Markdown table
"""

import json
import sys
import os
from typing import Dict, Any, List
from pathlib import Path
from openai import OpenAI


class InsuranceDataExtractor:
    """Insurance data extraction class using OpenAI API"""
    
    def __init__(self, json_file_path: str):
        """
        Initialize the extractor
        
        Args:
            json_file_path: Path to the JSON file to analyze
        """
        self.json_file_path = json_file_path
        self.data = self._load_json()
        
        # Initialize OpenAI API client
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("Error: OPENAI_API_KEY environment variable is not set")
            print("Please set the environment variable")
            print("Example: export OPENAI_API_KEY='sk-...'")
            sys.exit(1)
        
        self.client = OpenAI(api_key=api_key)
        
        self.extracted_info = []
    
    def _load_json(self) -> list:
        """Load JSON file"""
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: File '{self.json_file_path}' not found")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse JSON: {e}")
            sys.exit(1)
    
    def _prepare_document_text(self) -> str:
        """Prepare text containing important information from JSON data"""
        document_parts = []
        
        for page in self.data:
            page_num = page.get('page_number', 'Unknown')
            
            # Page number and summary
            if page.get('summary'):
                document_parts.append(f"[Page {page_num}]")
                document_parts.append(f"Summary: {page['summary']}")
            
            # Key information
            if page.get('key_information'):
                key_info = page['key_information']
                if any(key_info.values()):
                    document_parts.append("Key Information:")
                    for k, v in key_info.items():
                        if v and v not in ["null", "None", None]:
                            document_parts.append(f"  - {k}: {v}")
            
            # Tables and figures
            if page.get('tables_and_figures'):
                for table in page['tables_and_figures']:
                    if table.get('content'):
                        document_parts.append(f"Table/Figure: {table.get('description', '')}")
                        document_parts.append(table['content'])
            
            # Full text (important parts only)
            if page.get('full_text'):
                text = page['full_text']
                # Extract lines containing specific keywords
                keywords = ['limit', 'deductible', 'address', 'building', 'property', 
                           'business income', 'valuation', 'replacement cost', 'actual cash value',
                           'broadway', 'minneapolis', 'premium', 'coverage', 'premises', 'location']
                
                lines = text.split('\n')
                relevant_lines = []
                for line in lines:
                    if any(keyword in line.lower() for keyword in keywords):
                        relevant_lines.append(line.strip())
                
                if relevant_lines:
                    document_parts.append(f"Relevant text from page {page_num}:")
                    document_parts.extend(relevant_lines[:15])  # Maximum 15 lines
            
            document_parts.append("")  # Page separator
        
        return '\n'.join(document_parts)
    
    def extract_with_openai(self) -> List[Dict[str, Any]]:
        """Extract information using OpenAI API"""
        
        # Prepare document text
        document_text = self._prepare_document_text()
        
        # Prepare detailed full text
        full_texts = []
        for page in self.data[:15]:  # First 15 pages
            if page.get('full_text'):
                full_texts.append(f"[Page {page.get('page_number')}]\n{page['full_text']}\n")
        
        full_document = '\n'.join(full_texts)
        
        # Request to OpenAI API
        prompt = f"""
The following is the analysis result of an insurance certificate. Please comprehensively analyze this document and extract the following information for all buildings/properties:

Extraction items:
1. Location/Premises Number, Building Number: e.g., Location 1 Building 1
2. Address: Complete address of the insured property
3. Building Limit: Building insurance limit amount (leave empty if not specified)
4. Personal Property Limit: Business Personal Property limit amount
5. Business Income: Business Income and Extra Expense limit amount (leave empty if not specified)
6. Deductible: Deductible amount (mainly related to Property coverage)
7. Valuation: RC (Replacement Cost), ACV (Actual Cash Value), etc.

Notes:
- If there are multiple buildings/properties, extract information for each
- 807 Broadway St Ne, Minneapolis, MN 55413 is confirmed as the main property address
- If Building Limit is not explicitly stated, use empty string
- Express amounts with $ symbol (e.g., $5,000)
- Use abbreviations for Valuation (e.g., RC, ACV)

Document summary:
{document_text}

Document details (first part):
{full_document[:10000]}

Please return information for each building in the following JSON array format:
[
  {{
    "location_building": "Location 1 Building 1",
    "address": "complete address",
    "building_limit": "amount or empty string",
    "personal_property_limit": "amount",
    "business_income": "amount or empty string",
    "deductible": "amount",
    "valuation": "RC/ACV abbreviation"
  }}
]
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a professional insurance document analyst. Extract information accurately and respond as a JSON array."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            
            # Extract as array if JSON object
            try:
                result = json.loads(result_text)
                if isinstance(result, dict) and 'buildings' in result:
                    return result['buildings']
                elif isinstance(result, dict) and 'data' in result:
                    return result['data']
                elif isinstance(result, list):
                    return result
                else:
                    # Convert to array if single object
                    return [result] if result else []
            except:
                # Fallback for JSON parse failure
                return []
            
        except Exception as e:
            print(f"Error: OpenAI API call failed: {e}")
            return []
    
    def extract_all(self) -> List[Dict[str, Any]]:
        """Extract all information"""
        print("Analyzing document with OpenAI API...")
        results = self.extract_with_openai()
        self.extracted_info = results
        return self.extracted_info
    
    def display_results_as_table(self):
        """Display extraction results as Markdown table"""
        results = self.extract_all()
        
        if not results:
            print("No information extracted.")
            return results
        
        # Markdown table header
        print("| Location/ Premises Number, Building Number | Addresses | Building | Personal Property | Business Income | Deductible | Valuation |")
        print("|--------------------------------------------|-----------|---------:| -----------------:| ---------------:| ----------:| ---------:|")
        
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
    
    def export_to_markdown(self, output_file: str = None):
        """Export results to Markdown file"""
        results = self.extracted_info
        
        if output_file is None:
            # Generate default filename
            input_path = Path(self.json_file_path)
            output_file = str(input_path.parent / f"{input_path.stem}_extracted.md")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            if not results:
                f.write("No information extracted.\n")
                return output_file
            
            # Markdown table
            f.write("| Location/ Premises Number, Building Number | Addresses | Building | Personal Property | Business Income | Deductible | Valuation |\n")
            f.write("|--------------------------------------------|-----------|---------:| -----------------:| ---------------:| ----------:| ---------:|\n")
            
            for building in results:
                location = building.get('location_building', '')
                address = building.get('address', '')
                building_limit = building.get('building_limit', '')
                personal_property = building.get('personal_property_limit', '')
                business_income = building.get('business_income', '')
                deductible = building.get('deductible', '')
                valuation = building.get('valuation', '')
                
                f.write(f"| {location} | {address} | {building_limit} | {personal_property} | {business_income} | {deductible} | {valuation} |\n")
        
        print(f"Results saved to: {output_file}")
        return output_file


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python parse_insurance_json.py <JSON_file_path>")
        print("Example: python parse_insurance_json.py loganpark_analysis.json")
        print("\nNote: Please set OPENAI_API_KEY environment variable")
        sys.exit(1)
    
    json_file = sys.argv[1]
    
    # Check file existence
    if not Path(json_file).exists():
        print(f"Error: File '{json_file}' not found")
        sys.exit(1)
    
    # Check environment variable
    if not os.getenv('OPENAI_API_KEY'):
        print("Error: OPENAI_API_KEY environment variable is not set")
        print("Please run: export OPENAI_API_KEY='your-api-key'")
        sys.exit(1)
    
    # Execute extraction
    extractor = InsuranceDataExtractor(json_file)
    results = extractor.display_results_as_table()
    
    # Save in Markdown format
    extractor.export_to_markdown()
    
    # Return results (for calling from other programs)
    return results


if __name__ == "__main__":
    main()