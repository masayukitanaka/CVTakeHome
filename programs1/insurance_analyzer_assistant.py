#!/usr/bin/env python3
import os
import sys
import argparse
import warnings
from dotenv import load_dotenv
from openai import OpenAI

# Suppress deprecation warnings for Assistant API
warnings.filterwarnings("ignore", category=DeprecationWarning)

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
        # Upload file to OpenAI
        with open(file_path, 'rb') as file:
            file_obj = client.files.create(
                file=file,
                purpose='assistants'
            )
        print(f"File uploaded successfully. File ID: {file_obj.id}")
        
        # Create assistant with file_search tool
        assistant = client.beta.assistants.create(
            name="Insurance Document Analyzer",
            instructions="You are an expert at analyzing insurance documents. Extract the insured building's address from the document. Look for terms like 'Property Address', 'Insured Property', 'Location', 'Premises', or similar. Return ONLY the complete address without any additional text or explanation.",
            model="gpt-4o",
            tools=[{"type": "file_search"}]
        )
        print(f"Assistant created. Assistant ID: {assistant.id}")
        
        # Create thread and run
        thread = client.beta.threads.create()
        print(f"Thread created. Thread ID: {thread.id}")
        
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content="Please find and extract the insured building's address from the uploaded insurance policy document.",
            attachments=[
                {
                    "file_id": file_obj.id,
                    "tools": [{"type": "file_search"}]
                }
            ]
        )
        
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant.id
        )
        print(f"Run completed with status: {run.status}")
        
        # Extract address from response
        if run.status == 'completed':
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            response_message = messages.data[0]
            address = response_message.content[0].text.value
            print(f"\nInsured Building Address:")
            print(f"{address}")
            return address
        else:
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
            if 'assistant' in locals():
                client.beta.assistants.delete(assistant.id)
                print(f"Cleaned up: Deleted assistant {assistant.id}")
        except:
            pass

def main():
    parser = argparse.ArgumentParser(description='Analyze insurance documents using Assistant API to extract insured building address')
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