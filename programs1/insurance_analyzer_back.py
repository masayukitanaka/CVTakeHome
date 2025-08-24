#!/usr/bin/env python3
import os
import sys
import argparse
from dotenv import load_dotenv
from openai import OpenAI

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
        # Upload file for file_search
        with open(file_path, 'rb') as file:
            file_obj = client.files.create(
                file=file,
                purpose='assistants'
            )
        print(f"File uploaded successfully. File ID: {file_obj.id}")
        
        # Create vector store
        vector_store = client.vector_stores.create(
            name="Insurance Documents"
        )
        print(f"Vector store created. ID: {vector_store.id}")
        
        # Add file to vector store
        vector_store_file = client.vector_stores.files.create(
            vector_store_id=vector_store.id,
            file_id=file_obj.id
        )
        print(f"File added to vector store")
        
        # Wait for file to be processed
        import time
        while vector_store_file.status == "in_progress":
            time.sleep(1)
            vector_store_file = client.vector_stores.files.retrieve(
                vector_store_id=vector_store.id,
                file_id=file_obj.id
            )
        
        if vector_store_file.status != "completed":
            raise Exception(f"File processing failed: {vector_store_file.status}")
        
        # Use the new Responses API with file_search
        response = client.responses.create(
            model="gpt-4o",
            input="""You are an expert at analyzing insurance documents. 
            Please search through the uploaded insurance policy document and extract the insured building's address.
            Look for the address of the insured property/building in the document.
            Search for terms like "Property Address", "Insured Property", "Location", "Premises", or similar.
            Return ONLY the complete address without any additional text or explanation.""",
            tools=[
                {
                    "type": "file_search",
                    "vector_store_ids": [vector_store.id]
                }
            ]
        )
        
        # Extract address from response
        if response.output and len(response.output) > 0:
            # Handle different output types
            for output in response.output:
                if hasattr(output, 'content'):
                    for content in output.content:
                        if hasattr(content, 'text'):
                            address = content.text
                            print(f"\nInsured Building Address:")
                            print(f"{address}")
                            return address
                elif hasattr(output, 'text'):
                    address = output.text
                    print(f"\nInsured Building Address:")
                    print(f"{address}")
                    return address
        
        # If no text found, print the response for debugging
        print(f"Response output: {response.output}")
        print("Failed to extract address from document")
        return None
    
    except Exception as e:
        print(f"Error analyzing document: {str(e)}")
        return None
    
    finally:
        # Cleanup resources
        try:
            if 'file_obj' in locals():
                client.files.delete(file_obj.id)
                print(f"\nCleaned up: Deleted uploaded file {file_obj.id}")
        except:
            pass
        
        try:
            if 'vector_store' in locals():
                client.vector_stores.delete(vector_store.id)
                print(f"Cleaned up: Deleted vector store {vector_store.id}")
        except:
            pass

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