"""Custom exceptions for SOW Analyzer."""

class SOWAnalyzerError(Exception):
    """Base exception for SOW Analyzer."""
    pass

class DocumentError(SOWAnalyzerError):
    """Raised when there are issues with document processing."""
    pass

class AnalysisError(SOWAnalyzerError):
    """Raised when there are issues with document analysis."""
    pass

class ExtractionError(SOWAnalyzerError):
    """Raised when there are issues with requirement extraction."""
    pass

class MatchingError(SOWAnalyzerError):
    """Raised when there are issues with proposal matching."""
    pass

class ConfigurationError(SOWAnalyzerError):
    """Raised when there are issues with configuration."""
    pass
