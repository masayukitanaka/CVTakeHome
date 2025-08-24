#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

def test_responses_api():
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file")
    
    client = OpenAI(api_key=api_key)
    
    # Test if responses API exists
    try:
        # Try basic responses.create
        if hasattr(client, 'responses'):
            print("✓ client.responses found")
            response = client.responses.create(
                model="gpt-4o",
                input="Hello, this is a test"
            )
            print(f"Response: {response}")
        else:
            print("✗ client.responses not found")
            
        # Check for beta.responses
        if hasattr(client.beta, 'responses'):
            print("✓ client.beta.responses found")
        else:
            print("✗ client.beta.responses not found")
            
        # List available attributes
        print("\nAvailable client attributes:")
        for attr in dir(client):
            if not attr.startswith('_'):
                print(f"  - {attr}")
                
        print("\nAvailable client.beta attributes:")
        for attr in dir(client.beta):
            if not attr.startswith('_'):
                print(f"  - {attr}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_responses_api()