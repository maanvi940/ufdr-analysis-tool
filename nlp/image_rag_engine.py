"""
Image RAG Search Engine
Semantic search over forensic images using CLIP embeddings
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Union
from dataclasses import dataclass, asdict

# Import our custom modules
from media.clip_embedder import get_clip_embedder
from vector.multimodal_index import get_multimodal_index

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ImageSearchResult:
    """Result from image search"""
    image_id: str
    case_id: str
    file_path: str
    confidence: float
    distance: float
    metadata: Dict
    
    def to_dict(self) -> Dict:
        return asdict(self)


class ImageRAGEngine:
    """
    Image RAG Search Engine
    
    Features:
    - Text-to-image search ("Find images with weapons")
    - Image-to-image search (find similar images)
    - Filter by case_id, timestamp, location
    - Semantic understanding via CLIP
    """
    
    def __init__(self):
        """Initialize image RAG engine"""
        self.clip_embedder = get_clip_embedder()
        self.multimodal_index = get_multimodal_index()
        
        logger.info("✅ Image RAG Engine initialized")
    
    def search_images_by_text(
        self,
        query: str,
        case_id: Optional[str] = None,
        n_results: int = 10
    ) -> List[ImageSearchResult]:
        """
        Search images using text query
        
        Args:
            query: Natural language query (e.g., "images showing weapons")
            case_id: Optional filter by case ID
            n_results: Number of results to return
            
        Returns:
            List of matching images ranked by relevance
            
        Example:
            >>> engine = ImageRAGEngine()
            >>> results = engine.search_images_by_text("weapons", case_id="CASE_001")
            >>> for r in results:
            >>>     print(f"{r.file_path}: {r.confidence:.2f}")
        """
        logger.info(f"Searching images for: '{query}' (case_id={case_id})")
        
        try:
            # Generate text embedding
            query_embedding = self.clip_embedder.encode_text(query)
            
            if query_embedding is None:
                logger.error("Failed to generate query embedding")
                return []
            
            # Search in FAISS
            faiss_results = self.multimodal_index.search(
                modality="image",
                query_embedding=query_embedding,
                n_results=n_results,
                case_id_filter=case_id
            )
            
            # Convert to ImageSearchResult
            search_results = [
                ImageSearchResult(
                    image_id=r.id,
                    case_id=r.case_id,
                    file_path=r.metadata.get("file_path", ""),
                    confidence=r.confidence,
                    distance=r.distance,
                    metadata=r.metadata
                )
                for r in faiss_results
            ]
            
            logger.info(f"Found {len(search_results)} images")
            return search_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def search_images_by_image(
        self,
        image_path: Union[str, Path],
        case_id: Optional[str] = None,
        n_results: int = 10
    ) -> List[ImageSearchResult]:
        """
        Find similar images to a given image
        
        Args:
            image_path: Path to query image
            case_id: Optional filter by case ID
            n_results: Number of results to return
            
        Returns:
            List of similar images
            
        Example:
            >>> results = engine.search_images_by_image("suspect_photo.jpg")
            >>> # Returns similar-looking images
        """
        logger.info(f"Finding similar images to: {image_path}")
        
        try:
            # Generate image embedding
            query_embedding = self.clip_embedder.encode_image(image_path)
            
            if query_embedding is None:
                logger.error("Failed to generate image embedding")
                return []
            
            # Search in FAISS
            faiss_results = self.multimodal_index.search(
                modality="image",
                query_embedding=query_embedding,
                n_results=n_results + 1,  # +1 to potentially exclude self
                case_id_filter=case_id
            )
            
            # Filter out the query image itself (if indexed)
            query_path_str = str(Path(image_path).resolve())
            filtered_results = [
                r for r in faiss_results
                if r.metadata.get("file_path") != query_path_str
            ][:n_results]
            
            # Convert to ImageSearchResult
            search_results = [
                ImageSearchResult(
                    image_id=r.id,
                    case_id=r.case_id,
                    file_path=r.metadata.get("file_path", ""),
                    confidence=r.confidence,
                    distance=r.distance,
                    metadata=r.metadata
                )
                for r in filtered_results
            ]
            
            logger.info(f"Found {len(search_results)} similar images")
            return search_results
            
        except Exception as e:
            logger.error(f"Similar image search failed: {e}")
            return []
    
    def search_images_by_objects(
        self,
        object_names: List[str],
        case_id: Optional[str] = None,
        n_results: int = 10
    ) -> List[ImageSearchResult]:
        """
        Search images containing specific objects
        
        Args:
            object_names: List of object names (e.g., ["weapon", "person"])
            case_id: Optional filter by case ID
            n_results: Number of results to return
            
        Returns:
            List of images containing the objects
            
        Example:
            >>> results = engine.search_images_by_objects(["gun", "person"])
        """
        # Construct query from object names
        query = f"photo containing {', '.join(object_names)}"
        logger.info(f"Searching for objects: {object_names}")
        
        return self.search_images_by_text(query, case_id, n_results)
    
    def search_images_advanced(
        self,
        query: Optional[str] = None,
        case_id: Optional[str] = None,
        min_confidence: float = 0.0,
        timestamp_range: Optional[tuple] = None,
        has_location: Optional[bool] = None,
        n_results: int = 10
    ) -> List[ImageSearchResult]:
        """
        Advanced image search with multiple filters
        
        Args:
            query: Optional text query
            case_id: Filter by case ID
            min_confidence: Minimum confidence score
            timestamp_range: (start_timestamp, end_timestamp) tuple
            has_location: Filter images with/without GPS data
            n_results: Number of results to return
            
        Returns:
            Filtered and ranked results
        """
        # Start with basic search
        if query:
            results = self.search_images_by_text(query, case_id, n_results * 3)
        else:
            # Get all images for case if no query
            results = self._get_all_images(case_id, n_results * 3)
        
        # Apply filters
        filtered_results = results
        
        # Confidence filter
        if min_confidence > 0:
            filtered_results = [r for r in filtered_results if r.confidence >= min_confidence]
        
        # Timestamp filter
        if timestamp_range:
            start, end = timestamp_range
            filtered_results = [
                r for r in filtered_results
                if start <= r.metadata.get('timestamp', 0) <= end
            ]
        
        # Location filter
        if has_location is not None:
            if has_location:
                filtered_results = [
                    r for r in filtered_results
                    if 'location' in r.metadata and r.metadata['location']
                ]
            else:
                filtered_results = [
                    r for r in filtered_results
                    if 'location' not in r.metadata or not r.metadata['location']
                ]
        
        # Return top results
        return filtered_results[:n_results]
    
    def _get_all_images(self, case_id: Optional[str], limit: int) -> List[ImageSearchResult]:
        """Get all images for a case (no query)"""
        # Use a generic query
        return self.search_images_by_text("photo", case_id, limit)
    
    def get_image_stats(self, case_id: Optional[str] = None) -> Dict:
        """
        Get statistics about indexed images
        
        Args:
            case_id: Optional filter by case
            
        Returns:
            Dictionary with statistics
        """
        stats = self.multimodal_index.get_stats()
        
        result = {
            "total_images": stats.get("image", 0),
            "case_id": case_id
        }
        
        # If case_id specified, count images for that case
        if case_id:
            # Do a large search to count
            all_results = self.search_images_by_text("photo", case_id, n_results=10000)
            result["case_images"] = len(all_results)
        
        return result
    
    def batch_search(
        self,
        queries: List[str],
        case_id: Optional[str] = None,
        n_results_per_query: int = 10
    ) -> Dict[str, List[ImageSearchResult]]:
        """
        Execute multiple searches in batch
        
        Args:
            queries: List of text queries
            case_id: Optional case filter
            n_results_per_query: Results per query
            
        Returns:
            Dictionary mapping query to results
        """
        results = {}
        
        for query in queries:
            results[query] = self.search_images_by_text(
                query, case_id, n_results_per_query
            )
        
        return results


# Singleton instance
_image_rag_instance = None


def get_image_rag_engine() -> ImageRAGEngine:
    """Get singleton image RAG engine"""
    global _image_rag_instance
    if _image_rag_instance is None:
        _image_rag_instance = ImageRAGEngine()
    return _image_rag_instance
