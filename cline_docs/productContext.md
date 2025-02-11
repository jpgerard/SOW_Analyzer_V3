# Product Context

## Purpose
The SOW Analyzer V3 is designed to extract requirements (with associated section IDs) from Statement of Work (SOW) documents and optionally check whether these requirements are addressed in a proposal document.

## Core Features
- Advanced document extraction with adaptive multi-column detection, table extraction, and noise removal
- Table of Contents (TOC) extraction to help refine section headers
- Section extraction using multiple regex patterns and hierarchical organization
- Requirement extraction using spaCy sentence segmentation and heuristic analysis
- Proposal matching for requirement coverage (hybrid rule-based and LLM-based refinement)
- Streamlit UI providing:
  - Document preview
  - Adjustable settings impacting extraction quality
  - Interactive clarifying questions
  - Detailed analysis output

## Technical Stack
- spacy (with en_core_web_sm model)
- pdfplumber
- python-docx
- anthropic
- streamlit
- sentence_transformers (optional, for vector search)

## Usage
The application provides a web interface through Streamlit where users can:
1. Upload SOW documents (PDF, DOCX, TXT)
2. Extract text, tables, and sections (with TOC integration)
3. Extract requirements and associate them with sections
4. Optionally upload a proposal document for requirement matching
5. View detailed analysis and matching results
