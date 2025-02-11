# Technical Context

## Dependencies
1. Document Processing
   ```
   pdfplumber      # PDF text and table extraction
   python-docx     # DOCX file processing
   ```

2. NLP & Analysis
   ```
   spacy           # Core NLP processing
   en_core_web_sm  # spaCy language model
   anthropic       # Claude API integration
   ```

3. User Interface
   ```
   streamlit       # Web interface framework
   ```

## Environment Setup
1. Create and activate virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate
   ```

2. Install dependencies:
   ```powershell
   pip install pdfplumber python-docx spacy streamlit anthropic
   python -m spacy download en_core_web_sm
   ```

3. Environment Variables:
   ```
   ANTHROPIC_API_KEY  # Required for LLM-based analysis
   ```

## Project Structure
```
SOW_Analyzer_V3/
├── cline_docs/          # Project documentation
├── src/                 # Source code
├── temp/               # Temporary files (auto-created)
├── requirements.txt    # Project dependencies
└── README.md          # Project overview
```

## Running the Application
```powershell
streamlit run src/main.py
```

## Technical Constraints
1. Document Processing
   - PDF text extraction quality depends on document formatting
   - Multi-column detection requires proper spacing
   - Table extraction works best with well-defined borders

2. Memory Usage
   - Large documents may require significant memory
   - spaCy model loads into memory (~100MB)

3. API Limitations
   - Claude API rate limits apply
   - API key required for LLM features
   - Internet connection needed for LLM analysis

4. Performance Considerations
   - Document processing is CPU-intensive
   - Multiple retries on extraction failures
   - Caching support planned for optimization

## Development Guidelines
1. Code Style
   - Type hints required for all functions
   - Docstrings for classes and methods
   - Exception handling with custom classes
   - Comprehensive logging

2. Testing
   - Unit tests for each module
   - Integration tests for document processing
   - Mock LLM responses for testing

3. Error Handling
   - Custom exceptions per module
   - Graceful degradation of features
   - User-friendly error messages
   - Detailed logging for debugging
