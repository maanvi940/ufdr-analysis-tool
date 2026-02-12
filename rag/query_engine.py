"""
Query Engine for UFDR Analysis Tool

Orchestrates the full query pipeline:
1. Classifies query intent
2. Retrieves relevant data via HybridRetriever (all local)
3. Optionally sends context to cloud LLM for reasoning
4. Returns structured response with citations

If no API key is configured, queries still work — you just get
raw retrieval results without LLM reasoning.
"""

import os
import logging
from typing import Optional, Callable
from pathlib import Path

from dotenv import load_dotenv

from rag.retriever import HybridRetriever

logger = logging.getLogger(__name__)

# Load environment
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env")

from utils.retry import retry_with_backoff


from rag.llm_client import get_llm_client


class QueryEngine:
    """
    Main query orchestrator for UFDR forensic data.
    
    Usage:
        engine = QueryEngine()
        result = engine.query(
            "Find messages about cryptocurrency",
            case_ids=["sample_case_001"]
        )
    """
    
    def __init__(self, db_path: Optional[str] = None):
        from rag import DB_PATH
        self._retriever = HybridRetriever(db_path or DB_PATH)
        self._llm = get_llm_client()
    
    def query(
        self,
        query_text: str,
        case_ids: list[str],
        n_results: int = 20,
        data_type_filter: Optional[str] = None,
        use_llm: bool = True,
        streaming: bool = False,
    ) -> dict:
        """
        Execute a query against forensic data.
        
        Args:
            query_text: Natural language query
            case_ids: Cases to search
            n_results: Max retrieval results
            data_type_filter: Filter by data type (message, contact, etc.)
            use_llm: Whether to use LLM for reasoning (if available)
            streaming: Whether to stream LLM response
            
        Returns:
            {
                "answer": str,           # LLM-generated answer or summary
                "citations": list[dict],  # Source documents with metadata
                "query_type": str,        # semantic/exact/statistical
                "raw_results": dict,      # Raw retrieval results
                "llm_used": bool,         # Whether LLM was used
            }
        """
        # Step 1: Retrieve relevant documents
        retrieval = self._retriever.retrieve(
            query_text, case_ids, n_results, data_type_filter
        )
        
        # Step 2: Build citations
        citations = []
        for i, (doc_id, doc, meta) in enumerate(zip(
            retrieval.get("ids", []),
            retrieval.get("documents", []),
            retrieval.get("metadatas", [])
        )):
            citations.append({
                "rank": i + 1,
                "id": doc_id,
                "text": doc,
                "data_type": meta.get("data_type", "unknown"),
                "case_id": meta.get("case_id", ""),
                "metadata": meta,
            })
        
        # Step 3: LLM reasoning (if available and requested)
        answer = ""
        llm_used = False
        
        if use_llm and self._llm and citations:
            try:
                answer = self._generate_answer(query_text, citations, streaming)
                llm_used = True
            except Exception as e:
                logger.warning(f"LLM reasoning failed, using raw results: {e}")
                answer = self._format_raw_answer(query_text, citations, retrieval.get("query_type", ""))
        else:
            answer = self._format_raw_answer(query_text, citations, retrieval.get("query_type", ""))
        
        return {
            "answer": answer,
            "citations": citations,
            "query_type": retrieval.get("query_type", "semantic"),
            "raw_results": retrieval,
            "llm_used": llm_used,
        }
    
    @retry_with_backoff(max_retries=3, initial_delay=2.0)
    def _generate_answer(
        self,
        query: str,
        citations: list[dict],
        streaming: bool = False
    ) -> str:
        """Generate LLM-powered answer from retrieved context."""
        # Build context from top citations
        context_parts = []
        for c in citations[:15]:  # Limit context to top 15
            context_parts.append(
                f"[{c['data_type'].upper()} | Case: {c['case_id']}] {c['text']}"
            )
        context = "\n".join(context_parts)
        
        prompt = f"""You are a forensic data analyst. Answer the following question based ONLY on the provided evidence data. 
Be precise, cite specific records, and note any patterns.

QUESTION: {query}

EVIDENCE DATA:
{context}

INSTRUCTIONS:
- Answer based ONLY on the evidence above
- Cite specific records (mention names, phone numbers, timestamps)
- If the data is insufficient, say so
- Be concise but thorough
- Format the answer in Markdown
"""
        
        provider, client = self._llm
        
        if provider == "gemini":
            response = client.generate_content(prompt)
            return response.text
        
        elif provider == "openai":
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
            )
            return response.choices[0].message.content
            
        elif provider == "openrouter":
            response = client.chat.completions.create(
                model="google/gemini-2.0-flash-001",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                extra_headers={
                    "HTTP-Referer": "https://github.com/kartikay/ufdr-analysis-tool",
                    "X-Title": "UFDR Analysis Tool",
                },
            )
            return response.choices[0].message.content
        
        return ""
    
    def _format_raw_answer(
        self,
        query: str,
        citations: list[dict],
        query_type: str
    ) -> str:
        """Format raw retrieval results as a readable answer (no LLM)."""
        if not citations:
            return "No relevant results found for your query."
        
        lines = [f"**Found {len(citations)} relevant results:**\n"]
        
        for c in citations[:10]:
            dtype_emoji = {
                "message": "💬",
                "contact": "👤",
                "call": "📞",
                "media": "🖼️",
                "location": "📍",
                "statistics": "📊",
            }.get(c["data_type"], "📄")
            
            lines.append(f"{dtype_emoji} {c['text']}")
        
        if len(citations) > 10:
            lines.append(f"\n*...and {len(citations) - 10} more results*")
        
        if not self._llm:
            lines.append("\n> 💡 *Set `GEMINI_API_KEY` in `.env` for AI-powered analysis of these results.*")
        
        return "\n\n".join(lines)
