"""
Query Engine for UFDR Analysis Tool

Orchestrates the full query pipeline:
1. Checks query cache for instant results
2. Intent Classification: Decide between Tool (Structured) or Semantic Search
3. Execution:
   - Tool: Execute deterministic SQL (e.g. "contacts ending with 'a'")
   - Semantic: Rewritten Query + HyDE + Vector Search
4. LLM Reasoning: Generate final answer from retrieved context
"""

import os
import hashlib
import json
import logging
from typing import Optional, Callable
from pathlib import Path
from collections import OrderedDict

from dotenv import load_dotenv

from rag.retriever import HybridRetriever, reciprocal_rank_fusion
from rag.tools import lookup_contacts, search_messages, count_records, get_case_summary

logger = logging.getLogger(__name__)

# Load environment
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env")

from utils.retry import retry_with_backoff
from rag.llm_client import get_llm_client


class QueryCache:
    """
    LRU query result cache.
    Avoids redundant embedding computation and LLM calls.
    """
    
    def __init__(self, max_size: int = 200):
        self._cache: OrderedDict = OrderedDict()
        self._max_size = max_size
    
    @staticmethod
    def _make_key(query: str, case_ids: list[str], n_results: int) -> str:
        raw = f"{query.strip().lower()}|{'|'.join(sorted(case_ids))}|{n_results}"
        return hashlib.md5(raw.encode()).hexdigest()
    
    def get(self, query: str, case_ids: list[str], n_results: int) -> Optional[dict]:
        key = self._make_key(query, case_ids, n_results)
        if key in self._cache:
            self._cache.move_to_end(key)  # Mark as recently used
            logger.info("Query cache HIT")
            return self._cache[key]
        return None
    
    def put(self, query: str, case_ids: list[str], n_results: int, result: dict):
        key = self._make_key(query, case_ids, n_results)
        if len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)  # Evict oldest
        self._cache[key] = result
    
    def clear(self):
        self._cache.clear()


class QueryEngine:
    """
    Forensic Query Engine.
    
    Pipeline:
    1. Cache check
    2. Intent Classification (Tool vs Semantic)
    3. Execution (Tool SQL or Vector Search)
    4. LLM Synthesis
    """
    
    def __init__(self, db_path: Optional[str] = None):
        from rag import DB_PATH
        self._retriever = HybridRetriever(db_path or DB_PATH)
        self._llm = get_llm_client()
        self._cache = QueryCache(max_size=200)
    
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
        Execute a forensic query.
        """
        # Step 0: Check cache
        cached = self._cache.get(query_text, case_ids, n_results)
        if cached:
            return cached
            
        # Step 1: Intent Classification & Tool Selection
        # The LLM decides: Strict Tool Query OR Semantic Search?
        intent = self._classify_intent(query_text)
        
        tool_results = None
        search_query = query_text
        rewritten_query = ""
        
        if isinstance(intent, dict) and "tool" in intent:
            # A tool was selected! Execute it.
            logger.info(f"Intent classified as TOOL: {intent['tool']}")
            try:
                tool_results = self._execute_tool(intent["tool"], intent.get("args", {}), case_ids)
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                # Fallback to semantic search if tool fails
                search_query = query_text
        else:
            # Semantic search intent
            if isinstance(intent, str) and intent.strip():
                search_query = intent.strip()
                rewritten_query = search_query
                logger.info(f"Intent classified as SEMANTIC. Rewritten: '{search_query}'")

        # Step 2: Retrieval
        retrieval = {}
        
        if tool_results is not None:
            # We have structured results from a tool
            retrieval = {
                "ids": [f"tool_{i}" for i in range(len(tool_results))],
                "documents": [r.get("text", str(r)) for r in tool_results],
                "metadatas": tool_results,
                "scores": [1.0] * len(tool_results),
                "query_type": "exact"
            }
        else:
            # Semantic Retrieval Pipeline
            
            # HyDE Generation
            hyde_results = None
            if use_llm and self._llm:
                try:
                    hyde_doc = self._generate_hyde(query_text)
                    if hyde_doc and hyde_doc.strip():
                        hyde_results = self._retriever.retrieve(
                            hyde_doc.strip(), case_ids, n_results, data_type_filter
                        )
                except Exception as e:
                    logger.warning(f"HyDE generation failed: {e}")
            
            # Primary retrieval
            retrieval = self._retriever.retrieve(
                search_query, case_ids, n_results, data_type_filter
            )
            
            # Merge HyDE
            if hyde_results and hyde_results.get("ids"):
                merged = reciprocal_rank_fusion(
                    [retrieval, hyde_results], n_results=n_results
                )
                merged["query_type"] = retrieval.get("query_type", "semantic")
                retrieval = merged

        # Step 3: Build citations
        citations = []
        for i, (doc, meta) in enumerate(zip(
            retrieval.get("documents", []),
            retrieval.get("metadatas", [])
        )):
            citations.append({
                "rank": i + 1,
                "text": doc,
                "data_type": meta.get("data_type", "unknown"),
                "case_id": meta.get("case_id", ""),
                "metadata": meta,
            })
        
        # Step 4: LLM Synthesis
        answer = ""
        llm_used = False
        
        if use_llm and self._llm and citations:
            try:
                answer = self._generate_answer(query_text, citations, streaming)
                llm_used = True
            except Exception as e:
                logger.warning(f"LLM reasoning failed: {e}")
                answer = self._format_raw_answer(query_text, citations, retrieval.get("query_type", ""))
        else:
            answer = self._format_raw_answer(query_text, citations, retrieval.get("query_type", ""))
            
        result = {
            "answer": answer,
            "citations": citations,
            "query_type": retrieval.get("query_type", "semantic"),
            "llm_used": llm_used,
            "rewritten_query": rewritten_query,
        }
        
        # Cache the result
        self._cache.put(query_text, case_ids, n_results, result)
        
        return result

    def _execute_tool(self, tool_name: str, args: dict, case_ids: list) -> Optional[list]:
        """Execute a selected forensic tool."""
        if tool_name == "lookup_contacts":
            return lookup_contacts(case_ids, **args)
        elif tool_name == "search_messages":
            return search_messages(case_ids, **args)
        elif tool_name == "count_records":
            res = count_records(case_ids, **args)
            return [res] if "error" not in res else []
        elif tool_name == "get_case_summary":
            return get_case_summary(case_ids)
        return None

    def _classify_intent(self, query: str) -> str | dict:
        """
        Decide: Semantic Search OR Structured Tool?
        Returns:
            - str: Rewritten query (for semantic search)
            - dict: {'tool': 'name', 'args': {...}} (for tool execution)
        """
        provider, client = self._llm
        
        prompt = f"""You are a Forensic Query Planner.
Your goal is to choose the best strategy to answer the user's request.

Available Tools (for precise, structured queries):
1. lookup_contacts(name_pattern: str, phone_pattern: str)
   - Use for: "contacts ending with X", "find phone 1234", "list all contacts"
   - Patterns: Use SQL LIKE syntax (% for wildcard). E.g. name_pattern="%a" (ends with a).
2. search_messages(keyword: str, sender: str)
   - Use for: "messages from Mom", "text about 'bomb'"
3. count_records(record_type: str)
   - Use for: "how many messages", "count calls"
   - record_type: 'message', 'call', 'contact', 'location'

Strategy:
- If the query requires EXACT MATCHING (e.g. specific substring, phone number), COUNTING, or specific FILTERING: output a JSON tool call.
- If the query is VAGUE, SEMANTIC ("suspicious chats", "summary of events"): output a plain text string (a rewritten search query).

User Query: "{query}"

Output (JSON for tool, or plain text for semantic):"""

        try:
            if provider == "gemini":
                response = client.generate_content(prompt)
                text = response.text.strip()
            elif provider in ("openai", "openrouter"):
                 extra = {}
                 if provider == "openrouter":
                    extra["extra_headers"] = {
                        "HTTP-Referer": "https://github.com/kartikay/ufdr-analysis-tool",
                        "X-Title": "UFDR Analysis Tool",
                    }
                 response = client.chat.completions.create(
                    model="google/gemini-2.0-flash-001" if provider == "openrouter" else "gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150,
                    **extra
                 )
                 text = response.choices[0].message.content.strip()
            
            # Heuristic to detect JSON tool call
            if "{" in text and "}" in text:
                # Extract potential JSON block
                start = text.find("{")
                end = text.rfind("}") + 1
                json_str = text[start:end]
                try:
                    return json.loads(json_str)
                except:
                    pass
            
            return text
            
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return query  # Fallback to original
    
    def _generate_hyde(self, query: str) -> str:
        """HyDE generation (same as before)."""
        provider, client = self._llm
        prompt = f"""Generate a short example forensic database record that would be the perfect answer to this question.
Include realistic but fictional names, phone numbers, timestamps, and details.
Keep it under 100 words. Output ONLY the record text, no explanation.

Question: {query}
Example record:"""
        try:
            if provider == "gemini":
                response = client.generate_content(prompt)
                return response.text.strip()
            elif provider in ("openai", "openrouter"):
                extra = {}
                if provider == "openrouter":
                    extra["extra_headers"] = { "HTTP-Referer": "https://github.com/kartikay/ufdr-analysis-tool" }
                response = client.chat.completions.create(
                    model="google/gemini-2.0-flash-001" if provider == "openrouter" else "gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    **extra
                )
                return response.choices[0].message.content.strip()
        except Exception:
            pass
        return ""

    def _generate_answer(self, query: str, citations: list, streaming: bool) -> str:
        """Generate final answer using LLM."""
        provider, client = self._llm
        
        context = "\n".join([f"[{c['rank']}] {c['text']}" for c in citations[:15]])
        
        prompt = f"""You are a digital forensics expert assistant.
Answer the user's question based strictly on the provided evidence.

QUERY: {query}

EVIDENCE:
{context}

INSTRUCTIONS:
- Answer directly and concisely.
- Cite your sources using [1], [2], etc.
- If the evidence supports a count or list, summarize it clearly.
- If the evidence is insufficient, state that clearly.
- Do NOT make up information.

ANSWER:"""

        if provider == "gemini":
            response = client.generate_content(prompt)
            return response.text.strip()
        elif provider in ("openai", "openrouter"):
            extra = {}
            if provider == "openrouter":
                    extra["extra_headers"] = { "HTTP-Referer": "https://github.com/kartikay/ufdr-analysis-tool" }
            response = client.chat.completions.create(
                model="google/gemini-2.0-flash-001" if provider == "openrouter" else "gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                **extra
            )
            return response.choices[0].message.content.strip()
        return ""

    def _format_raw_answer(self, query: str, citations: list, query_type: str) -> str:
        """Fallback answer formatting."""
        if not citations:
            return "No relevant evidence found for this query."
        return f"Found {len(citations)} records relevant to your query. See the evidence tables below."
