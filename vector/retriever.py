"""
Vector Retriever
Provides semantic search capabilities for forensic artifacts
Includes query enhancement and result ranking
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import json

from .index_builder import VectorIndexBuilder

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorRetriever:
    """Retrieves relevant documents using vector similarity search"""
    
    def __init__(self, index_dir: str = "data/indices"):
        """
        Initialize retriever with existing index
        
        Args:
            index_dir: Directory containing FAISS index
        """
        self.index_builder = VectorIndexBuilder(index_dir=index_dir)
        self.crypto_pattern = re.compile(
            r'\b(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}\b|'  # Bitcoin
            r'\b0x[a-fA-F0-9]{40}\b|'  # Ethereum
            r'\b[LM3][a-km-zA-HJ-NP-Z1-9]{26,33}\b'  # Litecoin
        )
        self.foreign_phone_pattern = re.compile(
            r'\+(?!91)[0-9]{1,3}[0-9\s\-\(\)]+' # Non-Indian international numbers
        )
    
    def retrieve(self, 
                query: str, 
                top_k: int = 10,
                case_ids: Optional[List[str]] = None,
                boost_exact: bool = True) -> List[Dict]:
        """
        Retrieve relevant documents for a query
        
        Args:
            query: Search query
            top_k: Number of results to return
            case_ids: Filter to specific cases
            boost_exact: Boost exact pattern matches
            
        Returns:
            List of relevant documents with scores
        """
        # Get semantic search results
        results = self.index_builder.search(query, top_k * 2, case_ids)
        
        if boost_exact:
            # Apply boosting for exact matches
            results = self._boost_exact_matches(query, results)
        
        # Sort by score and return top_k
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results[:top_k]
    
    def _boost_exact_matches(self, query: str, results: List[Dict]) -> List[Dict]:
        """Apply boosting for exact pattern matches"""
        boosted_results = []
        
        # Check for special patterns in query
        has_crypto = bool(self.crypto_pattern.search(query))
        has_foreign_phone = bool(self.foreign_phone_pattern.search(query))
        query_lower = query.lower()
        
        for result in results:
            score = result['score']
            content = result.get('content', '').lower()
            
            # Boost if query terms appear exactly
            if query_lower in content:
                score *= 1.5
            
            # Boost crypto matches
            if has_crypto and self.crypto_pattern.search(content):
                score *= 2.0
            
            # Boost foreign phone matches
            if has_foreign_phone and self.foreign_phone_pattern.search(content):
                score *= 1.8
            
            # Boost based on artifact type relevance
            if 'crypto' in query_lower or 'bitcoin' in query_lower:
                if result.get('artifact_type') == 'messages':
                    score *= 1.3
            
            if 'call' in query_lower or 'phone' in query_lower:
                if result.get('artifact_type') == 'calls':
                    score *= 1.4
            
            result['score'] = score
            boosted_results.append(result)
        
        return boosted_results
    
    def hybrid_search(self,
                     query: str,
                     regex_patterns: Optional[List[str]] = None,
                     date_range: Optional[Tuple[str, str]] = None,
                     top_k: int = 10,
                     case_ids: Optional[List[str]] = None) -> List[Dict]:
        """
        Perform hybrid search combining semantic and pattern matching
        
        Args:
            query: Natural language query
            regex_patterns: Additional regex patterns to match
            date_range: Filter by date range (start, end) in ISO format
            top_k: Number of results
            case_ids: Filter to specific cases
            
        Returns:
            Filtered and ranked results
        """
        # Get semantic results
        results = self.retrieve(query, top_k * 3, case_ids)
        
        filtered_results = []
        
        for result in results:
            # Apply regex filters if provided
            if regex_patterns:
                content = result.get('content', '')
                if not any(re.search(pattern, content) for pattern in regex_patterns):
                    continue
            
            # Apply date range filter if provided
            if date_range:
                timestamp = result.get('metadata', {}).get('timestamp')
                if timestamp:
                    if not (date_range[0] <= timestamp <= date_range[1]):
                        continue
            
            filtered_results.append(result)
        
        return filtered_results[:top_k]
    
    def find_crypto_addresses(self, case_ids: Optional[List[str]] = None) -> List[Dict]:
        """Find all crypto addresses in the indexed data"""
        # Search with crypto-related terms
        queries = [
            "bitcoin address crypto",
            "ethereum wallet 0x",
            "cryptocurrency transfer payment"
        ]
        
        all_results = []
        seen_ids = set()
        
        for query in queries:
            results = self.retrieve(query, top_k=50, case_ids=case_ids)
            
            for result in results:
                # Check if content contains crypto pattern
                content = result.get('content', '')
                if self.crypto_pattern.search(content):
                    doc_id = result.get('doc_id')
                    if doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        # Extract the actual crypto addresses
                        addresses = self.crypto_pattern.findall(content)
                        result['crypto_addresses'] = addresses
                        all_results.append(result)
        
        return all_results
    
    def find_foreign_communications(self, case_ids: Optional[List[str]] = None) -> List[Dict]:
        """Find all communications with foreign numbers"""
        # Search for international communications
        queries = [
            "international call foreign number",
            "+1 +44 +86 +7",  # Common country codes
            "overseas communication"
        ]
        
        all_results = []
        seen_ids = set()
        
        for query in queries:
            results = self.retrieve(query, top_k=50, case_ids=case_ids)
            
            for result in results:
                content = result.get('content', '')
                if self.foreign_phone_pattern.search(content):
                    doc_id = result.get('doc_id')
                    if doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        # Extract foreign numbers
                        foreign_numbers = self.foreign_phone_pattern.findall(content)
                        result['foreign_numbers'] = foreign_numbers
                        all_results.append(result)
        
        return all_results
    
    def get_conversation_thread(self, 
                               thread_id: str,
                               case_id: str) -> List[Dict]:
        """Get all messages in a conversation thread"""
        # Search for thread ID
        query = f"thread conversation {thread_id}"
        results = self.retrieve(query, top_k=100, case_ids=[case_id])
        
        # Filter to only messages in the thread
        thread_messages = []
        for result in results:
            metadata = result.get('metadata', {})
            if metadata.get('thread_id') == thread_id:
                thread_messages.append(result)
        
        # Sort by timestamp
        thread_messages.sort(
            key=lambda x: x.get('metadata', {}).get('timestamp', ''),
        )
        
        return thread_messages
    
    def export_results(self, 
                      results: List[Dict],
                      output_file: str,
                      format: str = 'json'):
        """
        Export search results to file
        
        Args:
            results: Search results to export
            output_file: Output file path
            format: Export format (json, csv, txt)
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        
        elif format == 'csv':
            import csv
            
            if not results:
                return
            
            # Get all unique keys
            keys = set()
            for result in results:
                keys.update(result.keys())
                keys.update(result.get('metadata', {}).keys())
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=sorted(keys))
                writer.writeheader()
                
                for result in results:
                    # Flatten metadata
                    row = result.copy()
                    metadata = row.pop('metadata', {})
                    row.update(metadata)
                    writer.writerow(row)
        
        elif format == 'txt':
            with open(output_path, 'w', encoding='utf-8') as f:
                for i, result in enumerate(results, 1):
                    f.write(f"=== Result {i} ===\n")
                    f.write(f"Score: {result.get('score', 0):.4f}\n")
                    f.write(f"Type: {result.get('artifact_type', 'unknown')}\n")
                    f.write(f"Content: {result.get('content', '')}\n")
                    f.write(f"Source: {result.get('source_file', '')}\n")
                    f.write("\n")
        
        logger.info(f"Exported {len(results)} results to {output_path}")


def main():
    """CLI interface for retriever"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Search UFDR artifacts")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--case-id", help="Filter to specific case")
    parser.add_argument("--top-k", type=int, default=10, help="Number of results")
    parser.add_argument("--index-dir", default="data/indices", help="Index directory")
    parser.add_argument("--export", help="Export results to file")
    parser.add_argument("--format", choices=['json', 'csv', 'txt'], default='json',
                       help="Export format")
    parser.add_argument("--crypto", action="store_true", help="Find crypto addresses")
    parser.add_argument("--foreign", action="store_true", help="Find foreign communications")
    
    args = parser.parse_args()
    
    # Create retriever
    retriever = VectorRetriever(args.index_dir)
    
    try:
        case_ids = [args.case_id] if args.case_id else None
        
        if args.crypto:
            results = retriever.find_crypto_addresses(case_ids)
            print(f"\nFound {len(results)} artifacts with crypto addresses")
        elif args.foreign:
            results = retriever.find_foreign_communications(case_ids)
            print(f"\nFound {len(results)} artifacts with foreign communications")
        else:
            results = retriever.retrieve(args.query, args.top_k, case_ids)
            print(f"\nFound {len(results)} relevant results")
        
        # Display results
        for i, result in enumerate(results[:args.top_k], 1):
            print(f"\n--- Result {i} ---")
            print(f"Score: {result.get('score', 0):.4f}")
            print(f"Type: {result.get('artifact_type', 'unknown')}")
            print(f"Content: {result.get('content', '')[:200]}...")
            
            if 'crypto_addresses' in result:
                print(f"Crypto Addresses: {', '.join(result['crypto_addresses'])}")
            if 'foreign_numbers' in result:
                print(f"Foreign Numbers: {', '.join(result['foreign_numbers'])}")
        
        # Export if requested
        if args.export:
            retriever.export_results(results, args.export, args.format)
            print(f"\nResults exported to {args.export}")
        
    except Exception as e:
        print(f"\n✗ Search failed: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())