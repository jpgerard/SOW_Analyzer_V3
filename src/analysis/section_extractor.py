"""Section extraction module."""

import re
from typing import Dict, Optional

def extract_toc(text: str) -> Dict[str, str]:
    """Extract table of contents from document text."""
    toc = {}
    lines = text.splitlines()[:50]  # Look deeper in the document
    toc_started = False
    toc_patterns = [
        r'^\d+(?:\.\d+)*\s+(.*)',  # Numbered sections
        r'^[A-Z]\.?\s+(.*)',       # Lettered sections
        r'^(?:Section|SECTION)\s+\d+:?\s*(.*)',  # "Section X" format
        r'^(?:I|II|III|IV|V|VI|VII|VIII|IX|X)\.?\s+(.*)'  # Roman numerals
    ]
    
    for i, line in enumerate(lines):
        # Look for TOC indicators
        if re.search(r'(?:Table\s+of\s+Contents|Contents|TABLE\s+OF\s+CONTENTS)', line, re.IGNORECASE):
            toc_started = True
            continue
            
        if toc_started:
            # Try all patterns
            for pattern in toc_patterns:
                m = re.match(pattern, line.strip())
                if m:
                    header = m.group(1).strip()
                    if header and len(header) > 3:  # Avoid very short headers
                        toc[header] = line.strip()
                    break
            
            # Check if we've reached the end of TOC
            if toc and not any(p for p in toc_patterns if re.match(p, line.strip())):
                # Look ahead a few lines to confirm TOC end
                next_lines = lines[i:i+3]
                if not any(any(re.match(p, nl.strip()) for p in toc_patterns) for nl in next_lines):
                    break
    
    return toc

class EnhancedSectionExtractor:
    """
    Splits document text into sections using multiple regex patterns.
    Incorporates TOC hints to refine section titles.
    """
    def __init__(self):
        # Common section names in SOW documents
        self.common_sections = {
            'overview': 'Overview',
            'scope': 'Scope of Work',
            'background': 'Background',
            'objectives': 'Objectives',
            'requirements': 'Requirements',
            'deliverables': 'Deliverables',
            'schedule': 'Schedule',
            'timeline': 'Timeline',
            'qualifications': 'Qualifications',
            'responsibilities': 'Responsibilities',
            'assumptions': 'Assumptions',
            'constraints': 'Constraints',
            'acceptance': 'Acceptance Criteria',
            'payment': 'Payment Terms',
            'security': 'Security Requirements',
            'compliance': 'Compliance Requirements',
            'technical': 'Technical Requirements',
            'functional': 'Functional Requirements'
        }
        
        # Enhanced patterns for headers
        self.patterns = [
            re.compile(r'^\d+(?:\.\d+)*\s+(.+)'),  # Numbered sections
            re.compile(r'^[A-Z]\.?\s+(.+)'),       # Lettered sections
            re.compile(r'^(?:Section|SECTION)\s+\d+:?\s*(.+)'),  # "Section X" format
            re.compile(r'^(?:I|II|III|IV|V|VI|VII|VIII|IX|X)\.?\s+(.+)'),  # Roman numerals
            re.compile(r'^([A-Z][A-Z\s]+(?:\s+[A-Z][a-z]+)*):'),  # ALL CAPS or Title Case with colon
            re.compile(r'^([A-Z][a-z]+(?:\s+(?:of|and|or|the|for|to|in|on|by|with)\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*$'),  # Title Case with common prepositions
            re.compile(r'^(?:ARTICLE|Article)\s+\d+:?\s*(.+)')  # Article format
        ]
        
    def extract_sections(self, text: str, toc_hints: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Extract sections from document text using regex patterns, TOC hints, and common section names."""
        sections = {}
        lines = text.splitlines()
        current_section = None
        current_text = []
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            # Try to match section headers
            header_found = False
            
            # First try TOC hints if available
            if toc_hints:
                for toc_header in toc_hints:
                    if stripped.lower().startswith(toc_header.lower()):
                        if current_section and current_text:
                            sections[current_section] = "\n".join(current_text)
                        current_section = toc_header
                        current_text = []
                        header_found = True
                        break
            
            # Then try regex patterns
            if not header_found:
                for pattern in self.patterns:
                    m = pattern.match(stripped)
                    if m:
                        header_candidate = m.group(1).strip()
                        # Check if it matches a common section name
                        header_lower = header_candidate.lower()
                        for common_key, common_name in self.common_sections.items():
                            if common_key in header_lower:
                                header_candidate = common_name
                                break
                        
                        if current_section and current_text:
                            sections[current_section] = "\n".join(current_text)
                        current_section = header_candidate
                        current_text = []
                        header_found = True
                        break
            
            # Add line to current section
            if not header_found:
                if current_section:
                    current_text.append(stripped)
                else:
                    # Try to identify the first section based on content
                    lower_stripped = stripped.lower()
                    if any(term in lower_stripped for term in ['purpose', 'overview', 'introduction']):
                        current_section = "Introduction and Purpose"
                    else:
                        current_section = "Document Overview"
                    current_text.append(stripped)
        
        if current_section and current_text:
            sections[current_section] = "\n".join(current_text)
        if not sections:
            sections["main"] = text
        return sections
