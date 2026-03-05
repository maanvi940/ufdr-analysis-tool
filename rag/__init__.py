"""
RAG (Retrieval-Augmented Generation) Engine for UFDR Analysis Tool

Production-grade architecture:
- Embeddings: Local SentenceTransformer (all-MiniLM-L6-v2, auto-downloads ~80MB)
- Vector Store: FAISS (Facebook AI Similarity Search — fast, scalable)
- Keyword Search: bm25s (500x faster BM25 via SciPy sparse matrices)
- Re-Ranking: FlashRank (4MB cross-encoder, CPU-only)
- Cloud API: Only for LLM reasoning (Gemini/OpenAI/OpenRouter)

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
FAISS_DIR = str(PROJECT_ROOT / "data" / "faiss_indices")
BM25_DIR = str(PROJECT_ROOT / "data" / "bm25_indices")
