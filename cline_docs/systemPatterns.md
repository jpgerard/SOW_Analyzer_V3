# System Patterns

## Core Components

### 1. Document Processing (AdvancedDocumentExtractor)
- Factory pattern for handling different file types (PDF, DOCX, TXT)
- Retry mechanism for robust extraction
- Noise removal using regex patterns
- Table extraction with cleaning
- Multi-column detection support

### 2. Section Analysis
- TOC extraction with early exit optimization
- Section extraction using multiple regex patterns
- Hierarchical section organization
- Pattern matching with TOC validation

### 3. Requirement Analysis
- Dataclass-based requirement representation
- Heuristic analysis with confidence scoring
- Keyword-based classification (mandatory vs informative)
- Action verb detection for requirement validation

### 4. Proposal Matching
- Hybrid approach combining rule-based and LLM analysis
- Confidence thresholds for LLM fallback
- JSON-based LLM response parsing
- Error handling with graceful degradation

### 5. UI Integration
- Streamlit-based interface
- Column-based layout
- File upload handling with type validation
- Progress tracking and error reporting

## Error Handling
- Custom exception classes for each module
- Multi-retry mechanism for critical operations
- Graceful degradation when optional components fail
- Comprehensive logging throughout

## Data Flow
1. Document Upload → Text Extraction → Section Analysis
2. Section Content → Requirement Extraction → Requirement Objects
3. Requirements + Proposal → Hybrid Matching → Match Results
4. Results → UI Presentation

## Implementation Notes
- Heavy use of type hints for code clarity
- Dataclasses for structured data representation
- Modular design with clear separation of concerns
- Configuration through environment variables
- Caching support (placeholder) for optimization
