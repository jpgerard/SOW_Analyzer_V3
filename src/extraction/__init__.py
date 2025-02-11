"""Information extraction module for identifying key SOW elements."""

import re
from typing import Dict, Any, List
from dataclasses import dataclass, field

import spacy
from spacy.tokens import Doc

from ..utils.exceptions import RequirementExtractionError

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
        doc = spacy.load("en_core_web_sm")(section_text)
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
