# SOW Analyzer V3 Implementation

This document contains the complete implementation code for reference.

```python
import re
import os
import json
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field

import spacy
from spacy.tokens import Doc
import pdfplumber
from docx import Document
import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

###########################################################
# Dataclasses for Requirements, LLM Analysis, and Match Results
###########################################################

@dataclass
class Requirement:
    section_id: str
    section_title: str
    text: str
    req_type: str = "Unknown"
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_id": self.section_id,
            "section_title": self.section_title,
            "text": self.text,
            "req_type": self.req_type,
            "confidence": self.confidence,
            "metadata": self.metadata
        }

@dataclass
class LLMAnalysis:
    is_addressed: bool
    how_addressed: str
    compliance_level: str
    confidence_rating: str
    improvement_suggestions: List[str]

@dataclass
class MatchResult:
    requirement_id: str
    requirement_text: str
    matched_sections: List[Dict[str, Any]]
    confidence_score: float
    match_explanation: str
    llm_analysis: Optional[LLMAnalysis] = None
    suggested_improvements: Optional[str] = None

###########################################################
# Module 1: Document Extraction
###########################################################

class DocumentProcessingError(Exception):
    pass

class AdvancedDocumentExtractor:
    """
    Extract document text, tables, and basic metadata from PDF, DOCX, or TXT files.
    Handles multi-column detection using DBSCAN and removes noise.
    """
    def __init__(self, file_path: str, column_eps: float = 50, min_samples: int = 2, cache_dir: Optional[str] = None, max_retries: int = 3):
        self.file_path = file_path
        self.column_eps = column_eps
        self.min_samples = min_samples
        self.max_retries = max_retries
        self.cache_dir = cache_dir  # Not used in this example
        self.text_lines: List[str] = []
        self.tables: List[List[List[str]]] = []
        self.processing_stats: Dict[str, Any] = {
            "pages_processed": 0,
            "tables_extracted": 0,
            "processing_time": 0
        }

    def extract(self) -> Tuple[str, List[List[List[str]]], Dict[str, Any]]:
        for attempt in range(self.max_retries):
            try:
                ext = self.file_path.lower().split('.')[-1]
                if ext == "pdf":
                    self._extract_pdf()
                elif ext in ["docx", "doc"]:
                    self._extract_docx()
                elif ext == "txt":
                    with open(self.file_path, "r", encoding="utf-8") as f:
                        self.text_lines = f.read().splitlines()
                else:
                    raise DocumentProcessingError(f"Unsupported file type: {ext}")
                self._remove_noise()
                full_text = "\n".join(self.text_lines)
                return full_text, self.tables, self.processing_stats
            except Exception as e:
                logger.error(f"Extraction attempt {attempt+1} failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise DocumentProcessingError(f"Failed after {self.max_retries} attempts: {str(e)}")
        return "", [], {}

    def _extract_pdf(self):
        start_time = time.time()
        with pdfplumber.open(self.file_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                try:
                    page_lines = self._process_pdf_page(page)
                    if page_lines:
                        self.text_lines.append(f"--- Page {page_number} ---")
                        self.text_lines.extend(page_lines)
                    # Extract tables
                    for table in page.extract_tables():
                        processed = self._process_table(table)
                        if processed:
                            self.tables.append(processed)
                            self.processing_stats["tables_extracted"] += 1
                    self.processing_stats["pages_processed"] += 1
                except Exception as e:
                    logger.warning(f"Error on page {page_number}: {str(e)}")
                    continue
        self.processing_stats["processing_time"] = time.time() - start_time

    def _process_pdf_page(self, page) -> List[str]:
        words = page.extract_words()
        if not words:
            text = page.extract_text()
            return text.splitlines() if text else []
        # Simple column grouping by x0 (for demonstration)
        words.sort(key=lambda w: float(w["top"]))
        lines = []
        current_top = None
        current_line = []
        for word in words:
            word_top = float(word["top"])
            if current_top is None or abs(word_top - current_top) < 3:
                current_line.append(word["text"])
                current_top = word_top
            else:
                lines.append(" ".join(current_line))
                current_line = [word["text"]]
                current_top = word_top
        if current_line:
            lines.append(" ".join(current_line))
        return lines

    def _process_table(self, table: List[List[str]]) -> Optional[List[List[str]]]:
        if not table:
            return None
        cleaned = []
        for row in table:
            cleaned_row = [ " ".join(cell.split()).strip() for cell in row ]
            if any(cleaned_row):
                cleaned.append(cleaned_row)
        return cleaned if cleaned else None

    def _extract_docx(self):
        doc = Document(self.file_path)
        for para in doc.paragraphs:
            if para.text.strip():
                self.text_lines.append(para.text.strip())
        for table in doc.tables:
            processed = self._process_docx_table(table)
            if processed:
                self.tables.append(processed)
                self.processing_stats["tables_extracted"] += 1

    def _process_docx_table(self, table) -> Optional[List[List[str]]]:
        data = []
        for row in table.rows:
            row_data = [ " ".join(cell.text.split()).strip() for cell in row.cells ]
            if any(row_data):
                data.append(row_data)
        return data if data else None

    def _remove_noise(self):
        noise_patterns = [
            r'^Page \d+( of \d+)?$', r'^For Official Use Only$', r'^Confidential$', r'^Draft$',
            r'^\d+$', r'^-{3,}$', r'^\s*$', r'^Rev\.?\s*\d+$', r'^Document No\.?.*$', r'^\d{1,2}/\d{1,2}/\d{2,4}$'
        ]
        compiled = [ re.compile(p, re.IGNORECASE) for p in noise_patterns ]
        self.text_lines = [ line for line in self.text_lines if line and not any(c.match(line.strip()) for c in compiled) ]

###########################################################
# Module 2: Section Extraction (with TOC)
###########################################################

def extract_toc(text: str) -> Dict[str, str]:
    toc = {}
    lines = text.splitlines()[:30]
    toc_started = False
    for line in lines:
        if re.search(r'(Table of Contents|Contents)', line, re.IGNORECASE):
            toc_started = True
            continue
        if toc_started:
            m = re.match(r'^\d+(?:\.\d+)*\s+(.*)', line)
            if m:
                header = m.group(1).strip()
                # Use the header (without number) as key, store full line as value if desired
                toc[header] = line.strip()
            else:
                if toc:
                    break
    return toc

class EnhancedSectionExtractor:
    """
    Splits document text into sections using multiple regex patterns.
    Incorporates TOC hints to refine section titles.
    """
    def __init__(self):
        # Define multiple regexes for headers
        self.patterns = [
            re.compile(r'^\d+(?:\.\d+)+\.?\s+(.*)'),  # Numbered sections (e.g., "1. Overview" or "1.1. Details")
            re.compile(r'^[A-Z]\.?\s+(.*)'),           # Lettered sections (e.g., "A. Title")
            re.compile(r'^(?:I|II|III|IV|V|VI|VII|VIII|IX|X)\.?\s+(.*)'),  # Roman numeral sections
            re.compile(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$')  # Title Case sections
        ]
        
    def extract_sections(self, text: str, toc_hints: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        sections = {}
        lines = text.splitlines()
        current_section = None
        current_text = []
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            header_found = False
            for pattern in self.patterns:
                m = pattern.match(stripped)
                if m:
                    header_candidate = m.group(1).strip()
                    # If TOC hints are available, check for match
                    if toc_hints and header_candidate not in toc_hints:
                        continue
                    if current_section and current_text:
                        sections[current_section] = "\n".join(current_text)
                    current_section = header_candidate
                    current_text = []
                    header_found = True
                    break
            if not header_found:
                if current_section:
                    current_text.append(stripped)
                else:
                    current_section = "Introduction"
                    current_text.append(stripped)
        
        if current_section and current_text:
            sections[current_section] = "\n".join(current_text)
        if not sections:
            sections["main"] = text
        return sections

###########################################################
# Module 3: Requirement Extraction
###########################################################

class RequirementExtractionError(Exception):
    pass

class RequirementExtractor:
    """
    Extracts candidate requirements from section text using spaCy sentence segmentation and heuristics.
    """
    def __init__(self, min_confidence: float = 0.5):
        self.min_confidence = min_confidence
        self.mandatory_keywords = {'shall', 'must', 'required', 'mandatory', 'will', 'needs to'}
        self.informative_keywords = {'should', 'may', 'can', 'optionally', 'recommended'}
        self.action_verbs = {'provide', 'implement', 'support', 'develop', 'maintain'}

    def extract_requirements(self, section_title: str, section_text: str) -> List[Requirement]:
        requirements = []
        doc = nlp(section_text)
        for sent in doc.sents:
            sentence = sent.text.strip()
            if len(sentence.split()) < 5:
                continue
            analysis = self._analyze_sentence(sentence)
            if analysis["is_requirement"]:
                req = Requirement(
                    section_id=section_title,
                    section_title=section_title,
                    text=sentence,
                    req_type=analysis["type"],
                    confidence=analysis["confidence"],
                    metadata=analysis.get("metadata", {})
                )
                requirements.append(req)
        return requirements

    def _analyze_sentence(self, sentence: str) -> Dict[str, Any]:
        text_lower = sentence.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))
        has_mandatory = bool(words & self.mandatory_keywords)
        has_informative = bool(words & self.informative_keywords)
        has_action = bool(words & self.action_verbs)
        confidence = 0.0
        if has_mandatory:
            confidence = 0.8
            req_type = "Mandatory"
        elif has_informative:
            confidence = 0.6
            req_type = "Informative"
        else:
            req_type = "Unknown"
        if has_action:
            confidence += 0.1
        if len(sentence.split()) < 5:
            confidence *= 0.5
        return {
            "is_requirement": confidence >= self.min_confidence,
            "type": req_type,
            "confidence": confidence,
            "metadata": {"word_count": len(sentence.split())}
        }

###########################################################
# Module 4: Proposal Matching (Hybrid: Rule-based + LLM Fallback)
###########################################################

class MatcherError(Exception):
    pass

# Tuning constants for confidence (adjust as needed)
SEMANTIC_WEIGHT = 0.7
OVERLAP_WEIGHT = 0.3
BASE_BOOST = 0.3
SECTION_BONUS = 0.1
TECHNICAL_BONUS = 0.1
FINAL_THRESHOLD = 0.6

class HybridProposalMatcher:
    """
    Hybrid matcher that uses a rule-based matcher with an LLM fallback for borderline cases.
    """
    def __init__(self, nlp: spacy.language.Language, api_key: Optional[str] = None):
        self.nlp = nlp
        self.rule_matcher = ProposalMatcher(nlp)  # Use the earlier ProposalMatcher implementation (Implementation 1)
        self.llm_threshold = 0.65
        if api_key:
            try:
                from anthropic import Client as AnthropicClient
                self.llm_client = AnthropicClient(api_key)
            except Exception as e:
                logger.error(f"LLM client initialization error: {e}")
                self.llm_client = None
        else:
            self.llm_client = None
        self.vector_search = None  # Placeholder: assume rule_matcher handles vector search

    def match_requirement(
        self,
        requirement: Requirement,
        proposal_text: str
    ) -> MatchResult:
        # First pass: rule-based matching
        rule_result = self.rule_matcher.match_requirement(requirement, proposal_text)
        logger.info(f"Rule-based confidence: {rule_result['match_confidence']:.2f}")
        # LLM fallback if needed
        if self.llm_client and rule_result["match_confidence"] < self.llm_threshold and rule_result["match_confidence"] > 0.4:
            llm_result = self._llm_refinement(requirement.text, proposal_text, rule_result.get("matched_section"), rule_result["match_confidence"])
            merged_confidence = max(rule_result["match_confidence"], llm_result.get("confidence", rule_result["match_confidence"]))
            merged_analysis = f"{rule_result['analysis']}; LLM: {llm_result.get('analysis', '')}"
            rule_result["match_confidence"] = merged_confidence
            rule_result["matched"] = merged_confidence > FINAL_THRESHOLD
            rule_result["analysis"] = merged_analysis
            rule_result["improvements"] = llm_result.get("improvements", [])
        else:
            rule_result["improvements"] = []
        
        return MatchResult(
            requirement_id=requirement.metadata.get("id", "UNKNOWN"),
            requirement_text=requirement.text,
            matched_sections=rule_result.get("matched_section", []),
            confidence_score=rule_result["match_confidence"],
            match_explanation=rule_result["analysis"],
            llm_analysis=None,  # For now, already merged in analysis
            suggested_improvements=rule_result.get("improvements")
        )

    def _llm_refinement(self, req_text: str, proposal_text: str, matched_section: Optional[str], current_confidence: float) -> Dict[str, Any]:
        prompt = f"""
You are an expert document analyst. Analyze how well the following proposal section addresses this requirement.
Requirement: "{req_text}"
Proposal Section: "{matched_section if matched_section else 'N/A'}"
Current rule-based confidence: {current_confidence:.2f}
Provide a refined confidence score (0-1), detailed analysis, and improvement suggestions.
Return your answer as JSON in the format:
{{
  "confidence": <float>,
  "analysis": "<detailed explanation>",
  "improvements": ["<suggestion1>", "<suggestion2>", ...]
}}
"""
        try:
            response = self.llm_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=500,
                temperature=0,
                system="You are an expert at analyzing proposals.",
                messages=[{"role": "user", "content": prompt}]
            )
            response_text = response.content[0].text.strip()
            # Clean markdown markers if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            analysis = json.loads(response_text)
            return analysis
        except Exception as e:
            logger.error(f"LLM refinement error: {e}")
            return {
                "confidence": current_confidence,
                "analysis": f"Error: {str(e)}",
                "improvements": []
            }

###########################################################
# Streamlit UI Integration
###########################################################

def save_uploaded_file(uploaded_file: st.runtime.uploaded_file_manager.UploadedFile, prefix: str) -> str:
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, f"{prefix}_{uploaded_file.name}")
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getvalue())
    return file_path

def main():
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
        # Save and extract SOW text
        sow_path = save_uploaded_file(sow_file, "sow")
        try:
            extractor = AdvancedDocumentExtractor(sow_path, column_eps=50 if layout_choice == "Multiple Columns" else 200, min_samples=2)
            sow_text, tables, doc_stats = extractor.extract()
        except Exception as e:
            st.error(f"Error extracting SOW document: {str(e)}")
            return
        
        st.subheader("SOW Document Preview")
        st.text_area("Preview", sow_text[:2000] + ("..." if len(sow_text) > 2000 else ""), height=300)
        
        toc = extract_toc(sow_text)
        if toc:
            st.write("Extracted TOC:", toc)
        
        section_extractor = EnhancedSectionExtractor()
        sections = section_extractor.extract_sections(sow_text, toc_hints=toc)
        st.write("Detected Sections:", list(sections.keys()))
        
        req_extractor = RequirementExtractor()
        all_requirements = []
        for sec_title, sec_text in sections.items():
            reqs = req_extractor.extract_requirements(sec_title, sec_text)
            all_requirements.extend(reqs)
        st.success(f"Extracted {len(all_requirements)} requirements from the SOW document.")
        st.json([req.to_dict() for req in all_requirements])
        
        if proposal_file:
            prop_path = save_uploaded_file(proposal_file, "proposal")
            try:
                prop_extractor = AdvancedDocumentExtractor(prop_path)
                proposal_text, prop_tables, prop_stats = prop_extractor.extract()
            except Exception as e:
                st.error(f"Error extracting proposal document: {str(e)}")
                return
            st.subheader("Proposal Document Preview")
            st.text_area("Proposal Preview", proposal_text[:2000] + ("..." if len(proposal_text) > 2000 else ""), height=300)
            
            # Initialize hybrid matcher (use your Anthropic API key from Streamlit secrets)
            api_key = st.secrets["general"].get("ANTHROPIC_API_KEY", None)
            hybrid_matcher = HybridProposalMatcher(nlp, api_key)
            match_results = []
            for req in all_requirements:
                result = hybrid_matcher.match_requirement(req, proposal_text)
                match_results.append(result)
            st.subheader("Matching Results")
            st.json([mr.__dict__ for mr in match_results])
    
if __name__ == "__main__":
    main()
