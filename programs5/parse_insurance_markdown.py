#!/usr/bin/env python3
"""
Insurance certificate Markdown analysis parser using OpenAI API

This program analyzes insurance documents that have been converted to Markdown format
and extracts key insurance information using OpenAI's GPT models.

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
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()


class InsuranceMarkdownAnalyzer:
    """Insurance Markdown document analysis class using OpenAI API"""
    
    def __init__(self, markdown_path: str):
        """
        Initialize the analyzer
        
        Args:
            markdown_path: Path to the Markdown file to analyze
        """
        self.markdown_path = markdown_path
        self.markdown_content = self._load_markdown()
        
        # Initialize OpenAI API client
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("Error: OPENAI_API_KEY environment variable is not set")
            print("Please set the environment variable")
            print("Example: export OPENAI_API_KEY='sk-...'")
            sys.exit(1)
        
        self.client = OpenAI(api_key=api_key)
        self.extracted_info = []
    
    def _load_markdown(self) -> str:
        """Load Markdown file content"""
        try:
            with open(self.markdown_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return content
        except FileNotFoundError:
            print(f"Error: File '{self.markdown_path}' not found")
            sys.exit(1)
        except Exception as e:
            print(f"Error: Failed to read Markdown file: {e}")
            sys.exit(1)
    
    def _extract_relevant_sections(self) -> str:
        """Extract relevant sections from Markdown content for analysis"""
        lines = self.markdown_content.split('\n')
        relevant_sections = []
        
        # Track if we're in a relevant section
        in_relevant_section = False
        current_section = []
        
        # Keywords that indicate relevant sections
        relevant_keywords = [
            'property coverage', 'business income', 'liability coverage',
            'declarations', 'premises', 'address', 'coverage', 'limits',
            'deductible', 'valuation', 'location summary', 'location',
            'premium', 'buildings', 'personal property', 'quote number',
            'street', 'city', 'state', 'zip'
        ]
        
        for line in lines:
            line_lower = line.lower()
            
            # Check if line starts a new section (starts with #)
            if line.startswith('#'):
                # Save previous section if it was relevant
                if in_relevant_section and current_section:
                    relevant_sections.extend(current_section)
                    relevant_sections.append("")  # Section separator
                
                # Check if new section is relevant
                in_relevant_section = any(keyword in line_lower for keyword in relevant_keywords)
                current_section = [line] if in_relevant_section else []
                
            elif in_relevant_section:
                current_section.append(line)
                
            # Also include lines with relevant keywords regardless of section
            elif any(keyword in line_lower for keyword in relevant_keywords):
                relevant_sections.append(line)
        
        # Add the last section if relevant
        if in_relevant_section and current_section:
            relevant_sections.extend(current_section)
        
        result = '\n'.join(relevant_sections)
        return result
    
    def extract_with_openai(self) -> List[Dict[str, Any]]:
        """Extract insurance information using OpenAI API"""
        
        # Get relevant sections of the document
        relevant_content = self._extract_relevant_sections()
        
        # If relevant content is too large, truncate but keep key sections
        if len(relevant_content) > 15000:
            # Split into sections and prioritize property coverage sections
            sections = relevant_content.split('\n\n')
            priority_sections = []
            regular_sections = []
            
            for section in sections:
                section_lower = section.lower()
                if any(keyword in section_lower for keyword in ['property coverage', 'business income', 'premises', 'broadway']):
                    priority_sections.append(section)
                else:
                    regular_sections.append(section)
            
            # Reconstruct with priority sections first
            combined_sections = priority_sections + regular_sections
            relevant_content = '\n\n'.join(combined_sections[:20])  # Limit to 20 sections
        
        prompt = f"""
Please analyze this insurance document in Markdown format and extract comprehensive insurance information for all buildings/properties.

The document appears to be a business owner's policy with both property coverage and liability coverage. I need you to extract the following specific information for ALL locations/properties mentioned in the document:

EXTRACTION REQUIREMENTS:
1. Location/Premises Number, Building Number: Find actual premises/location and building numbers from the document
2. Address: Complete physical address of the insured property as stated in the document  
3. Building Limit: Building coverage limit amount - this is the maximum insurance amount for the physical building structure itself (NOT liability coverage)
4. Personal Property Limit: Business Personal Property coverage limit amount
5. Business Income: Business Income and Extra Expense coverage limit amount (leave empty string if not found)
6. Deductible: Property coverage deductible amount (for Property coverage, not Liability)
7. Valuation: Type of valuation like "RC" (Replacement Cost) or "ACV" (Actual Cash Value)

CRITICAL ANALYSIS GUIDELINES:
- EXTRACT ALL LOCATIONS: Look for location summaries, address tables, or multiple property entries
- DISTINGUISH between PROPERTY COVERAGE and LIABILITY COVERAGE:
  * PROPERTY COVERAGE: Covers physical buildings, business personal property, business income
  * LIABILITY COVERAGE: Covers legal liability, medical expenses, bodily injury
- For Building Limit: Look specifically for:
  * Building coverage in PROPERTY COVERAGE sections
  * "Building" coverage limits in property declarations tables
  * Physical structure coverage amounts
  * DO NOT use Liability coverage amounts
- Focus on BUSINESSOWNERS PROPERTY COVERAGE PART DECLARATIONS or similar property coverage sections
- Extract the ACTUAL addresses found in the document - do not assume or guess addresses
- Express amounts with $ symbol
- Use standard abbreviations for Valuation (RC for Replacement Cost, ACV for Actual Cash Value)
- If Building Limit is not explicitly stated in property coverage sections, use empty string
- If multiple locations share the same coverage amounts, create separate entries for each location

DOCUMENT CONTENT TO ANALYZE:
{relevant_content}

Please return the extracted information in the following JSON format with separate entries for each location:
{{
  "buildings": [
    {{
      "location_building": "Location 1 Building 1",
      "address": "actual address for location 1",
      "building_limit": "actual amount or empty string if not found",
      "personal_property_limit": "actual amount",
      "business_income": "actual amount or empty string if not found", 
      "deductible": "actual deductible amount",
      "valuation": "actual valuation type from document"
    }},
    {{
      "location_building": "Location 2 Building 1", 
      "address": "actual address for location 2",
      "building_limit": "actual amount or empty string if not found",
      "personal_property_limit": "actual amount",
      "business_income": "actual amount or empty string if not found",
      "deductible": "actual deductible amount", 
      "valuation": "actual valuation type from document"
    }}
  ]
}}

IMPORTANT: Return only valid JSON. Use actual values found in the document. Create separate entries for each distinct location/address found. Be very careful to distinguish between property coverage limits and liability coverage limits.
"""

        try:
            # Log request details
            print("=" * 80)
            print("OpenAI API REQUEST:")
            print("=" * 80)
            print(f"Model: gpt-4o")
            print(f"Temperature: 0.1")
            print(f"Response format: json_object")
            print(f"Content length: {len(relevant_content)} characters")
            print("\nSystem message:")
            print("You are a professional insurance document analyst specializing in property coverage analysis.")
            print("\nUser prompt:")
            print(prompt)
            print("=" * 80)
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a professional insurance document analyst specializing in property coverage analysis. Extract information accurately from Markdown-formatted insurance documents and return valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            
            # Log response details
            print("\nOPENAI API RESPONSE:")
            print("=" * 80)
            print(f"Response content:")
            print(result_text)
            print("=" * 80)
            
            # Parse JSON response and extract buildings array
            try:
                result = json.loads(result_text)
                print(f"\nParsed JSON result:")
                print(json.dumps(result, indent=2))
                print("=" * 80)
                
                if isinstance(result, dict) and 'buildings' in result:
                    buildings = result['buildings']
                    return buildings
                else:
                    return []
            except json.JSONDecodeError as e:
                print(f"\nJSON parsing error: {e}")
                print("=" * 80)
                return []
            
        except Exception as e:
            print(f"Error: OpenAI API call failed: {e}")
            return []
    
    def extract_all(self) -> List[Dict[str, Any]]:
        """Extract all insurance information"""
        results = self.extract_with_openai()
        self.extracted_info = results
        return self.extracted_info
    
    def display_results_as_table(self):
        """Display extraction results as simple Markdown table (like example.md)"""
        results = self.extract_all()
        
        if not results:
            print("No information extracted.")
            return results
        
        # Simple table format matching example.md
        print("| Location/ Premises Number, Building Number | Addresses | Building | Personal Property | Business Income | Deductible | Valuation |")
        print("|--------------------------------------------|-----------|---------:| -----------------:| ---------------:| ----------:| ---------:|")
        
        # Display information for each building
        for i, building in enumerate(results, 1):
            location = building.get('location_building', f'Building {i}')
            address = building.get('address', '')
            building_limit = building.get('building_limit', '')
            personal_property = building.get('personal_property_limit', '')
            business_income = building.get('business_income', '')
            deductible = building.get('deductible', '')
            valuation = building.get('valuation', '')
            
            print(f"| {location:<42} | {address:<9} | {building_limit:>8} | {personal_property:>17} | {business_income:>15} | {deductible:>10} | {valuation:>9} |")
        
        return results
    
    def export_to_markdown(self, output_file: str = None):
        """Export results to Markdown file (simple format like example.md)"""
        results = self.extracted_info
        
        if output_file is None:
            # Generate default filename
            input_path = Path(self.markdown_path)
            output_file = str(input_path.parent / f"{input_path.stem}_insurance_analysis.md")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            if not results:
                f.write("No information extracted.\n")
                return output_file
            
            # Simple table format like example.md
            f.write("| Location/ Premises Number, Building Number | Addresses | Building | Personal Property | Business Income | Deductible | Valuation |\n")
            f.write("|--------------------------------------------|-----------|---------:| -----------------:| ---------------:| ----------:| ---------:|\n")
            
            for i, building in enumerate(results, 1):
                location = building.get('location_building', f'Building {i}')
                address = building.get('address', '')
                building_limit = building.get('building_limit', '') 
                personal_property = building.get('personal_property_limit', '')
                business_income = building.get('business_income', '')
                deductible = building.get('deductible', '')
                valuation = building.get('valuation', '')
                
                f.write(f"| {location} | {address} | {building_limit} | {personal_property} | {business_income} | {deductible} | {valuation} |\n")
        
        return output_file
    


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python parse_insurance_markdown.py <markdown_file>")
        print("Example: python parse_insurance_markdown.py loganpark_converted.md")
        print("\nNote: Please set OPENAI_API_KEY environment variable")
        sys.exit(1)
    
    markdown_file = sys.argv[1]
    
    # Check file existence
    if not Path(markdown_file).exists():
        print(f"Error: File '{markdown_file}' not found")
        sys.exit(1)
    
    # Check if it's a Markdown file
    if not markdown_file.lower().endswith('.md'):
        print(f"Warning: File '{markdown_file}' does not have .md extension")
        print("Proceeding anyway, but ensure this is a Markdown file...")
    
    # Check environment variable
    if not os.getenv('OPENAI_API_KEY'):
        print("Error: OPENAI_API_KEY environment variable is not set")
        print("Please run: export OPENAI_API_KEY='your-api-key'")
        sys.exit(1)
    
    try:
        # Execute analysis
        analyzer = InsuranceMarkdownAnalyzer(markdown_file)
        results = analyzer.display_results_as_table()
        
        # Save results to Markdown file
        analyzer.export_to_markdown()
        
        # Return results (for calling from other programs)
        return results
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()