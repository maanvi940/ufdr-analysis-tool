"""
Backend package for UFDR Analysis Tool

This package contains all backend engines and services:
- Unified Query Engine (orchestrates all search types)
- SQL Query Engine (structured data queries)
- Semantic Query Engine (semantic search)
- RAG Semantic Engine (enhanced RAG with 50+ patterns)
- Comprehensive Media Search (CLIP + YOLO image search)
- Cross-Case Analyzer (multi-case analysis with LLMs)
- Media Processing Pipeline (YOLO, BLIP, DeepFace)
- Cloud services and LLM integration
"""

__version__ = "2.0.0"
__author__ = "UFDR Analysis Team"

# Import main components with error handling
try:
    from .unified_query_engine import get_unified_query_engine, UnifiedQueryEngine
except ImportError as e:
    get_unified_query_engine = None
    UnifiedQueryEngine = None
    print(f"Warning: Could not import unified_query_engine: {e}")

try:
    from .sql_query_engine import SQLQueryEngine
except ImportError as e:
    SQLQueryEngine = None
    print(f"Warning: Could not import sql_query_engine: {e}")

try:
    from .semantic_query_engine import SemanticQueryEngine
except ImportError as e:
    SemanticQueryEngine = None
    print(f"Warning: Could not import semantic_query_engine: {e}")

try:
    from .rag_semantic_engine import RAGSemanticEngine
except ImportError as e:
    RAGSemanticEngine = None
    print(f"Warning: Could not import rag_semantic_engine: {e}")

try:
    from .comprehensive_media_search import ComprehensiveMediaSearch
except ImportError as e:
    ComprehensiveMediaSearch = None
    print(f"Warning: Could not import comprehensive_media_search: {e}")

try:
    from .cross_case_analyzer import CrossCaseAnalyzer
except ImportError as e:
    CrossCaseAnalyzer = None
    print(f"Warning: Could not import cross_case_analyzer: {e}")

try:
    from .media_processing_pipeline import MediaProcessingPipeline
except ImportError as e:
    MediaProcessingPipeline = None
    print(f"Warning: Could not import media_processing_pipeline: {e}")

__all__ = [
    'get_unified_query_engine',
    'UnifiedQueryEngine',
    'SQLQueryEngine',
    'SemanticQueryEngine',
    'RAGSemanticEngine',
    'ComprehensiveMediaSearch',
    'CrossCaseAnalyzer',
    'MediaProcessingPipeline'
]
