"""
Custom exceptions for the SOW Analyzer application.
"""

class SOWAnalyzerError(Exception):
    """Base exception class for SOW Analyzer."""
    pass

class DocumentProcessingError(SOWAnalyzerError):
    """Raised when there's an error processing a document."""
    pass

class RequirementExtractionError(SOWAnalyzerError):
    """Raised when there's an error extracting requirements."""
    pass

class MatcherError(SOWAnalyzerError):
    """Raised when there's an error in proposal matching."""
    pass

class ConfigurationError(SOWAnalyzerError):
    """Raised when there's an error in configuration."""
    pass
