"""
Hybrid Retriever for UFDR Analysis Tool

Combines three retrieval strategies:
1. Semantic search (FAISS with local embeddings)
2. Keyword search (bm25s — 500x faster BM25)
3. CLIP image search (SentenceTransformers, if available)

Results are merged using Reciprocal Rank Fusion (RRF),
then re-ranked with FlashRank cross-encoder.

NO API KEY NEEDED — everything runs locally.
"""

import os
import re
import json
import logging
import numpy as np
from typing import Optional, Callable

import bm25s

from rag import DB_PATH, BM25_DIR
from rag.faiss_store import FAISSStore

logger = logging.getLogger(__name__)

# NOTE: sentence_transformers and flashrank are imported LAZILY 
# to avoid slow transformers library filesystem scan on module load.
# They're loaded on first use inside _get_clip_model() and _get_ranker().


class BM25Index:
    """
    BM25 keyword search index per case.
    Uses bm25s for 500x faster queries via SciPy sparse matrices.
    Persists to disk for fast reload.
    """
    
    def __init__(self, case_id: str, persist_dir: str = BM25_DIR):
        self.case_id = case_id
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)
        self._index_dir = os.path.join(persist_dir, case_id)
        self._meta_path = os.path.join(self._index_dir, "meta.json")
        self._bm25: Optional[bm25s.BM25] = None
        self._documents: list[str] = []
        self._doc_ids: list[str] = []
        self._metadatas: list[dict] = []
    
    def build(
        self,
        documents: list[str],
        doc_ids: list[str],
        metadatas: list[dict]
    ):
        """Build BM25 index from documents using bm25s."""
        self._documents = documents
        self._doc_ids = doc_ids
        self._metadatas = metadatas
        
        # Tokenize with bm25s (includes stopword removal)
        corpus_tokens = bm25s.tokenize(documents, stopwords="en")
        
        # Build index
        self._bm25 = bm25s.BM25()
        self._bm25.index(corpus_tokens)
        
        # Save to disk
        self._save()
        logger.info(f"Built bm25s index for case '{self.case_id}': {len(documents)} docs")
    
    def query(self, query_text: str, n_results: int = 20) -> dict:
        """
        Search by keywords using bm25s.
        
        Returns:
            Dict with keys: ids, documents, metadatas, scores
        """
        if not self._bm25:
            self._load()
        
        if not self._bm25 or not self._documents:
            return {"ids": [], "documents": [], "metadatas": [], "scores": []}
        
        # Tokenize query
        query_tokens = bm25s.tokenize([query_text], stopwords="en")
        
        # Retrieve top results
        k = min(n_results, len(self._documents))
        results, scores = self._bm25.retrieve(query_tokens, k=k)
        
        # Flatten from batch dimension
        result_indices = results[0]  # first (only) query
        result_scores = scores[0]
        
        # Filter out zero-score results and build output
        out_ids = []
        out_docs = []
        out_metas = []
        out_scores = []
        
        for idx, score in zip(result_indices, result_scores):
            score = float(score)
            if score <= 0:
                continue
            idx = int(idx)
            if 0 <= idx < len(self._documents):
                out_ids.append(self._doc_ids[idx])
                out_docs.append(self._documents[idx])
                out_metas.append(self._metadatas[idx])
                out_scores.append(score)
        
        return {
            "ids": out_ids,
            "documents": out_docs,
            "metadatas": out_metas,
            "scores": out_scores,
        }
    
    def _save(self):
        """Persist index to disk."""
        os.makedirs(self._index_dir, exist_ok=True)
        
        # Save bm25s index
        self._bm25.save(self._index_dir)
        
        # Save metadata separately
        with open(self._meta_path, "w") as f:
            json.dump({
                "documents": self._documents,
                "doc_ids": self._doc_ids,
                "metadatas": self._metadatas,
            }, f)
    
    def _load(self):
        """Load index from disk."""
        if os.path.exists(self._index_dir) and os.path.exists(self._meta_path):
            try:
                self._bm25 = bm25s.BM25.load(self._index_dir)
                with open(self._meta_path, "r") as f:
                    meta = json.load(f)
                self._documents = meta["documents"]
                self._doc_ids = meta["doc_ids"]
                self._metadatas = meta["metadatas"]
                logger.debug(f"Loaded bm25s index for case '{self.case_id}'")
            except Exception as e:
                logger.warning(f"Failed to load bm25s index: {e}")
    
    @property
    def is_built(self) -> bool:
        if self._bm25:
            return True
        return os.path.exists(self._meta_path)


def reciprocal_rank_fusion(
    result_lists: list[dict],
    k: int = 60,
    n_results: int = 20
) -> dict:
    """
    Merge multiple result sets using Reciprocal Rank Fusion.
    
    RRF score = sum(1 / (k + rank_i)) across all lists.
    Parameter-free, handles different score scales naturally.
    
    Args:
        result_lists: List of result dicts, each with 'ids', 'documents', 'metadatas'
        k: RRF constant (default 60, standard value)
        n_results: Max results to return
        
    Returns:
        Merged and re-ranked results
    """
    doc_scores = {}
    
    for results in result_lists:
        ids = results.get("ids", [])
        docs = results.get("documents", [])
        metas = results.get("metadatas", [])
        
        for rank, (doc_id, doc, meta) in enumerate(zip(ids, docs, metas)):
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {
                    "rrf_score": 0.0,
                    "document": doc,
                    "metadata": meta,
                }
            doc_scores[doc_id]["rrf_score"] += 1.0 / (k + rank + 1)
    
    ranked = sorted(doc_scores.items(), key=lambda x: x[1]["rrf_score"], reverse=True)
    ranked = ranked[:n_results]
    
    return {
        "ids": [doc_id for doc_id, _ in ranked],
        "documents": [info["document"] for _, info in ranked],
        "metadatas": [info["metadata"] for _, info in ranked],
        "scores": [info["rrf_score"] for _, info in ranked],
    }


# ---- Query classification ----

_STAT_PATTERNS = [
    r"\bhow many\b", r"\bcount\b", r"\btotal\b", r"\baverage\b",
    r"\bsum\b", r"\bmost\b", r"\bfrequen\b", r"\btop \d+",
]

_EXACT_PATTERNS = [
    r"\bphone\b.*\d{4,}", r"\b\d{10,}\b", r"\bIMEI\b",
    r"\bemail\b.*@", r"\bhash\b", r"\bexact\b",
]


# ---- Smart data-type detection ----

def detect_data_type(query: str) -> Optional[str]:
    """
    Detect the target data type from a natural language query.
    Used as a metadata filter to focus retrieval.
    
    Returns:
        data_type string ("contact", "message", "call", etc.) or None for broad queries.
    """
    q = query.lower()
    
    type_map = {
        "contact": ["contact", "people", "person", "phone number", "phone book", "address book", "names"],
        "message": ["message", "sms", "chat", "whatsapp", "telegram", "signal", "text message", "conversation"],
        "call":    ["call", "dial", "ring", "phone call", "voice call", "call log", "call history"],
        "media":   ["media", "photo", "image", "video", "picture", "camera", "gallery"],
        "location":["location", "place", "gps", "coordinate", "latitude", "longitude", "map"],
    }
    
    for data_type, keywords in type_map.items():
        if any(kw in q for kw in keywords):
            return data_type
    
    return None


def is_broad_query(query: str) -> bool:
    """
    Detect if a query is a broad listing request (e.g., 'show me contacts').
    Used to increase n_results for maximum recall.
    """
    q = query.lower().strip()
    
    browse_indicators = [
        "show me", "show all", "list all", "list the", "get all",
        "display all", "view all", "give me", "find all",
        "show", "list", "get", "display", "view",
    ]
    targets = [
        "contacts", "contact", "messages", "message", "calls", "call",
        "chats", "chat", "sms", "texts",
        "phone numbers", "phone number", "names", "people",
        "media", "photos", "photo", "images", "image", "videos", "video",
        "locations", "location", "location data", "places",
    ]
    
    if q in targets or q in [f"all {t}" for t in targets]:
        return True
    
    if any(ind in q for ind in browse_indicators) and any(t in q for t in targets):
        return True
    
    if any(t in q for t in targets):
        return True
    
    return False


class HybridRetriever:
    """
    Combines FAISS semantic search, bm25s keyword search, and CLIP
    image search with Reciprocal Rank Fusion + FlashRank re-ranking.
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._store = FAISSStore()
        self._bm25_indices: dict[str, BM25Index] = {}
        
        # FlashRank re-ranker (lazy-loaded on first use to avoid blocking)
        self._ranker = None
        self._ranker_loaded = False
        
        # CLIP for image search (lazy-loaded)
        self._clip_model = None
        self._clip_loaded = False
    
    def _get_ranker(self):
        """Lazy-load FlashRank re-ranker on first use."""
        if self._ranker_loaded:
            return self._ranker
        self._ranker_loaded = True
        try:
            from flashrank import Ranker, RerankRequest
            self._ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir="data/flashrank")
            # Store RerankRequest class for later use
            self._RerankRequest = RerankRequest
            logger.info("FlashRank re-ranker loaded (ms-marco-MiniLM-L-12-v2)")
        except ImportError:
            logger.info("flashrank not installed — skipping neural re-ranking")
        except Exception as e:
            logger.warning(f"FlashRank load failed: {e}")
        return self._ranker
    
    def _get_clip_model(self):
        """Lazy-load CLIP model on first image search."""
        if self._clip_loaded:
            return self._clip_model
        self._clip_loaded = True
        try:
            # Suppress "UNEXPECTED" keys warning from transformers
            logging.getLogger("transformers.modeling_utils").setLevel(logging.ERROR)
            
            from sentence_transformers import SentenceTransformer
            self._clip_model = SentenceTransformer('clip-ViT-B-32')
            logger.info("Loaded CLIP model for image search")
        except ImportError:
            logger.info("sentence_transformers not installed — image search disabled")
        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
        return self._clip_model
    
    def _get_bm25(self, case_id: str) -> BM25Index:
        """Get or load BM25 index for a case."""
        if case_id not in self._bm25_indices:
            idx = BM25Index(case_id)
            if idx.is_built:
                self._bm25_indices[case_id] = idx
            else:
                return idx
        return self._bm25_indices[case_id]
    
    def retrieve(
        self,
        query: str,
        case_ids: list[str],
        n_results: int = 20,
        data_type_filter: Optional[str] = None,
    ) -> dict:
        """
        Run unified RAG retrieval across specified cases.
        
        Pipeline:
        1. FAISS semantic search (with optional data_type filter)
        2. bm25s keyword search
        3. CLIP image search (if available)
        4. Reciprocal Rank Fusion to merge results
        5. FlashRank cross-encoder re-ranking
        
        Args:
            query: Natural language query
            case_ids: Cases to search
            n_results: Max results
            data_type_filter: Optional filter (e.g., "message", "contact")
        Returns:
            Dict with ids, documents, metadatas, scores, query_type
        """
        # Smart data-type detection for focused retrieval
        auto_type = detect_data_type(query)
        effective_filter = data_type_filter or auto_type
        broad = is_broad_query(query)
        
        # For broad queries, retrieve more candidates for better recall
        effective_n = max(n_results, 50) if broad else n_results
        
        logger.info(
            f"RAG retrieval: type_filter={effective_filter}, "
            f"broad={broad}, n={effective_n}, query='{query[:80]}'"
        )
        
        result_lists = []
        
        # 1. Semantic search via FAISS
        try:
            where = {"data_type": effective_filter} if effective_filter else None
            threshold = 1.5 if broad else 0.55  # Very permissive for broad queries
            semantic_results = self._store.query_multiple_cases(
                case_ids, query, effective_n, where, threshold=threshold
            )
            if semantic_results["ids"]:
                result_lists.append(semantic_results)
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            
        # 2. Image search via CLIP (if available)
        clip_model = self._get_clip_model()
        if clip_model and (not effective_filter or effective_filter in ("media", "video_frame")):
            try:
                image_results = self._image_search(query, case_ids, n_results=10)
                if image_results["ids"]:
                    result_lists.append(image_results)
            except Exception as e:
                logger.warning(f"Image search failed: {e}")
        
        # 3. bm25s keyword search
        for case_id in case_ids:
            try:
                bm25 = self._get_bm25(case_id)
                bm25_results = bm25.query(query, effective_n)
                if bm25_results["ids"]:
                    # Apply data_type filter if specified
                    if effective_filter:
                        filtered = {"ids": [], "documents": [], "metadatas": [], "scores": []}
                        for i, meta in enumerate(bm25_results["metadatas"]):
                            if meta.get("data_type") == effective_filter:
                                filtered["ids"].append(bm25_results["ids"][i])
                                filtered["documents"].append(bm25_results["documents"][i])
                                filtered["metadatas"].append(bm25_results["metadatas"][i])
                                filtered["scores"].append(bm25_results["scores"][i])
                        bm25_results = filtered
                    if bm25_results["ids"]:
                        result_lists.append(bm25_results)
            except Exception as e:
                logger.warning(f"BM25 search failed for case '{case_id}': {e}")
        
        # Merge with RRF
        if not result_lists:
            return {
                "ids": [], "documents": [], "metadatas": [],
                "scores": [], "query_type": "semantic"
            }
        
        merged = reciprocal_rank_fusion(result_lists, n_results=effective_n)
        merged["query_type"] = "semantic"
        
        # FlashRank cross-encoder re-ranking (lazy-loaded)
        ranker = self._get_ranker()
        if ranker and merged["ids"]:
            try:
                passages = []
                for i in range(len(merged["ids"])):
                    passages.append({
                        "id": i,
                        "text": merged["documents"][i],
                        "meta": {
                            "doc_id": merged["ids"][i],
                            "metadata": merged["metadatas"][i],
                            "rrf_score": merged["scores"][i],
                        }
                    })
                
                rerank_request = self._RerankRequest(query=query, passages=passages)
                reranked = ranker.rerank(rerank_request)
                
                # Rebuild results in re-ranked order
                final_ids = []
                final_docs = []
                final_metas = []
                final_scores = []
                
                for item in reranked:
                    meta_info = item["meta"]
                    final_ids.append(meta_info["doc_id"])
                    final_docs.append(item["text"])
                    final_metas.append(meta_info["metadata"])
                    final_scores.append(float(item["score"]))
                
                return {
                    "ids": final_ids,
                    "documents": final_docs,
                    "metadatas": final_metas,
                    "scores": final_scores,
                    "query_type": "semantic"
                }
            except Exception as e:
                logger.warning(f"FlashRank re-ranking failed: {e}")
        
        return merged

    def _image_search(self, query: str, case_ids: list[str], n_results: int = 10) -> dict:
        """Embed query with CLIP and search image collection."""
        clip_model = self._get_clip_model()
        if not clip_model:
            return {"ids": [], "documents": [], "metadatas": [], "scores": []}
            
        query_embedding = clip_model.encode(query).tolist()
        
        all_results = {"ids": [], "documents": [], "metadatas": [], "distances": []}
        
        for case_id in case_ids:
            try:
                results = self._store.query(
                    case_id=case_id,
                    query_text="",
                    n_results=n_results,
                    modality="image",
                    query_embeddings=[query_embedding]
                )
                
                for i in range(len(results["ids"])):
                    dist = results["distances"][i]
                    logger.debug(f"Image result: {results['ids'][i]} dist={dist:.4f}")
                    if dist < 0.9:
                        all_results["ids"].append(results["ids"][i])
                        all_results["documents"].append(results["documents"][i])
                        all_results["metadatas"].append(results["metadatas"][i])
                        all_results["distances"].append(dist)
                        
            except Exception as e:
                logger.warning(f"Image search failed for case '{case_id}': {e}")
                
        if all_results["distances"]:
            combined = list(zip(
                all_results["distances"],
                all_results["ids"],
                all_results["documents"],
                all_results["metadatas"]
            ))
            combined.sort(key=lambda x: x[0])
            combined = combined[:n_results]
            
            scores = [1.0 - c[0] for c in combined] 
            
            return {
                "ids": [c[1] for c in combined],
                "documents": [c[2] for c in combined],
                "metadatas": [c[3] for c in combined],
                "scores": scores
            }
            
        return {"ids": [], "documents": [], "metadatas": [], "scores": []}
