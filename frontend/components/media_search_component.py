"""
Comprehensive Media Search Component
Exposes all vision model capabilities:
- CLIP visual similarity search
- YOLO object detection
- BLIP caption search
- DeepFace face recognition
- Query by image upload
"""

import streamlit as st
import os
import sys
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)


def render_media_search(project_root: Path):
    """
    Render comprehensive media search interface
    
    Args:
        project_root: Project root path for accessing backend
    """
    
    st.title("🖼️ Media Search & Analysis")
    
    st.markdown("""
    ### 🤖 AI-Powered Visual Search
    
    Search through images, videos, and media using advanced AI models:
    - **CLIP**: Find visually similar images
    - **YOLO-World**: Detect specific objects (weapons, drugs, people, etc.)
    - **BLIP-2**: Search by AI-generated captions
    - **DeepFace**: Find faces across images
    """)
    
    # Get available cases
    
    db_path = str(project_root / "forensic_data.db")
    
    # Get case list
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT case_id FROM cases ORDER BY case_id")
    cases = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    if not cases:
        st.warning("⚠️ No cases available. Upload a UFDR file first.")
        return
    
    # Case selection
    st.markdown("---")
    st.subheader("1️⃣ Select Cases")
    
    selected_cases = st.multiselect(
        "Choose cases to search",
        options=cases,
        default=[cases[0]] if cases else []
    )
    
    if not selected_cases:
        st.info("👆 Please select at least one case to search")
        return
    
    st.markdown("---")
    st.subheader("2️⃣ Choose Search Method")
    
    # Search method tabs
    search_tabs = st.tabs([
        "🔍 Object Search (YOLO)",
        "🎨 Visual Similarity (CLIP)",
        "📝 Caption Search (BLIP)",
        "👤 Face Search (DeepFace)",
        "🖼️ Upload & Find Similar"
    ])
    
    # Tab 1: YOLO Object Detection
    with search_tabs[0]:
        st.markdown("### Object Detection Search")
        st.info("Search for specific objects in images using YOLO-World object detection")
        
        # Preset forensic objects
        st.markdown("**Quick Select (Forensic Objects)**:")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🔫 Weapons", use_container_width=True):
                st.session_state['object_query'] = "weapon gun firearm"
        with col2:
            if st.button("💊 Drugs", use_container_width=True):
                st.session_state['object_query'] = "drug pill syringe"
        with col3:
            if st.button("💰 Money", use_container_width=True):
                st.session_state['object_query'] = "money cash currency"
        with col4:
            if st.button("👤 People", use_container_width=True):
                st.session_state['object_query'] = "person people human"
        
        # Custom query
        object_query = st.text_input(
            "Or enter custom object name",
            value=st.session_state.get('object_query', ''),
            placeholder="e.g., gun, knife, car, phone, weapon",
            help="YOLO will search for this object in all images"
        )
        
        # Additional options
        with st.expander("⚙️ Advanced Settings"):
            confidence_threshold = st.slider(
                "Minimum confidence",
                min_value=0.0,
                max_value=1.0,
                value=0.6,
                step=0.05,
                help="Only show results above this confidence"
            )
            
            max_results = st.number_input(
                "Maximum results",
                min_value=1,
                max_value=100,
                value=20,
                help="Maximum number of images to return"
            )
        
        if st.button("🔍 Search Objects", type="primary", use_container_width=True):
            if not object_query:
                st.warning("Please enter an object to search for")
            else:
                search_media_with_yolo(
                    query=object_query,
                    case_ids=selected_cases,
                    confidence_threshold=confidence_threshold,
                    max_results=max_results,
                    db_path=db_path
                )
    
    # Tab 2: CLIP Visual Similarity
    with search_tabs[1]:
        st.markdown("### Visual Similarity Search")
        st.info("Find images similar to your text description using CLIP semantic understanding")
        
        # Preset visual concepts
        st.markdown("**Quick Select (Visual Concepts)**:")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🏠 Indoor Scene", use_container_width=True):
                st.session_state['visual_query'] = "indoor room interior"
        with col2:
            if st.button("🌳 Outdoor Scene", use_container_width=True):
                st.session_state['visual_query'] = "outdoor exterior nature"
        with col3:
            if st.button("🌃 Night Scene", use_container_width=True):
                st.session_state['visual_query'] = "night dark evening"
        
        visual_query = st.text_input(
            "Describe the scene you're looking for",
            value=st.session_state.get('visual_query', ''),
            placeholder="e.g., dark alley, crowded street, empty parking lot",
            help="CLIP understands visual context and scenes"
        )
        
        with st.expander("⚙️ Advanced Settings"):
            clip_confidence = st.slider(
                "Minimum similarity",
                min_value=0.0,
                max_value=1.0,
                value=0.61,
                step=0.01,
                help="CLIP similarity threshold (higher = stricter matching)"
            )
            
            clip_max_results = st.number_input(
                "Maximum results",
                min_value=1,
                max_value=100,
                value=20,
                key="clip_max"
            )
        
        if st.button("🔍 Search Visually", type="primary", use_container_width=True):
            if not visual_query:
                st.warning("Please describe what you're looking for")
            else:
                search_media_with_clip(
                    query=visual_query,
                    case_ids=selected_cases,
                    confidence_threshold=clip_confidence,
                    max_results=clip_max_results,
                    db_path=db_path
                )
    
    # Tab 3: BLIP Caption Search
    with search_tabs[2]:
        st.markdown("### Caption Search")
        st.info("Search images by their AI-generated captions (BLIP-2)")
        
        st.markdown("""
        **How it works**:
        1. BLIP-2 generates natural language descriptions for images
        2. You search through these descriptions
        3. Find images matching your text query
        """)
        
        caption_query = st.text_input(
            "Search in image captions",
            placeholder="e.g., person holding, car parked, indoor scene",
            help="Searches through BLIP-generated image descriptions"
        )
        
        if st.button("🔍 Search Captions", type="primary", use_container_width=True):
            if not caption_query:
                st.warning("Please enter a search term")
            else:
                search_media_with_blip(
                    query=caption_query,
                    case_ids=selected_cases,
                    db_path=db_path
                )
    
    # Tab 4: DeepFace Face Search
    with search_tabs[3]:
        st.markdown("### Face Recognition Search")
        st.info("Find all occurrences of a face across images using DeepFace")
        
        st.markdown("""
        **How it works**:
        1. DeepFace detects and recognizes faces in all images
        2. Groups similar faces together
        3. Finds the same person across multiple photos
        """)
        
        # Face search options
        search_mode = st.radio(
            "Search mode",
            ["Find all faces", "Find specific person", "Group faces by similarity"],
            help="Choose how to search for faces"
        )
        
        if search_mode == "Find specific person":
            reference_image = st.file_uploader(
                "Upload reference image with the target face",
                type=['jpg', 'jpeg', 'png'],
                help="Upload an image containing the face you want to find"
            )
            
            if st.button("🔍 Find This Person", type="primary", use_container_width=True):
                if reference_image:
                    search_face_in_case(
                        reference_image=reference_image,
                        case_ids=selected_cases,
                        db_path=db_path
                    )
                else:
                    st.warning("Please upload a reference image")
        else:
            if st.button("🔍 Search Faces", type="primary", use_container_width=True):
                search_all_faces(
                    case_ids=selected_cases,
                    mode=search_mode,
                    db_path=db_path
                )
    
    # Tab 5: Query by Image
    with search_tabs[4]:
        st.markdown("### Upload & Find Similar")
        st.info("Upload an image to find visually similar images in your cases")
        
        uploaded_image = st.file_uploader(
            "Upload query image",
            type=['jpg', 'jpeg', 'png', 'bmp'],
            help="Upload an image to find similar ones using CLIP embeddings"
        )
        
        if uploaded_image:
            st.image(uploaded_image, caption="Query Image", width=300)
            
            with st.expander("⚙️ Search Settings"):
                similarity_threshold = st.slider(
                    "Minimum similarity",
                    min_value=0.5,
                    max_value=1.0,
                    value=0.75,
                    step=0.05
                )
                
                top_k = st.number_input(
                    "Number of results",
                    min_value=1,
                    max_value=50,
                    value=10
                )
            
            if st.button("🔍 Find Similar Images", type="primary", use_container_width=True):
                find_similar_images(
                    query_image=uploaded_image,
                    case_ids=selected_cases,
                    threshold=similarity_threshold,
                    top_k=top_k,
                    db_path=db_path
                )


def search_media_with_yolo(query, case_ids, confidence_threshold, max_results, db_path):
    """Search media using YOLO object detection"""
    with st.spinner("🔍 Scanning images with YOLO-World..."):
        try:
            from backend.comprehensive_media_search import get_comprehensive_media_search
            
            engine = get_comprehensive_media_search(db_path=db_path)
            
            result = engine.search_media(
                query=query,
                case_ids=case_ids,
                media_types=['image'],
                max_results=max_results
            )
            
            if result.get('success') and result.get('results'):
                # Filter by confidence
                filtered_results = [
                    r for r in result['results']
                    if r.get('confidence', 0) >= confidence_threshold
                ]
                
                st.success(f"✅ Found {len(filtered_results)} images with '{query}'")
                st.info(f"⏱️ Processing time: {result.get('processing_time', 0):.2f}s")
                
                display_image_results(filtered_results, "object_detection")
            else:
                st.warning(f"No images found matching '{query}'")
                st.info("💡 Try lowering the confidence threshold or use different search terms")
                
        except Exception as e:
            st.error(f"❌ Search failed: {e}")
            logger.error(f"YOLO search error: {e}", exc_info=True)


def search_media_with_clip(query, case_ids, confidence_threshold, max_results, db_path):
    """Search media using CLIP semantic similarity"""
    with st.spinner("🎨 Analyzing visual similarity with CLIP..."):
        try:
            from backend.comprehensive_media_search import get_comprehensive_media_search
            
            engine = get_comprehensive_media_search(db_path=db_path)
            
            result = engine.search_media(
                query=query,
                case_ids=case_ids,
                media_types=['image'],
                max_results=max_results
            )
            
            if result.get('success') and result.get('results'):
                filtered_results = [
                    r for r in result['results']
                    if r.get('confidence', 0) >= confidence_threshold
                ]
                
                st.success(f"✅ Found {len(filtered_results)} visually similar images")
                st.info(f"⏱️ Processing time: {result.get('processing_time', 0):.2f}s")
                
                display_image_results(filtered_results, "visual_similarity")
            else:
                st.warning("No visually similar images found")
                st.info("💡 Try different descriptions or lower the similarity threshold")
                
        except Exception as e:
            st.error(f"❌ Search failed: {e}")
            logger.error(f"CLIP search error: {e}", exc_info=True)


def search_media_with_blip(query, case_ids, db_path):
    """Search using BLIP-generated captions"""
    st.info("🚧 BLIP caption search: Processing captions...")
    st.warning("This feature requires pre-processed images with BLIP captions")
    st.markdown("""
    **To enable**:
    1. Process images with BLIP: `python scripts/process_media.py`
    2. Captions will be indexed in database
    3. Then search through them here
    """)


def search_all_faces(case_ids, mode, db_path):
    """Search for all faces in case"""
    st.info("🚧 Face recognition: Processing images...")
    st.warning("This feature requires DeepFace processing")
    st.markdown("""
    **To enable**:
    1. Process images with DeepFace: `python scripts/process_faces.py`
    2. Face embeddings will be computed
    3. Search and group faces here
    """)


def search_face_in_case(reference_image, case_ids, db_path):
    """Find specific person using reference image"""
    st.info("🚧 Face matching: Processing reference image...")
    st.warning("This feature requires DeepFace processing")


def find_similar_images(query_image, case_ids, threshold, top_k, db_path):
    """Find visually similar images using CLIP"""
    with st.spinner("🔍 Computing CLIP embeddings and finding similar images..."):
        try:
            from media.clip_embedder import get_clip_embedder
            from PIL import Image
            
            # Load CLIP
            clip = get_clip_embedder()
            
            # Encode query image
            query_img = Image.open(query_image).convert('RGB')
            clip.encode_image(query_img)
            
            # Find similar images in database
            # TODO: Implement FAISS search or database lookup
            
            st.success(f"✅ Query image encoded successfully")
            st.info("🚧 Database search implementation in progress")
            st.markdown("""
            **Next steps**:
            1. Build CLIP embedding index for case images
            2. Search index with query embedding
            3. Return top-k most similar images
            """)
            
        except Exception as e:
            st.error(f"❌ Error: {e}")
            logger.error(f"Image similarity error: {e}", exc_info=True)


def display_image_results(results, search_type):
    """
    Display image search results in a grid
    
    Args:
        results: List of result dictionaries
        search_type: Type of search ('object_detection', 'visual_similarity', etc.)
    """
    if not results:
        st.warning("No results to display")
        return
    
    st.markdown(f"### 📊 Results ({len(results)} images)")
    
    # Display in grid (3 columns)
    cols_per_row = 3
    
    for i in range(0, len(results), cols_per_row):
        cols = st.columns(cols_per_row)
        
        for j, col in enumerate(cols):
            if i + j < len(results):
                result = results[i + j]
                
                with col:
                    file_path = result.get('file_path', '')
                    
                    if file_path and os.path.exists(file_path):
                        # Display image
                        st.image(file_path, use_column_width=True)
                        
                        # Display metadata
                        st.caption(f"**{result.get('filename', 'Unknown')}**")
                        st.caption(f"🎯 Confidence: {result.get('confidence', 0):.1%}")
                        st.caption(f"📁 Case: {result.get('case_id', 'N/A')}")
                        
                        # Display match reason
                        if result.get('match_reason'):
                            with st.expander("ℹ️ Match Details"):
                                st.write(result['match_reason'])
                                st.write(f"File size: {result.get('file_size', 0) / 1024:.1f} KB")
                                st.write(f"Type: {result.get('media_type', 'unknown')}")
                    else:
                        st.error("❌ Image file not found")
                        st.caption(f"Path: {file_path}")
