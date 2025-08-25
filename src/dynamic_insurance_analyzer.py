#!/usr/bin/env python3
"""
Dynamic Insurance Certificate Markdown Analysis Parser using OpenAI API

This program analyzes insurance documents that have been converted to Markdown format
and dynamically extracts all insurance information, including new terms not previously known.
The program adapts to different schedule formats and coverage types.

Key Features:
- Dynamic discovery of new insurance terms and coverages
- Flexible output format that adapts to document structure
- Comprehensive extraction of all coverage types and limits
- Automatic generation of markdown tables with all discovered terms

Output format: Adaptive Markdown table with all discovered columns
"""

import json
import sys
import os
from typing import Dict, Any, List, Set
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()


class DynamicInsuranceAnalyzer:
    """Dynamic Insurance Markdown document analysis class using OpenAI API"""
    
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
        self.discovered_terms = set()
    
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
        
        # Keywords that indicate relevant sections (expanded for dynamic discovery)
        relevant_keywords = [
            'property coverage', 'business income', 'liability coverage',
            'declarations', 'premises', 'address', 'coverage', 'limits',
            'deductible', 'valuation', 'location summary', 'location',
            'premium', 'buildings', 'personal property', 'quote number',
            'street', 'city', 'state', 'zip', 'schedule', 'endorsement',
            'form', 'policy', 'insured', 'aggregate', 'occurrence',
            'retention', 'coinsurance', 'blanket', 'specific', 'sublimit',
            'equipment breakdown', 'ordinance', 'law', 'terrorism',
            'cyber', 'crime', 'fidelity', 'umbrella', 'excess',
            'workers compensation', 'auto', 'general liability'
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
            
            # Include table lines (likely to contain coverage information)
            elif '|' in line and line.strip().startswith('|'):
                relevant_sections.append(line)
        
        # Add the last section if relevant
        if in_relevant_section and current_section:
            relevant_sections.extend(current_section)
        
        result = '\n'.join(relevant_sections)
        return result
    
    def discover_terms_with_openai(self) -> Set[str]:
        """First pass: Discover all insurance terms and coverage types in the document"""
        
        # Get relevant sections of the document
        relevant_content = self._extract_relevant_sections()
        
        # Truncate if content is too large
        if len(relevant_content) > 15000:
            relevant_content = relevant_content[:15000]
        
        discovery_prompt = f"""
Analyze this insurance document and discover ALL insurance terms, coverage types, and financial amounts mentioned.

Your task is to identify every unique insurance-related term that appears in schedules, tables, or coverage sections. Look for:
- Coverage types (Building, Personal Property, Business Income, Equipment Breakdown, etc.)
- Financial terms (Limits, Deductibles, Premiums, Retentions, Coinsurance, etc.)
- Policy terms (Valuation, Territory, Protection Class, etc.)
- Location identifiers (Premises, Location, Building numbers, etc.)
- Any other insurance-specific terms with associated values

DOCUMENT CONTENT TO ANALYZE:
{relevant_content}

Return a JSON object with discovered terms:
{{
  "coverage_terms": [
    "Building",
    "Personal Property", 
    "Business Income",
    "Equipment Breakdown",
    "General Liability",
    "etc..."
  ],
  "financial_terms": [
    "Limit",
    "Deductible", 
    "Premium",
    "Retention",
    "Coinsurance",
    "etc..."
  ],
  "property_terms": [
    "Valuation",
    "Territory",
    "Protection Class",
    "Construction",
    "Occupancy",
    "etc..."
  ],
  "location_terms": [
    "Premises",
    "Location", 
    "Building",
    "Address",
    "etc..."
  ]
}}

IMPORTANT: Return only valid JSON. Include ALL terms you find, even if they're uncommon or specialized.
"""

        try:
            print("=" * 80)
            print("DISCOVERING INSURANCE TERMS...")
            print("=" * 80)
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a comprehensive insurance document analyst who discovers and categorizes all insurance terms in documents."
                    },
                    {"role": "user", "content": discovery_prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            print(f"Discovery result: {result_text}")
            print("=" * 80)
            
            # Parse discovered terms
            try:
                result = json.loads(result_text)
                all_terms = set()
                for category in result.values():
                    if isinstance(category, list):
                        all_terms.update(category)
                
                self.discovered_terms = all_terms
                return all_terms
                
            except json.JSONDecodeError:
                print("Failed to parse discovery results, using default terms")
                return {"Building", "Personal Property", "Business Income", "Deductible", "Valuation"}
            
        except Exception as e:
            print(f"Error during term discovery: {e}")
            return {"Building", "Personal Property", "Business Income", "Deductible", "Valuation"}
    
    def extract_with_dynamic_openai(self, discovered_terms: Set[str]) -> List[Dict[str, Any]]:
        """Extract insurance information dynamically based on discovered terms"""
        
        # Get relevant sections of the document
        relevant_content = self._extract_relevant_sections()
        
        # Truncate if content is too large
        if len(relevant_content) > 15000:
            sections = relevant_content.split('\n\n')
            priority_sections = []
            regular_sections = []
            
            for section in sections:
                section_lower = section.lower()
                if any(keyword in section_lower for keyword in ['property coverage', 'business income', 'premises', 'location', 'schedule']):
                    priority_sections.append(section)
                else:
                    regular_sections.append(section)
            
            combined_sections = priority_sections + regular_sections
            relevant_content = '\n\n'.join(combined_sections[:20])
        
        # Convert discovered terms to dynamic extraction requirements
        terms_list = sorted(list(discovered_terms))
        
        dynamic_prompt = f"""
Analyze this insurance document and extract comprehensive insurance information for all buildings/properties.

DYNAMIC EXTRACTION REQUIREMENTS:
Based on document analysis, extract the following information for ALL locations/properties:

STANDARD FIELDS (always include):
1. Location/Premises/Building Number: Actual designation from document
2. Address: Complete physical address as stated in document

DISCOVERED TERMS TO EXTRACT:
{chr(10).join([f'{i+3}. {term}: Extract any values, amounts, or details for this term' for i, term in enumerate(terms_list)])}

CRITICAL ANALYSIS GUIDELINES:
- EXTRACT ALL LOCATIONS: Look for location summaries, address tables, or multiple property entries
- DISTINGUISH between different coverage types and their limits
- Extract ACTUAL values from the document - do not assume or guess
- If a term appears in the document but has no associated value, use empty string
- Create separate entries for each distinct location/address found
- Express monetary amounts with $ symbol where applicable

DOCUMENT CONTENT TO ANALYZE:
{relevant_content}

Please return extracted information in JSON format with dynamic fields based on discovered terms:
{{
  "buildings": [
    {{
      "location_building": "actual designation from document",
      "address": "actual address from document",
{chr(10).join([f'      "{term.lower().replace(" ", "_")}": "actual value or empty string",' for term in terms_list])}
    }}
  ]
}}

IMPORTANT: 
- Return only valid JSON
- Use actual values found in the document
- Create separate entries for each distinct location
- Include all discovered terms, even if some locations don't have values for certain terms
"""

        try:
            print("EXTRACTING INSURANCE INFORMATION WITH DYNAMIC TERMS...")
            print(f"Discovered terms: {', '.join(sorted(terms_list))}")
            print("=" * 80)
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a professional insurance document analyst who extracts comprehensive insurance information with dynamic field discovery."
                    },
                    {"role": "user", "content": dynamic_prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            print(f"Extraction result:")
            print(result_text)
            print("=" * 80)
            
            # Parse JSON response
            try:
                result = json.loads(result_text)
                if isinstance(result, dict) and 'buildings' in result:
                    return result['buildings']
                else:
                    return []
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                return []
            
        except Exception as e:
            print(f"Error: OpenAI API call failed: {e}")
            return []
    
    def extract_all_dynamic(self) -> List[Dict[str, Any]]:
        """Extract all insurance information dynamically"""
        # First, discover all terms in the document
        discovered_terms = self.discover_terms_with_openai()
        
        # Then extract information using discovered terms
        results = self.extract_with_dynamic_openai(discovered_terms)
        self.extracted_info = results
        return self.extracted_info
    
    def display_dynamic_results_as_table(self):
        """Display extraction results as dynamic Markdown table with Term | Value format"""
        results = self.extract_all_dynamic()
        
        if not results:
            print("| Term | Value |")
            print("|------|-------|")
            return results
        
        # Standard fields to exclude (covered by other programs)
        excluded_fields = {
            'address', 'building_limit', 'personal_property_limit', 'business_income',
            'primary_deductible', 'deductible', 'valuation', 'building', 'personal_property'
        }
        
        print("| Term | Value |")
        print("|------|-------|")
        
        # Display each building separately with all its terms
        for i, building in enumerate(results):
            # Building separator
            if i > 0:
                print("|------|-------|")
            
            # Display all terms for this building, excluding standard fields
            for key, value in sorted(building.items()):
                # Skip excluded fields
                if key.lower() in excluded_fields:
                    continue
                    
                # Format key for display
                display_key = key.replace('_', ' ').title()
                display_value = str(value) if value else ""
                
                print(f"| {display_key} | {display_value} |")
        
        return results
    
    def export_dynamic_to_markdown(self, output_file: str = None):
        """Export results to Markdown file with Term | Value format"""
        results = self.extracted_info
        
        if output_file is None:
            input_path = Path(self.markdown_path)
            output_file = str(input_path.parent / f"{input_path.stem}_dynamic_insurance_analysis.md")
        
        # Standard fields to exclude (covered by other programs)
        excluded_fields = {
            'address', 'building_limit', 'personal_property_limit', 'business_income',
            'primary_deductible', 'deductible', 'valuation', 'building', 'personal_property'
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            
            if not results:
                f.write("| Term | Value |\n")
                f.write("|---------|-------|\n")
                return output_file
            
            f.write("| Term | Value |\n")
            f.write("|------|-------|\n")
            
            # Write each building separately with all its terms, excluding standard fields
            for i, building in enumerate(results):
                # Building separator
                if i > 0:
                    f.write("|------|-------|\n")
                
                # Write all terms for this building, excluding standard fields
                for key, value in sorted(building.items()):
                    # Skip excluded fields
                    if key.lower() in excluded_fields:
                        continue
                        
                    # Format key for display
                    display_key = key.replace('_', ' ').title()
                    display_value = str(value) if value else ""
                    
                    f.write(f"| {display_key} | {display_value} |\n")
        
        return output_file


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python dynamic_insurance_analyzer.py <markdown_file>")
        print("Example: python dynamic_insurance_analyzer.py ../programs5/Commercial_Extra_Terms_converted.md")
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
        # Execute dynamic analysis
        analyzer = DynamicInsuranceAnalyzer(markdown_file)
        results = analyzer.display_dynamic_results_as_table()
        
        # Save results to Markdown file
        output_file = analyzer.export_dynamic_to_markdown()
        print(f"\nResults saved to: {output_file}")
        
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