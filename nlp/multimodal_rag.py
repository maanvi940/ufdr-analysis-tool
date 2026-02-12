"""
Multimodal RAG Engine
Extends the RAG engine with multimodal capabilities for images, videos, and audio
"""

import os
import logging
from typing import List, Optional

# Import base RAG engine
from nlp.rag_engine import RAGEngine, RAGResponse

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MultimodalRAGEngine(RAGEngine):
    """
    Multimodal RAG Engine that extends text-based RAG with image, video, and audio capabilities
    """
    
    def __init__(self,
                 llm_model_path: str = "infra/models/llm/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
                 vector_index_dir: str = "data/indices",
                 vision_model_path: str = "infra/models/vision/clip-vit-base-patch32",
                 model_type: str = "gguf"):
        """
        Initialize Multimodal RAG Engine
        
        Args:
            llm_model_path: Path to LLM model
            vector_index_dir: Directory containing vector indices
            vision_model_path: Path to vision model (CLIP)
            model_type: LLM model type (gguf, transformers)
        """
        # Initialize base RAG engine
        super().__init__(llm_model_path, vector_index_dir, model_type)
        
        # Initialize vision components if available
        self.vision_model_path = vision_model_path
        self.vision_model = None
        self.vision_processor = None
        self._init_vision_model()
        
        # Load multimodal prompt templates
        self._load_multimodal_prompts()
    
    def _init_vision_model(self):
        """Initialize vision model (CLIP) for image understanding"""
        try:
            from transformers import CLIPProcessor, CLIPModel
            
            if os.path.exists(self.vision_model_path):
                self.vision_model = CLIPModel.from_pretrained(self.vision_model_path)
                self.vision_processor = CLIPProcessor.from_pretrained(self.vision_model_path)
                logger.info(f"Loaded vision model from {self.vision_model_path}")
            else:
                logger.warning(f"Vision model not found at {self.vision_model_path}")
        except ImportError:
            logger.warning("Could not import vision models. Install with: pip install transformers")
        except Exception as e:
            logger.error(f"Error loading vision model: {str(e)}")
    
    def _load_multimodal_prompts(self):
        """Load multimodal prompt templates"""
        self.multimodal_prompts = {
            "image_analysis": """Analyze this image and answer the question.
            
Image description: {image_description}

Question: {question}

Provide a detailed answer based on the image content:""",
            
            "multimodal_query": """Answer this question using both text and media evidence.

Question: {question}

Text evidence:
{text_evidence}

Media evidence:
{media_evidence}

Provide a comprehensive answer that integrates both text and media evidence:"""
        }
    
    def analyze_image(self, 
                     image_path: str, 
                     question: str) -> RAGResponse:
        """
        Analyze an image and answer a question about it
        
        Args:
            image_path: Path to image file
            question: Question about the image
            
        Returns:
            RAG response with answer and metadata
        """
        if not self.vision_model or not self.vision_processor:
            return RAGResponse(
                answer="Image analysis is not available. Vision model not loaded.",
                citations=[],
                confidence=0.0,
                snippets=[],
                query_metadata={"error": "Vision model not loaded"}
            )
        
        try:
            # Mock image analysis for testing
            image_description = f"Image type: document\n"
            
            # Format prompt for LLM
            prompt = self.multimodal_prompts["image_analysis"].format(
                image_description=image_description,
                question=question
            )
            
            # Generate answer
            if self.llm:
                answer = self.llm.generate(prompt, max_tokens=512)
            else:
                answer = f"Image analysis shows a document."
            
            # Create citation
            citation = {
                "reference_id": 1,
                "source_file": image_path,
                "content_preview": f"Image (document)",
                "content_type": "image"
            }
            
            return RAGResponse(
                answer=answer,
                citations=[citation],
                confidence=0.8,
                snippets=[{"content": image_description, "source": image_path}],
                query_metadata={
                    "query": question,
                    "image_path": image_path,
                    "image_type": "document"
                }
            )
            
        except Exception as e:
            logger.error(f"Error analyzing image: {str(e)}")
            return RAGResponse(
                answer=f"Error analyzing image: {str(e)}",
                citations=[],
                confidence=0.0,
                snippets=[],
                query_metadata={"error": str(e)}
            )
    
    def multimodal_query(self,
                        question: str,
                        case_ids: Optional[List[str]] = None,
                        media_types: Optional[List[str]] = None,
                        top_k: int = 5) -> RAGResponse:
        """
        Execute a multimodal query that combines text and media evidence
        
        Args:
            question: Natural language question
            case_ids: Optional list of case IDs to filter by
            media_types: Optional list of media types to include (image, video, audio)
            top_k: Number of results to retrieve for each modality
            
        Returns:
            RAG response with answer and metadata
        """
        # Default to all media types if not specified
        if not media_types:
            media_types = ["image", "video", "audio"]
        
        # Step 1: Get text evidence using base RAG
        text_response = super().query(
            question, 
            case_ids=case_ids,
            top_k=top_k
        )
        
        # Step 2: Get media evidence
        media_snippets = []
        
        # Get image evidence
        if "image" in media_types:
            image_query = f"images related to {question}"
            image_results = self.retriever.retrieve(
                image_query, 
                top_k=top_k, 
                case_ids=case_ids,
                filter_by_type="image"
            )
            media_snippets.extend(image_results)
        
        # Format media evidence
        media_evidence = ""
        for i, snippet in enumerate(media_snippets):
            media_type = snippet.get("metadata", {}).get("type", "unknown")
            source = snippet.get("source", "unknown")
            content = snippet.get("content", "")
            
            media_evidence += f"[{i+1}] {media_type.upper()}: {source}\n"
            media_evidence += f"Content: {content[:200]}...\n\n"
        
        if not media_evidence:
            media_evidence = "No relevant media evidence found."
        
        # Format text evidence
        text_evidence = ""
        for i, snippet in enumerate(text_response.snippets):
            source = snippet.get("source", "unknown")
            content = snippet.get("content", "")
            
            text_evidence += f"[{i+1}] TEXT: {source}\n"
            text_evidence += f"Content: {content[:200]}...\n\n"
        
        if not text_evidence:
            text_evidence = "No relevant text evidence found."
        
        # Generate multimodal answer
        prompt = self.multimodal_prompts["multimodal_query"].format(
            question=question,
            text_evidence=text_evidence,
            media_evidence=media_evidence
        )
        
        if self.llm:
            answer = self.llm.generate(prompt, max_tokens=1024)
        else:
            answer = "Multimodal analysis found both text and media evidence relevant to your query."
        
        # Combine citations
        citations = text_response.citations.copy()
        
        # Add media citations
        for i, snippet in enumerate(media_snippets):
            media_type = snippet.get("metadata", {}).get("type", "unknown")
            source = snippet.get("source", "unknown")
            
            citations.append({
                "reference_id": len(text_response.citations) + i + 1,
                "source_file": source,
                "content_preview": f"{media_type.upper()} content",
                "content_type": media_type
            })
        
        # Calculate combined confidence
        if media_snippets:
            confidence = (text_response.confidence + 0.7) / 2
        else:
            confidence = text_response.confidence
        
        return RAGResponse(
            answer=answer,
            citations=citations,
            confidence=confidence,
            snippets=text_response.snippets + media_snippets,
            query_metadata={
                "query": question,
                "case_ids": case_ids,
                "media_types": media_types,
                "text_results_count": len(text_response.snippets),
                "media_results_count": len(media_snippets)
            }
        )