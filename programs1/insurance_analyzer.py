#!/usr/bin/env python3
import os
import sys
import time
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
        with open(file_path, 'rb') as file:
            file_obj = client.files.create(
                file=file,
                purpose='assistants'
            )
        print(f"File uploaded successfully. File ID: {file_obj.id}")
        
        assistant = client.beta.assistants.create(
            name="Insurance Document Analyzer",
            instructions="""You are an expert at analyzing insurance documents. 
            Your task is to extract the insured building's address from the insurance policy document.
            Look for the address of the insured property/building in the document.
            Return ONLY the complete address without any additional text or explanation.""",
            model="gpt-4o-mini",
            tools=[{"type": "file_search"}],
            tool_resources={
                "file_search": {
                    "vector_stores": [{
                        "file_ids": [file_obj.id]
                    }]
                }
            }
        )
        print(f"Assistant created. Assistant ID: {assistant.id}")
        
        thread = client.beta.threads.create()
        print(f"Thread created. Thread ID: {thread.id}")
        
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content="Please extract and return the insured building's address (被保険建物の住所) from this insurance policy document.",
            attachments=[
                {
                    "file_id": file_obj.id,
                    "tools": [{"type": "file_search"}]
                }
            ]
        )
        
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id
        )
        print(f"Run started. Run ID: {run.id}")
        
        while run.status in ['queued', 'in_progress']:
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            print(f"Run status: {run.status}")
        
        if run.status == 'completed':
            messages = client.beta.threads.messages.list(
                thread_id=thread.id
            )
            
            for msg in messages.data:
                if msg.role == 'assistant':
                    for content in msg.content:
                        if content.type == 'text':
                            address = content.text.value
                            print(f"\n被保険建物の住所 (Insured Building Address):")
                            print(f"{address}")
                            return address
        else:
            print(f"Run failed with status: {run.status}")
            if hasattr(run, 'last_error'):
                print(f"Error: {run.last_error}")
            return None
    
    except Exception as e:
        print(f"Error analyzing document: {str(e)}")
        return None
    
    finally:
        try:
            if 'file_obj' in locals():
                client.files.delete(file_obj.id)
                print(f"\nCleaned up: Deleted uploaded file {file_obj.id}")
        except:
            pass
        
        try:
            if 'assistant' in locals():
                if hasattr(assistant, 'tool_resources') and assistant.tool_resources:
                    if 'file_search' in assistant.tool_resources:
                        vector_store_ids = assistant.tool_resources['file_search'].get('vector_store_ids', [])
                        for vs_id in vector_store_ids:
                            try:
                                client.beta.vector_stores.delete(vs_id)
                                print(f"Cleaned up: Deleted vector store {vs_id}")
                            except:
                                pass
        except:
            pass
        
        try:
            if 'assistant' in locals():
                client.beta.assistants.delete(assistant.id)
                print(f"Cleaned up: Deleted assistant {assistant.id}")
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