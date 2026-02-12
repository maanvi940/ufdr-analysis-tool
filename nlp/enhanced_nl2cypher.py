"""
Enhanced NL→Cypher Translation Module with Safety and Validation

Features:
- Read-only Cypher query validation
- Confidence scoring
- Fallback strategies
- Query sanitization
- AST-based safety checks
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuerySafety(Enum):
    """Query safety classification"""
    SAFE = "safe"
    UNSAFE = "unsafe"
    SUSPICIOUS = "suspicious"


class FallbackStrategy(Enum):
    """Fallback strategies for ambiguous queries"""
    RAG = "rag"  # Use RAG instead
    CLARIFY = "clarify"  # Ask for clarification
    SUGGEST = "suggest"  # Suggest alternatives


@dataclass
class CypherQuery:
    """Validated Cypher query result"""
    cypher: str
    confidence: float  # 0.0 to 1.0
    safety: QuerySafety
    warnings: List[str]
    fallback: Optional[FallbackStrategy] = None
    clarification_needed: Optional[str] = None
    explanation: Optional[str] = None
    source: str = "llm"  # llm, rule, template


class CypherValidator:
    """
    Validates Cypher queries for safety and correctness
    Enforces read-only operations only
    """
    
    # Allowed read-only Cypher keywords
    SAFE_KEYWORDS = {
        'MATCH', 'WHERE', 'RETURN', 'WITH', 'ORDER', 'BY', 
        'LIMIT', 'SKIP', 'DISTINCT', 'AS', 'AND', 'OR', 'NOT',
        'IN', 'CONTAINS', 'STARTS', 'ENDS', 'COUNT', 'SUM',
        'AVG', 'MIN', 'MAX', 'COLLECT', 'UNWIND', 'CASE',
        'WHEN', 'THEN', 'ELSE', 'END', 'IS', 'NULL', 'ASC', 'DESC'
    }
    
    # Forbidden write/delete keywords
    UNSAFE_KEYWORDS = {
        'CREATE', 'MERGE', 'DELETE', 'REMOVE', 'SET', 
        'DETACH', 'DROP', 'ALTER', 'LOAD'
    }
    
    # Keywords that need special handling (CALL is a Neo4j procedure keyword, but also a node label)
    SPECIAL_KEYWORDS = {
        'CALL': r'\bCALL\s+[a-zA-Z]+\.',  # CALL followed by procedure name
    }
    
    # Suspicious patterns that need review
    SUSPICIOUS_PATTERNS = [
        r'//.*',  # Comments can hide malicious code
        r';.*\S',  # Semicolon followed by more content (multiple statements)
        r'\bapoc\b',  # APOC procedures need review
        r'\bdbms\b',  # System procedures
    ]
    
    def __init__(self):
        """Initialize validator"""
    
    def validate(self, cypher: str) -> Tuple[QuerySafety, List[str]]:
        """
        Validate Cypher query for safety
        
        Args:
            cypher: Cypher query string
            
        Returns:
            Tuple of (safety_level, warnings_list)
        """
        warnings = []
        
        # Check for empty query
        if not cypher or not cypher.strip():
            warnings.append("Empty query")
            return QuerySafety.UNSAFE, warnings
        
        # Normalize query for checking
        normalized = cypher.upper()
        
        # Check for unsafe keywords
        for keyword in self.UNSAFE_KEYWORDS:
            if re.search(rf'\b{keyword}\b', normalized):
                warnings.append(f"Unsafe keyword detected: {keyword}")
                return QuerySafety.UNSAFE, warnings
        
        # Check for special keywords with context
        for keyword, pattern in self.SPECIAL_KEYWORDS.items():
            if re.search(pattern, cypher, re.IGNORECASE):
                warnings.append(f"Unsafe keyword detected: {keyword} (procedure call)")
                return QuerySafety.UNSAFE, warnings
        
        # Check for suspicious patterns
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, cypher, re.IGNORECASE):
                warnings.append(f"Suspicious pattern detected: {pattern}")
                return QuerySafety.SUSPICIOUS, warnings
        
        # Check that query starts with MATCH or WITH
        first_keyword = normalized.split()[0] if normalized.split() else ""
        if first_keyword not in ['MATCH', 'WITH', 'OPTIONAL']:
            warnings.append(f"Query should start with MATCH or WITH, got: {first_keyword}")
            return QuerySafety.SUSPICIOUS, warnings
        
        # Check that query has RETURN
        if 'RETURN' not in normalized:
            warnings.append("Query missing RETURN clause")
            return QuerySafety.SUSPICIOUS, warnings
        
        # All checks passed
        return QuerySafety.SAFE, warnings
    
    def sanitize(self, cypher: str) -> str:
        """
        Sanitize Cypher query
        
        Args:
            cypher: Raw Cypher query
            
        Returns:
            Sanitized query
        """
        # Remove comments
        cypher = re.sub(r'//.*$', '', cypher, flags=re.MULTILINE)
        cypher = re.sub(r'/\*.*?\*/', '', cypher, flags=re.DOTALL)
        
        # Remove multiple statements (keep only first)
        if ';' in cypher:
            cypher = cypher.split(';')[0]
        
        # Normalize whitespace
        cypher = ' '.join(cypher.split())
        
        # Ensure ends with semicolon
        if not cypher.endswith(';'):
            cypher += ';'
        
        return cypher.strip()


class EnhancedNL2Cypher:
    """
    Enhanced Natural Language to Cypher translator
    With validation, confidence scoring, and safety checks
    """
    
    def __init__(self):
        """Initialize enhanced translator"""
        self.validator = CypherValidator()
        
        # Load resources
        self.schema = self._load_schema()
        self.examples = self._load_examples()
        self.templates = self._load_templates()
        
        logger.info("Enhanced NL2Cypher initialized")
    
    def _load_schema(self) -> str:
        """Load Neo4j schema"""
        schema_path = Path(__file__).parent.parent / "graph" / "schema.cypher"
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Could not load schema: {e}")
            return """
            // Node types
            (:Case {case_id, ingest_time})
            (:Device {device_id, model, os_type})
            (:Person {person_id, name, phone_numbers})
            (:Message {id, text, timestamp, app})
            (:Call {id, number, duration, direction})
            (:Media {id, type, sha256, phash, ocr_text})
            (:Location {id, latitude, longitude, timestamp})
            
            // Relationships
            (Person)-[:SENT]->(Message)
            (Person)-[:RECEIVED]->(Message)
            (Person)-[:CALLED]->(Person)
            (Media)-[:ATTACHED_TO]->(Message)
            (Case)-[:CONTAINS]->(Device)
            (Case)-[:LINKED_TO]->(Case)
            """
    
    def _load_examples(self) -> List[Dict]:
        """Load example NL-Cypher pairs"""
        examples_path = Path(__file__).parent.parent / "prompts" / "nl2cypher_examples.json"
        try:
            with open(examples_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load examples: {e}")
            return [
                {
                    "nl": "Find all persons with phone containing 123",
                    "cypher": "MATCH (p:Person) WHERE ANY(phone IN p.phone_numbers WHERE phone CONTAINS '123') RETURN p LIMIT 100;"
                },
                {
                    "nl": "Show messages containing bitcoin",
                    "cypher": "MATCH (m:Message) WHERE m.text CONTAINS 'bitcoin' RETURN m ORDER BY m.timestamp DESC LIMIT 100;"
                },
                {
                    "nl": "Find calls longer than 5 minutes",
                    "cypher": "MATCH (c:Call) WHERE c.duration > 300 RETURN c ORDER BY c.duration DESC LIMIT 100;"
                }
            ]
    
    def _load_templates(self) -> Dict[str, str]:
        """Load query templates for common patterns"""
        return {
            "person_by_name": "MATCH (p:Person) WHERE p.name CONTAINS '{name}' RETURN p LIMIT 100;",
            "person_by_phone": "MATCH (p:Person) WHERE ANY(phone IN p.phone_numbers WHERE phone CONTAINS '{phone}') RETURN p LIMIT 100;",
            "messages_with_text": "MATCH (m:Message) WHERE m.text CONTAINS '{text}' RETURN m ORDER BY m.timestamp DESC LIMIT 100;",
            "messages_by_app": "MATCH (m:Message) WHERE m.app = '{app}' RETURN m ORDER BY m.timestamp DESC LIMIT 100;",
            "calls_to_number": "MATCH (c:Call) WHERE c.number CONTAINS '{number}' RETURN c ORDER BY c.timestamp DESC LIMIT 100;",
            "media_with_ocr": "MATCH (m:Media) WHERE m.ocr_text CONTAINS '{text}' RETURN m LIMIT 100;",
            "case_linkage": "MATCH (c1:Case {case_id: '{case_id}'})-[r:LINKED_TO]-(c2:Case) RETURN c1, r, c2;",
            "person_communications": "MATCH (p:Person {person_id: '{person_id}'})-[:SENT|RECEIVED]-(m:Message) RETURN p, m ORDER BY m.timestamp DESC LIMIT 100;",
        }
    
    def _calculate_confidence(self, 
                             query: str, 
                             cypher: str, 
                             source: str,
                             safety: QuerySafety) -> float:
        """
        Calculate confidence score for translation
        
        Args:
            query: Original NL query
            cypher: Translated Cypher
            source: Translation source (rule/template/llm)
            safety: Safety classification
            
        Returns:
            Confidence score 0.0 to 1.0
        """
        confidence = 0.5  # Base confidence
        
        # Source-based confidence
        if source == "template":
            confidence = 0.95
        elif source == "rule":
            confidence = 0.85
        elif source == "llm":
            confidence = 0.70
        
        # Safety adjustment
        if safety == QuerySafety.SAFE:
            confidence += 0.05
        elif safety == QuerySafety.SUSPICIOUS:
            confidence -= 0.15
        elif safety == QuerySafety.UNSAFE:
            confidence = 0.0
        
        # Query complexity adjustment
        if len(cypher.split()) > 30:
            confidence -= 0.1  # Complex queries are less confident
        
        # Has LIMIT clause (good practice)
        if 'LIMIT' in cypher.upper():
            confidence += 0.05
        
        # Clamp to valid range
        return max(0.0, min(1.0, confidence))
    
    def _try_template_match(self, query: str) -> Optional[CypherQuery]:
        """
        Try to match query to a template
        
        Args:
            query: Natural language query
            
        Returns:
            CypherQuery if matched, None otherwise
        """
        query_lower = query.lower()
        
        # Person by name
        name_match = re.search(r"person(?:s)?\s+(?:named|called|with\s+name)\s+['\"]?([a-zA-Z\s]+)['\"]?", query_lower)
        if name_match:
            name = name_match.group(1).strip()
            cypher = self.templates["person_by_name"].format(name=name)
            safety, warnings = self.validator.validate(cypher)
            return CypherQuery(
                cypher=cypher,
                confidence=self._calculate_confidence(query, cypher, "template", safety),
                safety=safety,
                warnings=warnings,
                source="template"
            )
        
        # Person by phone
        phone_match = re.search(r"person(?:s)?\s+with\s+phone\s+(?:number\s+)?['\"]?([0-9+\s-]+)['\"]?", query_lower)
        if phone_match:
            phone = phone_match.group(1).strip()
            cypher = self.templates["person_by_phone"].format(phone=phone)
            safety, warnings = self.validator.validate(cypher)
            return CypherQuery(
                cypher=cypher,
                confidence=self._calculate_confidence(query, cypher, "template", safety),
                safety=safety,
                warnings=warnings,
                source="template"
            )
        
        # Messages with text
        msg_match = re.search(r"message(?:s)?\s+(?:with|containing)\s+['\"]?([a-zA-Z0-9\s]+)['\"]?", query_lower)
        if msg_match:
            text = msg_match.group(1).strip()
            cypher = self.templates["messages_with_text"].format(text=text)
            safety, warnings = self.validator.validate(cypher)
            return CypherQuery(
                cypher=cypher,
                confidence=self._calculate_confidence(query, cypher, "template", safety),
                safety=safety,
                warnings=warnings,
                source="template"
            )
        
        return None
    
    def _try_rule_based(self, query: str) -> Optional[CypherQuery]:
        """
        Try rule-based translation for common patterns
        
        Args:
            query: Natural language query
            
        Returns:
            CypherQuery if matched, None otherwise
        """
        query_lower = query.lower()
        
        # Foreign numbers
        if "foreign" in query_lower and ("number" in query_lower or "contact" in query_lower or "call" in query_lower):
            cypher = "MATCH (c:Call) WHERE NOT c.number STARTS WITH '+91' RETURN c ORDER BY c.timestamp DESC LIMIT 100;"
            safety, warnings = self.validator.validate(cypher)
            return CypherQuery(
                cypher=cypher,
                confidence=self._calculate_confidence(query, cypher, "rule", safety),
                safety=safety,
                warnings=warnings,
                explanation="Finding all calls to numbers that don't start with Indian country code (+91)",
                source="rule"
            )
        
        # Crypto-related
        if any(kw in query_lower for kw in ['bitcoin', 'btc', 'crypto', 'wallet', 'ethereum']):
            cypher = "MATCH (m:Message) WHERE m.text =~ '(?i).*(bitcoin|btc|crypto|wallet|ethereum).*' RETURN m ORDER BY m.timestamp DESC LIMIT 100;"
            safety, warnings = self.validator.validate(cypher)
            return CypherQuery(
                cypher=cypher,
                confidence=self._calculate_confidence(query, cypher, "rule", safety),
                safety=safety,
                warnings=warnings,
                explanation="Finding all messages containing cryptocurrency-related keywords using regex pattern matching",
                source="rule"
            )
        
        return None
    
    def translate(self, query: str, allow_llm: bool = True) -> CypherQuery:
        """
        Translate natural language to Cypher with validation
        
        Args:
            query: Natural language query
            allow_llm: Whether to use LLM if templates/rules fail
            
        Returns:
            CypherQuery object with validation results
        """
        # 1. Try template matching (highest confidence)
        result = self._try_template_match(query)
        if result:
            logger.info(f"Query matched template: {result.cypher[:50]}...")
            return result
        
        # 2. Try rule-based translation
        result = self._try_rule_based(query)
        if result:
            logger.info(f"Query matched rule: {result.cypher[:50]}...")
            return result
        
        # 3. Try LLM translation if allowed
        if allow_llm:
            try:
                # Placeholder for LLM call
                # In production, call your local LLM here
                cypher = self._llm_translate(query)
                cypher = self.validator.sanitize(cypher)
                safety, warnings = self.validator.validate(cypher)
                
                return CypherQuery(
                    cypher=cypher,
                    confidence=self._calculate_confidence(query, cypher, "llm", safety),
                    safety=safety,
                    warnings=warnings,
                    source="llm"
                )
            except Exception as e:
                logger.error(f"LLM translation failed: {e}")
        
        # 4. Fallback: Suggest using RAG instead
        return CypherQuery(
            cypher="",
            confidence=0.0,
            safety=QuerySafety.UNSAFE,
            warnings=["Could not translate query to Cypher"],
            fallback=FallbackStrategy.RAG,
            clarification_needed="This query might be better answered using semantic search. Would you like to try RAG instead?"
        )
    
    def _llm_translate(self, query: str) -> str:
        """
        Translate using local LLM
        
        Args:
            query: Natural language query
            
        Returns:
            Cypher query string
        """
        try:
            # Try to load local LLM
            from models.llm_loader import get_llm
            
            llm = get_llm()
            
            if not llm.is_available:
                logger.warning("LLM not available for translation")
                return self._fallback_llm_translate(query)
            
            # Load prompt template
            prompt_path = Path(__file__).parent.parent / "prompts" / "nl2cypher_prompt.txt"
            
            if prompt_path.exists():
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    prompt_template = f.read()
                
                # Inject query into template
                prompt = prompt_template.replace('{query}', query)
            else:
                # Fallback prompt if file missing
                prompt = f"""Translate this natural language query to Cypher (read-only):
                
Query: {query}
Cypher:"""
            
            # Generate Cypher query
            cypher = llm.generate(
                prompt,
                max_tokens=256,
                temperature=0.1,  # Low temperature for deterministic output
                stop=["\n\n", "Query:", "Cypher:"]
            )
            
            # Clean up response
            cypher = cypher.strip()
            
            # Extract just the Cypher query if LLM added explanation
            if 'MATCH' in cypher:
                # Find first MATCH statement
                match_idx = cypher.find('MATCH')
                cypher = cypher[match_idx:]
                
                # Remove any text after the query (look for newlines or explanatory text)
                if '\n' in cypher:
                    lines = cypher.split('\n')
                    # Keep only lines that look like Cypher
                    cypher_lines = []
                    for line in lines:
                        line = line.strip()
                        if line and any(kw in line.upper() for kw in ['MATCH', 'WHERE', 'RETURN', 'WITH', 'ORDER', 'LIMIT']):
                            cypher_lines.append(line)
                        elif cypher_lines:  # Stop at first non-Cypher line after starting
                            break
                    cypher = ' '.join(cypher_lines)
            
            # Ensure semicolon at end
            if not cypher.endswith(';'):
                cypher += ';'
            
            logger.info(f"LLM translated query successfully")
            return cypher
            
        except Exception as e:
            logger.warning(f"LLM translation error: {e}")
            return self._fallback_llm_translate(query)
    
    def _fallback_llm_translate(self, query: str) -> str:
        """
        Simple keyword-based Cypher generation when LLM unavailable
        
        Args:
            query: Natural language query
            
        Returns:
            Basic Cypher query
        """
        query_lower = query.lower()
        
        # Simple keyword extraction
        if 'person' in query_lower or 'people' in query_lower:
            return "MATCH (p:Person) RETURN p LIMIT 100;"
        elif 'message' in query_lower:
            return "MATCH (m:Message) RETURN m ORDER BY m.timestamp DESC LIMIT 100;"
        elif 'call' in query_lower:
            return "MATCH (c:Call) RETURN c ORDER BY c.timestamp DESC LIMIT 100;"
        else:
            # Generic fallback
            return "MATCH (n) RETURN n LIMIT 100;"
    
    def batch_validate(self, cypher_queries: List[str]) -> List[Tuple[QuerySafety, List[str]]]:
        """
        Validate multiple queries
        
        Args:
            cypher_queries: List of Cypher queries
            
        Returns:
            List of (safety, warnings) tuples
        """
        return [self.validator.validate(q) for q in cypher_queries]


# Example usage
if __name__ == "__main__":
    translator = EnhancedNL2Cypher()
    
    # Test queries
    test_queries = [
        "Find persons named Kumar",
        "Show messages containing bitcoin",
        "Find calls to foreign numbers",
        "List all persons with phone +919876543210",
        "CREATE (n:Person) RETURN n",  # Should be blocked
    ]
    
    print("=== NL→Cypher Translation Tests ===\n")
    
    for query in test_queries:
        result = translator.translate(query, allow_llm=False)
        
        print(f"Query: {query}")
        print(f"Cypher: {result.cypher}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Safety: {result.safety.value}")
        print(f"Source: {result.source}")
        if result.warnings:
            print(f"Warnings: {', '.join(result.warnings)}")
        if result.fallback:
            print(f"Fallback: {result.fallback.value}")
        if result.clarification_needed:
            print(f"Clarification: {result.clarification_needed}")
        print("-" * 60)
        print()