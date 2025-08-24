#!/usr/bin/env python3
import os
import sys
import argparse
from dotenv import load_dotenv
from openai import OpenAI
import pdfplumber

load_dotenv()

def extract_text_from_pdf(file_path):
    """Extract text from PDF file using pdfplumber"""
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
    return text

def analyze_insurance_document(file_path):
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file")
    
    client = OpenAI(api_key=api_key)
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    print(f"Analyzing insurance document: {file_path}")
    
    try:
        # Extract text from PDF
        pdf_text = extract_text_from_pdf(file_path)
        
        if not pdf_text:
            print("Failed to extract text from PDF")
            return None
        
        print(f"Extracted {len(pdf_text)} characters from PDF")
        
        # Use Responses API directly with extracted text
        response = client.responses.create(
            model="gpt-4o",
            input=f"""You are an expert at analyzing insurance documents. 
            
Here is the text from an insurance policy document:

{pdf_text[:8000]}  # Limit to first 8000 characters to avoid token limits

Please extract the insured building's address from this insurance policy.
Look for the address of the insured property/building.
Search for terms like "Property Address", "Insured Property", "Location", "Premises", or similar.
Return ONLY the complete address without any additional text or explanation."""
        )
        
        # Extract address from response
        if response.output and len(response.output) > 0:
            for output in response.output:
                if hasattr(output, 'content'):
                    for content in output.content:
                        if hasattr(content, 'text'):
                            address = content.text
                            print(f"\n被保険建物の住所 (Insured Building Address):")
                            print(f"{address}")
                            return address
                elif hasattr(output, 'text'):
                    address = output.text
                    print(f"\n被保険建物の住所 (Insured Building Address):")
                    print(f"{address}")
                    return address
        
        print("Failed to extract address from document")
        return None
    
    except Exception as e:
        print(f"Error analyzing document: {str(e)}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Analyze insurance documents to extract insured building address using Responses API')
    parser.add_argument('file_path', type=str, help='Path to the insurance document (PDF)')
    
    args = parser.parse_args()
    
    try:
        address = analyze_insurance_document(args.file_path)
        if address:
            sys.exit(0)
        else:
            print("Failed to extract address from document")
            sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()