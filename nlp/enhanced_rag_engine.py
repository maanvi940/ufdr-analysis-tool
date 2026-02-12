"""
Enhanced RAG Engine with Intent Detection and Exact Matching
Phase 0 Implementation: Adds pattern-based exact search before semantic RAG
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional
import time

# Import intent detector
from nlp.query_intent_detector import QueryIntentDetector, QueryIntent

# Import original RAG engine
from nlp.rag_engine import RAGEngine, RAGResponse

logger = logging.getLogger(__name__)


class ExactPatternSearcher:
    """Fast exact pattern matching for phone numbers"""
    
    def __init__(self, parsed_data_dir: str = "data/parsed"):
        self.parsed_data_dir = Path(parsed_data_dir)
    
    def search_phone_suffix(self, suffix: str, case_ids: Optional[List[str]] = None) -> List[Dict]:
        """
        Search for phone numbers ending with specific suffix
        
        Args:
            suffix: Suffix digits to match
            case_ids: Optional list of case IDs to filter
            
        Returns:
            List of matching artifacts with high confidence
        """
        results = []
        pattern = re.compile(rf'{re.escape(suffix)}$')
        
        # Determine which cases to search
        if case_ids:
            case_dirs = [self.parsed_data_dir / cid for cid in case_ids]
        else:
            case_dirs = [d for d in self.parsed_data_dir.iterdir() if d.is_dir()]
        
        for case_dir in case_dirs:
            if not case_dir.exists():
                continue
            
            # Search all JSON/JSONL files in case
            for json_file in case_dir.rglob('*.json*'):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        # Handle both JSON and JSONL
                        if json_file.suffix == '.jsonl':
                            for line_num, line in enumerate(f, 1):
                                if line.strip():
                                    artifact = json.loads(line)
                                    match = self._check_phone_match(artifact, pattern)
                                    if match:
                                        results.append({
                                            'case_id': case_dir.name,
                                            'source_file': str(json_file.relative_to(self.parsed_data_dir)),
                                            'artifact': artifact,
                                            'match_type': 'phone_suffix',
                                            'match_value': match,
                                            'line_number': line_num,
                                            'score': 0.95,  # High confidence for exact match
                                            'content': self._extract_content(artifact, match)
                                        })
                        else:
                            data = json.load(f)
                            # Handle both single objects and arrays
                            artifacts = data if isinstance(data, list) else [data]
                            
                            for idx, artifact in enumerate(artifacts):
                                match = self._check_phone_match(artifact, pattern)
                                if match:
                                    results.append({
                                        'case_id': case_dir.name,
                                        'source_file': str(json_file.relative_to(self.parsed_data_dir)),
                                        'artifact': artifact,
                                        'match_type': 'phone_suffix',
                                        'match_value': match,
                                        'artifact_index': idx,
                                        'score': 0.95,
                                        'content': self._extract_content(artifact, match)
                                    })
                
                except Exception as e:
                    logger.warning(f"Error reading {json_file}: {e}")
                    continue
        
        logger.info(f"Exact suffix search found {len(results)} matches for suffix '{suffix}'")
        return results
    
    def search_phone_prefix(self, prefix: str, case_ids: Optional[List[str]] = None) -> List[Dict]:
        """Search for phone numbers starting with specific prefix"""
        results = []
        pattern = re.compile(rf'^{re.escape(prefix)}')
        
        case_dirs = [self.parsed_data_dir / cid for cid in case_ids] if case_ids else \
                    [d for d in self.parsed_data_dir.iterdir() if d.is_dir()]
        
        for case_dir in case_dirs:
            if not case_dir.exists():
                continue
            
            for json_file in case_dir.rglob('*.json*'):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        if json_file.suffix == '.jsonl':
                            for line_num, line in enumerate(f, 1):
                                if line.strip():
                                    artifact = json.loads(line)
                                    match = self._check_phone_match(artifact, pattern)
                                    if match:
                                        results.append({
                                            'case_id': case_dir.name,
                                            'source_file': str(json_file.relative_to(self.parsed_data_dir)),
                                            'artifact': artifact,
                                            'match_type': 'phone_prefix',
                                            'match_value': match,
                                            'line_number': line_num,
                                            'score': 0.95,
                                            'content': self._extract_content(artifact, match)
                                        })
                        else:
                            data = json.load(f)
                            artifacts = data if isinstance(data, list) else [data]
                            
                            for idx, artifact in enumerate(artifacts):
                                match = self._check_phone_match(artifact, pattern)
                                if match:
                                    results.append({
                                        'case_id': case_dir.name,
                                        'source_file': str(json_file.relative_to(self.parsed_data_dir)),
                                        'artifact': artifact,
                                        'match_type': 'phone_prefix',
                                        'match_value': match,
                                        'artifact_index': idx,
                                        'score': 0.95,
                                        'content': self._extract_content(artifact, match)
                                    })
                
                except Exception as e:
                    logger.warning(f"Error reading {json_file}: {e}")
                    continue
        
        logger.info(f"Exact prefix search found {len(results)} matches for prefix '{prefix}'")
        return results
    
    def search_phone_contains(self, substring: str, case_ids: Optional[List[str]] = None) -> List[Dict]:
        """Search for phone numbers containing specific substring"""
        results = []
        pattern = re.compile(re.escape(substring))
        
        case_dirs = [self.parsed_data_dir / cid for cid in case_ids] if case_ids else \
                    [d for d in self.parsed_data_dir.iterdir() if d.is_dir()]
        
        for case_dir in case_dirs:
            if not case_dir.exists():
                continue
            
            for json_file in case_dir.rglob('*.json*'):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        if json_file.suffix == '.jsonl':
                            for line_num, line in enumerate(f, 1):
                                if line.strip():
                                    artifact = json.loads(line)
                                    match = self._check_phone_match(artifact, pattern)
                                    if match:
                                        results.append({
                                            'case_id': case_dir.name,
                                            'source_file': str(json_file.relative_to(self.parsed_data_dir)),
                                            'artifact': artifact,
                                            'match_type': 'phone_contains',
                                            'match_value': match,
                                            'line_number': line_num,
                                            'score': 0.90,
                                            'content': self._extract_content(artifact, match)
                                        })
                        else:
                            data = json.load(f)
                            artifacts = data if isinstance(data, list) else [data]
                            
                            for idx, artifact in enumerate(artifacts):
                                match = self._check_phone_match(artifact, pattern)
                                if match:
                                    results.append({
                                        'case_id': case_dir.name,
                                        'source_file': str(json_file.relative_to(self.parsed_data_dir)),
                                        'artifact': artifact,
                                        'match_type': 'phone_contains',
                                        'match_value': match,
                                        'artifact_index': idx,
                                        'score': 0.90,
                                        'content': self._extract_content(artifact, match)
                                    })
                
                except Exception as e:
                    logger.warning(f"Error reading {json_file}: {e}")
                    continue
        
        logger.info(f"Contains search found {len(results)} matches for substring '{substring}'")
        return results
    
    def _check_phone_match(self, artifact: Dict, pattern: re.Pattern) -> Optional[str]:
        """Check if artifact contains a phone number matching the pattern"""
        # Check common phone fields
        phone_fields = ['sender', 'receiver', 'phone', 'from', 'to', 'number', 'contact']
        
        # Check metadata
        metadata = artifact.get('metadata', {})
        for field in phone_fields:
            value = metadata.get(field) or artifact.get(field)
            if value:
                digits = self._normalize_phone(str(value))
                if digits and pattern.search(digits):
                    return value
        
        # Check nested structures
        for key, val in artifact.items():
            if isinstance(val, dict):
                for field in phone_fields:
                    value = val.get(field)
                    if value:
                        digits = self._normalize_phone(str(value))
                        if digits and pattern.search(digits):
                            return value
        
        return None
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone to digits only"""
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        
        # Remove leading country code (heuristic: if starts with 91 and length > 10)
        if digits.startswith('91') and len(digits) > 10:
            digits = digits[2:]  # Keep subscriber number
        elif digits.startswith('1') and len(digits) == 11:
            digits = digits[1:]  # US/Canada
        
        return digits
    
    def _extract_content(self, artifact: Dict, matched_phone: str) -> str:
        """Extract meaningful content from artifact"""
        # Try to get message content
        content = artifact.get('content') or artifact.get('message') or artifact.get('text')
        
        if content:
            return f"Phone: {matched_phone} | Content: {content[:200]}"
        
        # Fallback to metadata summary
        metadata = artifact.get('metadata', {})
        timestamp = metadata.get('timestamp') or metadata.get('date') or 'Unknown time'
        artifact_type = artifact.get('type') or metadata.get('artifact_type') or 'Unknown'
        
        return f"Phone: {matched_phone} | Type: {artifact_type} | Time: {timestamp}"


class EnhancedRAGEngine:
    """Enhanced RAG with intent detection and hybrid retrieval"""
    
    def __init__(self,
                 llm_model_path: str = "infra/models/llm/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
                 vector_index_dir: str = "data/indices",
                 parsed_data_dir: str = "data/parsed",
                 model_type: str = "gguf"):
        
        # Initialize intent detector
        self.intent_detector = QueryIntentDetector()
        
        # Initialize exact searcher
        self.exact_searcher = ExactPatternSearcher(parsed_data_dir)
        
        # Initialize original RAG engine
        self.rag_engine = RAGEngine(llm_model_path, vector_index_dir, model_type)
        
        logger.info("Enhanced RAG Engine initialized with intent detection and exact matching")
    
    def query(self,
             question: str,
             case_ids: Optional[List[str]] = None,
             top_k: int = 10,
             require_citations: bool = True,
             force_semantic: bool = False) -> RAGResponse:
        """
        Enhanced query with intent detection and hybrid retrieval
        
        Args:
            question: Natural language query
            case_ids: Filter to specific cases
            top_k: Number of results
            require_citations: Enforce citations
            force_semantic: Skip intent detection, use semantic only
            
        Returns:
            RAGResponse with answer and citations
        """
        time.time()
        
        # Step 1: Detect query intent
        if not force_semantic:
            intent_result = self.intent_detector.detect(question)
            intent = intent_result['intent']
            confidence = intent_result['confidence']
            params = intent_result['parameters']
            
            logger.info(f"Query intent: {intent.value} (confidence: {confidence:.2%})")
            
            # Step 2: Route to exact search for pattern queries
            if intent == QueryIntent.PHONE_SUFFIX:
                return self._handle_phone_suffix(params['suffix'], case_ids, question)
            
            elif intent == QueryIntent.PHONE_PREFIX:
                return self._handle_phone_prefix(params['prefix'], case_ids, question)
            
            elif intent == QueryIntent.PHONE_CONTAINS:
                return self._handle_phone_contains(params['contains'], case_ids, question)
            
            elif intent == QueryIntent.EXACT_NUMBER:
                return self._handle_exact_number(params['phone'], case_ids, question)
        
        # Step 3: Fall back to semantic RAG for other queries
        logger.info("Using semantic RAG for query")
        return self.rag_engine.query(question, case_ids, top_k, require_citations)
    
    def _handle_phone_suffix(self, suffix: str, case_ids: Optional[List[str]], question: str) -> RAGResponse:
        """Handle phone suffix query with exact matching"""
        start_time = time.time()
        logger.info(f"Executing exact suffix search for: {suffix}")
        
        # Run exact search
        exact_matches = self.exact_searcher.search_phone_suffix(suffix, case_ids)
        
        if not exact_matches:
            return RAGResponse(
                answer=f"No phone numbers ending with '{suffix}' were found in the specified case(s).",
                citations=[],
                confidence=0.95,  # High confidence in "not found"
                snippets=[],
                query_metadata={
                    'query': question,
                    'intent': 'phone_suffix',
                    'suffix': suffix,
                    'exact_matches': 0,
                    'processing_time': time.time() - start_time
                }
            )
        
        # Format results
        answer_parts = [f"Found {len(exact_matches)} phone number(s) ending with '{suffix}':"]
        citations = []
        
        for i, match in enumerate(exact_matches[:20], 1):  # Limit to 20 results
            phone = match['match_value']
            source = match['source_file']
            case_id = match['case_id']
            
            answer_parts.append(f"  {i}. {phone} (Case: {case_id}, Source: {source})")
            
            citations.append({
                'reference_id': str(i),
                'source_file': source,
                'case_id': case_id,
                'phone_number': phone,
                'artifact_type': match.get('artifact', {}).get('type', 'unknown')
            })
        
        if len(exact_matches) > 20:
            answer_parts.append(f"\n... and {len(exact_matches) - 20} more results.")
        
        return RAGResponse(
            answer="\n".join(answer_parts),
            citations=citations,
            confidence=0.95,  # High confidence for exact matches
            snippets=exact_matches[:10],
            query_metadata={
                'query': question,
                'intent': 'phone_suffix',
                'suffix': suffix,
                'exact_matches': len(exact_matches),
                'processing_time': time.time() - start_time,
                'method': 'exact_regex_search'
            }
        )
    
    def _handle_phone_prefix(self, prefix: str, case_ids: Optional[List[str]], question: str) -> RAGResponse:
        """Handle phone prefix query"""
        start_time = time.time()
        logger.info(f"Executing exact prefix search for: {prefix}")
        
        exact_matches = self.exact_searcher.search_phone_prefix(prefix, case_ids)
        
        if not exact_matches:
            return RAGResponse(
                answer=f"No phone numbers starting with '{prefix}' were found.",
                citations=[],
                confidence=0.95,
                snippets=[],
                query_metadata={
                    'query': question,
                    'intent': 'phone_prefix',
                    'prefix': prefix,
                    'exact_matches': 0,
                    'processing_time': time.time() - start_time
                }
            )
        
        answer_parts = [f"Found {len(exact_matches)} phone number(s) starting with '{prefix}':"]
        citations = []
        
        for i, match in enumerate(exact_matches[:20], 1):
            phone = match['match_value']
            source = match['source_file']
            case_id = match['case_id']
            
            answer_parts.append(f"  {i}. {phone} (Case: {case_id})")
            
            citations.append({
                'reference_id': str(i),
                'source_file': source,
                'case_id': case_id,
                'phone_number': phone
            })
        
        if len(exact_matches) > 20:
            answer_parts.append(f"\n... and {len(exact_matches) - 20} more results.")
        
        return RAGResponse(
            answer="\n".join(answer_parts),
            citations=citations,
            confidence=0.95,
            snippets=exact_matches[:10],
            query_metadata={
                'query': question,
                'intent': 'phone_prefix',
                'prefix': prefix,
                'exact_matches': len(exact_matches),
                'processing_time': time.time() - start_time,
                'method': 'exact_regex_search'
            }
        )
    
    def _handle_phone_contains(self, substring: str, case_ids: Optional[List[str]], question: str) -> RAGResponse:
        """Handle phone contains query"""
        start_time = time.time()
        logger.info(f"Executing contains search for: {substring}")
        
        exact_matches = self.exact_searcher.search_phone_contains(substring, case_ids)
        
        if not exact_matches:
            return RAGResponse(
                answer=f"No phone numbers containing '{substring}' were found.",
                citations=[],
                confidence=0.90,
                snippets=[],
                query_metadata={
                    'query': question,
                    'intent': 'phone_contains',
                    'substring': substring,
                    'exact_matches': 0,
                    'processing_time': time.time() - start_time
                }
            )
        
        answer_parts = [f"Found {len(exact_matches)} phone number(s) containing '{substring}':"]
        citations = []
        
        for i, match in enumerate(exact_matches[:20], 1):
            phone = match['match_value']
            source = match['source_file']
            case_id = match['case_id']
            
            answer_parts.append(f"  {i}. {phone} (Case: {case_id})")
            
            citations.append({
                'reference_id': str(i),
                'source_file': source,
                'case_id': case_id,
                'phone_number': phone
            })
        
        if len(exact_matches) > 20:
            answer_parts.append(f"\n... and {len(exact_matches) - 20} more results.")
        
        return RAGResponse(
            answer="\n".join(answer_parts),
            citations=citations,
            confidence=0.90,
            snippets=exact_matches[:10],
            query_metadata={
                'query': question,
                'intent': 'phone_contains',
                'substring': substring,
                'exact_matches': len(exact_matches),
                'processing_time': time.time() - start_time,
                'method': 'exact_regex_search'
            }
        )
    
    def _handle_exact_number(self, phone: str, case_ids: Optional[List[str]], question: str) -> RAGResponse:
        """Handle exact phone number query"""
        start_time = time.time()
        # Normalize and search for exact number
        digits = re.sub(r'\D', '', phone)
        
        # Search using contains (will match exact if normalized correctly)
        exact_matches = self.exact_searcher.search_phone_contains(digits[-10:], case_ids)
        
        if not exact_matches:
            return RAGResponse(
                answer=f"No records found for phone number {phone}.",
                citations=[],
                confidence=0.95,
                snippets=[],
                query_metadata={
                    'query': question,
                    'intent': 'exact_number',
                    'phone': phone,
                    'processing_time': time.time() - start_time
                }
            )
        
        answer_parts = [f"Found {len(exact_matches)} record(s) for phone number {phone}:"]
        citations = []
        
        for i, match in enumerate(exact_matches[:10], 1):
            content = match.get('content', 'No content')
            source = match['source_file']
            
            answer_parts.append(f"  [{i}] {content}")
            
            citations.append({
                'reference_id': str(i),
                'source_file': source,
                'case_id': match['case_id']
            })
        
        return RAGResponse(
            answer="\n".join(answer_parts),
            citations=citations,
            confidence=0.95,
            snippets=exact_matches[:10],
            query_metadata={
                'query': question,
                'intent': 'exact_number',
                'phone': phone,
                'exact_matches': len(exact_matches),
                'processing_time': time.time() - start_time,
                'method': 'exact_search'
            }
        )