"""
Query Intent Detector
Detects specific query patterns (phone suffix, prefix, date range, etc.)
and extracts relevant parameters before semantic search
"""

import re
import logging
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """Query intent types"""
    PHONE_SUFFIX = "phone_suffix"
    PHONE_PREFIX = "phone_prefix"
    PHONE_CONTAINS = "phone_contains"
    DATE_RANGE = "date_range"
    COUNTRY_CODE = "country_code"
    APP_FILTER = "app_filter"
    CRYPTO_ADDRESS = "crypto_address"
    FOREIGN_NUMBER = "foreign_number"
    EXACT_NUMBER = "exact_number"
    SEMANTIC = "semantic"  # fallback to vector search


class QueryIntentDetector:
    """Detects intent and extracts parameters from natural language queries"""
    
    def __init__(self):
        """Initialize intent detection patterns"""
        self.patterns = {
            'phone_suffix': [
                r'(?i)(ending\s+with|ends\s+with|ends\s+in|last\s+\d+\s+digits?)\s+([0-9]+)',
                r'(?i)number[s]?\s+(ending|ends)\s+with\s+([0-9]+)',
                r'(?i)phone[s]?\s+(ending|ends)\s+with\s+([0-9]+)',
                r'(?i)suffix\s+([0-9]+)',
                r'(?i)last\s+([0-9]+)\s+digit',
            ],
            'phone_prefix': [
                r'(?i)(starting\s+with|starts\s+with|begins\s+with|prefix)\s+([0-9]+)',
                r'(?i)number[s]?\s+(starting|starts)\s+with\s+([0-9]+)',
                r'(?i)area\s+code\s+([0-9]+)',
            ],
            'phone_contains': [
                r'(?i)(containing|contains)\s+([0-9]+)',
                r'(?i)number[s]?\s+with\s+([0-9]+)',
            ],
            'country_code': [
                r'(?i)country\s+code\s+\+?([0-9]+)',
                r'(?i)international\s+code\s+\+?([0-9]+)',
                r'(?i)from\s+country\s+\+?([0-9]+)',
            ],
            'date_range': [
                r'(?i)(after|since|from)\s+([\d\-\/]+)',
                r'(?i)(before|until|to)\s+([\d\-\/]+)',
                r'(?i)between\s+([\d\-\/]+)\s+and\s+([\d\-\/]+)',
                r'(?i)in\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})',
            ],
            'app_filter': [
                r'(?i)(from|in|on)\s+(whatsapp|telegram|instagram|facebook|signal|viber)',
            ],
            'exact_number': [
                r'(?i)exact\s+number\s+(\+?[0-9\-\s\(\)]+)',
                r'(?i)phone\s+number\s+(\+?[0-9\-\s\(\)]+)',
            ],
            'crypto_address': [
                r'(?i)(bitcoin|btc|ethereum|eth|crypto)\s+(address|wallet)',
                r'(?i)(0x[a-fA-F0-9]{40})',  # Ethereum address
                r'(?i)([13][a-km-zA-HJ-NP-Z1-9]{25,34})',  # Bitcoin address
            ],
        }
    
    def detect(self, query: str) -> Dict[str, Any]:
        """
        Detect query intent and extract parameters
        
        Args:
            query: Natural language query
            
        Returns:
            Dict with intent, confidence, and extracted parameters
        """
        result = {
            'intent': QueryIntent.SEMANTIC,
            'confidence': 0.0,
            'parameters': {},
            'original_query': query
        }
        
        # Check phone suffix
        suffix = self._detect_phone_suffix(query)
        if suffix:
            result['intent'] = QueryIntent.PHONE_SUFFIX
            result['confidence'] = 0.95
            result['parameters']['suffix'] = suffix
            logger.info(f"Detected phone suffix query: suffix={suffix}")
            return result
        
        # Check phone prefix
        prefix = self._detect_phone_prefix(query)
        if prefix:
            result['intent'] = QueryIntent.PHONE_PREFIX
            result['confidence'] = 0.95
            result['parameters']['prefix'] = prefix
            logger.info(f"Detected phone prefix query: prefix={prefix}")
            return result
        
        # Check phone contains
        contains = self._detect_phone_contains(query)
        if contains:
            result['intent'] = QueryIntent.PHONE_CONTAINS
            result['confidence'] = 0.90
            result['parameters']['contains'] = contains
            logger.info(f"Detected phone contains query: contains={contains}")
            return result
        
        # Check country code
        country = self._detect_country_code(query)
        if country:
            result['intent'] = QueryIntent.COUNTRY_CODE
            result['confidence'] = 0.90
            result['parameters']['country_code'] = country
            logger.info(f"Detected country code query: code={country}")
            return result
        
        # Check exact number
        exact = self._detect_exact_number(query)
        if exact:
            result['intent'] = QueryIntent.EXACT_NUMBER
            result['confidence'] = 0.95
            result['parameters']['phone'] = exact
            logger.info(f"Detected exact number query: phone={exact}")
            return result
        
        # Check app filter
        app = self._detect_app_filter(query)
        if app:
            result['parameters']['app'] = app
        
        # Check date range
        dates = self._detect_date_range(query)
        if dates:
            result['parameters'].update(dates)
        
        # Default to semantic search
        logger.info("No specific pattern detected, using semantic search")
        result['confidence'] = 0.5
        return result
    
    def _detect_phone_suffix(self, query: str) -> Optional[str]:
        """Detect phone number suffix in query"""
        for pattern in self.patterns['phone_suffix']:
            match = re.search(pattern, query)
            if match:
                # Extract the digits from the last group
                digits = match.group(match.lastindex)
                if digits and digits.isdigit():
                    return digits
        return None
    
    def _detect_phone_prefix(self, query: str) -> Optional[str]:
        """Detect phone number prefix in query"""
        for pattern in self.patterns['phone_prefix']:
            match = re.search(pattern, query)
            if match:
                digits = match.group(match.lastindex)
                if digits and digits.isdigit():
                    return digits
        return None
    
    def _detect_phone_contains(self, query: str) -> Optional[str]:
        """Detect phone number substring in query"""
        for pattern in self.patterns['phone_contains']:
            match = re.search(pattern, query)
            if match:
                digits = match.group(match.lastindex)
                if digits and digits.isdigit():
                    return digits
        return None
    
    def _detect_country_code(self, query: str) -> Optional[str]:
        """Detect country code in query"""
        for pattern in self.patterns['country_code']:
            match = re.search(pattern, query)
            if match:
                return match.group(match.lastindex)
        return None
    
    def _detect_app_filter(self, query: str) -> Optional[str]:
        """Detect app name filter"""
        for pattern in self.patterns['app_filter']:
            match = re.search(pattern, query)
            if match:
                return match.group(match.lastindex).lower()
        return None
    
    def _detect_exact_number(self, query: str) -> Optional[str]:
        """Detect exact phone number"""
        for pattern in self.patterns['exact_number']:
            match = re.search(pattern, query)
            if match:
                return match.group(match.lastindex).strip()
        return None
    
    def _detect_date_range(self, query: str) -> Dict[str, str]:
        """Detect date range in query"""
        dates = {}
        for pattern in self.patterns['date_range']:
            match = re.search(pattern, query)
            if match:
                if 'after' in match.group(1).lower() or 'since' in match.group(1).lower():
                    dates['start_date'] = match.group(2)
                elif 'before' in match.group(1).lower() or 'until' in match.group(1).lower():
                    dates['end_date'] = match.group(2)
                elif 'between' in match.group(0).lower():
                    dates['start_date'] = match.group(2)
                    dates['end_date'] = match.group(3) if match.lastindex >= 3 else None
        return dates


# Convenience function
def detect_query_intent(query: str) -> Dict[str, Any]:
    """Convenience function to detect query intent"""
    detector = QueryIntentDetector()
    return detector.detect(query)


if __name__ == "__main__":
    # Test the detector
    logging.basicConfig(level=logging.INFO)
    
    test_queries = [
        "number ending with 20",
        "show phone numbers ending with 652",
        "find all contacts starting with 968",
        "messages from numbers containing 192",
        "calls from country code +91",
        "WhatsApp messages after 2024-01-01",
        "find exact number +919681920652",
        "who called from foreign numbers"
    ]
    
    detector = QueryIntentDetector()
    for q in test_queries:
        result = detector.detect(q)
        print(f"\nQuery: {q}")
        print(f"Intent: {result['intent'].value}")
        print(f"Confidence: {result['confidence']:.2%}")
        print(f"Parameters: {result['parameters']}")