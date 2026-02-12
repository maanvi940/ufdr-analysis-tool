"""
Case Indexer for UFDR Analysis Tool

After uploading a UFDR file and ingesting into SQLite, this module:
1. Reads all records for a case from SQLite
2. Chunks them into searchable text documents
3. Embeds and stores in ChromaDB (local)
4. Builds a BM25 keyword index (local)

ALL OFFLINE — no API key needed for indexing.
"""

import sqlite3
import logging
from typing import Optional, Callable

from rag import DB_PATH
from rag.chunker import chunk_records
from rag.chroma_store import ChromaStore
from rag.retriever import BM25Index

logger = logging.getLogger(__name__)

# Tables to index (must match tables in forensic_data.db)
INDEXABLE_TABLES = ["messages", "contacts", "calls", "media", "locations"]


class CaseIndexer:
    """
    Indexes a case's data into ChromaDB and BM25 after upload.
    
    Usage:
        indexer = CaseIndexer()
        stats = indexer.index_case("sample_case_001")
        # stats = {"messages": 150, "contacts": 25, ...}
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._chroma = ChromaStore()
    
    def index_case(
        self,
        case_id: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> dict:
        """
        Index all data for a case into ChromaDB and BM25.
        
        Args:
            case_id: Case identifier to index
            progress_callback: Optional fn(current, total, status_msg)
            
        Returns:
            Dict with counts per table: {"messages": 150, "contacts": 25, ...}
        """
        stats = {}
        all_documents = []
        all_metadatas = []
        all_ids = []
        
        total_steps = len(INDEXABLE_TABLES) + 2  # tables + chroma + bm25
        current_step = 0
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        for table in INDEXABLE_TABLES:
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, f"Reading {table}...")
            
            try:
                # Check if table exists
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,)
                )
                if not cursor.fetchone():
                    logger.info(f"Table '{table}' not found, skipping")
                    stats[table] = 0
                    continue
                
                # Fetch all rows for this case
                cursor.execute(
                    f"SELECT * FROM {table} WHERE case_id = ?", (case_id,)
                )
                rows = [dict(row) for row in cursor.fetchall()]
                
                if not rows:
                    stats[table] = 0
                    continue
                
                # Chunk the records
                docs, metas, ids = chunk_records(table, rows, case_id)
                
                all_documents.extend(docs)
                all_metadatas.extend(metas)
                all_ids.extend(ids)
                
                stats[table] = len(docs)
                logger.info(f"Chunked {len(docs)} {table} records for case '{case_id}'")
                
            except Exception as e:
                logger.warning(f"Failed to read '{table}': {e}")
                stats[table] = 0
        
        conn.close()
        
        total_docs = len(all_documents)
        if total_docs == 0:
            logger.warning(f"No data found for case '{case_id}'")
            return stats
        
        # Index into ChromaDB
        current_step += 1
        if progress_callback:
            progress_callback(current_step, total_steps, f"Embedding {total_docs} documents...")
        
        try:
            self._chroma.add_documents(
                case_id=case_id,
                documents=all_documents,
                metadatas=all_metadatas,
                ids=all_ids,
                batch_size=100
            )
        except Exception as e:
            logger.error(f"ChromaDB indexing failed: {e}")
            raise
        
        # Build BM25 index
        current_step += 1
        if progress_callback:
            progress_callback(current_step, total_steps, "Building keyword index...")
        
        try:
            bm25 = BM25Index(case_id)
            bm25.build(all_documents, all_ids, all_metadatas)
        except Exception as e:
            logger.error(f"BM25 indexing failed: {e}")
            # Non-fatal — ChromaDB still works
        
        logger.info(
            f"Indexed case '{case_id}': {total_docs} total documents "
            f"({', '.join(f'{k}={v}' for k, v in stats.items() if v > 0)})"
        )
        
        if progress_callback:
            progress_callback(total_steps, total_steps, "Indexing complete!")
        
        return stats
    
    def is_case_indexed(self, case_id: str) -> bool:
        """Check if a case has been indexed in ChromaDB."""
        return self._chroma.get_case_doc_count(case_id) > 0
    
    def reindex_case(
        self,
        case_id: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> dict:
        """Delete existing index and re-index a case."""
        self._chroma.delete_case(case_id)
        return self.index_case(case_id, progress_callback)
    
    def delete_case_index(self, case_id: str) -> bool:
        """Delete a case's search index."""
        return self._chroma.delete_case(case_id)
