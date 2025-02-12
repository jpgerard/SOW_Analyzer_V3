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
from src.reporting.proposal_matcher import ProposalMatcher

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
            
            # Extract TOC and sections silently
            toc = extract_toc(sow_text)
            section_extractor = EnhancedSectionExtractor()
            sections = section_extractor.extract_sections(sow_text, toc_hints=toc)
            
            # Extract requirements
            req_extractor = RequirementExtractor()
            all_requirements = []
            for sec_title, sec_text in sections.items():
                reqs = req_extractor.extract_requirements(sec_title, sec_text)
                all_requirements.extend(reqs)
            
            # Count requirement types
            mandatory_reqs = [r for r in all_requirements if r.type == "Mandatory"]
            informative_reqs = [r for r in all_requirements if r.type == "Informative"]
            
            # Display requirements summary
            st.success(f"Found {len(all_requirements)} requirements!")
            
            # Requirements counts
            col1, col2, col3 = st.columns(3)
            with col1:
                st.subheader("Total Requirements")
                st.header(str(len(all_requirements)))
            with col2:
                st.subheader("Mandatory Requirements")
                st.header(str(len(mandatory_reqs)))
            with col3:
                st.subheader("Informative Requirements")
                st.header(str(len(informative_reqs)))
            
            # Requirements by Category
            st.subheader("Requirements by Category")
            categories = {}
            for req in all_requirements:
                cat = req.category if hasattr(req, 'category') and req.category else "Uncategorized"
                categories[cat] = categories.get(cat, 0) + 1
            
            for cat, count in categories.items():
                st.write(f"{cat}")
                st.header(str(count))
            
            # Requirements Analysis Table
            st.subheader("Requirements Analysis")
            df_data = []
            for req in all_requirements:
                df_data.append({
                    "Requirement": req.text,
                    "Type": req.type if hasattr(req, 'type') else "Unspecified",
                    "Confidence": f"{req.confidence:.2f}" if hasattr(req, 'confidence') else "N/A",
                    "Section": req.section_id if hasattr(req, 'section_id') else "N/A"
                })
            
            st.dataframe(
                df_data,
                column_config={
                    "Requirement": st.column_config.TextColumn("Requirement", width="large"),
                    "Type": st.column_config.TextColumn("Type", width="small"),
                    "Confidence": st.column_config.NumberColumn("Confidence", format="%.2f"),
                    "Section": st.column_config.TextColumn("Section", width="small")
                },
                hide_index=True
            )
            
            if proposal_file:
                # Process proposal document
                prop_path = save_uploaded_file(proposal_file, "proposal")
                prop_extractor = AdvancedDocumentExtractor(prop_path)
                proposal_text, prop_tables, prop_stats = prop_extractor.extract()
                
                # Match requirements to proposal
                api_key = st.secrets["general"].get("ANTHROPIC_API_KEY")
                matcher = ProposalMatcher(nlp, api_key)
                match_results = []
                
                with st.spinner("Analyzing proposal matches..."):
                    for req in all_requirements:
                        result = matcher.match_requirement(req, proposal_text)
                        match_results.append(result)
                
                # Display matching results
                st.subheader("Proposal Matching Analysis")
                
                # Match statistics
                matched_reqs = [r for r in match_results if r.get("matched", False)]
                high_conf = [r for r in matched_reqs if r.get("match_confidence", 0) > 0.8]
                med_conf = [r for r in matched_reqs if 0.6 <= r.get("match_confidence", 0) <= 0.8]
                low_conf = [r for r in matched_reqs if r.get("match_confidence", 0) < 0.6]
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Matches", len(matched_reqs))
                with col2:
                    st.metric("High Confidence", len(high_conf))
                with col3:
                    st.metric("Medium Confidence", len(med_conf))
                with col4:
                    st.metric("Low Confidence", len(low_conf))
                
                # Detailed matching results table
                st.subheader("Detailed Matching Analysis")
                match_data = []
                for req, result in zip(all_requirements, match_results):
                    match_data.append({
                        "Requirement": req.text,
                        "Match Found": "✓" if result.get("matched", False) else "✗",
                        "Confidence": f"{result.get('match_confidence', 0):.2f}",
                        "Analysis": result.get("analysis", "No analysis available"),
                        "LLM Insights": result.get("llm_analysis", {}).get("how_addressed", "N/A")
                    })
                
                st.dataframe(
                    match_data,
                    column_config={
                        "Requirement": st.column_config.TextColumn("Requirement", width="large"),
                        "Match Found": st.column_config.TextColumn("Match", width="small"),
                        "Confidence": st.column_config.NumberColumn("Confidence", format="%.2f"),
                        "Analysis": st.column_config.TextColumn("Analysis", width="medium"),
                        "LLM Insights": st.column_config.TextColumn("LLM Analysis", width="medium")
                    },
                    hide_index=True
                )
        
        except Exception as e:
            logger.error(f"Error processing files: {str(e)}")
            st.error(f"An error occurred: {str(e)}")
    
if __name__ == "__main__":
    main()
