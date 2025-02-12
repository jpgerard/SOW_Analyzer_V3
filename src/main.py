"""SOW Analyzer V3 main application."""

import os
import json
import logging
from typing import Dict, Any, Optional

import spacy
import streamlit as st
from anthropic import Client as AnthropicClient

from document_processing import AdvancedDocumentExtractor
from analysis import extract_toc, EnhancedSectionExtractor
from extraction import RequirementExtractor
from reporting import HybridProposalMatcher
from utils.monitoring import (
    setup_monitoring,
    PerformanceMonitor,
    track_api_call,
    track_requirements,
    log_error
)

# Configure monitoring
logger = setup_monitoring(
    sentry_dsn=st.secrets["monitoring"].get("SENTRY_DSN"),
    log_file="sow_analyzer.log",
    metrics_port=8000
)

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
            with PerformanceMonitor("document_processing", {"file_type": sow_file.type}):
                # Save and extract SOW text
                sow_path = save_uploaded_file(sow_file, "sow")
                extractor = AdvancedDocumentExtractor(
                    sow_path,
                    column_eps=50 if layout_choice == "Multiple Columns" else 200,
                    min_samples=2
                )
                sow_text, tables, doc_stats = extractor.extract()
                
                # Log document stats
                logger.info("Document processed", extra={
                    "file_name": sow_file.name,
                    "file_size": sow_file.size,
                    "pages": doc_stats["pages_processed"],
                    "tables": len(tables)
                })
            
            st.subheader("SOW Document Preview")
            st.text_area("Preview", sow_text[:2000] + ("..." if len(sow_text) > 2000 else ""), height=300)
            
            with PerformanceMonitor("section_extraction"):
                toc = extract_toc(sow_text)
                if toc:
                    st.write("Extracted TOC:", toc)
                
                section_extractor = EnhancedSectionExtractor()
                sections = section_extractor.extract_sections(sow_text, toc_hints=toc)
                st.write("Detected Sections:", list(sections.keys()))
            
            with PerformanceMonitor("requirement_extraction"):
                req_extractor = RequirementExtractor()
                all_requirements = []
                for sec_title, sec_text in sections.items():
                    reqs = req_extractor.extract_requirements(sec_title, sec_text)
                    all_requirements.extend(reqs)
                
                track_requirements(len(all_requirements))
                st.success(f"Extracted {len(all_requirements)} requirements from the SOW document.")
                st.json([req.to_dict() for req in all_requirements])
            
            if proposal_file:
                with PerformanceMonitor("proposal_processing", {"file_type": proposal_file.type}):
                    prop_path = save_uploaded_file(proposal_file, "proposal")
                    prop_extractor = AdvancedDocumentExtractor(prop_path)
                    proposal_text, prop_tables, prop_stats = prop_extractor.extract()
                
                st.subheader("Proposal Document Preview")
                st.text_area("Proposal Preview", proposal_text[:2000] + ("..." if len(proposal_text) > 2000 else ""), height=300)
                
                with PerformanceMonitor("proposal_matching"):
                    # Initialize hybrid matcher
                    api_key = st.secrets["general"].get("ANTHROPIC_API_KEY")
                    hybrid_matcher = HybridProposalMatcher(nlp, api_key)
                    match_results = []
                    
                    for req in all_requirements:
                        track_api_call("anthropic_proposal_matching")
                        result = hybrid_matcher.match_requirement(req, proposal_text)
                        match_results.append(result)
                    
                    st.subheader("Matching Results")
                    st.json([mr.__dict__ for mr in match_results])
                    
                    # Log matching stats
                    logger.info("Proposal matching completed", extra={
                        "requirements_matched": len(match_results),
                        "avg_confidence": sum(mr.confidence_score for mr in match_results) / len(match_results)
                    })
        
        except Exception as e:
            log_error(e, {
                "sow_file": sow_file.name if sow_file else None,
                "proposal_file": proposal_file.name if proposal_file else None
            })
            st.error(f"An error occurred: {str(e)}")
    
if __name__ == "__main__":
    main()
