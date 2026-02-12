"""
Canonical Data Models for UFDR Analysis System
Aligned with Phase B requirements from the development plan

These models ensure:
- Normalized data representation
- ISO8601 timestamps
- E.164 phone numbers
- Standardized app names
- Forensic integrity preservation
"""

import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import json


class MessageType(Enum):
    """Message types across different platforms"""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"
    LOCATION = "location"
    CONTACT = "contact"
    STICKER = "sticker"
    GIF = "gif"
    VOICE_NOTE = "voice_note"
    VIDEO_NOTE = "video_note"
    DELETED = "deleted"


class CallDirection(Enum):
    """Call direction types"""
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    MISSED = "missed"
    REJECTED = "rejected"
    BLOCKED = "blocked"


class MediaType(Enum):
    """Media file types"""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    UNKNOWN = "unknown"


@dataclass
class Case:
    """
    Case - Root entity for forensic investigation
    """
    case_id: str
    ingest_manifest_hash: str
    ingest_time: datetime
    uploader: str
    agency: str
    description: Optional[str] = None
    status: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary with ISO timestamps"""
        data = asdict(self)
        data['ingest_time'] = self.ingest_time.isoformat()
        return data
    
    @staticmethod
    def generate_manifest_hash(file_path: str) -> str:
        """Generate SHA256 hash of ingested file for integrity"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()


@dataclass
class Device:
    """
    Device - Mobile device or computer information
    """
    device_id: str
    case_id: str
    imei: Optional[str] = None
    serial_number: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    os_type: Optional[str] = None
    os_version: Optional[str] = None
    phone_numbers: List[str] = field(default_factory=list)
    mac_addresses: List[str] = field(default_factory=list)
    acquisition_date: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        if self.acquisition_date:
            data['acquisition_date'] = self.acquisition_date.isoformat()
        return data


@dataclass
class Person:
    """
    Person - Entity representing a person in the investigation
    """
    person_id: str
    case_id: str
    name: Optional[str] = None
    phone_numbers: List[str] = field(default_factory=list)
    emails: List[str] = field(default_factory=list)
    usernames: List[str] = field(default_factory=list)
    addresses: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def normalize_phone_number(self, phone: str) -> Optional[str]:
        """Normalize phone number to E.164 format"""
        try:
            import phonenumbers
            parsed = phonenumbers.parse(phone, "IN")  # Default to India
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(
                    parsed, 
                    phonenumbers.PhoneNumberFormat.E164
                )
        except:
            # Fallback to basic cleaning
            cleaned = ''.join(filter(str.isdigit, phone))
            if len(cleaned) >= 10:
                return f"+{cleaned}"
        return None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class Message:
    """
    Message - Communications message (SMS, WhatsApp, Telegram, etc.)
    """
    id: str
    case_id: str
    device_id: str
    app: str  # Standardized: whatsapp, telegram, signal, sms, etc.
    from_person: Optional[str] = None
    to_person: Optional[str] = None
    participants: List[str] = field(default_factory=list)
    text: Optional[str] = None
    message_type: MessageType = MessageType.TEXT
    timestamp: Optional[datetime] = None
    is_deleted: bool = False
    source_path: Optional[str] = None
    media_references: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @staticmethod
    def standardize_app_name(raw_app: str) -> str:
        """Standardize application names"""
        app_mapping = {
            'whatsapp': 'whatsapp',
            'whatsapp business': 'whatsapp_business',
            'telegram': 'telegram',
            'telegram x': 'telegram',
            'signal': 'signal',
            'sms': 'sms',
            'mms': 'mms',
            'imessage': 'imessage',
            'facebook messenger': 'facebook_messenger',
            'instagram': 'instagram',
            'snapchat': 'snapchat',
            'viber': 'viber',
            'wechat': 'wechat',
            'line': 'line',
            'skype': 'skype',
            'discord': 'discord',
            'slack': 'slack',
        }
        normalized = raw_app.lower().strip()
        return app_mapping.get(normalized, normalized)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary with ISO timestamps"""
        data = asdict(self)
        if self.timestamp:
            data['timestamp'] = self.timestamp.isoformat()
        data['message_type'] = self.message_type.value
        return data


@dataclass
class Call:
    """
    Call - Phone call record
    """
    id: str
    case_id: str
    device_id: str
    number: str  # E.164 format
    direction: CallDirection
    duration: int  # in seconds
    timestamp: datetime
    contact_name: Optional[str] = None
    is_deleted: bool = False
    source_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['direction'] = self.direction.value
        return data


@dataclass
class Media:
    """
    Media - Media file (image, video, audio, document)
    """
    id: str
    case_id: str
    device_id: str
    type: MediaType
    original_path: str
    stored_path: str
    sha256: str
    phash: Optional[str] = None  # Perceptual hash for images
    file_size: int = 0
    mime_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None  # For video/audio in seconds
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    ocr_text: Optional[str] = None
    caption: Optional[str] = None
    embeddings: List[float] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @staticmethod
    def compute_sha256(file_path: str) -> str:
        """Compute SHA256 hash of file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    @staticmethod
    def compute_perceptual_hash(image_path: str) -> Optional[str]:
        """
        Compute perceptual hash (pHash) for duplicate detection
        Uses imagehash library for robust image comparison
        """
        try:
            from PIL import Image
            import imagehash
            
            image = Image.open(image_path)
            # Use average hash for speed, can switch to phash for accuracy
            hash_value = imagehash.average_hash(image)
            return str(hash_value)
        except Exception as e:
            return None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['type'] = self.type.value
        if self.created_date:
            data['created_date'] = self.created_date.isoformat()
        if self.modified_date:
            data['modified_date'] = self.modified_date.isoformat()
        return data


@dataclass
class Location:
    """
    Location - Geographic location data
    """
    id: str
    case_id: str
    device_id: str
    latitude: float
    longitude: float
    timestamp: datetime
    altitude: Optional[float] = None
    accuracy: Optional[float] = None
    source_app: Optional[str] = None
    source_path: Optional[str] = None
    address: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class IngestManifest:
    """
    Ingest Manifest - Tracks ingestion process for chain of custody
    """
    manifest_id: str
    case_id: str
    file_name: str
    file_size: int
    file_hash_sha256: str
    ingest_timestamp: datetime
    examiner: str
    agency: str
    extraction_tool: Optional[str] = None
    extraction_version: Optional[str] = None
    total_messages: int = 0
    total_calls: int = 0
    total_contacts: int = 0
    total_media: int = 0
    total_locations: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['ingest_timestamp'] = self.ingest_timestamp.isoformat()
        return data
    
    def to_json(self, file_path: str):
        """Save manifest to JSON file"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


# Utility functions for canonical data processing

def normalize_timestamp(timestamp_str: str) -> Optional[datetime]:
    """
    Normalize various timestamp formats to ISO8601 datetime
    
    Args:
        timestamp_str: Timestamp string in various formats
        
    Returns:
        datetime object or None if parsing fails
    """
    if not timestamp_str:
        return None
    
    # Try common formats
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%d/%m/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(timestamp_str, fmt)
        except ValueError:
            continue
    
    # Try dateutil parser if available
    try:
        from dateutil import parser
        return parser.parse(timestamp_str)
    except:
        pass
    
    return None


def normalize_phone_number(phone: str, default_country: str = "IN") -> Optional[str]:
    """
    Normalize phone number to E.164 format
    
    Args:
        phone: Phone number string
        default_country: Default country code (ISO 3166-1 alpha-2)
        
    Returns:
        E.164 formatted phone number or None
    """
    if not phone:
        return None
    
    try:
        import phonenumbers
        parsed = phonenumbers.parse(phone, default_country)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(
                parsed, 
                phonenumbers.PhoneNumberFormat.E164
            )
    except:
        pass
    
    # Fallback: basic cleaning
    cleaned = ''.join(filter(str.isdigit, phone))
    if len(cleaned) >= 10:
        if not cleaned.startswith('+'):
            return f"+{cleaned}"
        return cleaned
    
    return None


# Export all models
__all__ = [
    'Case',
    'Device',
    'Person',
    'Message',
    'Call',
    'Media',
    'Location',
    'IngestManifest',
    'MessageType',
    'CallDirection',
    'MediaType',
    'normalize_timestamp',
    'normalize_phone_number',
]