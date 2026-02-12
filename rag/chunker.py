"""
Forensic-Aware Document Chunker for UFDR Analysis Tool

Converts SQLite forensic records into text chunks optimized for 
semantic search and keyword matching. Each record → one chunk with 
rich metadata for ChromaDB filtering.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def chunk_message(row: dict, case_id: str) -> tuple[str, dict, str]:
    """
    Convert a message record into a searchable text chunk.
    
    Returns:
        (document_text, metadata_dict, unique_id)
    """
    app = row.get("app", "Unknown")
    sender = row.get("sender_raw", row.get("sender_digits", "Unknown"))
    receiver = row.get("receiver_raw", row.get("receiver_digits", "Unknown"))
    timestamp = row.get("timestamp", "")
    body = row.get("body", row.get("text", ""))
    direction = row.get("direction", "")
    
    text = f"[{app}] Message from {sender} to {receiver}"
    if timestamp:
        text += f" at {timestamp}"
    if direction:
        text += f" ({direction})"
    text += f": {body}" if body else ""
    
    metadata = {
        "data_type": "message",
        "case_id": case_id,
        "app": str(app or ""),
        "sender": str(sender or ""),
        "receiver": str(receiver or ""),
        "timestamp": str(timestamp or ""),
        "direction": str(direction or ""),
    }
    
    msg_id = row.get("msg_id", row.get("id", f"msg_{hash(text)}"))
    doc_id = f"{case_id}_msg_{msg_id}"
    
    return text, metadata, doc_id


def chunk_contact(row: dict, case_id: str) -> tuple[str, dict, str]:
    """Convert a contact record into a searchable text chunk."""
    name = row.get("name", "Unknown")
    phone = row.get("phone_raw", row.get("phone_digits", row.get("phone", "")))
    email = row.get("email", "")
    
    text = f"Contact: {name}"
    if phone:
        text += f" | Phone: {phone}"
    if email:
        text += f" | Email: {email}"
    
    metadata = {
        "data_type": "contact",
        "case_id": case_id,
        "name": str(name or ""),
        "phone": str(phone or ""),
        "email": str(email or ""),
    }
    
    contact_id = row.get("contact_id", row.get("id", f"contact_{hash(text)}"))
    doc_id = f"{case_id}_contact_{contact_id}"
    
    return text, metadata, doc_id


def chunk_call(row: dict, case_id: str) -> tuple[str, dict, str]:
    """Convert a call record into a searchable text chunk."""
    caller = row.get("caller_raw", row.get("caller_digits", row.get("caller", "Unknown")))
    receiver = row.get("receiver_raw", row.get("receiver_digits", row.get("receiver", "Unknown")))
    direction = row.get("direction", "")
    duration = row.get("duration_seconds", row.get("duration", ""))
    timestamp = row.get("timestamp", "")
    call_type = row.get("call_type", "")
    
    # Format duration nicely
    dur_str = ""
    if duration:
        try:
            secs = int(duration)
            mins, secs = divmod(secs, 60)
            dur_str = f"{mins}m {secs}s" if mins else f"{secs}s"
        except (ValueError, TypeError):
            dur_str = str(duration)
    
    text = f"{direction.capitalize() if direction else 'Call'} call"
    text += f" from {caller} to {receiver}"
    if dur_str:
        text += f" | Duration: {dur_str}"
    if timestamp:
        text += f" | {timestamp}"
    if call_type:
        text += f" | Type: {call_type}"
    
    metadata = {
        "data_type": "call",
        "case_id": case_id,
        "caller": str(caller or ""),
        "receiver": str(receiver or ""),
        "direction": str(direction or ""),
        "duration": str(duration or ""),
        "timestamp": str(timestamp or ""),
    }
    
    call_id = row.get("call_id", row.get("id", f"call_{hash(text)}"))
    doc_id = f"{case_id}_call_{call_id}"
    
    return text, metadata, doc_id


def chunk_media(row: dict, case_id: str) -> tuple[str, dict, str]:
    """Convert a media record into a searchable text chunk."""
    filename = row.get("filename", row.get("file_path", "Unknown"))
    media_type = row.get("media_type", row.get("type", ""))
    file_size = row.get("file_size", row.get("size", ""))
    timestamp = row.get("timestamp", row.get("created_at", ""))
    md5 = row.get("md5", row.get("hash", ""))
    caption = row.get("caption", "")
    
    text = f"Media file: {filename}"
    if media_type:
        text += f" | Type: {media_type}"
    if file_size:
        text += f" | Size: {file_size}"
    if timestamp:
        text += f" | {timestamp}"
    if caption:
        text += f" | Caption: {caption}"
    if md5:
        text += f" | Hash: {md5}"
    
    metadata = {
        "data_type": "media",
        "case_id": case_id,
        "filename": str(filename or ""),
        "media_type": str(media_type or ""),
        "timestamp": str(timestamp or ""),
    }
    
    media_id = row.get("media_id", row.get("id", f"media_{hash(text)}"))
    doc_id = f"{case_id}_media_{media_id}"
    
    return text, metadata, doc_id


def chunk_location(row: dict, case_id: str) -> tuple[str, dict, str]:
    """Convert a location record into a searchable text chunk."""
    latitude = row.get("latitude", row.get("lat", ""))
    longitude = row.get("longitude", row.get("lng", row.get("lon", "")))
    timestamp = row.get("timestamp", "")
    source = row.get("source", "")
    accuracy = row.get("accuracy", "")
    address = row.get("address", "")
    
    text = f"Location: ({latitude}, {longitude})"
    if address:
        text += f" | Address: {address}"
    if source:
        text += f" | Source: {source}"
    if accuracy:
        text += f" | Accuracy: {accuracy}m"
    if timestamp:
        text += f" | {timestamp}"
    
    metadata = {
        "data_type": "location",
        "case_id": case_id,
        "latitude": str(latitude or ""),
        "longitude": str(longitude or ""),
        "source": str(source or ""),
        "timestamp": str(timestamp or ""),
    }
    
    loc_id = row.get("location_id", row.get("id", f"loc_{hash(text)}"))
    doc_id = f"{case_id}_loc_{loc_id}"
    
    return text, metadata, doc_id


# Mapping of table names to chunker functions
CHUNKERS = {
    "messages": chunk_message,
    "contacts": chunk_contact,
    "calls": chunk_call,
    "media": chunk_media,
    "locations": chunk_location,
}


def chunk_records(
    table_name: str,
    rows: list[dict],
    case_id: str
) -> tuple[list[str], list[dict], list[str]]:
    """
    Chunk a batch of records from a given table.
    
    Args:
        table_name: Name of the SQLite table
        rows: List of row dicts
        case_id: Case identifier
        
    Returns:
        (documents, metadatas, ids) — ready for ChromaDB
    """
    chunker = CHUNKERS.get(table_name)
    if not chunker:
        logger.warning(f"No chunker for table '{table_name}', skipping")
        return [], [], []
    
    documents = []
    metadatas = []
    ids = []
    
    for row in rows:
        try:
            doc, meta, doc_id = chunker(row, case_id)
            if doc.strip():  # Skip empty documents
                documents.append(doc)
                metadatas.append(meta)
                ids.append(doc_id)
        except Exception as e:
            logger.warning(f"Failed to chunk row in {table_name}: {e}")
    
    logger.info(f"Chunked {len(documents)} records from '{table_name}' for case '{case_id}'")
    return documents, metadatas, ids
