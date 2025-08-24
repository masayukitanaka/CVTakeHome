
# Insurance Document Analyzer

A Python program that analyzes insurance policy documents using OpenAI's Assistants API with File Search capability to extract the insured building's address.

## Prerequisites

- Python 3.8 or higher
- OpenAI API key

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
Create a `.env` file in the project directory and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## Usage

Run the analyzer with an insurance document (PDF, TXT, or other supported formats):

```bash
python insurance_analyzer_responses.py <path_to_insurance_document>
```

### Basic Usage

```bash
python insurance_analyzer_responses.py ../documents/loganpark.pdf
```

### Reusing Existing Resources

You can reuse existing assistants and vector stores to save API costs and time:

```bash
python insurance_analyzer_responses.py ../documents/loganpark.pdf --assistant-id asst_yPwA1XiVOJSKelr8piF43Ruq --vector-store-id vs_xxxxx
```

### Command Line Options

- `file_path`: Path to the insurance document (required)
- `--assistant-id`: Existing assistant ID to reuse (optional)
- `--vector-store-id`: Existing vector store ID to reuse (optional)

### Output

The program will:
1. Upload the document to OpenAI
2. Use existing or create new Assistant specialized in insurance document analysis
3. Use existing or create new vector store for document processing
4. Process the document using File Search
5. Extract and display the insured building's address

Sample output:
```
Analyzing insurance document: ../documents/loganpark.pdf
File uploaded successfully. File ID: file-xxxxx
Created new assistant ID: asst_xxxxx
Created new vector store ID: vs_xxxxx

Insured Building Address:
807 Broadway St Ne, Minneapolis, MN 55413
```

### Resource Management

- Resources (assistants, vector stores) are NOT automatically deleted
- Use the displayed IDs to reuse resources in subsequent runs
- Create a separate cleanup program to delete resources when no longer needed

## Supported File Formats

- PDF
- TXT
- Other text-based document formats supported by OpenAI's File Search

## Error Handling

The program includes error handling for:
- Missing API keys
- File not found errors
- API failures
- Invalid assistant or vector store IDs

## Notes

- The program uses OpenAI's Assistants API which may incur costs based on your OpenAI usage plan
- Resources are NOT automatically deleted - manage them manually for cost control
- The program uses GPT-4o model for better document understanding
- File uploads are temporary and will be cleaned up automatically by OpenAI after some time