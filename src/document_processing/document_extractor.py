"""Document extraction module."""

import re
import time
import logging
from typing import Dict, Any, Optional, List, Tuple

import pdfplumber
from docx import Document

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        """Process a PDF page with robust error handling."""
        if page is None:
            logger.warning("Received None page object")
            return []
            
        try:
            # First try to extract text directly
            text = page.extract_text()
            if text:
                return [line for line in text.splitlines() if line.strip()]
            
            # If no text, try word extraction
            words = page.extract_words()
            if not words:
                logger.debug("No words found on page")
                return []
                
            # Group words into lines
            try:
                words.sort(key=lambda w: float(w.get("top", 0)))
            except (ValueError, TypeError) as e:
                logger.warning(f"Error sorting words: {str(e)}")
                return []
                
            lines = []
            current_top = None
            current_line = []
            
            for word in words:
                if not isinstance(word, dict) or "text" not in word:
                    logger.warning("Invalid word object")
                    continue
                    
                try:
                    word_top = float(word.get("top", 0))
                    word_text = str(word.get("text", "")).strip()
                    
                    if not word_text:
                        continue
                        
                    if current_top is None or abs(word_top - current_top) < 3:
                        current_line.append(word_text)
                        current_top = word_top
                    else:
                        if current_line:
                            line_text = " ".join(current_line).strip()
                            if line_text:
                                lines.append(line_text)
                        current_line = [word_text]
                        current_top = word_top
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Error processing word: {str(e)}")
                    continue
                    
            if current_line:
                line_text = " ".join(current_line).strip()
                if line_text:
                    lines.append(line_text)
            
            return [line for line in lines if line.strip()]
            
        except Exception as e:
            logger.warning(f"Error processing page: {str(e)}")
            return []

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
