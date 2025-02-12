"""Analysis module for processing and validating SOW content."""

import re
from typing import Dict, Optional

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
