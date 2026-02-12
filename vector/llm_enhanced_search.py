"""
LLM-Enhanced Hybrid Search
Uses local LLM to enhance query understanding and verify results
"""

import re
import json
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class LLMEnhancedSearch:
    """
    Combines vector search with LLM query enhancement and result verification
    """
    
    def __init__(self, vector_index, llm_loader=None):
        """
        Initialize LLM-enhanced search
        
        Args:
            vector_index: VectorIndexBuilder instance
            llm_loader: Optional LocalLLMLoader instance (will create if None)
        """
        self.vector_index = vector_index
        
        # Detect hardware capabilities
        try:
            from utils.hardware_detector import get_capabilities
            self.hw_caps = get_capabilities()
            logger.info(f"LLM search using: {self.hw_caps.device_name}")
        except Exception as e:
            logger.warning(f"Hardware detection failed: {e}")
            self.hw_caps = None
        
        # Load LLM if not provided (hardware-aware)
        if llm_loader is None:
            try:
                from models.llm_loader import LocalLLM
                # LocalLLM now auto-detects hardware
                self.llm = LocalLLM(
                    model_path="models/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
                    backend="llama_cpp"
                )
                logger.info("Loaded local LLM for query enhancement (hardware-aware)")
            except Exception as e:
                logger.warning(f"Could not load LLM: {e}. Falling back to pattern matching.")
                self.llm = None
        else:
            self.llm = llm_loader
    
    def search(self, 
               query: str, 
               top_k: int = 10,
               case_ids: Optional[List[str]] = None,
               verify_results: bool = True) -> List[Dict]:
        """
        LLM-enhanced search with query optimization and result verification
        
        Args:
            query: Natural language search query
            top_k: Number of results to return
            case_ids: Filter by specific case IDs
            verify_results: Use LLM to verify each result (slower but more accurate)
            
        Returns:
            List of verified matching documents
        """
        # Step 1: Use LLM to enhance and structure the query
        enhanced_query, filters = self._enhance_query_with_llm(query)
        
        logger.info(f"Original query: {query}")
        logger.info(f"Enhanced query: {enhanced_query}")
        logger.info(f"Extracted filters: {filters}")
        
        # Step 2: Perform vector search with broader results
        search_k = top_k * 3 if verify_results else top_k
        initial_results = self.vector_index.search(enhanced_query, search_k, case_ids)
        
        # Step 3: Apply filter-based pre-filtering
        filtered_results = self._apply_filters(initial_results, filters)
        
        logger.info(f"Vector search returned {len(initial_results)} results, {len(filtered_results)} after filtering")
        
        # Step 4: Use LLM to verify results (if enabled)
        if verify_results and self.llm and filtered_results:
            verified_results = self._verify_results_with_llm(query, filtered_results, top_k)
            logger.info(f"LLM verification: {len(verified_results)} results passed")
            return verified_results
        
        return filtered_results[:top_k]
    
    def _enhance_query_with_llm(self, query: str) -> Tuple[str, Dict]:
        """
        Use LLM to enhance query and extract structured filters
        
        Args:
            query: User's natural language query
            
        Returns:
            Tuple of (enhanced_query, filters_dict)
        """
        if not self.llm:
            # Fallback to pattern-based extraction
            return query, self._extract_filters_pattern_based(query)
        
        prompt = f"""You are a search query optimizer for forensic data analysis. 
Your task is to analyze the user's query and extract:
1. A clean search query optimized for semantic vector search
2. Structured filters for exact matching

User Query: "{query}"

Respond in JSON format:
{{
    "search_query": "optimized query for semantic search",
    "filters": {{
        "phone_suffix": "digits" or null,
        "phone_prefix": "digits with +" or null,
        "phone_contains": "digits" or null,
        "call_type": "Incoming/Outgoing/Missed" or null,
        "date_after": "YYYY-MM-DD" or null,
        "date_before": "YYYY-MM-DD" or null,
        "duration_min": seconds as int or null,
        "duration_max": seconds as int or null,
        "location": "location name" or null,
        "message_contains": "text" or null
    }}
}}

Examples:
Query: "calls ending with number 54"
Response: {{"search_query": "phone calls", "filters": {{"phone_suffix": "54"}}}}

Query: "incoming calls from Mumbai longer than 10 minutes"
Response: {{"search_query": "phone calls Mumbai", "filters": {{"call_type": "Incoming", "location": "Mumbai", "duration_min": 600}}}}

Query: "messages mentioning bitcoin after 2024-05-01"
Response: {{"search_query": "messages bitcoin cryptocurrency", "filters": {{"message_contains": "bitcoin", "date_after": "2024-05-01"}}}}

Now process the user's query and respond with ONLY the JSON object:"""

        try:
            response = self.llm.generate(prompt, max_tokens=300, temperature=0.1)
            
            # Parse JSON response
            # Extract JSON from response (handle potential extra text)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                enhanced_query = result.get('search_query', query)
                filters = result.get('filters', {})
                
                # Clean up null values
                filters = {k: v for k, v in filters.items() if v is not None}
                
                return enhanced_query, filters
            else:
                logger.warning("Could not parse LLM response, using fallback")
                return query, self._extract_filters_pattern_based(query)
                
        except Exception as e:
            logger.error(f"LLM query enhancement failed: {e}")
            return query, self._extract_filters_pattern_based(query)
    
    def _extract_filters_pattern_based(self, query: str) -> Dict:
        """Fallback pattern-based filter extraction"""
        filters = {}
        query_lower = query.lower()
        
        # Phone patterns
        if 'ending with' in query_lower or 'ends with' in query_lower:
            match = re.search(r'ending\s+(?:with|in)\s+(?:number\s+)?(\d+)', query_lower)
            if match:
                filters['phone_suffix'] = match.group(1)
        
        if 'starting with' in query_lower or 'starts with' in query_lower:
            match = re.search(r'(?:starting|beginning)\s+with\s+(?:number\s+)?(\+?\d+)', query_lower)
            if match:
                filters['phone_prefix'] = match.group(1)
        
        # Call type
        if 'incoming' in query_lower:
            filters['call_type'] = 'Incoming'
        elif 'outgoing' in query_lower:
            filters['call_type'] = 'Outgoing'
        elif 'missed' in query_lower:
            filters['call_type'] = 'Missed'
        
        # Duration
        if 'longer than' in query_lower:
            match = re.search(r'longer\s+than\s+(\d+)\s*(min|minute|sec|second)?', query_lower)
            if match:
                duration = int(match.group(1))
                if 'min' in query_lower:
                    duration *= 60
                filters['duration_min'] = duration
        
        return filters
    
    def _apply_filters(self, results: List[Dict], filters: Dict) -> List[Dict]:
        """Apply extracted filters to results"""
        if not filters:
            return results
        
        filtered = []
        for result in results:
            if self._matches_filters(result, filters):
                filtered.append(result)
        
        return filtered
    
    def _matches_filters(self, result: Dict, filters: Dict) -> bool:
        """Check if result matches all filters"""
        metadata = result.get('metadata', {})
        
        # Phone suffix
        if 'phone_suffix' in filters:
            suffix = filters['phone_suffix']
            phone_fields = [
                str(metadata.get('caller', '')),
                str(metadata.get('receiver', '')),
                str(metadata.get('phone', ''))
            ]
            if not any(phone.endswith(suffix) for phone in phone_fields if phone):
                return False
        
        # Phone prefix
        if 'phone_prefix' in filters:
            prefix = filters['phone_prefix']
            phone_fields = [
                str(metadata.get('caller', '')),
                str(metadata.get('receiver', '')),
                str(metadata.get('phone', ''))
            ]
            if not any(phone.startswith(prefix) for phone in phone_fields if phone):
                return False
        
        # Phone contains
        if 'phone_contains' in filters:
            substring = filters['phone_contains']
            phone_fields = [
                str(metadata.get('caller', '')),
                str(metadata.get('receiver', '')),
                str(metadata.get('phone', ''))
            ]
            if not any(substring in phone for phone in phone_fields if phone):
                return False
        
        # Call type
        if 'call_type' in filters:
            if metadata.get('call_type') != filters['call_type']:
                return False
        
        # Duration
        if 'duration_min' in filters:
            duration = metadata.get('duration_seconds', 0) or metadata.get('duration', 0)
            if duration < filters['duration_min']:
                return False
        
        if 'duration_max' in filters:
            duration = metadata.get('duration_seconds', 0) or metadata.get('duration', 0)
            if duration > filters['duration_max']:
                return False
        
        # Date range
        if 'date_after' in filters or 'date_before' in filters:
            timestamp = metadata.get('timestamp', '')
            if timestamp:
                try:
                    date_str = timestamp.split()[0]
                    if 'date_after' in filters and date_str < filters['date_after']:
                        return False
                    if 'date_before' in filters and date_str > filters['date_before']:
                        return False
                except:
                    pass
        
        # Location
        if 'location' in filters:
            location = metadata.get('location', '').lower()
            if filters['location'].lower() not in location:
                return False
        
        # Message content
        if 'message_contains' in filters:
            text = metadata.get('text', '').lower()
            if filters['message_contains'].lower() not in text:
                return False
        
        return True
    
    def _verify_results_with_llm(self, 
                                  original_query: str, 
                                  results: List[Dict], 
                                  top_k: int) -> List[Dict]:
        """
        Use LLM to verify each result matches the original query
        
        Args:
            original_query: User's original query
            results: Filtered results from vector search
            top_k: Maximum results to return
            
        Returns:
            LLM-verified results
        """
        if not self.llm:
            return results
        
        verified_results = []
        
        for result in results:
            if len(verified_results) >= top_k:
                break
            
            # Create concise representation of result
            metadata = result.get('metadata', {})
            content = result.get('content', '')
            
            # Build result summary
            result_summary = self._build_result_summary(metadata, content)
            
            # Ask LLM to verify
            prompt = f"""Does this record match the user's query?

User Query: "{original_query}"

Record:
{result_summary}

Answer with ONLY "YES" or "NO":"""

            try:
                response = self.llm.generate(prompt, max_tokens=10, temperature=0.0)
                response_clean = response.strip().upper()
                
                if 'YES' in response_clean:
                    # Boost score for LLM-verified results
                    result['score'] = result.get('score', 0) * 1.5
                    result['llm_verified'] = True
                    verified_results.append(result)
                    logger.debug(f"LLM verified: {result_summary[:50]}...")
                else:
                    logger.debug(f"LLM rejected: {result_summary[:50]}...")
                    
            except Exception as e:
                logger.error(f"LLM verification error: {e}")
                # On error, keep the result (fail-safe)
                verified_results.append(result)
        
        return verified_results
    
    def _build_result_summary(self, metadata: Dict, content: str) -> str:
        """Build a concise summary of a result for LLM verification"""
        parts = []
        
        # Add artifact type
        artifact_type = metadata.get('artifact_type', 'unknown')
        parts.append(f"Type: {artifact_type}")
        
        # Add key fields based on type
        if artifact_type == 'calls':
            if 'caller' in metadata:
                parts.append(f"Caller: {metadata['caller']}")
            if 'receiver' in metadata:
                parts.append(f"Receiver: {metadata['receiver']}")
            if 'call_type' in metadata:
                parts.append(f"Call Type: {metadata['call_type']}")
            if 'duration_seconds' in metadata:
                parts.append(f"Duration: {metadata['duration_seconds']}s")
            if 'location' in metadata:
                parts.append(f"Location: {metadata['location']}")
            if 'timestamp' in metadata:
                parts.append(f"Time: {metadata['timestamp']}")
        
        elif artifact_type == 'messages':
            if 'sender' in metadata:
                parts.append(f"From: {metadata['sender']}")
            if 'recipient' in metadata:
                parts.append(f"To: {metadata['recipient']}")
            if 'text' in metadata:
                text = metadata['text'][:100]
                parts.append(f"Text: {text}")
            if 'timestamp' in metadata:
                parts.append(f"Time: {metadata['timestamp']}")
        
        elif artifact_type == 'contacts':
            if 'name' in metadata:
                parts.append(f"Name: {metadata['name']}")
            if 'phone' in metadata:
                parts.append(f"Phone: {metadata['phone']}")
        
        # Add content if available and not redundant
        if content and content not in str(parts):
            parts.append(f"Content: {content[:100]}")
        
        return "\n".join(parts)


def create_llm_search(vector_index, llm_loader=None):
    """
    Factory function to create LLMEnhancedSearch
    
    Args:
        vector_index: VectorIndexBuilder instance
        llm_loader: Optional LocalLLMLoader instance
        
    Returns:
        LLMEnhancedSearch instance
    """
    return LLMEnhancedSearch(vector_index, llm_loader)


# Example usage
if __name__ == "__main__":
    from vector.index_builder import VectorIndexBuilder
    
    # Load index
    builder = VectorIndexBuilder(index_dir="data/indices")
    
    # Create LLM-enhanced search
    llm_search = LLMEnhancedSearch(builder)
    
    # Test queries
    test_queries = [
        "calls ending with number 54",
        "incoming calls longer than 30 minutes",
        "messages mentioning bitcoin or cryptocurrency",
        "calls from Mumbai after 2025-01-01",
    ]
    
    for query in test_queries:
        print(f"\n{'='*70}")
        print(f"Query: {query}")
        print(f"{'='*70}")
        
        results = llm_search.search(query, top_k=3, case_ids=["ADV_TEST_001"], verify_results=True)
        
        print(f"\nFound {len(results)} verified results:")
        for i, result in enumerate(results, 1):
            metadata = result.get('metadata', {})
            verified = result.get('llm_verified', False)
            score = result.get('score', 0)
            
            print(f"\n{i}. {'✓ LLM Verified' if verified else 'Pattern Match'} (score: {score:.4f})")
            print(f"   {result.get('content', '')[:80]}")
            if 'caller' in metadata:
                print(f"   Caller: {metadata['caller']} → {metadata.get('receiver', 'N/A')}")
            if 'timestamp' in metadata:
                print(f"   Time: {metadata['timestamp']}")