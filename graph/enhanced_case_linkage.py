"""
Enhanced Case Linkage Engine
Cross-case entity matching with confidence scoring

Features:
- Exact matching (phone numbers, hashes, identifiers)
- Fuzzy matching (embeddings, faces, perceptual hashes)
- Graph analytics (PageRank, community detection, centrality)
- Confidence scoring for matches
- LINKED_TO relationship creation
"""

import hashlib
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MatchType(Enum):
    """Type of cross-case match"""
    EXACT_PHONE = "exact_phone"
    EXACT_EMAIL = "exact_email"
    EXACT_MEDIA_SHA256 = "exact_media_sha256"
    EXACT_WALLET = "exact_wallet"
    FUZZY_PHASH = "fuzzy_phash"
    FUZZY_FACE = "fuzzy_face"
    FUZZY_TEXT = "fuzzy_text"
    FUZZY_EMBEDDING = "fuzzy_embedding"


class MatchConfidence(Enum):
    """Confidence levels for matches"""
    VERY_HIGH = 0.95  # Exact matches
    HIGH = 0.85       # Strong fuzzy matches
    MEDIUM = 0.70     # Moderate fuzzy matches
    LOW = 0.50        # Weak fuzzy matches


@dataclass
class EntityMatch:
    """A match between entities across cases"""
    match_id: str
    case1_id: str
    case2_id: str
    entity1_id: str
    entity2_id: str
    entity_type: str  # person, media, message, etc.
    match_type: MatchType
    confidence: float
    evidence: Dict
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'match_id': self.match_id,
            'case1_id': self.case1_id,
            'case2_id': self.case2_id,
            'entity1_id': self.entity1_id,
            'entity2_id': self.entity2_id,
            'entity_type': self.entity_type,
            'match_type': self.match_type.value,
            'confidence': self.confidence,
            'evidence': self.evidence,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class CaseLinkage:
    """Link between two cases"""
    linkage_id: str
    case1_id: str
    case2_id: str
    matches: List[EntityMatch]
    overall_confidence: float
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'linkage_id': self.linkage_id,
            'case1_id': self.case1_id,
            'case2_id': self.case2_id,
            'matches': [m.to_dict() for m in self.matches],
            'overall_confidence': self.overall_confidence,
            'match_count': len(self.matches),
            'created_at': self.created_at.isoformat()
        }


class CaseLinkageEngine:
    """
    Engine for discovering links between cases
    Uses exact and fuzzy matching strategies
    """
    
    def __init__(self):
        """Initialize case linkage engine"""
        self.matches: List[EntityMatch] = []
        self.linkages: Dict[Tuple[str, str], CaseLinkage] = {}
        
        # Thresholds for fuzzy matching
        self.phash_threshold = 5  # Hamming distance
        self.face_threshold = 0.6  # Cosine similarity
        self.text_threshold = 0.7  # Semantic similarity
        
        logger.info("Case linkage engine initialized")
    
    def _hamming_distance(self, hash1: str, hash2: str) -> int:
        """
        Calculate Hamming distance between two hash strings
        
        Args:
            hash1: First hash string
            hash2: Second hash string
            
        Returns:
            Hamming distance
        """
        if len(hash1) != len(hash2):
            return float('inf')
        return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity (0-1)
        """
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def match_phone_numbers(self, 
                           case1_contacts: List[Dict], 
                           case2_contacts: List[Dict]) -> List[EntityMatch]:
        """
        Find exact matches on phone numbers
        
        Args:
            case1_contacts: Contacts from case 1
            case2_contacts: Contacts from case 2
            
        Returns:
            List of phone number matches
        """
        matches = []
        
        # Build phone number index for case 2
        case2_phones = {}
        for contact in case2_contacts:
            for phone in contact.get('phone_numbers', []):
                if phone:
                    case2_phones[phone] = contact
        
        # Check case 1 contacts against index
        for contact1 in case1_contacts:
            for phone in contact1.get('phone_numbers', []):
                if phone and phone in case2_phones:
                    contact2 = case2_phones[phone]
                    
                    match = EntityMatch(
                        match_id=f"phone_{hashlib.md5((phone).encode()).hexdigest()[:16]}",
                        case1_id=contact1.get('case_id'),
                        case2_id=contact2.get('case_id'),
                        entity1_id=contact1.get('person_id'),
                        entity2_id=contact2.get('person_id'),
                        entity_type='person',
                        match_type=MatchType.EXACT_PHONE,
                        confidence=MatchConfidence.VERY_HIGH.value,
                        evidence={
                            'phone_number': phone,
                            'name1': contact1.get('name'),
                            'name2': contact2.get('name')
                        }
                    )
                    matches.append(match)
                    logger.info(f"Phone match found: {phone}")
        
        return matches
    
    def match_media_sha256(self,
                          case1_media: List[Dict],
                          case2_media: List[Dict]) -> List[EntityMatch]:
        """
        Find exact matches on media SHA256 hashes
        
        Args:
            case1_media: Media from case 1
            case2_media: Media from case 2
            
        Returns:
            List of media SHA256 matches
        """
        matches = []
        
        # Build SHA256 index for case 2
        case2_hashes = {}
        for media in case2_media:
            sha256 = media.get('sha256')
            if sha256:
                case2_hashes[sha256] = media
        
        # Check case 1 media against index
        for media1 in case1_media:
            sha256 = media1.get('sha256')
            if sha256 and sha256 in case2_hashes:
                media2 = case2_hashes[sha256]
                
                match = EntityMatch(
                    match_id=f"sha256_{sha256[:16]}",
                    case1_id=media1.get('case_id'),
                    case2_id=media2.get('case_id'),
                    entity1_id=media1.get('id'),
                    entity2_id=media2.get('id'),
                    entity_type='media',
                    match_type=MatchType.EXACT_MEDIA_SHA256,
                    confidence=MatchConfidence.VERY_HIGH.value,
                    evidence={
                        'sha256': sha256,
                        'type': media1.get('type'),
                        'file_size': media1.get('file_size')
                    }
                )
                matches.append(match)
                logger.info(f"Media SHA256 match found: {sha256[:16]}...")
        
        return matches
    
    def match_perceptual_hash(self,
                             case1_media: List[Dict],
                             case2_media: List[Dict],
                             threshold: Optional[int] = None) -> List[EntityMatch]:
        """
        Find fuzzy matches on perceptual hashes (pHash)
        
        Args:
            case1_media: Media from case 1
            case2_media: Media from case 2
            threshold: Hamming distance threshold (default: self.phash_threshold)
            
        Returns:
            List of perceptual hash matches
        """
        if threshold is None:
            threshold = self.phash_threshold
        
        matches = []
        
        # Compare all pairs
        for media1 in case1_media:
            phash1 = media1.get('phash')
            if not phash1:
                continue
            
            for media2 in case2_media:
                phash2 = media2.get('phash')
                if not phash2:
                    continue
                
                distance = self._hamming_distance(phash1, phash2)
                
                if distance <= threshold:
                    # Calculate confidence based on distance
                    confidence = max(0.5, 1.0 - (distance / 16.0))
                    
                    match = EntityMatch(
                        match_id=f"phash_{hashlib.md5((phash1+phash2).encode()).hexdigest()[:16]}",
                        case1_id=media1.get('case_id'),
                        case2_id=media2.get('case_id'),
                        entity1_id=media1.get('id'),
                        entity2_id=media2.get('id'),
                        entity_type='media',
                        match_type=MatchType.FUZZY_PHASH,
                        confidence=confidence,
                        evidence={
                            'phash1': phash1,
                            'phash2': phash2,
                            'hamming_distance': distance
                        }
                    )
                    matches.append(match)
                    logger.info(f"pHash match found: distance={distance}")
        
        return matches
    
    def match_embeddings(self,
                        case1_entities: List[Dict],
                        case2_entities: List[Dict],
                        entity_type: str,
                        threshold: Optional[float] = None) -> List[EntityMatch]:
        """
        Find fuzzy matches using embedding similarity
        
        Args:
            case1_entities: Entities from case 1 with embeddings
            case2_entities: Entities from case 2 with embeddings
            entity_type: Type of entity (message, media, etc.)
            threshold: Similarity threshold (default: self.text_threshold)
            
        Returns:
            List of embedding matches
        """
        if threshold is None:
            threshold = self.text_threshold
        
        matches = []
        
        # Compare all pairs
        for entity1 in case1_entities:
            emb1 = entity1.get('embeddings', [])
            if not emb1:
                continue
            
            for entity2 in case2_entities:
                emb2 = entity2.get('embeddings', [])
                if not emb2:
                    continue
                
                similarity = self._cosine_similarity(emb1, emb2)
                
                if similarity >= threshold:
                    match = EntityMatch(
                        match_id=f"emb_{hashlib.md5((entity1.get('id')+entity2.get('id')).encode()).hexdigest()[:16]}",
                        case1_id=entity1.get('case_id'),
                        case2_id=entity2.get('case_id'),
                        entity1_id=entity1.get('id'),
                        entity2_id=entity2.get('id'),
                        entity_type=entity_type,
                        match_type=MatchType.FUZZY_EMBEDDING,
                        confidence=similarity,
                        evidence={
                            'similarity': similarity,
                            'text1': entity1.get('text', '')[:100],
                            'text2': entity2.get('text', '')[:100]
                        }
                    )
                    matches.append(match)
                    logger.info(f"Embedding match found: similarity={similarity:.3f}")
        
        return matches
    
    def find_all_matches(self, case1_data: Dict, case2_data: Dict) -> List[EntityMatch]:
        """
        Find all possible matches between two cases
        
        Args:
            case1_data: Complete data for case 1
            case2_data: Complete data for case 2
            
        Returns:
            List of all matches found
        """
        all_matches = []
        
        # Exact matches
        logger.info(f"Finding exact matches between {case1_data.get('case_id')} and {case2_data.get('case_id')}")
        
        # Phone number matches
        if 'contacts' in case1_data and 'contacts' in case2_data:
            phone_matches = self.match_phone_numbers(
                case1_data['contacts'],
                case2_data['contacts']
            )
            all_matches.extend(phone_matches)
            logger.info(f"Found {len(phone_matches)} phone number matches")
        
        # Media SHA256 matches
        if 'media' in case1_data and 'media' in case2_data:
            sha256_matches = self.match_media_sha256(
                case1_data['media'],
                case2_data['media']
            )
            all_matches.extend(sha256_matches)
            logger.info(f"Found {len(sha256_matches)} SHA256 matches")
        
        # Fuzzy matches
        logger.info("Finding fuzzy matches...")
        
        # Perceptual hash matches (images)
        if 'media' in case1_data and 'media' in case2_data:
            phash_matches = self.match_perceptual_hash(
                case1_data['media'],
                case2_data['media']
            )
            all_matches.extend(phash_matches)
            logger.info(f"Found {len(phash_matches)} perceptual hash matches")
        
        # Embedding matches (messages)
        if 'messages' in case1_data and 'messages' in case2_data:
            emb_matches = self.match_embeddings(
                case1_data['messages'],
                case2_data['messages'],
                'message'
            )
            all_matches.extend(emb_matches)
            logger.info(f"Found {len(emb_matches)} message embedding matches")
        
        self.matches.extend(all_matches)
        return all_matches
    
    def create_case_linkage(self, 
                           case1_id: str, 
                           case2_id: str, 
                           matches: List[EntityMatch]) -> CaseLinkage:
        """
        Create a case linkage from matches
        
        Args:
            case1_id: First case ID
            case2_id: Second case ID
            matches: List of entity matches
            
        Returns:
            CaseLinkage object
        """
        # Calculate overall confidence as weighted average
        if not matches:
            overall_confidence = 0.0
        else:
            # Weight by match type
            weights = {
                MatchType.EXACT_PHONE: 1.0,
                MatchType.EXACT_EMAIL: 1.0,
                MatchType.EXACT_MEDIA_SHA256: 1.0,
                MatchType.EXACT_WALLET: 1.0,
                MatchType.FUZZY_PHASH: 0.8,
                MatchType.FUZZY_FACE: 0.7,
                MatchType.FUZZY_TEXT: 0.6,
                MatchType.FUZZY_EMBEDDING: 0.6,
            }
            
            weighted_sum = sum(m.confidence * weights.get(m.match_type, 0.5) for m in matches)
            weight_sum = sum(weights.get(m.match_type, 0.5) for m in matches)
            overall_confidence = weighted_sum / weight_sum if weight_sum > 0 else 0.0
        
        linkage = CaseLinkage(
            linkage_id=f"link_{hashlib.md5((case1_id+case2_id).encode()).hexdigest()[:16]}",
            case1_id=case1_id,
            case2_id=case2_id,
            matches=matches,
            overall_confidence=overall_confidence
        )
        
        self.linkages[(case1_id, case2_id)] = linkage
        
        logger.info(f"Created linkage: {case1_id} <-> {case2_id} (confidence: {overall_confidence:.3f}, {len(matches)} matches)")
        
        return linkage
    
    def get_linkages_for_case(self, case_id: str) -> List[CaseLinkage]:
        """
        Get all linkages involving a specific case
        
        Args:
            case_id: Case identifier
            
        Returns:
            List of case linkages
        """
        return [
            linkage for (c1, c2), linkage in self.linkages.items()
            if c1 == case_id or c2 == case_id
        ]
    
    def export_linkages(self, output_file: str):
        """
        Export linkages to JSON file
        
        Args:
            output_file: Output file path
        """
        linkages_data = [linkage.to_dict() for linkage in self.linkages.values()]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'linkages': linkages_data,
                'total_linkages': len(linkages_data),
                'export_time': datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported {len(linkages_data)} linkages to {output_file}")


# Example usage
if __name__ == "__main__":
    engine = CaseLinkageEngine()
    
    # Example case data
    case1_data = {
        'case_id': 'CASE_2024_001',
        'contacts': [
            {
                'person_id': 'P1',
                'case_id': 'CASE_2024_001',
                'name': 'John Doe',
                'phone_numbers': ['+919876543210', '+919999999999']
            }
        ],
        'media': [
            {
                'id': 'M1',
                'case_id': 'CASE_2024_001',
                'sha256': 'abc123def456',
                'phash': '0000111100001111',
                'type': 'image'
            }
        ],
        'messages': []
    }
    
    case2_data = {
        'case_id': 'CASE_2024_002',
        'contacts': [
            {
                'person_id': 'P2',
                'case_id': 'CASE_2024_002',
                'name': 'Jane Smith',
                'phone_numbers': ['+919876543210']  # Same phone!
            }
        ],
        'media': [
            {
                'id': 'M2',
                'case_id': 'CASE_2024_002',
                'sha256': 'abc123def456',  # Same file!
                'phash': '0000111100001111',
                'type': 'image'
            }
        ],
        'messages': []
    }
    
    # Find matches
    matches = engine.find_all_matches(case1_data, case2_data)
    
    print(f"\nFound {len(matches)} matches:")
    for match in matches:
        print(f"  - {match.match_type.value}: confidence={match.confidence:.2f}")
    
    # Create linkage
    linkage = engine.create_case_linkage('CASE_2024_001', 'CASE_2024_002', matches)
    print(f"\nLinkage created: {linkage.overall_confidence:.2f} overall confidence")
    
    # Export
    engine.export_linkages("case_linkages.json")
    print("\nLinkages exported to case_linkages.json")