"""Requirement extraction module."""

import re
from typing import Dict, Any, List
from dataclasses import dataclass, field

@dataclass
class Requirement:
    """Class representing a requirement extracted from text."""
    section_id: str
    section_title: str
    text: str
    req_type: str = "Unknown"
    confidence: float = 0.0
    category: str = "Uncategorized"
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

class RequirementExtractionError(Exception):
    """Exception raised for errors in requirement extraction."""
    pass

class RequirementExtractor:
    """
    Extracts candidate requirements from section text using spaCy sentence segmentation and heuristics.
    """
    def __init__(self, min_confidence: float = 0.5):
        self.min_confidence = min_confidence
        # Mandatory requirement indicators
        self.mandatory_keywords = {
            'shall', 'must', 'required', 'mandatory', 'will', 'needs to', 'requires',
            'responsible for', 'expected to', 'has to', 'need to', 'necessary',
            'critical', 'essential', 'ensure', 'guarantee'
        }
        
        # Informative requirement indicators
        self.informative_keywords = {
            'should', 'may', 'can', 'optionally', 'recommended', 'desired',
            'preferred', 'ideally', 'typically', 'generally', 'usually',
            'where possible', 'if applicable'
        }
        
        # Action verbs common in SOC requirements
        self.action_verbs = {
            'provide', 'implement', 'support', 'develop', 'maintain',
            'monitor', 'detect', 'analyze', 'respond', 'report',
            'manage', 'configure', 'deploy', 'operate', 'assess',
            'investigate', 'remediate', 'coordinate', 'document',
            'review', 'update', 'establish', 'perform', 'conduct',
            'integrate', 'secure', 'protect', 'enforce', 'verify'
        }

    def extract_requirements(self, section_title: str, section_text: str) -> List[Requirement]:
        """Extract requirements from section text.
        
        Args:
            section_title: Title of the section being processed
            section_text: Text content of the section
            
        Returns:
            List of extracted requirements with section information
        """
        try:
            import spacy
            nlp = spacy.load("en_core_web_sm")
        except ImportError:
            raise RequirementExtractionError("spaCy model 'en_core_web_sm' not found. Please install it using 'python -m spacy download en_core_web_sm'")

        requirements = []
        # Split text into sentences using spaCy
        doc = nlp(section_text)
        
        # Process each sentence
        for sent in doc.sents:
            sentence = sent.text.strip()
            
            # Skip short sentences
            if len(sentence.split()) < 5:
                continue
                
            # Skip sentences that look like headers or noise
            if sentence.isupper() or sentence.startswith('---'):
                continue
                
            # Analyze the sentence
            analysis = self._analyze_sentence(sentence)
            
            # Check if it's a requirement
            if analysis["is_requirement"]:
                # Determine requirement category based on content
                category = self._determine_category(sentence, section_title)
                
                # Create requirement object
                req = Requirement(
                    section_id=section_title,  # Will be updated by main.py with actual section ID
                    section_title=section_title,
                    text=sentence,
                    req_type=analysis["type"],
                    confidence=analysis["confidence"],
                    category=category,
                    metadata={
                        "word_count": len(sentence.split()),
                        "has_mandatory": analysis.get("has_mandatory", False),
                        "has_action": analysis.get("has_action", False),
                        **analysis.get("metadata", {})
                    }
                )
                requirements.append(req)
                
        return requirements

    def _determine_category(self, text: str, section_title: str) -> str:
        """Determine requirement category based on content and section title."""
        text_lower = text.lower()
        title_lower = section_title.lower()
        
        # Category mapping based on keywords
        categories = {
            'technical': ['technical', 'system', 'software', 'hardware', 'network', 'database', 'security'],
            'functional': ['functional', 'feature', 'capability', 'operation'],
            'performance': ['performance', 'speed', 'efficiency', 'throughput', 'response time'],
            'security': ['security', 'authentication', 'authorization', 'encryption'],
            'compliance': ['compliance', 'regulatory', 'standard', 'policy'],
            'interface': ['interface', 'api', 'integration', 'interoperability'],
            'quality': ['quality', 'reliability', 'availability', 'maintainability'],
            'documentation': ['documentation', 'document', 'report', 'manual'],
            'testing': ['test', 'validation', 'verification', 'acceptance'],
            'training': ['training', 'user guide', 'instruction'],
            'support': ['support', 'maintenance', 'service level', 'helpdesk']
        }
        
        # Check section title first
        for category, keywords in categories.items():
            if any(keyword in title_lower for keyword in keywords):
                return category.title()
        
        # Then check requirement text
        for category, keywords in categories.items():
            if any(keyword in text_lower for keyword in keywords):
                return category.title()
        
        return "Uncategorized"

    def _analyze_sentence(self, sentence: str) -> Dict[str, Any]:
        """Analyze a sentence to determine if it contains a requirement."""
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
            "has_mandatory": has_mandatory,
            "has_action": has_action,
            "metadata": {
                "word_count": len(sentence.split()),
                "has_informative": has_informative,
                "confidence_factors": {
                    "mandatory_term": 0.8 if has_mandatory else 0.0,
                    "informative_term": 0.6 if has_informative else 0.0,
                    "action_verb": 0.1 if has_action else 0.0
                }
            }
        }
