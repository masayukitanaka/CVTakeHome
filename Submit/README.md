# PDF Insurance Analyzer

An automated tool for extracting insurance information (Location × Building) from PDF files. Uses OpenAI API to extract building information, coverage limits, deductibles, and other insurance details from insurance certificate PDFs.

## Features

- **Location/Building Information Extraction**: Correctly identifies multiple buildings within the same premise
- **Standard Insurance Field Extraction**:
  - Address
  - Building Limit
  - Personal Property Limit
  - Business Income
  - Deductible
  - Valuation (RC/ACV, etc.)
- **Additional Terms Extraction**: Special provisions like Equipment Breakdown, Ordinance & Law
- **Output Formats**: Markdown tables, JSON

## Prerequisites

- Docker
- OpenAI API Key

## Setup

### 1. Configure OpenAI API Key

Create `src/.env` file and set your API key:

```bash
echo "OPENAI_API_KEY=sk-your-api-key-here" > src/.env
```

### 2. Build Docker Image

```bash
docker build -t pdf-analyzer .
```

## Usage

### Basic Execution

Analyze a PDF file and output results to the `output/` directory:

```bash
docker run -it --rm \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/src/.env:/app/src/.env \
  pdf-analyzer \
  python src/pdf_insurance_analyzer.py docs/loganpark.pdf
```

### Analyze Custom PDF Files

To analyze external PDF files:

```bash
docker run -it --rm \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/src/.env:/app/src/.env \
  -v /path/to/your/pdf:/app/input.pdf \
  pdf-analyzer \
  python src/pdf_insurance_analyzer.py /app/input.pdf
```

### Specify Page Range

Analyze only specific pages of a large PDF:

```bash
docker run -it --rm \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/src/.env:/app/src/.env \
  pdf-analyzer \
  python src/pdf_insurance_analyzer.py docs/loganpark.pdf --start-page 1 --end-page 10
```

### Generate JSON Output

```bash
docker run -it --rm \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/src/.env:/app/src/.env \
  pdf-analyzer \
  python src/pdf_insurance_analyzer.py docs/loganpark.pdf --json output.json
```

### Enable Verbose Logging

```bash
docker run -it --rm \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/src/.env:/app/src/.env \
  pdf-analyzer \
  python src/pdf_insurance_analyzer.py docs/loganpark.pdf --verbose
```

### Development Mode (Interactive)

For debugging and development work inside the container:

```bash
docker run -it --rm \
  -v $(pwd):/app \
  -v $(pwd)/src/.env:/app/src/.env \
  pdf-analyzer \
  /bin/bash

# Inside container
python src/pdf_insurance_analyzer.py docs/loganpark.pdf
```

## Output Files

Analysis results are generated in the `output/` directory:

- `{PDF_filename}.md` - Markdown table of Location/Building information
- `{PDF_filename}_dynamic_terms.md` - Markdown table of additional insurance terms
- `{PDF_filename}.json` - JSON format output (when --json option is used)

### Output Examples

**loganpark.md:**
```markdown
| Location/ Premises Number, Building Number | Addresses | Building | Personal Property | Business Income | Deductible | Valuation |
|--------------------------------------------|-----------|----------|-------------------|-----------------|------------|-----------|
| Location 1 Building 1 | 123 Main St | $500,000 | $100,000 | $50,000 | $5,000 | RC |
| Location 1 Building 2 | 123 Main St | $300,000 | $75,000 | $25,000 | $5,000 | RC |
```

**loganpark_dynamic_terms.md:**
```markdown
| Term | Value |
|------|-------|
| Equipment Breakdown | $50,000 |
| Ordinance and Law | 10% of Building Limit |
```

## Command Line Options

```
usage: pdf_insurance_analyzer.py [-h] [--start-page START_PAGE] [--end-page END_PAGE]
                                 [--output OUTPUT] [--json JSON] [--verbose]
                                 [--output-dir OUTPUT_DIR]
                                 pdf_path

positional arguments:
  pdf_path              Path to the PDF file to analyze

optional arguments:
  -h, --help            Show help message and exit
  --start-page START_PAGE
                        Start analysis from this page (default: 1)
  --end-page END_PAGE   End analysis at this page (default: last page)
  --output OUTPUT, -o OUTPUT
                        Output Markdown file path
  --json JSON           Output JSON file path (optional)
  --verbose, -v         Enable verbose logging
  --output-dir OUTPUT_DIR
                        Output directory for results (default: output)
```

## Troubleshooting

### OpenAI API Errors

- Verify API Key is correctly configured
- Check if API rate limits have been reached

### PDF Processing Errors

- Ensure PDF is not encrypted
- Verify PDF is not corrupted

### Memory Issues

For large PDFs, process in segments using page ranges:

```bash
# Pages 1-50
docker run ... python src/pdf_insurance_analyzer.py large.pdf --start-page 1 --end-page 50

# Pages 51-100
docker run ... python src/pdf_insurance_analyzer.py large.pdf --start-page 51 --end-page 100
```

## Docker Container Details

The Docker container includes:
- Python 3.11
- PDF processing tools (poppler-utils)
- Development tools (git, vim, curl, wget)
- All required Python packages (openai, pdfplumber, python-dotenv)

## Project Structure

```
.
├── Dockerfile          # Docker container configuration
├── README.md          # This file
├── requirements.txt   # Python dependencies
├── src/
│   ├── .env          # OpenAI API key (create this)
│   └── pdf_insurance_analyzer.py
├── docs/             # Sample PDF files
│   └── *.pdf
└── output/           # Analysis results (created automatically)
    ├── *.md
    └── *.json
```

## License

[License information to be added]