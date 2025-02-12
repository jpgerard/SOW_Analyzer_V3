"""Performance testing for SOW Analyzer."""

import time
import psutil
import os
import pytest
from pathlib import Path
import spacy
from memory_profiler import profile

from src.document_processing import AdvancedDocumentExtractor
from src.analysis import extract_toc, EnhancedSectionExtractor
from src.extraction import RequirementExtractor
from src.reporting import ProposalMatcher

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# Get test data paths
TEST_DATA_DIR = Path(__file__).parent / "data" / "sow_samples"
SOW_FILES = list(TEST_DATA_DIR.glob("*.pdf"))

def get_process_memory():
    """Get current process memory usage."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # Convert to MB

def log_metrics(metrics_dict, file_path):
    """Log metrics to the test results file."""
    results_dir = Path(__file__).parent.parent / "test_results"
    results_dir.mkdir(exist_ok=True)
    
    metrics_file = results_dir / "performance_metrics.md"
    
    with open(metrics_file, "a") as f:
        f.write(f"\n## Results for {Path(file_path).name}\n")
        for metric, value in metrics_dict.items():
            f.write(f"- {metric}: {value}\n")
        f.write("\n")

@pytest.mark.parametrize("sow_file", SOW_FILES)
def test_file_processing_performance(sow_file):
    """Test performance metrics for processing each SOW file."""
    metrics = {}
    
    # Initial memory
    start_memory = get_process_memory()
    
    # Document extraction timing
    start_time = time.time()
    extractor = AdvancedDocumentExtractor(str(sow_file))
    text, tables, stats = extractor.extract()
    doc_extraction_time = time.time() - start_time
    metrics["document_extraction_time"] = f"{doc_extraction_time:.2f} seconds"
    
    # Section extraction timing
    start_time = time.time()
    toc = extract_toc(text)
    section_extractor = EnhancedSectionExtractor()
    sections = section_extractor.extract_sections(text, toc_hints=toc)
    section_extraction_time = time.time() - start_time
    metrics["section_extraction_time"] = f"{section_extraction_time:.2f} seconds"
    
    # Requirement extraction timing
    start_time = time.time()
    req_extractor = RequirementExtractor()
    requirements = []
    for section_title, section_text in sections.items():
        reqs = req_extractor.extract_requirements(section_title, section_text)
        requirements.extend(reqs)
    req_extraction_time = time.time() - start_time
    metrics["requirement_extraction_time"] = f"{req_extraction_time:.2f} seconds"
    
    # Proposal matching timing (using first requirement as sample)
    if requirements:
        start_time = time.time()
        matcher = ProposalMatcher(nlp)
        proposal_text = "\n\n".join(list(sections.values())[1:])  # Use remaining sections as proposal
        result = matcher.match_requirement(requirements[0], proposal_text)
        matching_time = time.time() - start_time
        metrics["proposal_matching_time"] = f"{matching_time:.2f} seconds"
    
    # Memory usage
    peak_memory = get_process_memory()
    memory_increase = peak_memory - start_memory
    metrics["memory_usage_increase"] = f"{memory_increase:.2f} MB"
    
    # File stats
    file_size = os.path.getsize(sow_file) / (1024 * 1024)  # Convert to MB
    metrics["file_size"] = f"{file_size:.2f} MB"
    metrics["pages_processed"] = stats["pages_processed"]
    metrics["tables_extracted"] = len(tables)
    metrics["sections_found"] = len(sections)
    metrics["requirements_found"] = len(requirements)
    
    # Log results
    log_metrics(metrics, sow_file)
    
    # Basic assertions
    assert doc_extraction_time > 0, "Document extraction should take some time"
    assert section_extraction_time > 0, "Section extraction should take some time"
    assert req_extraction_time > 0, "Requirement extraction should take some time"
    assert memory_increase > 0, "Should use some memory"

if __name__ == "__main__":
    # Clear previous results
    results_file = Path(__file__).parent.parent / "test_results" / "performance_metrics.md"
    if results_file.exists():
        results_file.unlink()
    
    # Write header
    with open(results_file, "w") as f:
        f.write("# SOW Analyzer Performance Test Results\n")
        f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    # Run tests
    pytest.main([__file__, "-v"])
