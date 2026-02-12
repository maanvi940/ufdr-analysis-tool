"""
Hybrid Search Module
Combines vector semantic search with exact pattern matching and filtering
"""

import re
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class HybridSearch:
    """
    Combines vector search with exact pattern matching for better results
    """
    
    def __init__(self, vector_index):
        """
        Initialize hybrid search
        
        Args:
            vector_index: VectorIndexBuilder instance
        """
        self.vector_index = vector_index
    
    def search(self, 
               query: str, 
               top_k: int = 10,
               case_ids: Optional[List[str]] = None,
               filters: Optional[Dict] = None) -> List[Dict]:
        """
        Hybrid search combining vector and exact matching
        
        Args:
            query: Natural language search query
            top_k: Number of results to return
            case_ids: Filter by specific case IDs
            filters: Additional filters (e.g., phone pattern, date range)
            
        Returns:
            List of matching documents with scores
        """
        # Parse query for patterns
        patterns = self._extract_patterns(query)
        
        # If query contains specific patterns, use filtered search
        if patterns:
            logger.info(f"Using hybrid search with patterns: {patterns}")
            return self._filtered_search(query, patterns, top_k, case_ids, filters)
        else:
            # Fall back to pure vector search
            logger.info("Using pure vector search (no patterns detected)")
            return self.vector_index.search(query, top_k, case_ids)
    
    def _extract_patterns(self, query: str) -> Dict[str, Any]:
        """
        Extract search patterns from natural language query
        
        Returns:
            Dictionary of detected patterns
        """
        patterns = {}
        query_lower = query.lower()
        
        # Phone number patterns
        if any(word in query_lower for word in ['ending with', 'ends with', 'ending in', 'ends in']):
            # Extract the digits after "ending with"
            match = re.search(r'ending\s+(?:with|in)\s+(?:number\s+)?(\d+)', query_lower)
            if match:
                patterns['phone_suffix'] = match.group(1)
        
        if any(word in query_lower for word in ['starting with', 'starts with', 'beginning with']):
            match = re.search(r'(?:starting|beginning)\s+with\s+(?:number\s+)?(\+?\d+)', query_lower)
            if match:
                patterns['phone_prefix'] = match.group(1)
        
        if 'contains' in query_lower or 'containing' in query_lower:
            match = re.search(r'contains?\s+(?:number\s+)?(\d+)', query_lower)
            if match:
                patterns['phone_contains'] = match.group(1)
        
        # Date patterns
        if 'after' in query_lower:
            match = re.search(r'after\s+(\d{4}-\d{2}-\d{2})', query_lower)
            if match:
                patterns['date_after'] = match.group(1)
        
        if 'before' in query_lower:
            match = re.search(r'before\s+(\d{4}-\d{2}-\d{2})', query_lower)
            if match:
                patterns['date_before'] = match.group(1)
        
        # Duration patterns
        if 'longer than' in query_lower or 'more than' in query_lower:
            match = re.search(r'(?:longer|more)\s+than\s+(\d+)\s*(?:seconds?|mins?|minutes?)?', query_lower)
            if match:
                duration = int(match.group(1))
                # Convert to seconds if minutes mentioned
                if 'min' in query_lower:
                    duration *= 60
                patterns['duration_min'] = duration
        
        if 'shorter than' in query_lower or 'less than' in query_lower:
            match = re.search(r'(?:shorter|less)\s+than\s+(\d+)\s*(?:seconds?|mins?|minutes?)?', query_lower)
            if match:
                duration = int(match.group(1))
                if 'min' in query_lower:
                    duration *= 60
                patterns['duration_max'] = duration
        
        # Location patterns
        if 'from' in query_lower and 'location' in query_lower:
            match = re.search(r'from\s+location\s+([A-Za-z\s]+?)(?:\s+|$)', query_lower)
            if match:
                patterns['location'] = match.group(1).strip()
        
        # Call type patterns
        if 'incoming' in query_lower:
            patterns['call_type'] = 'Incoming'
        elif 'outgoing' in query_lower:
            patterns['call_type'] = 'Outgoing'
        elif 'missed' in query_lower:
            patterns['call_type'] = 'Missed'
        
        return patterns
    
    def _filtered_search(self, 
                        query: str, 
                        patterns: Dict[str, Any],
                        top_k: int,
                        case_ids: Optional[List[str]],
                        extra_filters: Optional[Dict]) -> List[Dict]:
        """
        Perform filtered search using both vector and pattern matching
        
        Args:
            query: Natural language query
            patterns: Extracted patterns to match
            top_k: Number of results
            case_ids: Case IDs to filter
            extra_filters: Additional filter criteria
            
        Returns:
            Filtered and ranked results
        """
        # First, get broader vector search results
        initial_results = self.vector_index.search(query, top_k * 5, case_ids)
        
        # Apply pattern filters
        filtered_results = []
        for result in initial_results:
            if self._matches_patterns(result, patterns):
                filtered_results.append(result)
        
        # Apply additional filters
        if extra_filters:
            filtered_results = [r for r in filtered_results if self._matches_filters(r, extra_filters)]
        
        # Re-rank: boost exact matches
        for result in filtered_results:
            if self._is_exact_match(result, patterns):
                result['score'] = result.get('score', 0) * 2  # Boost exact matches
        
        # Sort by score
        filtered_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return filtered_results[:top_k]
    
    def _matches_patterns(self, result: Dict, patterns: Dict[str, Any]) -> bool:
        """
        Check if result matches all extracted patterns
        
        Args:
            result: Search result document
            patterns: Patterns to match
            
        Returns:
            True if all patterns match
        """
        metadata = result.get('metadata', {})
        
        # Phone suffix matching
        if 'phone_suffix' in patterns:
            suffix = patterns['phone_suffix']
            # Check caller/receiver/phone fields
            phone_fields = []
            if 'caller' in metadata:
                phone_fields.append(str(metadata['caller']))
            if 'receiver' in metadata:
                phone_fields.append(str(metadata['receiver']))
            if 'phone' in metadata:
                phone_fields.append(str(metadata['phone']))
            
            if not any(phone.endswith(suffix) for phone in phone_fields):
                return False
        
        # Phone prefix matching
        if 'phone_prefix' in patterns:
            prefix = patterns['phone_prefix']
            phone_fields = []
            if 'caller' in metadata:
                phone_fields.append(str(metadata['caller']))
            if 'receiver' in metadata:
                phone_fields.append(str(metadata['receiver']))
            if 'phone' in metadata:
                phone_fields.append(str(metadata['phone']))
            
            if not any(phone.startswith(prefix) for phone in phone_fields):
                return False
        
        # Phone contains matching
        if 'phone_contains' in patterns:
            substring = patterns['phone_contains']
            phone_fields = []
            if 'caller' in metadata:
                phone_fields.append(str(metadata['caller']))
            if 'receiver' in metadata:
                phone_fields.append(str(metadata['receiver']))
            if 'phone' in metadata:
                phone_fields.append(str(metadata['phone']))
            
            if not any(substring in phone for phone in phone_fields):
                return False
        
        # Date range matching
        if 'date_after' in patterns or 'date_before' in patterns:
            timestamp = metadata.get('timestamp', '')
            if timestamp:
                try:
                    result_date = timestamp.split()[0]  # Extract YYYY-MM-DD
                    if 'date_after' in patterns and result_date <= patterns['date_after']:
                        return False
                    if 'date_before' in patterns and result_date >= patterns['date_before']:
                        return False
                except:
                    pass
        
        # Duration matching
        if 'duration_min' in patterns:
            duration = metadata.get('duration_seconds', 0) or metadata.get('duration', 0)
            if duration < patterns['duration_min']:
                return False
        
        if 'duration_max' in patterns:
            duration = metadata.get('duration_seconds', 0) or metadata.get('duration', 0)
            if duration > patterns['duration_max']:
                return False
        
        # Location matching
        if 'location' in patterns:
            location = metadata.get('location', '').lower()
            if patterns['location'].lower() not in location:
                return False
        
        # Call type matching
        if 'call_type' in patterns:
            call_type = metadata.get('call_type', '')
            if call_type != patterns['call_type']:
                return False
        
        return True
    
    def _matches_filters(self, result: Dict, filters: Dict) -> bool:
        """Apply additional custom filters"""
        metadata = result.get('metadata', {})
        
        for key, value in filters.items():
            if key not in metadata:
                return False
            if isinstance(value, (list, tuple)):
                if metadata[key] not in value:
                    return False
            elif callable(value):
                if not value(metadata[key]):
                    return False
            else:
                if metadata[key] != value:
                    return False
        
        return True
    
    def _is_exact_match(self, result: Dict, patterns: Dict[str, Any]) -> bool:
        """
        Check if result is an exact match (for boosting)
        
        Returns:
            True if result exactly matches all patterns
        """
        # More strict matching for exact matches
        metadata = result.get('metadata', {})
        
        # For phone patterns, check if it's the only matching criteria
        if 'phone_suffix' in patterns:
            suffix = patterns['phone_suffix']
            phone_fields = []
            if 'caller' in metadata:
                phone_fields.append(str(metadata['caller']))
            if 'receiver' in metadata:
                phone_fields.append(str(metadata['receiver']))
            
            # Exact match if phone ends exactly with the pattern
            return any(phone.endswith(suffix) for phone in phone_fields)
        
        return False


def create_hybrid_search_from_index(index_builder) -> HybridSearch:
    """
    Factory function to create HybridSearch from existing index
    
    Args:
        index_builder: VectorIndexBuilder instance
        
    Returns:
        HybridSearch instance
    """
    return HybridSearch(index_builder)


# Example usage
if __name__ == "__main__":
    from vector.index_builder import VectorIndexBuilder
    
    # Load existing index
    builder = VectorIndexBuilder(index_dir="data/indices")
    
    # Create hybrid search
    hybrid = HybridSearch(builder)
    
    # Test queries
    test_queries = [
        "calls ending with number 54",
        "calls starting with +44",
        "calls longer than 30 minutes",
        "incoming calls from Mumbai",
        "messages containing bitcoin",
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        results = hybrid.search(query, top_k=5, case_ids=["ADV_TEST_001"])
        print(f"Found {len(results)} results")
        for i, result in enumerate(results, 1):
            metadata = result.get('metadata', {})
            print(f"{i}. {result.get('content', '')[:80]}... (score: {result.get('score', 0):.3f})")
            if 'caller' in metadata:
                print(f"   Caller: {metadata['caller']}")