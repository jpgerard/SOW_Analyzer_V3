"""SOW Analyzer V3 main application."""

import os
import logging
from typing import Dict, Any, Optional

import spacy
import streamlit as st
from anthropic import Client as AnthropicClient

from src.document_processing.document_extractor import AdvancedDocumentExtractor
from src.analysis.section_extractor import extract_toc, EnhancedSectionExtractor
from src.extraction.requirement_extractor import RequirementExtractor
from src.reporting.proposal_matcher import HybridProposalMatcher

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load improved spaCy model with word vectors
try:
    nlp = spacy.load("en_core_web_md")
except OSError:
    logger.warning("Downloading improved spaCy model...")
    os.system("python -m spacy download en_core_web_md")
    nlp = spacy.load("en_core_web_md")

def save_uploaded_file(uploaded_file: st.runtime.uploaded_file_manager.UploadedFile, prefix: str) -> str:
    """Save uploaded file to temp directory."""
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, f"{prefix}_{uploaded_file.name}")
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getvalue())
    return file_path

def main():
    """Main Streamlit application."""
    st.set_page_config(page_title="State-of-the-Art SOW Analyzer", layout="wide")
    st.title("State-of-the-Art SOW Analyzer")
    st.write("Upload a SOW document to extract requirements and sections, and optionally upload a proposal document for matching.")
    
    # Clarifying questions
    col1, col2 = st.columns(2)
    with col1:
        layout_choice = st.radio("Document Layout", ("Single Column", "Multiple Columns"))
    with col2:
        req_location = st.radio("Where are requirements primarily located?", ("Text", "Tables"))
    
    sow_file = st.file_uploader("Upload SOW Document (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])
    proposal_file = st.file_uploader("Upload Proposal Document (Optional)", type=["pdf", "docx", "txt"])
    
    if sow_file:
        try:
            # Save and extract SOW text
            sow_path = save_uploaded_file(sow_file, "sow")
            extractor = AdvancedDocumentExtractor(
                sow_path,
                column_eps=50 if layout_choice == "Multiple Columns" else 200,
                min_samples=2
            )
            sow_text, tables, doc_stats = extractor.extract()
            
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
            
            if proposal_file:
                # Process proposal document
                prop_path = save_uploaded_file(proposal_file, "proposal")
                prop_extractor = AdvancedDocumentExtractor(prop_path)
                proposal_text, prop_tables, prop_stats = prop_extractor.extract()
                
                st.subheader("Proposal Document Preview")
                st.text_area("Proposal Preview", proposal_text[:2000] + ("..." if len(proposal_text) > 2000 else ""), height=300)
                
                # Match requirements to proposal
                api_key = st.secrets["general"].get("ANTHROPIC_API_KEY")
                hybrid_matcher = HybridProposalMatcher(nlp, api_key)
                match_results = []
                
                for req in all_requirements:
                    result = hybrid_matcher.match_requirement(req, proposal_text)
                    match_results.append(result)
                
                st.subheader("Matching Results")
                st.json([mr.__dict__ for mr in match_results])
        
        except Exception as e:
            logger.error(f"Error processing files: {str(e)}")
            st.error(f"An error occurred: {str(e)}")
    
if __name__ == "__main__":
    main()
