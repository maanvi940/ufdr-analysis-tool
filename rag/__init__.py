"""
RAG (Retrieval-Augmented Generation) Engine for UFDR Analysis Tool

Offline-first architecture:
- Embeddings: Local SentenceTransformer (all-MiniLM-L6-v2, auto-downloads ~80MB)
- Vector Store: ChromaDB (persistent, local)
- Keyword Search: rank_bm25 (pure Python)
- Cloud API: Only for LLM reasoning (Gemini/OpenAI)

Usage:
    from rag.indexer import CaseIndexer
    from rag.query_engine import QueryEngine

    # After uploading a UFDR file and ingesting to SQLite:
    indexer = CaseIndexer()
    indexer.index_case(case_id)

    # To query:
    engine = QueryEngine()
    result = engine.query("Find messages about cryptocurrency", case_ids=["case_001"])
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = str(PROJECT_ROOT / "forensic_data.db")
CHROMA_DIR = str(PROJECT_ROOT / "data" / "chroma_db")
BM25_DIR = str(PROJECT_ROOT / "data" / "bm25_indices")
