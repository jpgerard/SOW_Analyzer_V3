"""Core functionality tests using real SOW files."""

import os
import pytest
import spacy
from pathlib import Path

from src.document_processing import AdvancedDocumentExtractor
from src.analysis import extract_toc, EnhancedSectionExtractor
from src.extraction import RequirementExtractor
from src.reporting import ProposalMatcher

# Load spaCy model once for all tests
nlp = spacy.load("en_core_web_sm")

# Get paths to test data
TEST_DATA_DIR = Path(__file__).parent / "data" / "sow_samples"
SOW_FILES = list(TEST_DATA_DIR.glob("*.pdf"))

def test_sow_files_exist():
    """Verify we have SOW files to test with."""
    assert len(SOW_FILES) > 0, "No SOW files found in test data directory"

@pytest.mark.parametrize("sow_file", SOW_FILES)
def test_document_extraction(sow_file):
    """Test document extraction on real SOW files."""
    extractor = AdvancedDocumentExtractor(str(sow_file))
    text, tables, stats = extractor.extract()
    
    # Basic validation
    assert text, "Extracted text should not be empty"
    assert isinstance(tables, list), "Tables should be a list"
    assert isinstance(stats, dict), "Stats should be a dictionary"
    assert stats["pages_processed"] > 0, "Should process at least one page"
    
    # Check for common SOW terms
    common_terms = ["scope", "requirements", "deliverables", "schedule"]
    text_lower = text.lower()
    found_terms = [term for term in common_terms if term in text_lower]
    assert found_terms, f"Should find some common SOW terms. Text: {text[:200]}..."

@pytest.mark.parametrize("sow_file", SOW_FILES)
def test_section_extraction(sow_file):
    """Test section extraction with TOC integration."""
    # First extract text
    extractor = AdvancedDocumentExtractor(str(sow_file))
    text, _, _ = extractor.extract()
    
    # Extract TOC and sections
    toc = extract_toc(text)
    section_extractor = EnhancedSectionExtractor()
    sections = section_extractor.extract_sections(text, toc_hints=toc)
    
    # Validation
    assert sections, "Should extract at least one section"
    assert isinstance(sections, dict), "Sections should be a dictionary"
    assert all(isinstance(k, str) and isinstance(v, str) 
              for k, v in sections.items()), "Section keys and values should be strings"

@pytest.mark.parametrize("sow_file", SOW_FILES)
def test_requirement_extraction(sow_file):
    """Test requirement extraction from real SOW files."""
    # Extract text and sections
    extractor = AdvancedDocumentExtractor(str(sow_file))
    text, _, _ = extractor.extract()
    section_extractor = EnhancedSectionExtractor()
    sections = section_extractor.extract_sections(text)
    
    # Extract requirements
    req_extractor = RequirementExtractor()
    all_requirements = []
    for section_title, section_text in sections.items():
        reqs = req_extractor.extract_requirements(section_title, section_text)
        all_requirements.extend(reqs)
    
    # Validation
    assert all_requirements, "Should find at least one requirement"
    for req in all_requirements:
        assert req.section_id, "Requirement should have section ID"
        assert req.text, "Requirement should have text"
        assert req.confidence > 0, "Requirement should have confidence score"

@pytest.mark.parametrize("sow_file", SOW_FILES)
def test_proposal_matching(sow_file):
    """Test proposal matching using sections as mock proposals."""
    # Extract text and sections
    extractor = AdvancedDocumentExtractor(str(sow_file))
    text, _, _ = extractor.extract()
    section_extractor = EnhancedSectionExtractor()
    sections = section_extractor.extract_sections(text)
    
    # Extract some requirements
    req_extractor = RequirementExtractor()
    requirements = []
    for section_title, section_text in list(sections.items())[:2]:  # Use first two sections
        reqs = req_extractor.extract_requirements(section_title, section_text)
        requirements.extend(reqs)
    
    if not requirements:
        pytest.skip("No requirements found for matching test")
    
    # Use remaining sections as mock proposal text
    proposal_text = "\n\n".join(list(sections.values())[2:])
    if not proposal_text:
        pytest.skip("No proposal text available for matching test")
    
    # Test matching
    matcher = ProposalMatcher(nlp)
    for req in requirements[:3]:  # Test first 3 requirements
        result = matcher.match_requirement(req, proposal_text)
        
        # Validation
        assert isinstance(result, dict), "Match result should be a dictionary"
        assert "match_confidence" in result, "Result should have confidence score"
        assert "matched_section" in result, "Result should have matched sections"
        assert "analysis" in result, "Result should have analysis"
        assert isinstance(result["match_confidence"], float), "Confidence should be float"
        assert 0 <= result["match_confidence"] <= 1, "Confidence should be between 0 and 1"
