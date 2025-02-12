"""Proposal matching module."""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

import spacy
from spacy.tokens import Doc

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class LLMAnalysis:
    """Class representing LLM analysis results."""
    is_addressed: bool
    how_addressed: str
    compliance_level: str
    confidence_rating: str
    improvement_suggestions: List[str]

@dataclass
class MatchResult:
    """Class representing the result of a proposal match."""
    requirement_id: str
    requirement_text: str
    matched_sections: List[Dict[str, Any]]
    confidence_score: float
    match_explanation: str
    llm_analysis: Optional[LLMAnalysis] = None
    suggested_improvements: Optional[str] = None

class MatcherError(Exception):
    """Exception raised for errors in proposal matching."""
    pass

# Tuning constants for confidence
SEMANTIC_WEIGHT = 0.7
OVERLAP_WEIGHT = 0.3
BASE_BOOST = 0.3
SECTION_BONUS = 0.1
TECHNICAL_BONUS = 0.1
FINAL_THRESHOLD = 0.6

class ProposalMatcher:
    """
    Matches requirements to proposal sections using spaCy's similarity features.
    """
    def __init__(self, nlp: spacy.language.Language):
        self.nlp = nlp
        self.technical_terms = {
            'api', 'database', 'security', 'network', 'cloud', 'infrastructure',
            'monitoring', 'backup', 'recovery', 'compliance', 'authentication'
        }

    def match_requirement(self, requirement: Any, proposal_text: str) -> Dict[str, Any]:
        """Match a requirement to sections in the proposal text."""
        try:
            # Process texts with spaCy
            req_doc = self.nlp(requirement.text)
            prop_doc = self.nlp(proposal_text)
            
            # Split proposal into sections (simple sentence-based for demonstration)
            sections = list(prop_doc.sents)
            
            # Find best matching sections
            matches = []
            for section in sections:
                if len(section.text.split()) < 5:  # Skip very short sections
                    continue
                score = self._calculate_match_score(req_doc, section)
                if score > FINAL_THRESHOLD:
                    matches.append({
                        "text": section.text,
                        "score": score
                    })
            
            # Sort matches by score
            matches.sort(key=lambda x: x["score"], reverse=True)
            matches = matches[:3]  # Keep top 3 matches
            
            # Generate analysis
            analysis = self._generate_analysis(requirement.text, matches)
            
            return {
                "matched": bool(matches),
                "match_confidence": max([m["score"] for m in matches]) if matches else 0.0,
                "matched_section": matches,
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"Error matching requirement: {str(e)}")
            raise MatcherError(f"Failed to match requirement: {str(e)}")

    def _calculate_match_score(self, req_doc: Doc, section: Doc) -> float:
        """Calculate match score between requirement and section."""
        # Semantic similarity using spaCy
        semantic_sim = req_doc.similarity(section)
        
        # Word overlap score
        req_words = set(token.text.lower() for token in req_doc if not token.is_stop)
        sec_words = set(token.text.lower() for token in section if not token.is_stop)
        overlap = len(req_words & sec_words) / max(len(req_words), len(sec_words))
        
        # Technical terms bonus
        tech_terms = set(token.text.lower() for token in section if token.text.lower() in self.technical_terms)
        tech_bonus = min(len(tech_terms) * TECHNICAL_BONUS, 0.2)
        
        # Combined score
        base_score = (semantic_sim * SEMANTIC_WEIGHT + overlap * OVERLAP_WEIGHT)
        final_score = min(base_score + BASE_BOOST + tech_bonus, 1.0)
        
        return final_score

    def _generate_analysis(self, requirement_text: str, matches: List[Dict[str, Any]]) -> str:
        """Generate analysis text for the match result."""
        if not matches:
            return "No matching sections found in the proposal."
        
        analysis = []
        best_match = matches[0]
        confidence = best_match["score"]
        
        if confidence > 0.8:
            analysis.append("Strong match found.")
        elif confidence > 0.6:
            analysis.append("Moderate match found.")
        else:
            analysis.append("Weak match found.")
        
        analysis.append(f"Best matching section (confidence: {confidence:.2f}):")
        analysis.append(best_match["text"])
        
        if len(matches) > 1:
            analysis.append(f"\nAdditional {len(matches)-1} relevant sections found.")
        
        return "\n".join(analysis)
