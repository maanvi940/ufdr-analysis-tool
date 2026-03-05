import os
import json
import logging
import asyncio
from pathlib import Path
from rag.indexer import CaseIndexer
from rag.faiss_store import FAISSStore
from rag.retriever import HybridRetriever
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_dummy_data(case_id):
    """Create dummy ASR and Video output files."""
    data_dir = Path("data")
    asr_dir = data_dir / "asr_output"
    video_dir = data_dir / "video_output"
    
    asr_dir.mkdir(parents=True, exist_ok=True)
    video_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Dummy ASR
    asr_data = {
        "audio_path": "audio1.wav",
        "transcript": "This is a secret conversation about the hidden funds.",
        "language": "en",
        "confidence": 0.95,
        "metadata": {"modified": "2024-01-01T12:00:00"},
        "sha256_hash": "audio_hash_123"
    }
    with open(asr_dir / f"{case_id}_asr_results.jsonl", "w") as f:
        f.write(json.dumps(asr_data) + "\n")
        
    # 2. Dummy Video
    # Use real embedding for 'gun' to test retrieval
    try:
        model = SentenceTransformer('clip-ViT-B-32')
        gun_embedding = model.encode("gun").tolist()
    except:
        gun_embedding = [0.1] * 512
        
    video_data = {
        "video_path": "video1.mp4",
        "audio_transcript": "Look at this object in the video.", # Changed text so it doesn't match 'gun' textually
        "metadata": {"modified": "2024-01-01T13:00:00"},
        "sha256_hash": "video_hash_456",
        "keyframes": [
            {
                "frame_index": 0,
                "timestamp": 5.0,
                "ocr_text": "CONFIDENTIAL DOCUMENT",
                "detections": ["gun", "person"],
                "embedding": gun_embedding
            }
        ]
    }
    with open(video_dir / f"{case_id}_video_results.jsonl", "w") as f:
        f.write(json.dumps(video_data) + "\n")
        
    logger.info(f"Created dummy data for {case_id}")

def verify_index(case_id):
    store = FAISSStore()
    
    # Check Text Collection
    print("\n--- Verifying Text Collection ---")
    results = store.query(case_id, "secret conversation", n_results=5)
    print(f"Text Search Results: {len(results['documents'])}")
    for doc, meta in zip(results['documents'], results['metadatas']):
        print(f"  - {doc[:50]}... (Type: {meta.get('data_type')})")
        
    # Check Image Collection
    print("\n--- Verifying Image Collection ---")
    # We query with the same embedding we used
    try:
        model = SentenceTransformer('clip-ViT-B-32')
        query_emb = model.encode("gun").tolist()
    except:
        query_emb = [[0.1] * 512]
        
    results = store.query(
        case_id, 
        query_text="", # ignored
        query_embeddings=[query_emb],
        modality="image", 
        n_results=5
    )
    print(f"Image Search Results: {len(results['documents'])}")
    print(f"Image Search Results: {len(results['documents'])}")
    for doc, meta, dist in zip(results['documents'], results['metadatas'], results['distances']):
        print(f"  - {doc} (Dist: {dist:.4f})")

def verify_retriever(case_id):
    print("\n--- Verifying Hybrid Retriever ---")
    retriever = HybridRetriever()
    
    # 1. Text Query
    print("\nQuery: 'secret funds'")
    results = retriever.retrieve("secret funds", [case_id], n_results=5)
    print(f"Results: {len(results['documents'])}")
    for doc, score in zip(results['documents'], results['scores']):
        print(f"  - [{score:.2f}] {doc[:50]}...")
        
    # 2. Image/Hybrid Query
    print("\nQuery: 'gun'")
    results = retriever.retrieve("gun", [case_id], n_results=5)
    print(f"Results: {len(results['documents'])}")
    for doc, score, meta in zip(results['documents'], results['scores'], results['metadatas']):
        dtype = meta.get('data_type')
        print(f"  - [{score:.2f}] ({dtype}) {doc[:50]}...")

def main():
    case_id = "test_multimodal_case"
    
    # Setup
    create_dummy_data(case_id)
    
    # Index
    indexer = CaseIndexer()
    
    # Reset index to ensure fresh data
    print("Resetting index...")
    indexer.delete_case_index(case_id)
    
    print("\nIndexing Case...")
    stats = indexer.index_case(case_id)
    print(f"Indexing Stats: {stats}")
    
    # Verify
    verify_index(case_id)
    verify_retriever(case_id)
    
    # Cleanup (optional)
    # indexer.delete_case_index(case_id)

if __name__ == "__main__":
    main()
