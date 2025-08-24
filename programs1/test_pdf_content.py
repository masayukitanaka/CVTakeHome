#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from openai import OpenAI
import time

load_dotenv()

def test_pdf_search(file_path):
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file")
    
    client = OpenAI(api_key=api_key)
    
    print(f"Testing PDF: {file_path}")
    
    try:
        # Upload file
        with open(file_path, 'rb') as file:
            file_obj = client.files.create(
                file=file,
                purpose='assistants'
            )
        print(f"File uploaded: {file_obj.id}")
        
        # Create vector store
        vector_store = client.vector_stores.create(
            name="Test PDF"
        )
        print(f"Vector store created: {vector_store.id}")
        
        # Add file to vector store
        vector_store_file = client.vector_stores.files.create(
            vector_store_id=vector_store.id,
            file_id=file_obj.id
        )
        print(f"File added to vector store")
        
        # Wait for processing
        while vector_store_file.status == "in_progress":
            time.sleep(1)
            vector_store_file = client.vector_stores.files.retrieve(
                vector_store_id=vector_store.id,
                file_id=file_obj.id
            )
            print(f"Processing status: {vector_store_file.status}")
        
        if vector_store_file.status != "completed":
            print(f"Processing failed: {vector_store_file.status}")
            if hasattr(vector_store_file, 'last_error'):
                print(f"Error: {vector_store_file.last_error}")
            return
        
        print("File processing completed successfully")
        
        # Test search with explicit query
        response = client.responses.create(
            model="gpt-4o",
            input="""Search the document for any of these terms and return what you find:
            - "807 Broadway"
            - "Minneapolis"
            - "Property Address"
            - "Insured Property"
            - "Location"
            
            Also, list the first 5 lines of text you can find in the document.""",
            tools=[
                {
                    "type": "file_search",
                    "vector_store_ids": [vector_store.id]
                }
            ]
        )
        
        print("\n=== Response Output ===")
        if response.output:
            for i, output in enumerate(response.output):
                print(f"\nOutput {i}: {output}")
                if hasattr(output, 'content'):
                    for j, content in enumerate(output.content):
                        print(f"  Content {j}: {content}")
                        if hasattr(content, 'text'):
                            print(f"    Text: {content.text}")
        
        # Cleanup
        client.files.delete(file_obj.id)
        client.vector_stores.delete(vector_store.id)
        print("\nCleaned up resources")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_pdf_search("../documents/loganpark.pdf")