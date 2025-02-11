# SOW Analyzer V3

A powerful tool for analyzing Statement of Work (SOW) documents to extract requirements and validate proposal coverage.

## Features

- Advanced document extraction with adaptive multi-column detection
- Table of Contents (TOC) extraction and section organization
- Requirement extraction using spaCy and heuristic analysis
- Proposal matching with hybrid rule-based and LLM refinement
- Interactive Streamlit UI with document preview and settings

## Installation

1. Create and activate a virtual environment:
```powershell
python -m venv venv
.\venv\Scripts\Activate
```

2. Install dependencies:
```powershell
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

3. Set up environment variables:
- Create a `.env` file in the project root
- Add your Anthropic API key:
```
ANTHROPIC_API_KEY=your_api_key_here
```

## Usage

Run the Streamlit application:
```powershell
streamlit run src/main.py
```

The web interface will guide you through:
1. Uploading SOW documents (PDF, DOCX, TXT)
2. Configuring document layout settings
3. Extracting and reviewing requirements
4. Optional proposal document analysis

## Project Structure

```
SOW_Analyzer_V3/
├── src/
│   ├── document_processing/  # Document handling and parsing
│   ├── analysis/            # Section extraction and TOC
│   ├── extraction/          # Requirement extraction
│   ├── reporting/           # Proposal matching and analysis
│   └── utils/              # Shared utilities
├── tests/                  # Test suite
├── cline_docs/            # Project documentation
└── requirements.txt       # Project dependencies
```

## Development

- Code formatting: `black src/`
- Linting: `pylint src/`
- Tests: `pytest`

## Notes

- PDF text extraction quality depends on document formatting
- Multi-column detection requires proper spacing
- LLM features require an Anthropic API key
- Large documents may require significant memory
