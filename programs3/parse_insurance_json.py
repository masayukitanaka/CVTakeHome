#!/usr/bin/env python3
"""
Insurance certificate PDF analysis parser using OpenAI API

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
import base64
import io
from typing import Dict, Any, List, Union
from pathlib import Path
from openai import OpenAI


class InsuranceDataExtractor:
    """Insurance data extraction class using OpenAI API"""
    
    def __init__(self, file_path: str):
        """
        Initialize the extractor
        
        Args:
            file_path: Path to the file to analyze (JSON or PDF)
        """
        self.file_path = file_path
        self.file_type = self._detect_file_type()
        
        if self.file_type == 'json':
            self.data = self._load_json()
        elif self.file_type == 'pdf':
            self.data = None
        else:
            print(f"Error: Unsupported file type. Please provide JSON or PDF file.")
            sys.exit(1)
        
        # Initialize OpenAI API client
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("Error: OPENAI_API_KEY environment variable is not set")
            print("Please set the environment variable")
            print("Example: export OPENAI_API_KEY='sk-...'")
            sys.exit(1)
        
        self.client = OpenAI(api_key=api_key)
        
        self.extracted_info = []
    
    def _detect_file_type(self) -> str:
        """Detect file type from extension"""
        file_extension = Path(self.file_path).suffix.lower()
        if file_extension == '.json':
            return 'json'
        elif file_extension == '.pdf':
            return 'pdf'
        else:
            return 'unknown'
    
    def _load_json(self) -> list:
        """Load JSON file"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: File '{self.file_path}' not found")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse JSON: {e}")
            sys.exit(1)
    
    def _convert_pdf_to_images(self) -> List[str]:
        """Convert PDF to images and encode as base64"""
        try:
            from pdf2image import convert_from_path
            from PIL import Image
        except ImportError:
            print("Error: pdf2image and PIL are required for PDF processing")
            print("Please install: pip install pdf2image pillow")
            sys.exit(1)
        
        try:
            # Convert PDF to images - all pages at DPI 150 for balanced quality/cost
            images = convert_from_path(self.file_path, dpi=150)  # All pages at optimal DPI
            
            base64_images = []
            for i, image in enumerate(images):
                # Convert PIL image to base64
                buffer = io.BytesIO()
                image.save(buffer, format='JPEG', quality=85)
                img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                base64_images.append(img_base64)
                print(f"Converted page {i+1} to image ({len(img_base64)} base64 characters)")
            
            return base64_images
            
        except FileNotFoundError:
            print(f"Error: File '{self.file_path}' not found")
            sys.exit(1)
        except Exception as e:
            print(f"Error: Failed to convert PDF to images: {e}")
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
        
        if self.file_type == 'pdf':
            return self._extract_from_pdf()
        else:
            return self._extract_from_json()
    
    def _extract_from_pdf(self) -> List[Dict[str, Any]]:
        """Extract information directly from PDF using OpenAI Vision API"""
        
        # Convert PDF to images
        print("Converting PDF to images...")
        images_base64 = self._convert_pdf_to_images()
        
        # Also try to get JSON analysis if available
        json_analysis = ""
        pdf_path = Path(self.file_path)
        
        # Try different JSON file naming patterns
        possible_json_files = [
            pdf_path.with_suffix('.json'),  # loganpark.json
            pdf_path.parent / f"{pdf_path.stem}_analysis.json",  # loganpark_analysis.json
            pdf_path.parent / f"{pdf_path.stem}_extracted.json",  # loganpark_extracted.json
        ]
        
        json_file_path = None
        for possible_path in possible_json_files:
            if possible_path.exists():
                json_file_path = possible_path
                break
        
        if json_file_path:
            try:
                print(f"Found corresponding JSON file: {json_file_path}")
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    
                    # Prepare document text from JSON data
                    document_parts = []
                    for page in json_data[:5]:  # First 5 pages for context
                        page_num = page.get('page_number', 'Unknown')
                        
                        # Key information
                        if page.get('key_information'):
                            key_info = page['key_information']
                            if any(key_info.values()):
                                document_parts.append(f"[Page {page_num}] Key Information:")
                                for k, v in key_info.items():
                                    if v and v not in ["null", "None", None]:
                                        document_parts.append(f"  - {k}: {v}")
                        
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
                                document_parts.append(f"[Page {page_num}] Relevant text:")
                                document_parts.extend(relevant_lines[:10])  # Maximum 10 lines per page
                    
                    json_summary = '\n'.join(document_parts)
                    json_analysis = f"\n\nADDITIONAL CONTEXT FROM JSON ANALYSIS:\n{json_summary[:4000]}...\n"
                    
            except Exception as e:
                print(f"Could not load JSON file: {e}")
        else:
            print("No corresponding JSON analysis file found")
        
        # Request to OpenAI API with images and JSON context
        prompt = f"""
Please analyze this insurance certificate document. I can see that this appears to be a business owner's policy with property coverage information.

I need you to extract the following specific information for each building/property:

1. Location/Premises Number, Building Number: e.g., "Location 1 Building 1"
2. Address: Complete physical address 
3. Building Limit: Building coverage limit amount (use empty string if not found)
4. Personal Property Limit: Business personal property coverage limit
5. Business Income: Business income and extra expense coverage limit (use empty string if not found)
6. Deductible: Property coverage deductible amount
7. Valuation: Type like "RC" (Replacement Cost) or "ACV" (Actual Cash Value)

Key areas to look for:
- BUSINESSOWNERS PROPERTY COVERAGE PART DECLARATIONS
- Tables showing Coverage, Limits of Insurance, Deductible, and Valuation
- Property coverage sections and schedules
- Address information (I expect to see 807 Broadway St Ne, Minneapolis, MN)

Example of what I'm looking for in tables:
- Business Personal Property: $5,000 limit with $1,000 deductible and RC valuation
- Business Income and Extra Expense: $16,552 limit

Please use both the visual PDF information AND the JSON analysis context below to provide the most accurate extraction.

{json_analysis}

Please provide detailed results even if some fields are missing. Always return valid JSON.

REQUIRED JSON format:
{{
  "buildings": [
    {{
      "location_building": "Location 1 Building 1",
      "address": "807 Broadway St Ne, Minneapolis, MN 55413",
      "building_limit": "",
      "personal_property_limit": "$5,000",
      "business_income": "$16,552",
      "deductible": "$1,000",
      "valuation": "RC"
    }}
  ]
}}
"""

        try:
            # Log request details
            print("=" * 60)
            print("OpenAI API REQUEST (PDF as Images):")
            print("=" * 60)
            print(f"Model: gpt-4o")
            print(f"Temperature: 0.1")
            print(f"Response format: json_object")
            print(f"Number of images: {len(images_base64)}")
            print("\nSystem message:")
            print("You are a professional insurance document analyst. Extract information accurately from PDF documents.")
            print("\nUser prompt:")
            print(prompt[:800] + "..." if len(prompt) > 800 else prompt)
            print("\n" + "=" * 60)
            
            # Prepare messages with images
            content = [{"type": "text", "text": prompt}]
            for i, img_base64 in enumerate(images_base64):
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{img_base64}"
                    }
                })
            
            response = self.client.chat.completions.create(
                model="gpt-4o",  # Using gpt-4o for image processing
                messages=[
                    {"role": "system", "content": "You are a professional insurance document analyst. Extract information accurately from PDF documents converted to images."},
                    {"role": "user", "content": content}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            
            # Log response details
            print("OpenAI API RESPONSE (PDF):")
            print("=" * 60)
            print(f"Response length: {len(result_text)} characters")
            print(f"Usage: {response.usage}")
            print("\nResponse content:")
            print(result_text)
            print("=" * 60)
            
            # Extract buildings array from JSON response
            try:
                result = json.loads(result_text)
                if isinstance(result, dict) and 'buildings' in result:
                    return result['buildings']
                else:
                    print(f"Error: Expected 'buildings' key in response, got: {result}")
                    return []
            except Exception as json_error:
                print(f"JSON parsing error: {json_error}")
                print(f"Raw response text: {result_text}")
                return []
            
        except Exception as e:
            print(f"Error: OpenAI API call failed: {e}")
            return []
    
    def _extract_from_json(self) -> List[Dict[str, Any]]:
        """Extract information from JSON analysis results"""
        
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
- If Building Limit is not explicitly stated, use empty string
- Express amounts with $ symbol (e.g., $5,000)
- Use abbreviations for Valuation (e.g., RC, ACV)

Document summary:
{document_text}

Document details (first part):
{full_document[:10000]}

Please return information for each building in the following JSON object format:
{{
  "buildings": [
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
}}
"""

        try:
            # Log request details
            print("=" * 60)
            print("OpenAI API REQUEST (JSON):")
            print("=" * 60)
            print(f"Model: gpt-4o-mini")
            print(f"Temperature: 0.1")
            print(f"Response format: json_object")
            print("\nSystem message:")
            print("You are a professional insurance document analyst. Extract information accurately and respond as a JSON array.")
            print("\nUser prompt:")
            print(prompt[:1000] + "..." if len(prompt) > 1000 else prompt)
            print("\n" + "=" * 60)
            
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
            
            # Log response details
            print("OpenAI API RESPONSE:")
            print("=" * 60)
            print(f"Response length: {len(result_text)} characters")
            print(f"Usage: {response.usage}")
            print("\nResponse content:")
            print(result_text)
            print("=" * 60)
            
            # Extract buildings array from JSON response
            try:
                result = json.loads(result_text)
                if isinstance(result, dict) and 'buildings' in result:
                    return result['buildings']
                else:
                    print(f"Error: Expected 'buildings' key in response, got: {result}")
                    return []
            except Exception as json_error:
                print(f"JSON parsing error: {json_error}")
                print(f"Raw response text: {result_text}")
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
            input_path = Path(self.file_path)
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
        print("Usage: python parse_insurance_json.py <file_path>")
        print("Example: python parse_insurance_json.py loganpark_analysis.json")
        print("Example: python parse_insurance_json.py loganpark.pdf")
        print("\nNote: Please set OPENAI_API_KEY environment variable")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    # Check file existence
    if not Path(file_path).exists():
        print(f"Error: File '{file_path}' not found")
        sys.exit(1)
    
    # Check environment variable
    if not os.getenv('OPENAI_API_KEY'):
        print("Error: OPENAI_API_KEY environment variable is not set")
        print("Please run: export OPENAI_API_KEY='your-api-key'")
        sys.exit(1)
    
    # Execute extraction
    extractor = InsuranceDataExtractor(file_path)
    results = extractor.display_results_as_table()
    
    # Save in Markdown format
    extractor.export_to_markdown()
    
    # Return results (for calling from other programs)
    return results


if __name__ == "__main__":
    main()