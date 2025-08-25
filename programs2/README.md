# Insurance PDF Analyzer

A comprehensive tool that analyzes insurance policy PDF documents page by page using OpenAI's Vision API. The program extracts detailed information from each page and saves the results in structured JSON format.

## Features

- **Page-by-page analysis**: Processes each PDF page individually using OpenAI Vision API
- **Progressive context**: Each page analysis includes context from previously analyzed pages
- **Comprehensive data extraction**: 
  - Full text content
  - Tables and figures descriptions
  - Key insurance information (property, coverage, dates, amounts, addresses)
  - Cross-page relationships and document structure
- **Resume capability**: Can resume interrupted analyses
- **Flexible page ranges**: Analyze specific page ranges
- **Error handling**: Graceful error handling with detailed logging

## Requirements

- Python 3.8+
- OpenAI API key
- Required Python packages (install with `pip install -r requirements.txt`):
  - openai
  - pdf2image
  - pillow
  - python-dotenv

## Setup

1. Install dependencies:
```bash
pip install openai pdf2image pillow python-dotenv
```

2. Set up environment variables:
Create a `.env` file in the project directory:
```
OPENAI_API_KEY=your_api_key_here
```

3. Install system dependencies for pdf2image:
   - **macOS**: `brew install poppler`
   - **Ubuntu/Debian**: `sudo apt-get install poppler-utils`
   - **Windows**: Download poppler binaries and add to PATH

## Usage

### Basic Usage

Analyze entire PDF document:
```bash
python insurance_pdf_analyzer.py document.pdf
```

### Advanced Options

```bash
# Specify output file
python insurance_pdf_analyzer.py document.pdf -o analysis.json

# Analyze specific page range
python insurance_pdf_analyzer.py document.pdf --start-page 1 --end-page 5

# Resume interrupted analysis
python insurance_pdf_analyzer.py document.pdf --resume

# Verbose output
python insurance_pdf_analyzer.py document.pdf --verbose
```

### Command Line Options

- `pdf_path`: Path to the insurance PDF document (required)
- `-o, --output`: Output JSON file path (default: `<pdf_name>_analysis.json`)
- `--start-page`: Start analysis from this page (default: 1)
- `--end-page`: End analysis at this page (default: last page)
- `--resume`: Resume analysis from existing JSON file
- `--verbose, -v`: Enable verbose output

## Output Format

The program generates a JSON file with the following structure for each page:

```json
{
  "page_number": 1,
  "summary": "Brief summary of page content",
  "full_text": "All text content found on this page",
  "tables_and_figures": [
    {
      "type": "table",
      "description": "Description of the table/figure",
      "content": "Text content if applicable"
    }
  ],
  "key_information": {
    "insured_property": "Property information if found",
    "coverage_details": "Coverage information if found", 
    "dates": "Important dates if found",
    "amounts": "Financial amounts if found",
    "addresses": "Any addresses mentioned"
  },
  "relationships": {
    "continues_from_previous": "Content continuing from previous page",
    "continues_to_next": "Content that appears to continue to next page",
    "references": "References to other pages or sections"
  },
  "document_structure": {
    "section_title": "Main section title if present",
    "subsections": ["List of subsection titles"],
    "page_type": "cover|content|table|appendix|other"
  },
  "analyzed_at": "2024-01-01T12:00:00.000000"
}
```

## Examples

### Analyze insurance policy with progress tracking
```bash
python insurance_pdf_analyzer.py policy.pdf --verbose
```

### Resume interrupted analysis
```bash
python insurance_pdf_analyzer.py policy.pdf --resume --verbose
```

### Analyze specific sections
```bash
python insurance_pdf_analyzer.py policy.pdf --start-page 5 --end-page 10 -o coverage_section.json
```

## Error Handling

The program includes comprehensive error handling:
- Invalid PDF files
- Network connectivity issues
- OpenAI API errors
- JSON parsing errors
- Interrupted processing (Ctrl+C)

Progress is saved after each page, so you can resume analysis even if the program is interrupted.

## Performance Notes

- Analysis time depends on page complexity and OpenAI API response times
- Each page typically takes 5-15 seconds to analyze
- Large documents are processed incrementally with progress saving
- Resume functionality allows for efficient re-processing

## Troubleshooting

1. **PDF conversion errors**: Ensure poppler is installed on your system
2. **OpenAI API errors**: Check your API key and billing status
3. **Memory issues**: For very large PDFs, consider analyzing in smaller page ranges
4. **JSON parsing errors**: The program automatically handles malformed API responses

## Cost Considerations

This program uses OpenAI's GPT-4o model with vision capabilities. Costs depend on:
- Number of pages analyzed
- Image resolution (set to 200 DPI)
- Token usage for context and responses

Monitor your OpenAI usage dashboard to track costs.