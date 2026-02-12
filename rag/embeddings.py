"""
Local Embedding Function for UFDR RAG Engine

Uses ChromaDB's built-in SentenceTransformerEmbeddingFunction with
all-MiniLM-L6-v2 (22MB model, 384 dimensions, runs on CPU).

NO API KEY NEEDED — model auto-downloads on first use (~90MB one-time).

If the download is interrupted, the module will try to load from the
local HuggingFace cache (where partial/complete downloads are stored).
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Default model — small, fast, good quality for general semantic search
DEFAULT_MODEL = "all-MiniLM-L6-v2"

# Suppress ChromaDB telemetry errors
os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")


def _find_cached_model_path(model_name: str):
    """
    Find the local cache path for a HuggingFace model.
    Returns the snapshot directory path if found, else None.
    """
    cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
    model_dir = cache_dir / f"models--sentence-transformers--{model_name}"
    
    if not model_dir.exists():
        return None
    
    snapshots_dir = model_dir / "snapshots"
    if not snapshots_dir.exists():
        return None
    
    # Get the latest snapshot
    snapshots = list(snapshots_dir.iterdir())
    if not snapshots:
        return None
    
    snapshot = snapshots[0]
    
    # Verify essential files exist
    model_file = snapshot / "model.safetensors"
    config_file = snapshot / "config.json"
    
    if model_file.exists() and config_file.exists():
        logger.info(f"Found cached model at: {snapshot}")
        return str(snapshot)
    
    return None


def get_embedding_function(model_name: str = DEFAULT_MODEL):
    """
    Get the local embedding function for ChromaDB.
    
    Uses SentenceTransformerEmbeddingFunction which runs entirely locally.
    Tries to load from local cache first; falls back to downloading.
    
    Args:
        model_name: SentenceTransformer model name (default: all-MiniLM-L6-v2)
        
    Returns:
        ChromaDB-compatible embedding function
    """
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    
    # Try loading normally (will use cache if model was already downloaded)
    try:
        ef = SentenceTransformerEmbeddingFunction(model_name=model_name)
        logger.info(f"Loaded local embedding model: {model_name}")
        return ef
    except Exception as e:
        logger.warning(f"Standard model load failed: {e}")
    
    # Fallback: try loading from cached snapshot path directly
    cached_path = _find_cached_model_path(model_name)
    if cached_path:
        try:
            logger.info(f"Attempting to load from cache: {cached_path}")
            ef = SentenceTransformerEmbeddingFunction(model_name=cached_path)
            logger.info(f"Loaded embedding model from cache: {cached_path}")
            return ef
        except Exception as e2:
            logger.error(f"Cache load also failed: {e2}")
    
    raise RuntimeError(
        f"Could not load embedding model '{model_name}'. "
        f"Check your internet connection and try again, or run:\n"
        f"  python -c \"from sentence_transformers import SentenceTransformer; "
        f"SentenceTransformer('{model_name}')\"\n"
        f"to download the model manually."
    )


def embed_texts(texts: list[str], model_name: str = DEFAULT_MODEL) -> list[list[float]]:
    """
    Embed a list of texts using the local model.
    
    Args:
        texts: List of text strings to embed
        model_name: SentenceTransformer model name
        
    Returns:
        List of embedding vectors (each 384 dims for default model)
    """
    ef = get_embedding_function(model_name)
    return ef(texts)
