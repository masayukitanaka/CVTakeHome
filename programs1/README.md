
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
python insurance_analyzer.py <path_to_insurance_document>
```

### Example

```bash
python insurance_analyzer.py ../documents/loganpark.pdf
```

### Output

The program will:
1. Upload the document to OpenAI
2. Create an Assistant specialized in insurance document analysis
3. Process the document using File Search
4. Extract and display the insured building's address
5. Clean up all resources (uploaded files, assistant, vector stores)

Sample output:
```
Analyzing insurance document: ../documents/loganpark.pdf
File uploaded successfully. File ID: file-xxxxx
Assistant created. Assistant ID: asst_xxxxx
Thread created. Thread ID: thread_xxxxx
Run started. Run ID: run_xxxxx
Run status: in_progress
Run status: completed

被保険建物の住所 (Insured Building Address):
807 Broadway St Ne, Minneapolis, MN 55413

Cleaned up: Deleted uploaded file file-xxxxx
Cleaned up: Deleted assistant asst_xxxxx
```

## Supported File Formats

- PDF
- TXT
- Other text-based document formats supported by OpenAI's File Search

## Error Handling

The program includes error handling for:
- Missing API keys
- File not found errors
- API failures
- Automatic cleanup of resources even if errors occur

## Notes

- The program uses OpenAI's Assistants API which may incur costs based on your OpenAI usage plan
- All uploaded files and created resources are automatically cleaned up after analysis
- The program currently displays deprecation warnings for the Assistants API as OpenAI is transitioning to the Responses API