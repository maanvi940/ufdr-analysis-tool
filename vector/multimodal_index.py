"""
Multi-Modal FAISS Index Manager
Extends existing FAISS infrastructure for images, audio, and video embeddings
Uses separate FAISS indices for each modality
"""

import logging
import pickle
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
import json
from datetime import datetime

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MultiModalSearchResult:
    """Result from multi-modal vector search"""
    id: str
    case_id: str
    modality: str  # 'text', 'image', 'audio', 'video'
    content: str
    metadata: Dict[str, Any]
    distance: float
    confidence: float
    vector_id: int
    
    def to_dict(self) -> Dict:
        return asdict(self)


class MultiModalIndex:
    """
    Manages separate FAISS indices for different modalities
    
    Indices:
    - text.index: Text embeddings (contacts, messages)
    - image.index: Image embeddings (CLIP)
    - audio.index: Audio embeddings (Whisper transcripts)
    - video.index: Video embeddings (combined)
    """
    
    def __init__(self, index_dir: str = "data/indices"):
        """
        Initialize multi-modal index manager
        
        Args:
            index_dir: Directory to store FAISS indices
        """
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS is required. Install with: pip install faiss-cpu")
        
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        # Define index configurations
        self.index_configs = {
            "text": {"dimension": 512, "metric": faiss.METRIC_L2},  # CLIP text embeddings
            "image": {"dimension": 512, "metric": faiss.METRIC_L2},  # CLIP ViT-B/32
            "face": {"dimension": 512, "metric": faiss.METRIC_L2},  # DeepFace embeddings (512-d VGG-Face)
            "audio": {"dimension": 384, "metric": faiss.METRIC_L2},  # text embeddings of transcripts
            "video": {"dimension": 512, "metric": faiss.METRIC_L2},  # combined embeddings
        }
        
        # Initialize indices and mappings
        self.indices = {}
        self.mappings = {}  # vector_id -> document metadata
        self.next_ids = {}
        
        self._load_or_create_indices()
        
        logger.info("✅ Multi-modal FAISS indices initialized")
    
    def _load_or_create_indices(self):
        """Load existing indices or create new ones"""
        for modality, config in self.index_configs.items():
            index_path = self.index_dir / f"{modality}.index"
            mapping_path = self.index_dir / f"{modality}_mapping.pkl"
            
            if index_path.exists() and mapping_path.exists():
                # Load existing index
                logger.info(f"Loading {modality} index from {index_path}")
                self.indices[modality] = faiss.read_index(str(index_path))
                
                with open(mapping_path, 'rb') as f:
                    data = pickle.load(f)
                    self.mappings[modality] = data['mapping']
                    self.next_ids[modality] = data['next_id']
                
                logger.info(f"✅ Loaded {modality} index: {self.indices[modality].ntotal} vectors")
            else:
                # Create new index
                logger.info(f"Creating new {modality} index (dimension={config['dimension']})")
                # Use HNSW index for fast similarity search
                self.indices[modality] = faiss.IndexHNSWFlat(config['dimension'], 32)
                self.indices[modality].hnsw.efConstruction = 200
                self.mappings[modality] = {}
                self.next_ids[modality] = 0
                
                logger.info(f"✅ Created {modality} index")
    
    def add_embeddings(
        self,
        modality: str,
        ids: List[str],
        embeddings: np.ndarray,
        metadatas: List[Dict[str, Any]]
    ) -> bool:
        """
        Add embeddings to a modality-specific index
        
        Args:
            modality: Type of data ('text', 'image', 'audio', 'video')
            ids: Unique IDs for each embedding
            embeddings: Numpy array of embeddings (n, dim)
            metadatas: Metadata for each embedding
            
        Returns:
            True if successful
        """
        if modality not in self.indices:
            logger.error(f"Unknown modality: {modality}. Available: {list(self.indices.keys())}")
            return False
        
        if len(ids) != len(embeddings) or len(ids) != len(metadatas):
            logger.error(f"Length mismatch: {len(ids)} ids, {len(embeddings)} embeddings, {len(metadatas)} metadatas")
            return False
        
        index = self.indices[modality]
        mapping = self.mappings[modality]
        
        try:
            # Ensure embeddings are float32 numpy array
            if not isinstance(embeddings, np.ndarray):
                embeddings = np.array(embeddings, dtype=np.float32)
            elif embeddings.dtype != np.float32:
                embeddings = embeddings.astype(np.float32)
            
            # Normalize embeddings for better search (optional but recommended)
            faiss.normalize_L2(embeddings)
            
            # Add to FAISS index
            start_id = self.next_ids[modality]
            index.add(embeddings)
            
            # Update mapping
            for i, (doc_id, metadata) in enumerate(zip(ids, metadatas)):
                vector_id = start_id + i
                mapping[vector_id] = {
                    "id": doc_id,
                    "metadata": metadata,
                    "vector_id": vector_id
                }
            
            self.next_ids[modality] += len(ids)
            
            logger.info(f"✅ Added {len(ids)} {modality} embeddings to index")
            return True
            
        except Exception as e:
            import traceback
            logger.error(f"Failed to add {modality} embeddings: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def search(
        self,
        modality: str,
        query_embedding: np.ndarray,
        n_results: int = 10,
        case_id_filter: Optional[str] = None
    ) -> List[MultiModalSearchResult]:
        """
        Search a modality-specific index
        
        Args:
            modality: Type of data to search
            query_embedding: Query embedding vector
            n_results: Number of results to return
            case_id_filter: Optional filter by case_id
            
        Returns:
            List of search results
        """
        if modality not in self.indices:
            logger.error(f"Unknown modality: {modality}")
            return []
        
        index = self.indices[modality]
        mapping = self.mappings[modality]
        
        if index.ntotal == 0:
            logger.warning(f"{modality} index is empty")
            return []
        
        try:
            # Ensure query is float32 and 2D
            if not isinstance(query_embedding, np.ndarray):
                query_embedding = np.array(query_embedding, dtype=np.float32)
            elif query_embedding.dtype != np.float32:
                query_embedding = query_embedding.astype(np.float32)
            
            if query_embedding.ndim == 1:
                query_embedding = query_embedding.reshape(1, -1)
            
            # Normalize query
            faiss.normalize_L2(query_embedding)
            
            # Search with more results if filtering by case_id
            search_k = n_results * 10 if case_id_filter else n_results
            distances, indices = index.search(query_embedding, search_k)
            
            # Parse results
            results = []
            for i, (distance, vector_id) in enumerate(zip(distances[0], indices[0])):
                if vector_id == -1:  # FAISS returns -1 for missing results
                    continue
                
                if vector_id not in mapping:
                    logger.warning(f"Vector ID {vector_id} not in mapping")
                    continue
                
                doc_data = mapping[vector_id]
                metadata = doc_data.get("metadata", {})
                
                # Apply case_id filter if specified
                if case_id_filter and metadata.get("case_id") != case_id_filter:
                    continue
                
                # Calculate confidence (inverse of distance)
                # For L2 distance, smaller is better
                confidence = max(0.0, 1.0 - (distance / 2.0))
                
                result = MultiModalSearchResult(
                    id=doc_data["id"],
                    case_id=metadata.get("case_id", "unknown"),
                    modality=modality,
                    content=metadata.get("content", ""),
                    metadata=metadata,
                    distance=float(distance),
                    confidence=float(confidence),
                    vector_id=int(vector_id)
                )
                results.append(result)
                
                if len(results) >= n_results:
                    break
            
            logger.info(f"Found {len(results)} {modality} results")
            return results
            
        except Exception as e:
            logger.error(f"Search failed for {modality}: {e}")
            return []
    
    def search_multi_modal(
        self,
        modalities: List[str],
        query_embeddings: Dict[str, np.ndarray],
        n_results: int = 10,
        case_id_filter: Optional[str] = None
    ) -> Dict[str, List[MultiModalSearchResult]]:
        """
        Search across multiple modalities in parallel
        
        Args:
            modalities: List of modalities to search
            query_embeddings: Dict mapping modality to query embedding
            n_results: Number of results per modality
            case_id_filter: Optional filter by case_id
            
        Returns:
            Dict mapping modality to list of results
        """
        results = {}
        
        for modality in modalities:
            if modality not in query_embeddings:
                logger.warning(f"No query embedding for {modality}, skipping")
                continue
            
            results[modality] = self.search(
                modality=modality,
                query_embedding=query_embeddings[modality],
                n_results=n_results,
                case_id_filter=case_id_filter
            )
        
        return results
    
    def save_indices(self):
        """Save all indices and mappings to disk"""
        for modality in self.indices.keys():
            index_path = self.index_dir / f"{modality}.index"
            mapping_path = self.index_dir / f"{modality}_mapping.pkl"
            
            try:
                # Save FAISS index
                faiss.write_index(self.indices[modality], str(index_path))
                
                # Save mapping
                with open(mapping_path, 'wb') as f:
                    pickle.dump({
                        'mapping': self.mappings[modality],
                        'next_id': self.next_ids[modality]
                    }, f)
                
                logger.info(f"✅ Saved {modality} index ({self.indices[modality].ntotal} vectors)")
                
            except Exception as e:
                logger.error(f"Failed to save {modality} index: {e}")
    
    def get_stats(self) -> Dict[str, int]:
        """Get count of vectors in each index"""
        stats = {}
        for modality, index in self.indices.items():
            stats[modality] = index.ntotal
        return stats
    
    def clear_index(self, modality: str) -> bool:
        """Clear a specific index"""
        if modality not in self.indices:
            return False
        
        try:
            config = self.index_configs[modality]
            self.indices[modality] = faiss.IndexHNSWFlat(config['dimension'], 32)
            self.indices[modality].hnsw.efConstruction = 200
            self.mappings[modality] = {}
            self.next_ids[modality] = 0
            
            logger.info(f"✅ Cleared {modality} index")
            return True
        except Exception as e:
            logger.error(f"Failed to clear {modality} index: {e}")
            return False
    
    def export_index(self, modality: str, output_file: Path) -> bool:
        """Export an index to JSON file"""
        if modality not in self.indices:
            return False
        
        try:
            mapping = self.mappings[modality]
            
            export_data = {
                "modality": modality,
                "count": len(mapping),
                "exported_at": datetime.now().isoformat(),
                "items": [
                    {
                        "vector_id": vector_id,
                        "id": data["id"],
                        "metadata": data["metadata"]
                    }
                    for vector_id, data in mapping.items()
                ]
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"✅ Exported {len(mapping)} {modality} items to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export {modality}: {e}")
            return False


# Convenience functions

def create_multimodal_index(index_dir: str = "data/indices") -> MultiModalIndex:
    """Create and return a multi-modal index instance"""
    return MultiModalIndex(index_dir=index_dir)


def get_multimodal_index() -> MultiModalIndex:
    """Get singleton multi-modal index instance"""
    if not hasattr(get_multimodal_index, "_instance"):
        get_multimodal_index._instance = MultiModalIndex()
    return get_multimodal_index._instance
