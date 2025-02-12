"""Report generation module for creating analysis outputs."""

from .proposal_matcher import ProposalMatcher
from dataclasses import dataclass
from typing import Dict, Any, Optional, List

@dataclass
class LLMAnalysis:
    is_addressed: bool
    how_addressed: str
    compliance_level: str
    confidence_rating: str
    improvement_suggestions: List[str]

@dataclass
class MatchResult:
    requirement_id: str
    requirement_text: str
    matched_sections: List[Dict[str, Any]]
    confidence_score: float
    match_explanation: str
    llm_analysis: Optional[LLMAnalysis] = None
    suggested_improvements: Optional[str] = None

__all__ = [
    'ProposalMatcher',
    'LLMAnalysis',
    'MatchResult'
]
