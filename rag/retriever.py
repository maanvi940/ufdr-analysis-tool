"""
Hybrid Retriever for UFDR Analysis Tool

Combines three retrieval strategies:
1. Semantic search (ChromaDB with local embeddings)
2. Keyword search (rank_bm25, pure Python)
3. SQL exact match (SQLite for precise/aggregate queries)

Results are merged using Reciprocal Rank Fusion (RRF).
NO API KEY NEEDED — everything runs locally.
"""

import os
import re
import pickle
import sqlite3
import logging
from typing import Optional, Callable

from rank_bm25 import BM25Okapi

from rag import DB_PATH, BM25_DIR
from rag.chroma_store import ChromaStore

logger = logging.getLogger(__name__)


class BM25Index:
    """
    BM25 keyword search index per case.
    Persists to disk for fast reload.
    """
    
    def __init__(self, case_id: str, persist_dir: str = BM25_DIR):
        self.case_id = case_id
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)
        self._index_path = os.path.join(persist_dir, f"{case_id}.pkl")
        self._bm25: Optional[BM25Okapi] = None
        self._documents: list[str] = []
        self._doc_ids: list[str] = []
        self._metadatas: list[dict] = []
    
    def build(
        self,
        documents: list[str],
        doc_ids: list[str],
        metadatas: list[dict]
    ):
        """Build BM25 index from documents."""
        self._documents = documents
        self._doc_ids = doc_ids
        self._metadatas = metadatas
        
        # Tokenize documents for BM25
        tokenized = [doc.lower().split() for doc in documents]
        self._bm25 = BM25Okapi(tokenized)
        
        # Save to disk
        self._save()
        logger.info(f"Built BM25 index for case '{self.case_id}': {len(documents)} docs")
    
    def query(self, query_text: str, n_results: int = 20) -> dict:
        """
        Search by keywords using BM25.
        
        Returns:
            Dict with keys: ids, documents, metadatas, scores
        """
        if not self._bm25:
            self._load()
        
        if not self._bm25 or not self._documents:
            return {"ids": [], "documents": [], "metadatas": [], "scores": []}
        
        tokenized_query = query_text.lower().split()
        scores = self._bm25.get_scores(tokenized_query)
        
        # Get top N indices sorted by score (descending)
        indexed_scores = list(enumerate(scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        top_indices = indexed_scores[:n_results]
        
        # Filter out zero-score results
        top_indices = [(i, s) for i, s in top_indices if s > 0]
        
        return {
            "ids": [self._doc_ids[i] for i, _ in top_indices],
            "documents": [self._documents[i] for i, _ in top_indices],
            "metadatas": [self._metadatas[i] for i, _ in top_indices],
            "scores": [s for _, s in top_indices],
        }
    
    def _save(self):
        """Persist index to disk."""
        data = {
            "bm25": self._bm25,
            "documents": self._documents,
            "doc_ids": self._doc_ids,
            "metadatas": self._metadatas,
        }
        with open(self._index_path, "wb") as f:
            pickle.dump(data, f)
    
    def _load(self):
        """Load index from disk."""
        if os.path.exists(self._index_path):
            try:
                with open(self._index_path, "rb") as f:
                    data = pickle.load(f)
                self._bm25 = data["bm25"]
                self._documents = data["documents"]
                self._doc_ids = data["doc_ids"]
                self._metadatas = data["metadatas"]
                logger.debug(f"Loaded BM25 index for case '{self.case_id}'")
            except Exception as e:
                logger.warning(f"Failed to load BM25 index: {e}")
    
    @property
    def is_built(self) -> bool:
        if self._bm25:
            return True
        return os.path.exists(self._index_path)


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
    # Build score map: doc_id -> {rrf_score, document, metadata}
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
    
    # Sort by RRF score descending
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


def classify_query(query: str) -> str:
    """
    Classify query intent for routing.
    
    Returns:
        "statistical" — aggregate/count queries → SQL
        "exact" — precise lookup → SQL + BM25
        "semantic" — meaning-based → ChromaDB + BM25 (hybrid)
    """
    q = query.lower()
    
    for pattern in _STAT_PATTERNS:
        if re.search(pattern, q):
            return "statistical"
    
    for pattern in _EXACT_PATTERNS:
        if re.search(pattern, q):
            return "exact"
    
    return "semantic"


class HybridRetriever:
    """
    Combines ChromaDB semantic search, BM25 keyword search, and SQLite 
    exact/statistical queries with Reciprocal Rank Fusion.
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._chroma = ChromaStore()
        self._bm25_indices: dict[str, BM25Index] = {}
    
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
        Run hybrid retrieval across specified cases.
        
        Args:
            query: Natural language query
            case_ids: Cases to search
            n_results: Max results
            data_type_filter: Optional filter (e.g., "message", "contact")
            
        Returns:
            Dict with ids, documents, metadatas, scores, query_type
        """
        query_type = classify_query(query)
        logger.info(f"Query classified as '{query_type}': {query[:80]}...")
        
        if query_type == "statistical":
            return self._statistical_query(query, case_ids)
        
        result_lists = []
        
        # 1. Semantic search via ChromaDB
        try:
            where = {"data_type": data_type_filter} if data_type_filter else None
            semantic_results = self._chroma.query_multiple_cases(
                case_ids, query, n_results, where, threshold=0.55
            )
            if semantic_results["ids"]:
                result_lists.append(semantic_results)
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
        
        # 2. BM25 keyword search
        for case_id in case_ids:
            try:
                bm25 = self._get_bm25(case_id)
                bm25_results = bm25.query(query, n_results)
                if bm25_results["ids"]:
                    # Apply data_type filter if specified
                    if data_type_filter:
                        filtered = {"ids": [], "documents": [], "metadatas": [], "scores": []}
                        for i, meta in enumerate(bm25_results["metadatas"]):
                            if meta.get("data_type") == data_type_filter:
                                filtered["ids"].append(bm25_results["ids"][i])
                                filtered["documents"].append(bm25_results["documents"][i])
                                filtered["metadatas"].append(bm25_results["metadatas"][i])
                                filtered["scores"].append(bm25_results["scores"][i])
                        bm25_results = filtered
                    if bm25_results["ids"]:
                        result_lists.append(bm25_results)
            except Exception as e:
                logger.warning(f"BM25 search failed for case '{case_id}': {e}")
        
        # 3. For exact queries, also try SQL
        if query_type == "exact":
            try:
                sql_results = self._exact_sql_query(query, case_ids)
                if sql_results["ids"]:
                    result_lists.append(sql_results)
            except Exception as e:
                logger.warning(f"SQL exact search failed: {e}")
        
        # Merge with RRF
        if not result_lists:
            return {
                "ids": [], "documents": [], "metadatas": [],
                "scores": [], "query_type": query_type
            }
        
        merged = reciprocal_rank_fusion(result_lists, n_results=n_results)
        merged["query_type"] = query_type
        return merged
    
    def _statistical_query(self, query: str, case_ids: list[str]) -> dict:
        """Handle statistical/aggregate queries via SQL."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            results_text = []
            q = query.lower()
            
            for case_id in case_ids:
                stats = {}
                for table in ["messages", "calls", "contacts", "media", "locations"]:
                    try:
                        cursor.execute(
                            f"SELECT COUNT(*) as cnt FROM {table} WHERE case_id = ?",
                            (case_id,)
                        )
                        stats[table] = cursor.fetchone()[0]
                    except Exception:
                        stats[table] = 0
                
                results_text.append(
                    f"Case {case_id}: {stats['messages']} messages, "
                    f"{stats['calls']} calls, {stats['contacts']} contacts, "
                    f"{stats['media']} media files, {stats['locations']} locations"
                )
            
            conn.close()
            
            doc = "\n".join(results_text)
            return {
                "ids": ["stats_summary"],
                "documents": [doc],
                "metadatas": [{"data_type": "statistics", "case_ids": ",".join(case_ids)}],
                "scores": [1.0],
                "query_type": "statistical",
            }
        except Exception as e:
            logger.error(f"Statistical query failed: {e}")
            return {"ids": [], "documents": [], "metadatas": [], "scores": [], "query_type": "statistical"}
    
    def _exact_sql_query(self, query: str, case_ids: list[str]) -> dict:
        """Extract phone numbers/identifiers from query and do exact SQL lookup."""
        # Extract potential phone digits from query
        digits = re.findall(r"\d{4,}", query)
        if not digits:
            return {"ids": [], "documents": [], "metadatas": [], "scores": []}
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            results = {"ids": [], "documents": [], "metadatas": [], "scores": []}
            
            placeholders = ",".join(["?" for _ in case_ids])
            
            for digit_seq in digits:
                # Search contacts by phone suffix
                try:
                    cursor.execute(f"""
                        SELECT * FROM contacts 
                        WHERE case_id IN ({placeholders})
                        AND (phone_raw LIKE ? OR phone_digits LIKE ? 
                             OR phone_suffix_4 = ?)
                        LIMIT 10
                    """, (*case_ids, f"%{digit_seq}", f"%{digit_seq}", digit_seq[-4:]))
                    
                    for row in cursor.fetchall():
                        row_dict = dict(row)
                        doc = f"Contact: {row_dict.get('name', 'Unknown')} | Phone: {row_dict.get('phone_raw', '')} | Case: {row_dict.get('case_id', '')}"
                        results["ids"].append(f"sql_contact_{row_dict.get('contact_id', '')}")
                        results["documents"].append(doc)
                        results["metadatas"].append({"data_type": "contact", "source": "sql_exact", "case_id": row_dict.get("case_id", "")})
                        results["scores"].append(1.0)
                except Exception:
                    pass
                
                # Search messages by sender/receiver digits
                try:
                    cursor.execute(f"""
                        SELECT * FROM messages
                        WHERE case_id IN ({placeholders})
                        AND (sender_digits LIKE ? OR receiver_digits LIKE ?)
                        LIMIT 10
                    """, (*case_ids, f"%{digit_seq}", f"%{digit_seq}"))
                    
                    for row in cursor.fetchall():
                        row_dict = dict(row)
                        doc = f"[{row_dict.get('app', '')}] {row_dict.get('sender_raw', '')} → {row_dict.get('receiver_raw', '')}: {row_dict.get('body', '')[:200]}"
                        results["ids"].append(f"sql_msg_{row_dict.get('msg_id', '')}")
                        results["documents"].append(doc)
                        results["metadatas"].append({"data_type": "message", "source": "sql_exact", "case_id": row_dict.get("case_id", "")})
                        results["scores"].append(0.9)
                except Exception:
                    pass
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"SQL exact query failed: {e}")
            return {"ids": [], "documents": [], "metadatas": [], "scores": []}
