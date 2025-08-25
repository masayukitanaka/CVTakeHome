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
    
    def count_locations_and_buildings(self) -> Dict[str, Any]:
        """Count locations and buildings only using OpenAI - handles any format"""
        
        # For very large documents, we need to process in chunks and let OpenAI analyze
        full_content = self.markdown_content
        content_length = len(full_content)
        
        print(f"Document length: {content_length} characters")
        
        # With GPT-5's larger context window, we can handle much larger documents
        if content_length > 500000:
            # Split into very large chunks for GPT-5
            chunk_size = 400000
            overlap = 50000
            chunks = []
            
            for i in range(0, content_length, chunk_size - overlap):
                chunk = full_content[i:i + chunk_size]
                chunks.append(chunk)
            
            print(f"Split document into {len(chunks)} chunks for analysis")
            
            # Analyze each chunk and merge results
            all_locations = {}
            total_locations = 0
            total_buildings = 0
            
            for i, chunk in enumerate(chunks):
                print(f"⏳ Analyzing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
                chunk_result = self._count_in_chunk(chunk, i+1)
                print(f"✅ Chunk {i+1} completed")
                
                if chunk_result:
                    # Merge location data with smart location matching
                    for location, building_count in chunk_result.get('locations', {}).items():
                        # Normalize location names to handle different formats
                        normalized_location = self._normalize_location_name(location)
                        
                        if normalized_location in all_locations:
                            # Take the maximum count (most comprehensive analysis)
                            all_locations[normalized_location] = max(all_locations[normalized_location], building_count)
                        else:
                            all_locations[normalized_location] = building_count
            
            # Calculate totals
            total_locations = len(all_locations)
            total_buildings = sum(all_locations.values())
            
            return {
                "total_locations": total_locations,
                "locations": all_locations,
                "total_buildings": total_buildings
            }
        
        else:
            # For smaller documents, analyze directly
            return self._count_in_chunk(full_content, 1)
    
    def _normalize_location_name(self, location_name: str) -> str:
        """Normalize location names to handle different formats from different chunks"""
        import re
        
        # Convert to lowercase for comparison
        name = location_name.lower().strip()
        
        # Extract location number using regex
        # Matches patterns like: location_1, location_0001, premises_1, premises_0001, location 1, etc.
        patterns = [
            r'location[_\s]*(\d+)',
            r'premises[_\s]*(\d+)', 
            r'property[_\s]*(\d+)',
            r'site[_\s]*(\d+)',
            r'building[_\s]*(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, name)
            if match:
                location_num = int(match.group(1))
                return f"Location_{location_num}"
        
        # If no pattern matches, return original name capitalized
        return location_name.strip().replace(' ', '_').title()
    
    def _count_in_chunk(self, content: str, chunk_num: int) -> Dict[str, Any]:
        """Count locations and buildings in a single chunk of content"""
        
        prompt = f"""
Please analyze this insurance document (chunk {chunk_num}) and COUNT locations and buildings.

TASK: Count the number of distinct insurance locations and buildings/properties mentioned in this document content.

IMPORTANT: This is a flexible analysis - look for ANY way that locations and buildings/properties are indicated in the document, such as:
- Numbered locations (Location 1, Location 2, etc.)
- Premises numbers (Premises 001, Premises 002, etc.)  
- Property addresses (different street addresses)
- Building designations (Building A, Building B, etc.)
- Property schedules or lists
- Coverage declarations by location
- Any other indication of separate insured properties or locations

INSTRUCTIONS:
1. Identify how many distinct LOCATIONS/PROPERTIES are mentioned
2. For each location, count how many distinct BUILDINGS/STRUCTURES exist
3. If buildings aren't explicitly mentioned per location, assume 1 building per location
4. Use flexible naming (Location_1, Location_2 or Premises_1, Premises_2, etc.)

Return ONLY a JSON object with counts:
{{
  "total_locations": number,
  "locations": {{
    "Location_1": number_of_buildings,
    "Location_2": number_of_buildings,
    "Location_3": number_of_buildings
  }},
  "total_buildings": total_number_across_all_locations
}}

DOCUMENT CONTENT TO ANALYZE:
{content[:50000]}

IMPORTANT: Return only valid JSON. Count flexibly based on ANY indication of separate insured properties or locations in the document.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an insurance document analyst. Count locations and buildings flexibly from any insurance document format and return only JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            print(f"Chunk {chunk_num} result: {result_text}")
            
            # Parse and return count result
            try:
                count_result = json.loads(result_text)
                return count_result
            except json.JSONDecodeError as e:
                print(f"JSON parsing error in chunk {chunk_num}: {e}")
                return {}
                
        except Exception as e:
            print(f"Error in counting chunk {chunk_num}: {e}")
            return {}
    
    def extract_detailed_info_by_location(self, count_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract detailed information for each location based on count results"""
        
        all_buildings = []
        locations = count_result.get('locations', {})
        
        print(f"\n🔍 PHASE 2: Extracting detailed information for {len(locations)} locations...")
        
        for location_key, building_count in locations.items():
            print(f"\nProcessing {location_key} with {building_count} buildings...")
            
            # Extract content related to this specific location
            location_content = self._extract_location_content(location_key)
            
            if not location_content:
                print(f"⚠️  No content found for {location_key}")
                continue
            
            # Extract detailed information for this location
            location_buildings = self._extract_location_details(location_key, location_content, building_count)
            all_buildings.extend(location_buildings)
            
        return all_buildings
    
    def _extract_location_content(self, location_key: str) -> str:
        """Extract content related to a specific location from the full document"""
        
        # Create flexible location patterns based on the location key
        patterns = []
        
        if "Location_" in location_key:
            loc_num = location_key.split("_")[1]
            patterns = [
                f"location {loc_num}",
                f"location 000{loc_num}",
                f"premises {loc_num}",
                f"premises 000{loc_num}",
                f"building {loc_num}",
                f"property {loc_num}"
            ]
        
        lines = self.markdown_content.split('\n')
        location_lines = []
        in_location_section = False
        
        for line in lines:
            line_lower = line.lower()
            
            # Check if this line relates to our location
            is_location_line = any(pattern in line_lower for pattern in patterns)
            
            if is_location_line:
                in_location_section = True
                location_lines.append(line)
            elif in_location_section:
                # Continue collecting lines until we hit a different location
                if any(f"location {other}" in line_lower or f"premises {other}" in line_lower 
                      for other in ['1', '2', '3', '4', '5'] if other != loc_num):
                    in_location_section = False
                else:
                    location_lines.append(line)
            
            # Also include lines with coverage information
            if any(keyword in line_lower for keyword in [
                'coverage', 'limit', 'deductible', 'valuation', 'premium',
                'building limit', 'personal property', 'business income'
            ]):
                location_lines.append(line)
        
        # Limit content size for GPT-5's larger context window
        content = '\n'.join(location_lines)
        if len(content) > 150000:
            content = content[:150000]
            
        return content
    
    def _extract_location_details(self, location_key: str, location_content: str, building_count: int) -> List[Dict[str, Any]]:
        """Extract detailed insurance information for a specific location"""
        
        prompt = f"""
Please extract detailed insurance information for {location_key}.

Based on my analysis, this location should have {building_count} buildings/properties.

Extract the following information for EACH building in this location:

1. Location/Building identifier (use format like "{location_key} Building 1", "{location_key} Building 2", etc.)
2. Address: Complete physical address if available
3. Building Limit: Building coverage limit amount (empty string if not found)
4. Personal Property Limit: Business Personal Property coverage limit
5. Business Income: Business Income and Extra Expense limit (empty string if not found)
6. Deductible: Property coverage deductible amount
7. Valuation: RC (Replacement Cost), ACV (Actual Cash Value), etc.

IMPORTANT GUIDELINES:
- Create {building_count} separate building entries for this location
- If specific building details aren't available, use the location's general coverage information for all buildings
- Express amounts with $ symbol (e.g., $5,000)
- Use actual values from the document
- If building-specific addresses aren't available, use the location's general address

DOCUMENT CONTENT FOR {location_key}:
{location_content}

Return JSON with exactly {building_count} building entries:
{{
  "buildings": [
    {{
      "location_building": "{location_key} Building 1",
      "address": "actual address or empty string",
      "building_limit": "amount or empty string",
      "personal_property_limit": "amount",
      "business_income": "amount or empty string",
      "deductible": "amount",
      "valuation": "RC/ACV/etc"
    }}
  ]
}}
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an insurance document analyst. Extract detailed property insurance information accurately."
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            
            try:
                result = json.loads(result_text)
                buildings = result.get('buildings', [])
                
                print(f"✅ Extracted {len(buildings)} buildings for {location_key}")
                return buildings
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing error for {location_key}: {e}")
                return []
                
        except Exception as e:
            print(f"❌ Error extracting details for {location_key}: {e}")
            return []

    def extract_with_openai(self) -> List[Dict[str, Any]]:
        """Extract insurance information using OpenAI API (legacy method)"""
        
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
                model="gpt-5",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a professional insurance document analyst specializing in property coverage analysis. Extract information accurately from Markdown-formatted insurance documents and return valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
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
    
    def extract_all_with_counting(self) -> List[Dict[str, Any]]:
        """Extract all insurance information using two-phase approach"""
        print("\n🔍 Starting two-phase analysis...")
        
        # Phase 1: Count locations and buildings
        count_result = self.count_locations_and_buildings()
        
        if not count_result:
            print("❌ Phase 1 failed - could not count locations and buildings")
            return []
        
        # Validate counts
        expected_total = 104  # 37+60+6+1 from user
        actual_total = count_result.get('total_buildings', 0)
        
        print(f"\n📊 COUNT VALIDATION:")
        print(f"Expected total buildings: {expected_total}")
        print(f"Actual total buildings: {actual_total}")
        
        if actual_total != expected_total:
            print(f"⚠️  Count mismatch detected!")
            print(f"Expected: Location 1=37, Location 2=60, Location 3=6, Location 4=1")
            print(f"Actual breakdown:")
            for loc, count in count_result.get('locations', {}).items():
                print(f"  {loc}: {count} buildings")
        
        # Phase 2: Extract detailed information based on counts
        print(f"\n🔄 Phase 2: Extracting detailed information for {actual_total} buildings...")
        results = self.extract_detailed_info_by_location(count_result)
        
        # Validate final result count
        if len(results) != actual_total:
            print(f"⚠️  Extraction count mismatch!")
            print(f"Expected {actual_total} records, got {len(results)} records")
        
        self.extracted_info = results
        return self.extracted_info
    
    def extract_all(self) -> List[Dict[str, Any]]:
        """Extract all insurance information (backward compatibility)"""
        return self.extract_all_with_counting()
    
    def display_results_as_table(self):
        """Display extraction results as simple Markdown table (like example.md)"""
        results = self.extract_all()
        
        # Always display table header, even if no results
        print("| Location/ Premises Number, Building Number | Addresses | Building | Personal Property | Business Income | Deductible | Valuation |")
        print("|--------------------------------------------|-----------|---------:| -----------------:| ---------------:| ----------:| ---------:|")
        
        if not results:
            # Return results (empty list) even when no information is extracted
            return results
        
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
            # Always write table header, even if no results
            f.write("| Location/ Premises Number, Building Number | Addresses | Building | Personal Property | Business Income | Deductible | Valuation |\n")
            f.write("|--------------------------------------------|-----------|---------:| -----------------:| ---------------:| ----------:| ---------:|\n")
            
            if not results:
                # Return output file path even when no information is extracted
                return output_file
            
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
        print("Usage: python parse_insurance_markdown.py <markdown_file> [--count-only]")
        print("Example: python parse_insurance_markdown.py loganpark_converted.md")
        print("         python parse_insurance_markdown.py loganpark_converted.md --count-only")
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