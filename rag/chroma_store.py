"""
ChromaDB Persistent Vector Store for UFDR Analysis Tool

Manages vector collections for forensic data:
- One collection per case (e.g., "case_CASE_2024_DT_001")
- Metadata filtering by data_type, timestamp, app, etc.
- Persistent storage in data/chroma_db/

NO API KEY NEEDED — uses local embedding model.
"""

import os
import logging
from typing import Optional

import chromadb
from chromadb.config import Settings

from rag import CHROMA_DIR
from rag.embeddings import get_embedding_function

logger = logging.getLogger(__name__)


def _sanitize_collection_name(case_id: str) -> str:
    """
    Convert case_id to a valid ChromaDB collection name.
    ChromaDB requires: 3-63 chars, start/end with alphanumeric, 
    no consecutive dots, only [a-zA-Z0-9._-]
    """
    name = f"case_{case_id}"
    # Replace invalid chars with underscore
    sanitized = ""
    for ch in name:
        if ch.isalnum() or ch in ("_", "-", "."):
            sanitized += ch
        else:
            sanitized += "_"
    # Ensure starts with alphanumeric
    if sanitized and not sanitized[0].isalnum():
        sanitized = "c" + sanitized
    # Ensure ends with alphanumeric
    if sanitized and not sanitized[-1].isalnum():
        sanitized = sanitized + "0"
    # Truncate to 63 chars
    sanitized = sanitized[:63]
    # Min length 3
    while len(sanitized) < 3:
        sanitized += "0"
    return sanitized


class ChromaStore:
    """
    ChromaDB wrapper for forensic case data.
    
    Each case gets its own collection for isolation and easy deletion.
    Uses local SentenceTransformer embeddings (no API key).
    """
    
    def __init__(self, persist_dir: str = CHROMA_DIR):
        """
        Initialize ChromaDB persistent client.
        
        Args:
            persist_dir: Directory for persistent storage
        """
        os.makedirs(persist_dir, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        self._ef = get_embedding_function()
        logger.info(f"ChromaDB initialized at: {persist_dir}")
    
    def get_or_create_collection(self, case_id: str):
        """Get or create a collection for a case."""
        name = _sanitize_collection_name(case_id)
        return self._client.get_or_create_collection(
            name=name,
            embedding_function=self._ef,
            metadata={"case_id": case_id}
        )
    
    def add_documents(
        self,
        case_id: str,
        documents: list[str],
        metadatas: list[dict],
        ids: list[str],
        batch_size: int = 100
    ) -> int:
        """
        Add documents to a case's collection in batches.
        
        Args:
            case_id: Case identifier
            documents: List of text documents (will be embedded locally)
            metadatas: List of metadata dicts for each document
            ids: List of unique IDs for each document
            batch_size: Number of documents per batch
            
        Returns:
            Number of documents added
        """
        collection = self.get_or_create_collection(case_id)
        total = len(documents)
        added = 0
        
        for i in range(0, total, batch_size):
            batch_docs = documents[i:i + batch_size]
            batch_metas = metadatas[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            
            # Sanitize metadata — ChromaDB only accepts str, int, float, bool
            clean_metas = []
            for m in batch_metas:
                clean = {}
                for k, v in m.items():
                    if v is None:
                        clean[k] = ""
                    elif isinstance(v, (str, int, float, bool)):
                        clean[k] = v
                    else:
                        clean[k] = str(v)
                clean_metas.append(clean)
            
            collection.add(
                documents=batch_docs,
                metadatas=clean_metas,
                ids=batch_ids
            )
            added += len(batch_docs)
            logger.debug(f"Added batch {i // batch_size + 1}: {added}/{total} docs")
        
        logger.info(f"Indexed {added} documents for case '{case_id}'")
        return added
    
    def query(
        self,
        case_id: str,
        query_text: str,
        n_results: int = 20,
        where: Optional[dict] = None,
        where_document: Optional[dict] = None
    ) -> dict:
        """
        Query a case's collection with semantic search.
        
        Args:
            case_id: Case to search
            query_text: Natural language query
            n_results: Max results to return
            where: Metadata filter (e.g., {"data_type": "message"})
            where_document: Document content filter
            
        Returns:
            Dict with keys: ids, documents, metadatas, distances
        """
        collection = self.get_or_create_collection(case_id)
        
        kwargs = {
            "query_texts": [query_text],
            "n_results": min(n_results, collection.count() or 1),
        }
        if where:
            kwargs["where"] = where
        if where_document:
            kwargs["where_document"] = where_document
        
        results = collection.query(**kwargs)
        
        # Flatten from batch format (ChromaDB returns lists of lists)
        return {
            "ids": results["ids"][0] if results["ids"] else [],
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else [],
        }
    
    def query_multiple_cases(
        self,
        case_ids: list[str],
        query_text: str,
        n_results: int = 20,
        where: Optional[dict] = None,
        threshold: float = 0.6  # Default distance threshold (lower is better for Cosine)
    ) -> dict:
        """
        Query across multiple cases and merge results.
        
        Args:
            case_ids: List of case IDs to search
            query_text: Natural language query
            n_results: Max results per case
            where: Metadata filter
            threshold: Distance threshold (results with distance > threshold are ignored)
            
        Returns:
            Merged results sorted by distance (best first)
        """
        all_results = {"ids": [], "documents": [], "metadatas": [], "distances": []}
        
        for case_id in case_ids:
            try:
                results = self.query(case_id, query_text, n_results, where)
                
                # Filter by threshold immediately
                for i in range(len(results["ids"])):
                    dist = results["distances"][i]
                    if dist <= threshold:
                        all_results["ids"].append(results["ids"][i])
                        all_results["documents"].append(results["documents"][i])
                        all_results["metadatas"].append(results["metadatas"][i])
                        all_results["distances"].append(dist)
                        
            except Exception as e:
                logger.warning(f"Failed to query case '{case_id}': {e}")
        
        # Sort by distance (lower = more similar)
        if all_results["distances"]:
            combined = list(zip(
                all_results["distances"],
                all_results["ids"],
                all_results["documents"],
                all_results["metadatas"]
            ))
            combined.sort(key=lambda x: x[0])
            
            # Take top N overall
            combined = combined[:n_results]
            
            all_results = {
                "distances": [c[0] for c in combined],
                "ids": [c[1] for c in combined],
                "documents": [c[2] for c in combined],
                "metadatas": [c[3] for c in combined],
            }
        
        return all_results
    
    def delete_case(self, case_id: str) -> bool:
        """Delete a case's entire collection."""
        name = _sanitize_collection_name(case_id)
        try:
            self._client.delete_collection(name)
            logger.info(f"Deleted collection for case '{case_id}'")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete case '{case_id}': {e}")
            return False
    
    def list_cases(self) -> list[str]:
        """List all indexed case IDs."""
        collections = self._client.list_collections()
        case_ids = []
        for col in collections:
            meta = col.metadata or {}
            if "case_id" in meta:
                case_ids.append(meta["case_id"])
        return case_ids
    
    def get_case_doc_count(self, case_id: str) -> int:
        """Get document count for a case."""
        try:
            collection = self.get_or_create_collection(case_id)
            return collection.count()
        except Exception:
            return 0
