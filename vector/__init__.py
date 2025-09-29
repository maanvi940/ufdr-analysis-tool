"""
Vector Indexing Package
FAISS-based semantic search for forensic artifacts
"""

from .index_builder import VectorIndexBuilder, IndexedDocument
from .retriever import VectorRetriever

__version__ = "1.0.0"
__all__ = [
    "VectorIndexBuilder",
    "VectorRetriever",
    "IndexedDocument"
]