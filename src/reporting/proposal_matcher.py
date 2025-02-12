"""Rule-based proposal matching implementation."""

import re
import logging
from typing import Dict, Any, List, Optional

import spacy
from spacy.language import Language
from spacy.tokens import Doc

from ..utils.exceptions import MatcherError
from ..extraction import Requirement

logger = logging.getLogger(__name__)

# Tuning constants for confidence calculation
SEMANTIC_WEIGHT = 0.7
OVERLAP_WEIGHT = 0.3
BASE_BOOST = 0.3
SECTION_BONUS = 0.1
TECHNICAL_BONUS = 0.1
FINAL_THRESHOLD = 0.6

class ProposalMatcher:
    """
    Rule-based matcher that evaluates how well proposal sections match requirements
    using spaCy similarity, keyword matching, and section relevance.
    """
    def __init__(self, nlp: Language):
        self.nlp = nlp
        # Keywords that indicate requirement relevance
        self.requirement_keywords = {
            'shall', 'must', 'required', 'mandatory', 'will', 'needs to',
            'should', 'may', 'can', 'optionally', 'recommended'
        }
        # Keywords that indicate technical sections
        self.technical_keywords = {
            'technical', 'requirements', 'specifications', 'implementation',
            'solution', 'approach', 'methodology', 'architecture'
        }

    def match_requirement(self, requirement: Requirement, proposal_text: str) -> Dict[str, Any]:
        """
        Match a requirement against proposal text using rule-based matching.
        
        Args:
            requirement: The requirement to match
            proposal_text: The full proposal text to search
            
        Returns:
            Dictionary containing:
            - match_confidence: float score indicating match quality
            - matched_section: list of matching sections with scores
            - analysis: string explaining the matching process
            - matched: boolean indicating if confidence exceeds threshold
        """
        try:
            # Process requirement text
            req_doc = self.nlp(requirement.text)
            
            # Split proposal into sections (simple paragraph splitting for now)
            sections = self._split_into_sections(proposal_text)
            
            # Find best matching sections
            matches = []
            for section_title, section_text in sections.items():
                section_doc = self.nlp(section_text)
                
                # Calculate various similarity scores
                semantic_sim = req_doc.similarity(section_doc)
                keyword_bonus = self._calculate_keyword_bonus(section_text)
                section_bonus = self._calculate_section_bonus(section_title)
                
                # Calculate final confidence score
                confidence = (
                    semantic_sim * SEMANTIC_WEIGHT +
                    keyword_bonus * OVERLAP_WEIGHT +
                    BASE_BOOST +
                    section_bonus
                )
                
                if confidence > 0.4:  # Only include somewhat relevant matches
                    matches.append({
                        "section": section_title,
                        "text": section_text[:200] + "..." if len(section_text) > 200 else section_text,
                        "confidence": confidence,
                        "semantic_similarity": semantic_sim,
                        "keyword_bonus": keyword_bonus,
                        "section_bonus": section_bonus
                    })
            
            # Sort matches by confidence
            matches.sort(key=lambda x: x["confidence"], reverse=True)
            
            # Get best match confidence
            best_confidence = matches[0]["confidence"] if matches else 0.0
            
            # Generate analysis explanation
            analysis = self._generate_analysis(requirement, matches)
            
            return {
                "match_confidence": best_confidence,
                "matched_section": matches[:3],  # Return top 3 matches
                "analysis": analysis,
                "matched": best_confidence > FINAL_THRESHOLD
            }
            
        except Exception as e:
            logger.error(f"Error in rule-based matching: {str(e)}")
            raise MatcherError(f"Rule-based matching failed: {str(e)}")

    def _split_into_sections(self, text: str) -> Dict[str, str]:
        """Split proposal text into sections using basic paragraph separation."""
        sections = {}
        current_title = "Main"
        paragraphs = text.split('\n\n')
        
        for i, para in enumerate(paragraphs):
            if not para.strip():
                continue
            # Simple heuristic: short, title-case lines might be section headers
            lines = para.strip().split('\n')
            if len(lines[0].split()) <= 6 and lines[0].istitle():
                current_title = lines[0]
                content = '\n'.join(lines[1:])
            else:
                content = para
            
            if content.strip():
                if current_title in sections:
                    sections[current_title] += f"\n\n{content}"
                else:
                    sections[current_title] = content
                    
        return sections

    def _calculate_keyword_bonus(self, text: str) -> float:
        """Calculate bonus score based on requirement keyword matches."""
        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))
        keyword_matches = words & self.requirement_keywords
        return min(0.3, len(keyword_matches) * 0.1)  # Cap at 0.3

    def _calculate_section_bonus(self, section_title: str) -> float:
        """Calculate bonus score based on section title relevance."""
        title_lower = section_title.lower()
        words = set(re.findall(r'\b\w+\b', title_lower))
        technical_matches = words & self.technical_keywords
        return min(0.2, len(technical_matches) * 0.1)  # Cap at 0.2

    def _generate_analysis(self, requirement: Requirement, matches: List[Dict[str, Any]]) -> str:
        """Generate detailed analysis of the matching process."""
        if not matches:
            return "No matching sections found in proposal."
            
        best_match = matches[0]
        analysis_parts = [
            f"Best matching section: '{best_match['section']}'",
            f"Semantic similarity: {best_match['semantic_similarity']:.2f}",
            f"Keyword relevance bonus: {best_match['keyword_bonus']:.2f}",
            f"Section relevance bonus: {best_match['section_bonus']:.2f}",
            f"Final confidence: {best_match['confidence']:.2f}"
        ]
        
        if len(matches) > 1:
            analysis_parts.append(f"\nOther potential matches:")
            for match in matches[1:3]:  # Show next 2 best matches
                analysis_parts.append(
                    f"- '{match['section']}' (confidence: {match['confidence']:.2f})"
                )
                
        return "\n".join(analysis_parts)
