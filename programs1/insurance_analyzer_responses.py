#!/usr/bin/env python3
import os
import sys
import argparse
from dotenv import load_dotenv
from openai import OpenAI
import base64
import pdfplumber

load_dotenv()

def analyze_insurance_document(file_path):
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file")
    
    client = OpenAI(api_key=api_key)
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    print(f"Analyzing insurance document: {file_path}")
    
    try:
        # Extract text from PDF or read text file
        if file_path.lower().endswith('.pdf'):
            # Extract text from PDF using pdfplumber
            pdf_text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pdf_text += text + "\n"
            
            print(f"Extracted text from PDF ({len(pdf_text)} characters)")
            file_content_text = pdf_text
        else:
            # Handle text files
            with open(file_path, 'rb') as file:
                file_content = file.read()
                file_content_text = file_content.decode('utf-8', errors='ignore')
            
        if not file_content_text.strip():
            print("No text content found in file")
            return None
            
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at analyzing insurance documents. Extract the insured building's address from the document. Return ONLY the complete address without any additional text or explanation."
                },
                {
                    "role": "user",
                    "content": f"Please analyze this insurance policy document and extract the insured building's address:\n\n{file_content_text}"
                }
            ],
            max_tokens=500
        )
        
        if response.choices and len(response.choices) > 0:
            address = response.choices[0].message.content.strip()
            print(f"\nInsured Building Address:")
            print(f"{address}")
            return address
        else:
            print("Failed to extract address from document")
            return None
    
    except Exception as e:
        print(f"Error analyzing document: {str(e)}")
        return None
    

def main():
    parser = argparse.ArgumentParser(description='Analyze insurance documents to extract insured building address')
    parser.add_argument('file_path', type=str, help='Path to the insurance document (PDF, TXT, etc.)')
    
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