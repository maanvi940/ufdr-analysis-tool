"""
Natural Language to Cypher Query Translator
Converts user queries to Neo4j Cypher queries for forensic graph analysis
"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of graph queries"""
    FIND_ENTITY = "find_entity"
    FIND_RELATIONSHIPS = "find_relationships"
    FIND_PATTERNS = "find_patterns"
    TRACE_COMMUNICATION = "trace_communication"
    ANALYZE_NETWORK = "analyze_network"
    DETECT_ANOMALIES = "detect_anomalies"
    TIMELINE_ANALYSIS = "timeline_analysis"


@dataclass
class CypherQuery:
    """Structured Cypher query with metadata"""
    query: str
    parameters: Dict[str, Any]
    query_type: QueryType
    description: str
    expected_return: List[str]


class NL2Cypher:
    """Natural Language to Cypher translator for forensic queries"""
    
    def __init__(self):
        self.query_patterns = self._init_patterns()
        self.entity_extractors = self._init_extractors()
        self.query_templates = self._init_templates()
        
    def _init_patterns(self) -> Dict[QueryType, List[re.Pattern]]:
        """Initialize regex patterns for query classification"""
        return {
            QueryType.FIND_ENTITY: [
                re.compile(r"(find|show|get|search for?)\s+(phone|person|device|address|crypto)", re.I),
                re.compile(r"who (is|has|owns|uses)", re.I),
                re.compile(r"(phone number|contact|device) (\+?\d+|\w+)", re.I)
            ],
            QueryType.FIND_RELATIONSHIPS: [
                re.compile(r"(who|what).*(called|messaged|contacted|communicated)", re.I),
                re.compile(r"(connections?|relationships?|links?) (between|of|from|to)", re.I),
                re.compile(r"(show|find|get) .*(calls?|messages?|communications?)", re.I)
            ],
            QueryType.FIND_PATTERNS: [
                re.compile(r"(suspicious|unusual|anomal|pattern|frequent)", re.I),
                re.compile(r"(crypto|bitcoin|foreign|international).*(transaction|transfer|contact)", re.I),
                re.compile(r"(flagged|marked|important|critical)", re.I)
            ],
            QueryType.TRACE_COMMUNICATION: [
                re.compile(r"(trace|track|follow).*(call|message|communication)", re.I),
                re.compile(r"communication (chain|path|flow|history)", re.I),
                re.compile(r"(all|every).*(call|message|contact).*(from|to|between)", re.I)
            ],
            QueryType.ANALYZE_NETWORK: [
                re.compile(r"(network|group|cluster|community)", re.I),
                re.compile(r"(most|top).*(connected|active|frequent)", re.I),
                re.compile(r"(central|important|key) (person|contact|node)", re.I)
            ],
            QueryType.DETECT_ANOMALIES: [
                re.compile(r"(anomaly|outlier|unusual|strange|weird)", re.I),
                re.compile(r"(burst|spike|surge|increase) (in|of)", re.I),
                re.compile(r"(midnight|late night|early morning|unusual time)", re.I)
            ],
            QueryType.TIMELINE_ANALYSIS: [
                re.compile(r"(timeline|chronolog|sequence|order)", re.I),
                re.compile(r"(before|after|during|between).*(date|time|period)", re.I),
                re.compile(r"(when did|what time|at what point)", re.I)
            ]
        }
    
    def _init_extractors(self) -> Dict[str, re.Pattern]:
        """Initialize entity extraction patterns"""
        return {
            'phone': re.compile(r'\+?\d{10,15}|\d{3}[-.\s]?\d{3}[-.\s]?\d{4}'),
            'crypto_address': re.compile(r'[13][a-km-zA-HJ-NP-Z1-9]{25,34}|0x[a-fA-F0-9]{40}'),
            'email': re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
            'date': re.compile(r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}'),
            'time': re.compile(r'\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AP]M)?'),
            'name': re.compile(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b')
        }
    
    def _init_templates(self) -> Dict[QueryType, List[str]]:
        """Initialize Cypher query templates"""
        return {
            QueryType.FIND_ENTITY: [
                """
                MATCH (n:{entity_type})
                WHERE n.{property} = $value
                RETURN n, labels(n) as types, n.flagged as flagged
                ORDER BY n.created_at DESC
                LIMIT 20
                """,
                """
                MATCH (n)
                WHERE n.phone = $phone OR n.normalized_phone = $phone
                RETURN n, labels(n) as types
                """
            ],
            QueryType.FIND_RELATIONSHIPS: [
                """
                MATCH (a)-[r:CALLED|MESSAGED]->(b)
                WHERE a.phone = $phone_a OR b.phone = $phone_b
                RETURN a, type(r) as rel_type, r, b
                ORDER BY r.timestamp DESC
                LIMIT 50
                """,
                """
                MATCH path = (a)-[*1..3]-(b)
                WHERE a.phone = $phone_a AND b.phone = $phone_b
                RETURN path, length(path) as distance
                ORDER BY distance
                LIMIT 10
                """
            ],
            QueryType.FIND_PATTERNS: [
                """
                MATCH (n)-[r:HAS_CRYPTO|FOREIGN_CONTACT]->(target)
                WHERE r.confidence > 0.8
                RETURN n, type(r) as pattern_type, r.confidence as confidence, target
                ORDER BY r.confidence DESC
                LIMIT 30
                """,
                """
                MATCH (n)
                WHERE n.flagged = true OR n.suspicious = true
                OPTIONAL MATCH (n)-[r]-(connected)
                RETURN n, collect(DISTINCT type(r)) as relationships, 
                       count(DISTINCT connected) as connection_count
                ORDER BY connection_count DESC
                """
            ],
            QueryType.TRACE_COMMUNICATION: [
                """
                MATCH path = (start:Person)-[r:CALLED|MESSAGED*1..5]->(end:Person)
                WHERE start.phone = $start_phone
                WITH path, [rel in relationships(path) | rel.timestamp] as timestamps
                RETURN path, timestamps
                ORDER BY length(path)
                LIMIT 20
                """,
                """
                MATCH (a:Person)-[r:CALLED|MESSAGED]->(b:Person)
                WHERE r.timestamp >= $start_time AND r.timestamp <= $end_time
                RETURN a, r, b, r.timestamp as time
                ORDER BY r.timestamp
                """
            ],
            QueryType.ANALYZE_NETWORK: [
                """
                MATCH (n:Person)
                WITH n, size((n)-[:CALLED|MESSAGED]-()) as degree
                WHERE degree > 5
                RETURN n, degree, 
                       size((n)-[:CALLED]->()) as outgoing_calls,
                       size((n)<-[:CALLED]-()) as incoming_calls
                ORDER BY degree DESC
                LIMIT 20
                """,
                """
                CALL gds.pageRank.stream('communications')
                YIELD nodeId, score
                WITH gds.util.asNode(nodeId) as node, score
                WHERE score > 0.5
                RETURN node, score as centrality
                ORDER BY centrality DESC
                LIMIT 10
                """
            ],
            QueryType.DETECT_ANOMALIES: [
                """
                MATCH (n:Person)-[r:CALLED|MESSAGED]->(m:Person)
                WHERE r.hour >= 0 AND r.hour <= 5
                WITH n, count(r) as night_activity
                WHERE night_activity > 10
                RETURN n, night_activity,
                       collect(DISTINCT m.phone) as night_contacts
                ORDER BY night_activity DESC
                """,
                """
                MATCH (n:Person)
                WITH n, size((n)-[:CALLED]->()) as call_count
                WITH avg(call_count) as avg_calls, stDev(call_count) as std_calls
                MATCH (outlier:Person)
                WITH outlier, size((outlier)-[:CALLED]->()) as outlier_calls, avg_calls, std_calls
                WHERE abs(outlier_calls - avg_calls) > 2 * std_calls
                RETURN outlier, outlier_calls, avg_calls, std_calls
                """
            ],
            QueryType.TIMELINE_ANALYSIS: [
                """
                MATCH (n)-[r:CALLED|MESSAGED|LOCATION_UPDATE]->(m)
                WHERE r.timestamp >= $start_date AND r.timestamp <= $end_date
                RETURN n, type(r) as event_type, r.timestamp as time, m
                ORDER BY r.timestamp
                """,
                """
                MATCH (n:Person {phone: $phone})-[r]->(m)
                WHERE r.timestamp IS NOT NULL
                WITH date(r.timestamp) as day, type(r) as rel_type, count(*) as count
                RETURN day, rel_type, count
                ORDER BY day
                """
            ]
        }
    
    def classify_query(self, nl_query: str) -> QueryType:
        """Classify the natural language query into a query type"""
        nl_query.lower()
        
        # Check each pattern type
        for query_type, patterns in self.query_patterns.items():
            for pattern in patterns:
                if pattern.search(nl_query):
                    logger.info(f"Query classified as: {query_type}")
                    return query_type
        
        # Default to finding entities
        return QueryType.FIND_ENTITY
    
    def extract_entities(self, nl_query: str) -> Dict[str, List[str]]:
        """Extract entities from natural language query"""
        entities = {}
        
        for entity_type, pattern in self.entity_extractors.items():
            matches = pattern.findall(nl_query)
            if matches:
                entities[entity_type] = matches
                logger.debug(f"Extracted {entity_type}: {matches}")
        
        return entities
    
    def translate(self, nl_query: str) -> CypherQuery:
        """
        Translate natural language query to Cypher
        
        Args:
            nl_query: Natural language query
            
        Returns:
            CypherQuery object with query and parameters
        """
        # Classify query type
        query_type = self.classify_query(nl_query)
        
        # Extract entities
        entities = self.extract_entities(nl_query)
        
        # Build Cypher query based on type and entities
        cypher_query = self._build_cypher_query(query_type, entities, nl_query)
        
        logger.info(f"Translated to Cypher: {cypher_query.query[:100]}...")
        return cypher_query
    
    def _build_cypher_query(self, 
                           query_type: QueryType,
                           entities: Dict[str, List[str]],
                           nl_query: str) -> CypherQuery:
        """Build specific Cypher query based on type and entities"""
        
        # Get appropriate template
        templates = self.query_templates.get(query_type, [])
        if not templates:
            raise ValueError(f"No template for query type: {query_type}")
        
        # Select template based on entities found
        template = templates[0]  # Default to first template
        parameters = {}
        
        # Build parameters based on query type
        if query_type == QueryType.FIND_ENTITY:
            if 'phone' in entities:
                parameters['phone'] = entities['phone'][0]
                template = templates[1] if len(templates) > 1 else templates[0]
            elif 'crypto_address' in entities:
                parameters['value'] = entities['crypto_address'][0]
                template = template.replace('{entity_type}', 'CryptoWallet')
                template = template.replace('{property}', 'address')
            elif 'email' in entities:
                parameters['value'] = entities['email'][0]
                template = template.replace('{entity_type}', 'Person')
                template = template.replace('{property}', 'email')
            else:
                # Generic entity search
                template = template.replace('{entity_type}', 'Person|Device|Location')
                template = template.replace('{property}', 'name')
                parameters['value'] = nl_query.split()[-1]  # Last word as search term
        
        elif query_type == QueryType.FIND_RELATIONSHIPS:
            phones = entities.get('phone', [])
            if len(phones) >= 2:
                parameters['phone_a'] = phones[0]
                parameters['phone_b'] = phones[1]
                template = templates[1] if len(templates) > 1 else templates[0]
            elif len(phones) == 1:
                parameters['phone_a'] = phones[0]
                parameters['phone_b'] = phones[0]
        
        elif query_type == QueryType.TRACE_COMMUNICATION:
            if 'phone' in entities:
                parameters['start_phone'] = entities['phone'][0]
            if 'date' in entities:
                dates = entities['date']
                parameters['start_time'] = dates[0] if dates else '2024-01-01'
                parameters['end_time'] = dates[1] if len(dates) > 1 else '2024-12-31'
        
        elif query_type == QueryType.TIMELINE_ANALYSIS:
            if 'phone' in entities:
                parameters['phone'] = entities['phone'][0]
            if 'date' in entities:
                dates = entities['date']
                parameters['start_date'] = dates[0] if dates else '2024-01-01'
                parameters['end_date'] = dates[1] if len(dates) > 1 else '2024-12-31'
        
        # Clean up template
        query = template.strip()
        
        return CypherQuery(
            query=query,
            parameters=parameters,
            query_type=query_type,
            description=f"Query for: {nl_query}",
            expected_return=['nodes', 'relationships', 'properties']
        )
    
    def suggest_queries(self, context: Optional[str] = None) -> List[str]:
        """Suggest relevant queries based on context"""
        suggestions = [
            "Show all suspicious contacts",
            "Find crypto wallet addresses",
            "Who called +919876543210",
            "Show communication between +919876543210 and +447890123456",
            "Find all foreign contacts",
            "Show night time activities",
            "Find most connected persons",
            "Show timeline for last week",
            "Trace all calls from +919876543210",
            "Find patterns of suspicious behavior",
            "Show devices used by multiple persons",
            "Find burst of activities"
        ]
        
        if context:
            # Filter suggestions based on context
            context_lower = context.lower()
            filtered = [s for s in suggestions if any(
                word in s.lower() for word in context_lower.split()
            )]
            return filtered[:5] if filtered else suggestions[:5]
        
        return suggestions[:5]


class CypherExecutor:
    """Execute Cypher queries against Neo4j"""
    
    def __init__(self, neo4j_uri: str = "bolt://localhost:7687",
                 username: str = "neo4j",
                 password: str = "password"):
        self.uri = neo4j_uri
        self.username = username
        self.password = password
        self.driver = None
    
    def connect(self):
        """Connect to Neo4j database"""
        try:
            from neo4j import GraphDatabase
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
            logger.info("Connected to Neo4j")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def execute(self, cypher_query: CypherQuery) -> List[Dict]:
        """Execute a Cypher query and return results"""
        if not self.driver:
            self.connect()
        
        results = []
        try:
            with self.driver.session() as session:
                result = session.run(cypher_query.query, cypher_query.parameters)
                for record in result:
                    results.append(dict(record))
            
            logger.info(f"Query executed, {len(results)} results returned")
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
        
        return results
    
    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")


def main():
    """Test the NL2Cypher translator"""
    translator = NL2Cypher()
    
    # Test queries
    test_queries = [
        "Find phone number +919876543210",
        "Show all calls from +919876543210",
        "Find suspicious crypto transactions",
        "Who is the most connected person?",
        "Show communication between +919876543210 and +447890123456",
        "Find all activities at night",
        "Show timeline for last week"
    ]
    
    print("NL2Cypher Translator Test")
    print("=" * 50)
    
    for nl_query in test_queries:
        print(f"\nQuery: {nl_query}")
        print("-" * 40)
        
        try:
            cypher = translator.translate(nl_query)
            print(f"Type: {cypher.query_type.value}")
            print(f"Cypher: {cypher.query[:200]}...")
            print(f"Parameters: {cypher.parameters}")
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n" + "=" * 50)
    print("Suggested queries:")
    for suggestion in translator.suggest_queries():
        print(f"  - {suggestion}")


if __name__ == "__main__":
    main()