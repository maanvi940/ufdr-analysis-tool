"""
Local Embedding Function for UFDR RAG Engine

Uses SentenceTransformer directly (no ChromaDB wrapper).
Model: all-MiniLM-L6-v2 (22MB, 384 dimensions, runs on CPU).

NO API KEY NEEDED — model auto-downloads on first use (~90MB one-time).
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default model — small, fast, good quality for general semantic search
DEFAULT_MODEL = "all-MiniLM-L6-v2"

# Suppress telemetry
os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")

# Model cache (singleton per model name)
_model_cache: dict = {}


def _find_cached_model_path(model_name: str) -> Optional[str]:
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
    
    snapshots = list(snapshots_dir.iterdir())
    if not snapshots:
        return None
    
    snapshot = snapshots[0]
    model_file = snapshot / "model.safetensors"
    config_file = snapshot / "config.json"
    
    if model_file.exists() and config_file.exists():
        logger.info(f"Found cached model at: {snapshot}")
        return str(snapshot)
    
    return None


def get_embedder(model_name: str = DEFAULT_MODEL):
    """
    Get a SentenceTransformer model instance (cached singleton).
    
    Args:
        model_name: SentenceTransformer model name
        
    Returns:
        SentenceTransformer model instance
    """
    if model_name in _model_cache:
        return _model_cache[model_name]
    
    from sentence_transformers import SentenceTransformer
    
    # Suppress harmless "UNEXPECTED position_ids" warnings from transformers
    logging.getLogger("transformers.modeling_utils").setLevel(logging.ERROR)
    
    # Try loading normally
    try:
        model = SentenceTransformer(model_name)
        logger.info(f"Loaded embedding model: {model_name}")
        _model_cache[model_name] = model
        return model
    except Exception as e:
        logger.warning(f"Standard model load failed: {e}")
    
    # Fallback: try loading from cached snapshot path directly
    cached_path = _find_cached_model_path(model_name)
    if cached_path:
        try:
            logger.info(f"Attempting to load from cache: {cached_path}")
            model = SentenceTransformer(cached_path)
            logger.info(f"Loaded embedding model from cache: {cached_path}")
            _model_cache[model_name] = model
            return model
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
    model = get_embedder(model_name)
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()


# Backward compatibility — old code may import get_embedding_function
def get_embedding_function(model_name: str = DEFAULT_MODEL):
    """Legacy wrapper for backward compatibility with old ChromaDB code."""
    logger.warning("get_embedding_function() is deprecated. Use get_embedder() instead.")
    return get_embedder(model_name)
