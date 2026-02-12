"""
Natural Language to SQL Translator
Uses Mistral-7B to convert forensic queries to safe, read-only SQL
"""

import logging
import re
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class NL2SQLTranslator:
    """Translates natural language queries to SQL using local LLM"""
    
    # Database schema description for prompt
    SCHEMA_DESCRIPTION = """
DATABASE SCHEMA:

cases(case_id, ingest_time, source_file, examiner, agency, notes)
devices(device_id, case_id, imei, serial_number, manufacturer, model, os_type, os_version, owner)
contacts(contact_id, case_id, name, phone_raw, phone_digits, phone_e164, phone_suffix_2, phone_suffix_4, email)
messages(msg_id, case_id, device_id, app, sender_raw, sender_digits, sender_suffix_2, sender_suffix_4, receiver_raw, receiver_digits, receiver_suffix_2, receiver_suffix_4, text, message_type, timestamp, encrypted, is_deleted, source_path)
calls(call_id, case_id, device_id, caller_raw, caller_digits, caller_suffix_2, caller_suffix_4, receiver_raw, receiver_digits, receiver_suffix_2, receiver_suffix_4, timestamp, duration_seconds, direction, source_path)
media(media_id, case_id, device_id, filename, media_type, sha256, phash, ocr_text, caption, timestamp, file_size, source_path)
locations(location_id, case_id, device_id, latitude, longitude, accuracy, altitude, timestamp, source_path)

KEY COLUMNS:
- phone_suffix_2: Last 2 digits of phone number (e.g., "20")
- phone_suffix_4: Last 4 digits of phone number (e.g., "3420")
- phone_digits: Full phone number digits only (e.g., "919876543210")
- *_raw: Original phone number with formatting (e.g., "+91 98765 43210")
"""
    
    # Few-shot examples for the LLM
    FEW_SHOT_EXAMPLES = """
EXAMPLE 1:
User: "Show me numbers ending with 20 in case ADV_TEST_001"
SQL: SELECT sender_raw AS phone, sender_digits, msg_id, timestamp, source_path FROM messages WHERE case_id='ADV_TEST_001' AND sender_suffix_2='20' ORDER BY timestamp DESC LIMIT 100;

EXAMPLE 2:
User: "Find all calls starting with 968"
SQL: SELECT caller_raw AS phone, caller_digits, call_id, timestamp, duration_seconds FROM calls WHERE caller_digits LIKE '968%' ORDER BY timestamp DESC LIMIT 100;

EXAMPLE 3:
User: "Messages containing 'crypto' in the last 30 days"
SQL: SELECT msg_id, sender_raw, receiver_raw, text, timestamp FROM messages WHERE text LIKE '%crypto%' AND timestamp >= datetime('now', '-30 days') ORDER BY timestamp DESC LIMIT 100;

EXAMPLE 4:
User: "Show me WhatsApp messages from case CASE_001"
SQL: SELECT msg_id, sender_raw, receiver_raw, text, timestamp FROM messages WHERE case_id='CASE_001' AND app='WhatsApp' ORDER BY timestamp DESC LIMIT 100;

EXAMPLE 5:
User: "Find phone number 9876543210"
SQL: SELECT sender_raw AS phone, msg_id, timestamp, app, source_path FROM messages WHERE sender_digits LIKE '%9876543210%' OR receiver_digits LIKE '%9876543210%' LIMIT 100;

EXAMPLE 6:
User: "All images with OCR text containing 'address'"
SQL: SELECT media_id, filename, ocr_text, timestamp, source_path FROM media WHERE media_type='image' AND ocr_text LIKE '%address%' ORDER BY timestamp DESC LIMIT 50;

EXAMPLE 7:
User: "Calls longer than 5 minutes"
SQL: SELECT call_id, caller_raw, receiver_raw, duration_seconds, timestamp FROM calls WHERE duration_seconds > 300 ORDER BY duration_seconds DESC LIMIT 100;

EXAMPLE 8:
User: "Numbers that appear in both calls and messages"
SQL: SELECT DISTINCT phone_digits FROM (SELECT sender_digits AS phone_digits FROM messages UNION SELECT receiver_digits AS phone_digits FROM messages UNION SELECT caller_digits AS phone_digits FROM calls UNION SELECT receiver_digits AS phone_digits FROM calls) WHERE phone_digits != '' LIMIT 100;

EXAMPLE 9:
User: "Find contacts with Indian names"
SQL: SELECT contact_id, name, phone_raw, phone_digits FROM contacts WHERE name LIKE '%Sharma%' OR name LIKE '%Kumar%' OR name LIKE '%Singh%' OR name LIKE '%Patel%' OR name LIKE '%Gupta%' OR name LIKE '%Reddy%' OR name LIKE '%Agarwal%' OR name LIKE '%Iyer%' OR name LIKE '%Joshi%' OR name LIKE '%Mehta%' ORDER BY name LIMIT 100;

EXAMPLE 10:
User: "Show me contacts with Chinese names"
SQL: SELECT contact_id, name, phone_raw, phone_digits FROM contacts WHERE name LIKE '%Wang%' OR name LIKE '%Li%' OR name LIKE '%Zhang%' OR name LIKE '%Liu%' OR name LIKE '%Chen%' OR name LIKE '%Yang%' OR name LIKE '%Wu%' OR name LIKE '%Lin%' ORDER BY name LIMIT 100;

EXAMPLE 11:
User: "Find contacts with Arabic names"
SQL: SELECT contact_id, name, phone_raw, phone_digits FROM contacts WHERE name LIKE '%Mohammed%' OR name LIKE '%Ahmed%' OR name LIKE '%Ali%' OR name LIKE '%Hassan%' OR name LIKE '%Khan%' OR name LIKE '%Malik%' OR name LIKE '%Ansari%' ORDER BY name LIMIT 100;
"""
    
    def __init__(self, llm_model_path: str = None):
        """
        Initialize NL2SQL translator
        
        Args:
            llm_model_path: Path to local LLM model (GGUF format). If None, uses fallback mode only.
        """
        self.llm_model_path = llm_model_path
        self.llm = None
        
        # Try to load LLM only if path is provided
        if llm_model_path and Path(llm_model_path).exists():
            self._load_llm()
        elif llm_model_path:
            logger.warning(f"LLM model not found at {llm_model_path}. Will use fallback mode.")
        else:
            logger.info("NL2SQL initialized in fallback mode (no LLM loaded)")
    
    def _load_llm(self):
        """Load local LLM for SQL generation"""
        try:
            import llama_cpp
            import torch
            
            # Check GPU availability
            device = "cuda" if torch.cuda.is_available() else "cpu"
            n_gpu_layers = -1 if device == "cuda" else 0
            
            self.llm = llama_cpp.Llama(
                model_path=str(self.llm_model_path),
                n_ctx=128000,  # Llama 3.1: 128K context (16× more than before)
                n_threads=8,   # Increased for better performance
                n_gpu_layers=n_gpu_layers,
                n_batch=512,
                verbose=False
            )
            
            if device == "cuda":
                logger.info("NL2SQL: Loaded LLM with GPU acceleration")
            else:
                logger.info("NL2SQL: Loaded LLM on CPU")
                
        except Exception as e:
            logger.error(f"Failed to load LLM: {e}")
            self.llm = None
    
    def translate(self, 
                  natural_query: str, 
                  case_id: Optional[str] = None,
                  default_limit: int = 100) -> Dict[str, Any]:
        """
        Translate natural language to SQL
        
        Args:
            natural_query: Natural language query from user
            case_id: Optional case ID to filter by
            default_limit: Default row limit for safety
            
        Returns:
            Dict with 'sql', 'confidence', 'explanation'
        """
        # If no LLM, use fallback pattern matching
        if not self.llm:
            return self._fallback_translation(natural_query, case_id, default_limit)
        
        # Build prompt
        prompt = self._build_prompt(natural_query, case_id)
        
        # Generate SQL
        try:
            response = self.llm(
                prompt,
                max_tokens=256,
                temperature=0.0,  # Deterministic for SQL
                top_k=1,
                top_p=0.95,
                stop=["</SQL>", "\n\n", "EXAMPLE", "User:"]
            )
            
            sql_text = response['choices'][0]['text'].strip()
            
            # Clean and extract SQL
            sql_query = self._extract_sql(sql_text)
            
            # Add case filter if specified and not already present
            if case_id and "case_id" not in sql_query.lower():
                sql_query = self._inject_case_filter(sql_query, case_id)
            
            # Ensure LIMIT clause for safety
            if "limit" not in sql_query.lower():
                sql_query = sql_query.rstrip(';') + f" LIMIT {default_limit};"
            
            return {
                'sql': sql_query,
                'confidence': 0.85,
                'explanation': f'Generated SQL query for: "{natural_query}"',
                'method': 'llm'
            }
            
        except Exception as e:
            logger.error(f"LLM SQL generation failed: {e}")
            return self._fallback_translation(natural_query, case_id, default_limit)
    
    def _build_prompt(self, query: str, case_id: Optional[str]) -> str:
        """Build prompt for LLM"""
        case_context = f"\nCase ID: {case_id}" if case_id else ""
        
        prompt = f"""You are a SQL query generator for a forensic database. Generate ONLY a single SELECT query.

{self.SCHEMA_DESCRIPTION}

RULES:
- Output ONLY SQL (no explanations, no markdown, no code blocks)
- Only SELECT queries allowed (no INSERT/UPDATE/DELETE)
- Always include LIMIT clause (max 100 rows)
- Use phone_suffix_2 or phone_suffix_4 for "ending with" queries
- Use LIKE for "starting with" or "containing" queries
- Always ORDER BY timestamp DESC when timestamps available
- SQLite syntax only

{self.FEW_SHOT_EXAMPLES}

NOW GENERATE SQL FOR:
User: "{query}"{case_context}
SQL: """
        
        return prompt
    
    def _extract_sql(self, text: str) -> str:
        """Extract clean SQL from LLM output"""
        # Remove markdown code blocks
        text = re.sub(r'```sql\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # Extract first SELECT statement
        match = re.search(r'(SELECT\s+.+?;)', text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # If no semicolon, take the whole thing
        if text.strip().upper().startswith('SELECT'):
            return text.strip()
        
        raise ValueError("No valid SELECT statement found in LLM output")
    
    def _inject_case_filter(self, sql: str, case_id: str) -> str:
        """Inject case_id filter into SQL query"""
        # Simple injection: add WHERE clause if none exists
        if "where" not in sql.lower():
            # Add WHERE before ORDER BY or LIMIT
            if "order by" in sql.lower():
                sql = sql.replace("ORDER BY", f"WHERE case_id='{case_id}' ORDER BY")
                sql = sql.replace("order by", f"WHERE case_id='{case_id}' ORDER BY")
            elif "limit" in sql.lower():
                sql = sql.replace("LIMIT", f"WHERE case_id='{case_id}' LIMIT")
                sql = sql.replace("limit", f"WHERE case_id='{case_id}' LIMIT")
            else:
                sql = sql.rstrip(';') + f" WHERE case_id='{case_id}';"
        else:
            # Add AND condition
            sql = sql.replace("WHERE", f"WHERE case_id='{case_id}' AND", 1)
            sql = sql.replace("where", f"WHERE case_id='{case_id}' AND", 1)
        
        return sql
    
    def _fallback_translation(self, query: str, case_id: Optional[str], limit: int) -> Dict[str, Any]:
        """
        Fallback pattern matching when LLM unavailable
        Handles common forensic query patterns
        """
        query_lower = query.lower()
        case_filter = f"case_id='{case_id}'" if case_id else "1=1"
        
        # Pattern 1: Contact name searches
        # "contacts with name starting with A" or "all contacts starting with letter A"
        # Match patterns like: "contacts...starting with A", "contacts...starting with letter A"
        match = re.search(r'contacts?.*(?:starting|begins?)\s+(?:with\s+)?(?:letter\s+)?([a-zA-Z])(?:\s|$)', query_lower)
        if match:
            letter = match.group(1).upper()
            sql = f"SELECT contact_id, name, phone_raw, phone_digits, email FROM contacts WHERE {case_filter} AND name LIKE '{letter}%' ORDER BY name LIMIT {limit};"
            return {
                'sql': sql,
                'confidence': 0.95,
                'explanation': f'Contacts with name starting with "{letter}"',
                'method': 'pattern'
            }
        
        # "contacts containing" or "find contact"
        if 'contact' in query_lower:
            # Check for semantic/ethnic name queries (indian, chinese, etc.)
            ethnicity_patterns = {
                'indian': ['Sharma', 'Kumar', 'Singh', 'Patel', 'Gupta', 'Reddy', 'Agarwal', 'Iyer', 
                          'Joshi', 'Mehta', 'Kapoor', 'Nair', 'Aadhya', 'Aarav', 'Aditi', 'Aditya',
                          'Ananya', 'Arjun', 'Diya', 'Kabir', 'Krishna', 'Navya', 'Priya', 'Rohan',
                          'Saanvi', 'Sai', 'Vivaan', 'Bansal', 'Chopra', 'Das', 'Ghosh', 'Malhotra',
                          'Mukherjee', 'Rao', 'Roy', 'Saha', 'Sen', 'Verma', 'Desai', 'Chatterjee'],
                'chinese': ['Wang', 'Li', 'Zhang', 'Liu', 'Chen', 'Yang', 'Huang', 'Wu', 'Wei', 
                           'Ming', 'Ling', 'Jun', 'Yan', 'Hui', 'Lei', 'Jian', 'Xin', 'Fang', 'Lin'],
                'arabic': ['Mohammed', 'Ahmed', 'Ali', 'Hassan', 'Hussein', 'Fatima', 'Abdul', 
                          'Omar', 'Amir', 'Jamal', 'Karim', 'Layla', 'Noor', 'Rashid', 'Samir',
                          'Zain', 'Aisha', 'Ansari', 'Khan', 'Malik', 'Qureshi', 'Rizvi', 'Siddiqui'],
                'western': ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Miller', 'Davis', 
                           'Garcia', 'Rodriguez', 'Wilson', 'Anderson', 'Taylor', 'Thomas', 'Moore',
                           'Martin', 'Jackson', 'Thompson', 'White', 'Lopez', 'Lee', 'Robinson']
            }
            
            # Check if query is asking for specific ethnicity
            for ethnicity, patterns in ethnicity_patterns.items():
                if ethnicity in query_lower and ('name' in query_lower or 'contact' in query_lower):
                    # Build LIKE clauses for name patterns
                    like_clauses = ' OR '.join([f"name LIKE '%{pattern}%'" for pattern in patterns])
                    sql = f"SELECT contact_id, name, phone_raw, phone_digits, email FROM contacts WHERE {case_filter} AND ({like_clauses}) ORDER BY name LIMIT {limit};"
                    return {
                        'sql': sql,
                        'confidence': 0.85,
                        'explanation': f'Contacts with {ethnicity.title()} names',
                        'method': 'pattern'
                    }
            
            # Regular name search
            match = re.search(r'(?:containing|with|named|called)\s+["\']?([a-zA-Z]+)', query_lower)
            if match:
                name_part = match.group(1)
                sql = f"SELECT contact_id, name, phone_raw, phone_digits, email FROM contacts WHERE {case_filter} AND name LIKE '%{name_part}%' ORDER BY name LIMIT {limit};"
                return {
                    'sql': sql,
                    'confidence': 0.90,
                    'explanation': f'Contacts with name containing "{name_part}"',
                    'method': 'pattern'
                }
            else:
                # All contacts
                sql = f"SELECT contact_id, name, phone_raw, phone_digits, email FROM contacts WHERE {case_filter} ORDER BY name LIMIT {limit};"
                return {
                    'sql': sql,
                    'confidence': 0.80,
                    'explanation': 'All contacts',
                    'method': 'pattern'
                }
        
        # Pattern 2: Phone numbers ending with X
        match = re.search(r'(?:number|phone).*ending?\s+with\s+(\d+)', query_lower)
        if match:
            suffix = match.group(1)
            suffix_len = len(suffix)
            
            # We only support 2 or 4 digit suffixes
            if suffix_len == 2 or suffix_len == 4:
                suffix_col = f"sender_suffix_{suffix_len}"
                sql = f"SELECT sender_raw AS phone, sender_digits, msg_id, timestamp, source_path FROM messages WHERE {case_filter} AND {suffix_col}='{suffix}' ORDER BY timestamp DESC LIMIT {limit};"
                return {
                    'sql': sql,
                    'confidence': 0.95,
                    'explanation': f'Phone numbers ending with {suffix}',
                    'method': 'pattern'
                }
            else:
                # Use LIKE for other lengths
                sql = f"SELECT sender_raw AS phone, sender_digits, msg_id, timestamp, source_path FROM messages WHERE {case_filter} AND sender_digits LIKE '%{suffix}' ORDER BY timestamp DESC LIMIT {limit};"
                return {
                    'sql': sql,
                    'confidence': 0.80,
                    'explanation': f'Phone numbers ending with {suffix} (using LIKE)',
                    'method': 'pattern'
                }
        
        # Pattern 3: Numbers starting with X
        match = re.search(r'(?:number|phone).*starting?\s+with\s+(\d+)', query_lower)
        if match:
            prefix = match.group(1)
            sql = f"SELECT sender_raw AS phone, sender_digits, msg_id, timestamp FROM messages WHERE {case_filter} AND sender_digits LIKE '{prefix}%' ORDER BY timestamp DESC LIMIT {limit};"
            return {
                'sql': sql,
                'confidence': 0.95,
                'explanation': f'Phone numbers starting with {prefix}',
                'method': 'pattern'
            }
        
        # Pattern 4: App-specific queries (WhatsApp, Telegram, Signal, etc.)
        apps = ['whatsapp', 'telegram', 'signal', 'sms', 'messenger', 'viber', 'wechat']
        for app in apps:
            if app in query_lower:
                app_name = app.title()
                if 'sms' in query_lower:
                    app_name = 'SMS'
                sql = f"SELECT msg_id, sender_raw, receiver_raw, text, timestamp, app FROM messages WHERE {case_filter} AND LOWER(app)='{app}' ORDER BY timestamp DESC LIMIT {limit};"
                return {
                    'sql': sql,
                    'confidence': 0.95,
                    'explanation': f'Messages from {app_name}',
                    'method': 'pattern'
                }
        
        # Pattern 5: Call queries
        if 'call' in query_lower:
            # Calls longer than X minutes/seconds
            match = re.search(r'longer\s+than\s+(\d+)\s+(minute|second)', query_lower)
            if match:
                duration = int(match.group(1))
                unit = match.group(2)
                seconds = duration * 60 if unit.startswith('minute') else duration
                sql = f"SELECT call_id, caller_raw, receiver_raw, duration_seconds, timestamp, direction FROM calls WHERE {case_filter} AND duration_seconds > {seconds} ORDER BY duration_seconds DESC LIMIT {limit};"
                return {
                    'sql': sql,
                    'confidence': 0.95,
                    'explanation': f'Calls longer than {duration} {unit}(s)',
                    'method': 'pattern'
                }
            else:
                # All calls
                sql = f"SELECT call_id, caller_raw, receiver_raw, duration_seconds, timestamp, direction FROM calls WHERE {case_filter} ORDER BY timestamp DESC LIMIT {limit};"
                return {
                    'sql': sql,
                    'confidence': 0.85,
                    'explanation': 'All calls',
                    'method': 'pattern'
                }
        
        # Pattern 6: Media queries
        if 'media' in query_lower or 'image' in query_lower or 'photo' in query_lower or 'video' in query_lower:
            media_type = None
            if 'image' in query_lower or 'photo' in query_lower:
                media_type = 'image'
            elif 'video' in query_lower:
                media_type = 'video'
            
            if media_type:
                sql = f"SELECT media_id, filename, media_type, timestamp, file_size, source_path FROM media WHERE {case_filter} AND media_type='{media_type}' ORDER BY timestamp DESC LIMIT {limit};"
                return {
                    'sql': sql,
                    'confidence': 0.95,
                    'explanation': f'All {media_type} files',
                    'method': 'pattern'
                }
            else:
                sql = f"SELECT media_id, filename, media_type, timestamp, file_size, source_path FROM media WHERE {case_filter} ORDER BY timestamp DESC LIMIT {limit};"
                return {
                    'sql': sql,
                    'confidence': 0.85,
                    'explanation': 'All media files',
                    'method': 'pattern'
                }
        
        # Pattern 7: Text/message search
        match = re.search(r'(?:message|text).*containing?\s+["\'](.+?)["\']', query_lower)
        if not match:
            match = re.search(r'(?:message|text).*about\s+(\w+)', query_lower)
        if match:
            search_term = match.group(1)
            sql = f"SELECT msg_id, sender_raw, receiver_raw, text, timestamp, app FROM messages WHERE {case_filter} AND text LIKE '%{search_term}%' ORDER BY timestamp DESC LIMIT {limit};"
            return {
                'sql': sql,
                'confidence': 0.85,
                'explanation': f'Messages containing "{search_term}"',
                'method': 'pattern'
            }
        
        # Pattern 8: Specific phone number
        match = re.search(r'(\d{10,})', query)
        if match:
            phone = match.group(1)
            sql = f"SELECT msg_id, sender_raw, receiver_raw, text, timestamp FROM messages WHERE {case_filter} AND (sender_digits LIKE '%{phone}%' OR receiver_digits LIKE '%{phone}%') ORDER BY timestamp DESC LIMIT {limit};"
            return {
                'sql': sql,
                'confidence': 0.90,
                'explanation': f'Messages involving {phone}',
                'method': 'pattern'
            }
        
        # Pattern 9: Date/time range queries
        if 'last' in query_lower:
            match = re.search(r'last\s+(\d+)\s+(day|week|month|hour)', query_lower)
            if match:
                count = int(match.group(1))
                unit = match.group(2)
                sql = f"SELECT msg_id, sender_raw, receiver_raw, text, timestamp FROM messages WHERE {case_filter} AND timestamp >= datetime('now', '-{count} {unit}s') ORDER BY timestamp DESC LIMIT {limit};"
                return {
                    'sql': sql,
                    'confidence': 0.90,
                    'explanation': f'Messages from last {count} {unit}(s)',
                    'method': 'pattern'
                }
        
        # Pattern 10: Location queries
        if 'location' in query_lower or 'gps' in query_lower or 'coordinate' in query_lower:
            sql = f"SELECT location_id, latitude, longitude, accuracy, timestamp, source_path FROM locations WHERE {case_filter} ORDER BY timestamp DESC LIMIT {limit};"
            return {
                'sql': sql,
                'confidence': 0.95,
                'explanation': 'All location data',
                'method': 'pattern'
            }
        
        # Pattern 11: Device queries
        if 'device' in query_lower:
            sql = f"SELECT device_id, imei, manufacturer, model, os_type, os_version, owner FROM devices WHERE {case_filter} LIMIT {limit};"
            return {
                'sql': sql,
                'confidence': 0.95,
                'explanation': 'All devices',
                'method': 'pattern'
            }
        
        # Default: return all messages
        sql = f"SELECT msg_id, sender_raw, receiver_raw, text, timestamp FROM messages WHERE {case_filter} ORDER BY timestamp DESC LIMIT {limit};"
        return {
            'sql': sql,
            'confidence': 0.50,
            'explanation': 'Showing recent messages (could not parse specific intent)',
            'method': 'fallback'
        }


# Quick test function
def test_nl2sql():
    """Test NL2SQL translator"""
    translator = NL2SQLTranslator()
    
    test_queries = [
        "numbers ending with 20",
        "calls starting with 968",
        "messages containing crypto",
        "find phone number 9876543210",
    ]
    
    print("=" * 80)
    print(" NL2SQL Translator Test")
    print("=" * 80)
    print()
    
    for query in test_queries:
        result = translator.translate(query, case_id="ADV_TEST_001")
        print(f"Query: {query}")
        print(f"SQL:   {result['sql']}")
        print(f"Confidence: {result['confidence']:.0%}")
        print(f"Method: {result['method']}")
        print()


if __name__ == "__main__":
    test_nl2sql()