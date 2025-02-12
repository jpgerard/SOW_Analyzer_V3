"""Section extraction module with robust hierarchical parsing."""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

@dataclass
class Section:
    """Represents a document section with hierarchical information."""
    id: str
    title: str
    level: int
    content: List[str]
    parent_id: Optional[str] = None
    subsections: List['Section'] = None
    
    def __post_init__(self):
        if self.subsections is None:
            self.subsections = []

    def to_dict(self) -> Dict:
        """Convert section to dictionary format."""
        return {
            "id": self.id,
            "title": self.title,
            "level": self.level,
            "content": "\n".join(self.content),
            "parent_id": self.parent_id
        }

def extract_toc(text: str) -> Dict[str, str]:
    """Extract table of contents with improved pattern matching."""
    toc = {}
    lines = text.splitlines()[:50]  # Look deeper in document
    toc_started = False
    toc_patterns = [
        r'^\d+(?:\.\d+)*\s+(.*)',  # Numbered sections
        r'^[A-Z]\.?\s+(.*)',       # Lettered sections
        r'^(?:Section|SECTION)\s+\d+:?\s*(.*)',  # "Section X" format
        r'^(?:I|II|III|IV|V|VI|VII|VIII|IX|X)\.?\s+(.*)',  # Roman numerals
        r'^(?:ARTICLE|Article)\s+\d+:?\s*(.*)' # Article format
    ]
    
    for i, line in enumerate(lines):
        if re.search(r'(?:Table\s+of\s+Contents|Contents|TABLE\s+OF\s+CONTENTS)', line, re.IGNORECASE):
            toc_started = True
            continue
            
        if toc_started:
            for pattern in toc_patterns:
                m = re.match(pattern, line.strip())
                if m:
                    header = m.group(1).strip()
                    if header and len(header) > 3:  # Avoid very short headers
                        toc[header] = line.strip()
                    break
            
            # Check for TOC end
            if toc and not any(re.match(p, line.strip()) for p in toc_patterns):
                next_lines = lines[i:i+3]
                if not any(any(re.match(p, nl.strip()) for p in toc_patterns) for nl in next_lines):
                    break
    
    return toc

class EnhancedSectionExtractor:
    """Enhanced section extractor with hierarchical parsing."""
    
    def __init__(self):
        # Section ID normalization patterns
        self.id_normalization_patterns = [
            (r'Section\s+(\d+)', r'\1'),
            (r'SECTION\s+(\d+)', r'\1'),
            (r'Article\s+(\d+)', r'\1'),
            (r'\((\d+)\)', r'\1'),
            (r'\(([A-Z])\)', r'\1'),
            (r'-', '.')
        ]
        
        # Section header patterns with capture groups
        self.section_patterns = [
            # Numbered sections with optional subsections
            (r'^\s*(?P<id>\d+(?:\.\d+)*)\s+(?P<title>[^.]+?)(?:\s*\.+\s*\d*\s*$|$)', 1),
            
            # Section/Article keyword format
            (r'^\s*(?:Section|SECTION|Article|ARTICLE)\s*(?P<id>\d+(?:\.\d+)*)\s*[-.:)]\s*(?P<title>.+?)(?:\s*\.+\s*\d*\s*$|$)', 1),
            
            # Lettered sections with optional numbers
            (r'^\s*(?P<id>[A-Z](?:\.\d+)*)\s+(?P<title>[^.]+?)(?:\s*\.+\s*\d*\s*$|$)', 1),
            
            # Roman numeral sections
            (r'^\s*(?P<id>(?:I|II|III|IV|V|VI|VII|VIII|IX|X)(?:\.\d+)*)\s+(?P<title>.+?)(?:\s*\.+\s*\d*\s*$|$)', 1),
            
            # Parenthesized sections
            (r'^\s*\((?P<id>[A-Z0-9](?:\.\d+)*)\)\s+(?P<title>[^.]+?)(?:\s*\.+\s*\d*\s*$|$)', 1)
        ]
        
        # Common section names for normalization
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

    def normalize_section_id(self, section_id: str) -> str:
        """Normalize section ID to standard format."""
        normalized = section_id
        for pattern, replacement in self.id_normalization_patterns:
            normalized = re.sub(pattern, replacement, normalized)
        return normalized.strip()

    def get_section_level(self, section_id: str) -> int:
        """Determine section level from ID."""
        clean_id = self.normalize_section_id(section_id)
        parts = re.split(r'[.-]', clean_id)
        
        if len(parts) > 1:
            return len(parts)
        
        # Single letter or number
        if len(clean_id) == 1:
            return 1
        
        # Count parts separated by any delimiter
        parts = re.findall(r'[A-Z]|\d+', clean_id)
        return len(parts)

    def extract_section_info(self, line: str) -> Optional[Tuple[str, str, int]]:
        """Extract section ID, title, and level from a line."""
        line = line.strip()
        if not line:
            return None
            
        for pattern, base_level in self.section_patterns:
            match = re.match(pattern, line)
            if match:
                section_id = match.group('id')
                title = match.group('title').strip()
                
                # Skip if title looks like a page number
                if re.match(r'^\d+$', title):
                    continue
                    
                # Clean up title
                title = re.sub(r'\s*-\s*', '-', title)
                title = re.sub(r'\s+', ' ', title)
                title = re.sub(r'\s*\.{2,}\s*\d*\s*$', '', title)
                
                # Check for common section names
                title_lower = title.lower()
                for key, common_name in self.common_sections.items():
                    if key in title_lower:
                        title = common_name
                        break
                
                # Calculate level
                level = self.get_section_level(section_id)
                if level == 1:
                    level = base_level
                
                return section_id, title, level
                
        return None

    def extract_sections(self, text: str, toc_hints: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Extract sections with hierarchical structure."""
        lines = text.splitlines()
        sections = []
        current_section = None
        section_stack = []
        content_buffer = []
        
        for line in lines:
            line = line.rstrip()
            if not line:
                continue
            
            # Try to extract section info
            section_info = self.extract_section_info(line)
            
            if section_info:
                # Process buffered content
                if current_section and content_buffer:
                    current_section.content.extend(content_buffer)
                    content_buffer = []
                
                # Create new section
                section_id, title, level = section_info
                section_id = self.normalize_section_id(section_id)
                
                # Update section stack based on level
                while section_stack and section_stack[-1].level >= level:
                    section_stack.pop()
                
                # Create section with parent info
                parent = section_stack[-1] if section_stack else None
                new_section = Section(
                    id=section_id,
                    title=title,
                    level=level,
                    content=[],
                    parent_id=parent.id if parent else None
                )
                
                # Add to hierarchy
                if parent:
                    parent.subsections.append(new_section)
                else:
                    sections.append(new_section)
                
                current_section = new_section
                section_stack.append(current_section)
                
            else:
                content_buffer.append(line)
        
        # Process remaining content
        if current_section and content_buffer:
            current_section.content.extend(content_buffer)
        
        # Convert to dictionary format for compatibility
        section_dict = {}
        for section in sections:
            section_dict[section.title] = self._get_section_content(section)
            for subsection in section.subsections:
                section_dict[subsection.title] = self._get_section_content(subsection)
        
        return section_dict

    def _get_section_content(self, section: Section) -> str:
        """Get section content including subsections."""
        content = "\n".join(section.content)
        for subsection in section.subsections:
            subcontent = self._get_section_content(subsection)
            if subcontent:
                content += f"\n{subcontent}"
        return content
