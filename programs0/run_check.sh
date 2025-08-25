#!/bin/bash
# Simple wrapper script to run OpenAI usage checker

# Load environment variables from .env if it exists
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# Run the Python script
python check_openai_usage.py "$@"