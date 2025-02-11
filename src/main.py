"""
SOW Analyzer V3 - Main Application
"""
import os
import logging
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import streamlit as st
import spacy

from .document_processing import AdvancedDocumentExtractor
from .analysis import extract_toc, EnhancedSectionExtractor
from .extraction import RequirementExtractor
from .reporting import HybridProposalMatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.error("Spacy model 'en_core_web_sm' not found. Please install it using: python -m spacy download en_core_web_sm")
    raise

def process_uploaded_file(uploaded_file) -> Tuple[str, Path]:
    """
    Process an uploaded file using BytesIO and create a temporary file if needed.
    
    Returns:
        Tuple of (file extension, temporary file path)
    """
    # Get file extension
    file_ext = Path(uploaded_file.name).suffix.lower()
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        return file_ext, Path(tmp_file.name)

def cleanup_temp_file(file_path: Optional[Path]):
    """Clean up temporary file if it exists."""
    if file_path and file_path.exists():
        try:
            file_path.unlink()
        except Exception as e:
            logger.error(f"Error cleaning up temporary file {file_path}: {e}")

def main():
    """Main application entry point."""
    st.set_page_config(page_title="State-of-the-Art SOW Analyzer", layout="wide")
    st.title("State-of-the-Art SOW Analyzer")
    st.write("Upload a SOW document to extract requirements and sections, and optionally upload a proposal document for matching.")
    
    # Clarifying questions
    col1, col2 = st.columns(2)
    with col1:
        layout_choice = st.radio("Document Layout", ("Single Column", "Multiple Columns"))
    with col2:
        req_location = st.radio("Where are requirements primarily located?", ("Text", "Tables"))
    
    # File upload section
    sow_file = st.file_uploader("Upload SOW Document (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])
    proposal_file = st.file_uploader("Upload Proposal Document (Optional)", type=["pdf", "docx", "txt"])
    
    sow_temp_path = None
    proposal_temp_path = None
    
    try:
        if sow_file:
            # Process SOW document
            file_ext, sow_temp_path = process_uploaded_file(sow_file)
            
            try:
                extractor = AdvancedDocumentExtractor(
                    str(sow_temp_path),
                    column_eps=50 if layout_choice == "Multiple Columns" else 200,
                    min_samples=2
                )
                sow_text, tables, doc_stats = extractor.extract()
            except Exception as e:
                st.error(f"Error extracting SOW document: {str(e)}")
                return
            
            st.subheader("SOW Document Preview")
            st.text_area("Preview", sow_text[:2000] + ("..." if len(sow_text) > 2000 else ""), height=300)
            
            # Extract TOC and sections
            toc = extract_toc(sow_text)
            if toc:
                st.write("Extracted TOC:", toc)
            
            section_extractor = EnhancedSectionExtractor()
            sections = section_extractor.extract_sections(sow_text, toc_hints=toc)
            st.write("Detected Sections:", list(sections.keys()))
            
            # Extract requirements
            req_extractor = RequirementExtractor()
            all_requirements = []
            for sec_title, sec_text in sections.items():
                reqs = req_extractor.extract_requirements(sec_title, sec_text)
                all_requirements.extend(reqs)
            st.success(f"Extracted {len(all_requirements)} requirements from the SOW document.")
            st.json([req.to_dict() for req in all_requirements])
            
            # Process proposal if provided
            if proposal_file:
                file_ext, proposal_temp_path = process_uploaded_file(proposal_file)
                
                try:
                    prop_extractor = AdvancedDocumentExtractor(str(proposal_temp_path))
                    proposal_text, prop_tables, prop_stats = prop_extractor.extract()
                except Exception as e:
                    st.error(f"Error extracting proposal document: {str(e)}")
                    return
                
                st.subheader("Proposal Document Preview")
                st.text_area("Proposal Preview", proposal_text[:2000] + ("..." if len(proposal_text) > 2000 else ""), height=300)
                
                # Initialize hybrid matcher with API key from secrets
                api_key = st.secrets.get("ANTHROPIC_API_KEY")
                if not api_key:
                    st.warning("No Anthropic API key found in secrets. LLM-based refinement will be disabled.")
                
                hybrid_matcher = HybridProposalMatcher(nlp, api_key)
                match_results = []
                for req in all_requirements:
                    result = hybrid_matcher.match_requirement(req, proposal_text)
                    match_results.append(result)
                st.subheader("Matching Results")
                st.json([mr.__dict__ for mr in match_results])
    
    finally:
        # Clean up temporary files
        cleanup_temp_file(sow_temp_path)
        cleanup_temp_file(proposal_temp_path)

if __name__ == "__main__":
    main()
