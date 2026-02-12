"""
Multi-Modal Vector Store Manager
Extends existing FAISS infrastructure for images, audio, and video embeddings
Builds on top of the existing vector/index_builder.py
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
import json
from datetime import datetime

try:
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logging.warning("FAISS not available. Install with: pip install faiss-cpu")

import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result from vector search"""
    id: str
    case_id: str
    modality: str  # 'text', 'image', 'audio', 'video'
    content: str
    metadata: Dict[str, Any]
    distance: float
    confidence: float
    
    def to_dict(self) -> Dict:
        return asdict(self)


class MultiModalVectorStore:
    """
    Manages multi-modal vector collections using ChromaDB
    
    Collections:
    - forensic_contacts: Contact name embeddings
    - forensic_messages: Message text embeddings
    - forensic_images: Image embeddings (CLIP)
    - forensic_audio: Audio transcript embeddings
    - forensic_videos: Video embeddings (combined visual + audio)
    - forensic_documents: Document embeddings
    """
    
    def __init__(self, persist_directory: str = "data/vector_db"):
        """
        Initialize multi-modal vector store
        
        Args:
            persist_directory: Directory to store ChromaDB data
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB is required. Install with: pip install chromadb==0.4.18")
        
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client with persistence
        logger.info(f"Initializing ChromaDB at: {self.persist_directory}")
        self.client = chromadb.Client(Settings(
            persist_directory=str(self.persist_directory),
            anonymized_telemetry=False,
        ))
        
        # Collection names
        self.collection_names = {
            "contacts": "forensic_contacts",
            "messages": "forensic_messages",
            "images": "forensic_images",
            "audio": "forensic_audio",
            "videos": "forensic_videos",
            "documents": "forensic_documents",
        }
        
        # Initialize collections
        self.collections = {}
        self._initialize_collections()
        
        logger.info("✅ Multi-modal vector store initialized")
    
    def _initialize_collections(self):
        """Create or load all collections"""
        metadata_specs = {
            "contacts": {
                "case_id": "string",
                "contact_name": "string",
                "phone_numbers": "string",
                "timestamp": "number",
            },
            "messages": {
                "case_id": "string",
                "sender": "string",
                "recipient": "string",
                "timestamp": "number",
                "app_type": "string",
            },
            "images": {
                "case_id": "string",
                "file_path": "string",
                "file_hash": "string",
                "detected_objects": "string",  # JSON string
                "scene_description": "string",
                "timestamp": "number",
                "location": "string",
            },
            "audio": {
                "case_id": "string",
                "file_path": "string",
                "duration": "number",
                "transcript": "string",
                "speakers": "string",  # JSON string
                "timestamp": "number",
            },
            "videos": {
                "case_id": "string",
                "file_path": "string",
                "duration": "number",
                "visual_summary": "string",
                "audio_transcript": "string",
                "timestamp": "number",
            },
            "documents": {
                "case_id": "string",
                "file_path": "string",
                "doc_type": "string",
                "timestamp": "number",
            }
        }
        
        for key, collection_name in self.collection_names.items():
            try:
                # Get or create collection
                collection = self.client.get_or_create_collection(
                    name=collection_name,
                    metadata={"description": f"Forensic {key} embeddings"}
                )
                self.collections[key] = collection
                logger.info(f"✅ Collection '{collection_name}' ready ({collection.count()} items)")
            except Exception as e:
                logger.error(f"Failed to initialize collection '{collection_name}': {e}")
                raise
    
    def add_embeddings(
        self,
        modality: str,
        ids: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        documents: Optional[List[str]] = None
    ) -> bool:
        """
        Add embeddings to a collection
        
        Args:
            modality: Type of data ('contacts', 'messages', 'images', etc.)
            ids: Unique IDs for each embedding
            embeddings: List of embedding vectors
            metadatas: Metadata for each embedding
            documents: Optional text content for each embedding
            
        Returns:
            True if successful
        """
        if modality not in self.collections:
            logger.error(f"Unknown modality: {modality}")
            return False
        
        collection = self.collections[modality]
        
        try:
            # Convert numpy arrays to lists if needed
            if isinstance(embeddings, np.ndarray):
                embeddings = embeddings.tolist()
            elif isinstance(embeddings[0], np.ndarray):
                embeddings = [e.tolist() for e in embeddings]
            
            # Add to collection
            collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents if documents else [f"{modality}_{id}" for id in ids]
            )
            
            logger.info(f"✅ Added {len(ids)} {modality} embeddings")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add {modality} embeddings: {e}")
            return False
    
    def search(
        self,
        modality: str,
        query_embedding: List[float],
        n_results: int = 10,
        where: Optional[Dict] = None,
        where_document: Optional[Dict] = None
    ) -> List[SearchResult]:
        """
        Search a collection by query embedding
        
        Args:
            modality: Type of data to search
            query_embedding: Query embedding vector
            n_results: Number of results to return
            where: Metadata filters (e.g., {"case_id": "CASE_001"})
            where_document: Document content filters
            
        Returns:
            List of SearchResult objects
        """
        if modality not in self.collections:
            logger.error(f"Unknown modality: {modality}")
            return []
        
        collection = self.collections[modality]
        
        try:
            # Convert numpy array if needed
            if isinstance(query_embedding, np.ndarray):
                query_embedding = query_embedding.tolist()
            
            # Query collection
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                where_document=where_document
            )
            
            # Parse results
            search_results = []
            for i in range(len(results['ids'][0])):
                # Calculate confidence from distance (1 - normalized distance)
                distance = results['distances'][0][i]
                confidence = max(0.0, 1.0 - (distance / 2.0))  # Normalize to 0-1
                
                result = SearchResult(
                    id=results['ids'][0][i],
                    case_id=results['metadatas'][0][i].get('case_id', 'unknown'),
                    modality=modality,
                    content=results['documents'][0][i],
                    metadata=results['metadatas'][0][i],
                    distance=distance,
                    confidence=confidence
                )
                search_results.append(result)
            
            logger.info(f"Found {len(search_results)} {modality} results")
            return search_results
            
        except Exception as e:
            logger.error(f"Search failed for {modality}: {e}")
            return []
    
    def search_multi_modal(
        self,
        modalities: List[str],
        query_embeddings: Dict[str, List[float]],
        n_results: int = 10,
        case_id: Optional[str] = None
    ) -> Dict[str, List[SearchResult]]:
        """
        Search across multiple modalities
        
        Args:
            modalities: List of modalities to search
            query_embeddings: Dict mapping modality to query embedding
            n_results: Number of results per modality
            case_id: Optional case_id filter
            
        Returns:
            Dict mapping modality to list of results
        """
        results = {}
        where = {"case_id": case_id} if case_id else None
        
        for modality in modalities:
            if modality not in query_embeddings:
                logger.warning(f"No query embedding for {modality}, skipping")
                continue
            
            results[modality] = self.search(
                modality=modality,
                query_embedding=query_embeddings[modality],
                n_results=n_results,
                where=where
            )
        
        return results
    
    def get_by_id(self, modality: str, item_id: str) -> Optional[Dict]:
        """Get a specific item by ID"""
        if modality not in self.collections:
            return None
        
        collection = self.collections[modality]
        
        try:
            result = collection.get(ids=[item_id])
            if result['ids']:
                return {
                    "id": result['ids'][0],
                    "metadata": result['metadatas'][0],
                    "document": result['documents'][0]
                }
        except Exception as e:
            logger.error(f"Failed to get item {item_id}: {e}")
        
        return None
    
    def delete(self, modality: str, ids: List[str]) -> bool:
        """Delete items by ID"""
        if modality not in self.collections:
            return False
        
        collection = self.collections[modality]
        
        try:
            collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} {modality} items")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {modality} items: {e}")
            return False
    
    def get_stats(self) -> Dict[str, int]:
        """Get count of items in each collection"""
        stats = {}
        for key, collection in self.collections.items():
            stats[key] = collection.count()
        return stats
    
    def clear_collection(self, modality: str) -> bool:
        """Clear all items from a collection"""
        if modality not in self.collection_names:
            return False
        
        try:
            # Delete and recreate collection
            collection_name = self.collection_names[modality]
            self.client.delete_collection(collection_name)
            self.collections[modality] = self.client.create_collection(
                name=collection_name,
                metadata={"description": f"Forensic {modality} embeddings"}
            )
            logger.info(f"✅ Cleared {modality} collection")
            return True
        except Exception as e:
            logger.error(f"Failed to clear {modality} collection: {e}")
            return False
    
    def export_collection(self, modality: str, output_file: Path) -> bool:
        """Export a collection to JSON file"""
        if modality not in self.collections:
            return False
        
        collection = self.collections[modality]
        
        try:
            # Get all items
            all_items = collection.get()
            
            export_data = {
                "modality": modality,
                "count": len(all_items['ids']),
                "exported_at": datetime.now().isoformat(),
                "items": [
                    {
                        "id": all_items['ids'][i],
                        "metadata": all_items['metadatas'][i],
                        "document": all_items['documents'][i],
                        "embedding": all_items['embeddings'][i] if 'embeddings' in all_items else None
                    }
                    for i in range(len(all_items['ids']))
                ]
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"✅ Exported {len(all_items['ids'])} {modality} items to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export {modality}: {e}")
            return False


# Convenience functions

def create_vector_store(persist_directory: str = "data/vector_db") -> MultiModalVectorStore:
    """Create and return a vector store instance"""
    return MultiModalVectorStore(persist_directory=persist_directory)


def get_vector_store() -> MultiModalVectorStore:
    """Get singleton vector store instance"""
    if not hasattr(get_vector_store, "_instance"):
        get_vector_store._instance = MultiModalVectorStore()
    return get_vector_store._instance
