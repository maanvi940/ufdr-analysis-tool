"""
UFDR File Browser Component
Shows all files extracted from UFDR with preview and SQL query capabilities
"""

import streamlit as st
import os
from pathlib import Path
import mimetypes
import sqlite3
import pandas as pd
from PIL import Image
import logging

logger = logging.getLogger(__name__)


def get_extraction_path_from_db(case_id: str) -> str:
    """Get extraction path for a case from database"""
    try:
        conn = sqlite3.connect("forensic_data.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT notes FROM cases WHERE case_id = ?", (case_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            notes = result[0]
            # Check if notes contain extraction path
            if notes.startswith("extraction_path:"):
                return notes.replace("extraction_path:", "").strip()
        
        return None
        
    except Exception as e:
        logger.warning(f"Could not get extraction path from database: {e}")
        return None


def render_file_browser(case_id: str, extraction_path: str = None, use_expanders: bool = True):
    """
    Render file browser for extracted UFDR files
    
    Args:
        case_id: Case ID to browse files for
        extraction_path: Path to extracted UFDR files (defaults to looking up from database)
        use_expanders: Whether to use expanders for file details (set to False if already in an expander)
    """
    
    st.subheader(f"📂 Files from Case: {case_id}")
    
    # Determine extraction path
    if not extraction_path:
        # Try to get extraction path from database
        extraction_path = get_extraction_path_from_db(case_id)
        
        if not extraction_path:
            # Fall back to common locations
            possible_paths = [
                Path("uploads/ufdr_extractions") / case_id,
                Path("uploads/ufdr") / case_id,
                Path(f"data/parsed/{case_id}")
            ]
            
            for path in possible_paths:
                if path.exists():
                    extraction_path = path
                    break
    else:
        extraction_path = Path(extraction_path)
    
    if not extraction_path or not Path(extraction_path).exists():
        st.warning(f"⚠️ No extracted files found for case {case_id}")
        st.info("""
        **Possible locations checked:**
        - uploads/ufdr_extractions/{case_id}/
        - uploads/ufdr/{case_id}/
        - data/parsed/{case_id}/
        
        Files may have been cleaned up or the case may need to be reprocessed.
        """)
        return
    
    extraction_path = Path(extraction_path)
    
    # Get all files recursively
    all_files = []
    for root, dirs, files in os.walk(extraction_path):
        for filename in files:
            file_path = Path(root) / filename
            relative_path = file_path.relative_to(extraction_path)
            
            # Get file info
            file_size = file_path.stat().st_size
            mime_type, _ = mimetypes.guess_type(str(file_path))
            
            all_files.append({
                'name': filename,
                'path': str(file_path),
                'relative_path': str(relative_path),
                'size': file_size,
                'mime_type': mime_type or 'unknown',
                'category': categorize_file(file_path, mime_type)
            })
    
    if not all_files:
        st.info("No files found in extraction folder")
        return
    
    # File statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Files", len(all_files))
    with col2:
        total_size = sum(f['size'] for f in all_files)
        st.metric("Total Size", format_file_size(total_size))
    with col3:
        image_count = len([f for f in all_files if f['category'] == 'Image'])
        st.metric("Images", image_count)
    with col4:
        db_count = len([f for f in all_files if f['category'] == 'Database'])
        st.metric("Database Files", db_count)
    
    # Filter by category
    categories = list(set(f['category'] for f in all_files))
    selected_category = st.selectbox(
        "Filter by Type:",
        ["All"] + sorted(categories)
    )
    
    if selected_category != "All":
        filtered_files = [f for f in all_files if f['category'] == selected_category]
    else:
        filtered_files = all_files
    
    st.info(f"Showing {len(filtered_files)} files")
    
    # Display files with preview
    if use_expanders:
        # Use expanders when not nested
        for file_info in filtered_files:
            with st.expander(f"📄 {file_info['name']} ({file_info['category']}) - {format_file_size(file_info['size'])}"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.text(f"Path: {file_info['relative_path']}")
                    st.text(f"Type: {file_info['mime_type']}")
                    st.text(f"Size: {format_file_size(file_info['size'])}")
                
                with col2:
                    # Action buttons based on file type
                    render_file_actions(file_info, case_id)
                
                # Preview area
                render_file_preview(file_info, use_expanders=True)
    else:
        # Use containers and dividers when already nested in an expander
        for idx, file_info in enumerate(filtered_files):
            if idx > 0:
                st.divider()
            
            # File header
            st.markdown(f"### 📝 {file_info['name']}")
            st.caption(f"{file_info['category']} • {format_file_size(file_info['size'])}")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.text(f"Path: {file_info['relative_path']}")
                st.text(f"Type: {file_info['mime_type']}")
                st.text(f"Size: {format_file_size(file_info['size'])}")
            
            with col2:
                # Action buttons based on file type
                render_file_actions(file_info, case_id)
            
            # Preview area
            render_file_preview(file_info, use_expanders=False)


def categorize_file(file_path: Path, mime_type: str = None) -> str:
    """Categorize file based on extension and mime type"""
    
    ext = file_path.suffix.lower()
    
    # Database files
    if ext in ['.db', '.sqlite', '.sqlite3', '.sql']:
        return 'Database'
    
    # Images
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic']:
        return 'Image'
    
    # Videos
    if ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
        return 'Video'
    
    # Audio
    if ext in ['.mp3', '.wav', '.m4a', '.flac', '.ogg']:
        return 'Audio'
    
    # Documents
    if ext in ['.pdf', '.doc', '.docx', '.txt', '.rtf']:
        return 'Document'
    
    # Archives
    if ext in ['.zip', '.rar', '.7z', '.tar', '.gz']:
        return 'Archive'
    
    # JSON/XML/Data
    if ext in ['.json', '.xml', '.csv', '.tsv']:
        return 'Data'
    
    # Plist (common in iOS)
    if ext in ['.plist', '.bplist']:
        return 'Config'
    
    return 'Other'


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def render_file_actions(file_info: dict, case_id: str):
    """Render action buttons for file"""
    
    category = file_info['category']
    
    if category == 'Database':
        if st.button("🔍 Query Database", key=f"query_{file_info['path']}"):
            st.session_state['active_db_file'] = file_info['path']
            st.session_state['active_db_case'] = case_id
    
    elif category == 'Image':
        if st.button("🖼️ View Image", key=f"view_{file_info['path']}"):
            st.session_state['active_image_file'] = file_info['path']
    
    elif category == 'Video':
        if st.button("🎬 Play Video", key=f"play_{file_info['path']}"):
            st.session_state['active_video_file'] = file_info['path']
    
    elif category in ['Data', 'Document']:
        if st.button("📝 View Content", key=f"content_{file_info['path']}"):
            st.session_state['active_text_file'] = file_info['path']


def render_file_preview(file_info: dict, use_expanders: bool = True):
    """Render file preview based on type"""
    
    category = file_info['category']
    file_path = file_info['path']
    
    try:
        # Handle active file from session state
        if category == 'Database' and st.session_state.get('active_db_file') == file_path:
            render_database_query_interface(file_path, st.session_state.get('active_db_case'), use_expanders)
        
        elif category == 'Image' and st.session_state.get('active_image_file') == file_path:
            render_image_preview(file_path)
        
        elif category == 'Video' and st.session_state.get('active_video_file') == file_path:
            render_video_preview(file_path)
        
        elif category in ['Data', 'Document'] and st.session_state.get('active_text_file') == file_path:
            render_text_preview(file_path)
        
        elif category == 'Database':
            # Show quick database info
            show_database_info(file_path)
        
        elif category == 'Image':
            # Show thumbnail
            show_image_thumbnail(file_path)
    
    except Exception as e:
        st.error(f"Error previewing file: {e}")
        logger.error(f"Preview error for {file_path}: {e}", exc_info=True)


def show_database_info(db_path: str):
    """Show basic database info"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        st.info(f"📊 Database contains {len(tables)} tables")
        st.text(", ".join(tables[:10]))
        
        conn.close()
    except Exception as e:
        st.warning(f"Could not read database: {e}")


def show_image_thumbnail(image_path: str):
    """Show image thumbnail"""
    try:
        img = Image.open(image_path)
        # Resize for thumbnail
        img.thumbnail((200, 200))
        st.image(img, caption="Thumbnail")
    except Exception as e:
        st.warning(f"Could not load image: {e}")


def render_database_query_interface(db_path: str, case_id: str, use_expanders: bool = True):
    """Interactive database query interface"""
    
    st.markdown("### 🗄️ Database Query Interface")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            st.warning("No tables found in database")
            conn.close()
            return
        
        # Table selector
        selected_table = st.selectbox("Select Table:", tables, key=f"table_{db_path}")
        
        if selected_table:
            # Get table info
            cursor.execute(f"PRAGMA table_info({selected_table})")
            columns_info = cursor.fetchall()
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Columns:** {len(columns_info)}")
            with col2:
                cursor.execute(f"SELECT COUNT(*) FROM {selected_table}")
                row_count = cursor.fetchone()[0]
                st.markdown(f"**Rows:** {row_count:,}")
            
            # Show schema
            if use_expanders:
                with st.expander("📋 Table Schema"):
                    schema_df = pd.DataFrame(
                        columns_info,
                        columns=['cid', 'name', 'type', 'notnull', 'dflt_value', 'pk']
                    )
                    st.dataframe(schema_df[['name', 'type', 'notnull', 'pk']], use_container_width=True)
            else:
                st.markdown("**📋 Table Schema:**")
                schema_df = pd.DataFrame(
                    columns_info,
                    columns=['cid', 'name', 'type', 'notnull', 'dflt_value', 'pk']
                )
                st.dataframe(schema_df[['name', 'type', 'notnull', 'pk']], use_container_width=True)
            
            # Quick view
            if st.button("👁️ View First 10 Rows", key=f"view_{db_path}_{selected_table}"):
                df = pd.read_sql_query(f"SELECT * FROM {selected_table} LIMIT 10", conn)
                st.dataframe(df, use_container_width=True)
            
            # Custom query
            st.markdown("**Custom SQL Query:**")
            custom_query = st.text_area(
                "Enter SQL:",
                value=f"SELECT * FROM {selected_table} LIMIT 100",
                height=100,
                key=f"query_text_{db_path}"
            )
            
            if st.button("▶️ Execute Query", key=f"exec_{db_path}"):
                try:
                    df = pd.read_sql_query(custom_query, conn)
                    st.success(f"✅ Found {len(df)} rows")
                    st.dataframe(df, use_container_width=True, height=300)
                    
                    # Download button
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Download Results (CSV)",
                        data=csv,
                        file_name=f"{selected_table}_export.csv",
                        mime="text/csv"
                    )
                except Exception as e:
                    st.error(f"Query failed: {e}")
        
        conn.close()
        
    except Exception as e:
        st.error(f"Database error: {e}")
        logger.error(f"DB query error for {db_path}: {e}", exc_info=True)


def render_image_preview(image_path: str):
    """Show full image preview"""
    try:
        img = Image.open(image_path)
        st.image(img, caption=Path(image_path).name, use_container_width=True)
        
        # Image info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Width", f"{img.width} px")
        with col2:
            st.metric("Height", f"{img.height} px")
        with col3:
            st.metric("Format", img.format)
            
    except Exception as e:
        st.error(f"Could not load image: {e}")


def render_video_preview(video_path: str):
    """Show video preview"""
    try:
        st.video(video_path)
    except Exception as e:
        st.error(f"Could not load video: {e}")
        st.info("Video may not be in a supported format")


def render_text_preview(file_path: str):
    """Show text file content"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(10000)  # Read first 10KB
        
        # Try to parse as JSON
        if file_path.endswith('.json'):
            import json
            try:
                data = json.loads(content)
                st.json(data)
            except:
                st.code(content, language='json')
        # Try to parse as CSV
        elif file_path.endswith('.csv'):
            df = pd.read_csv(file_path, nrows=100)
            st.dataframe(df, use_container_width=True)
        # Plain text
        else:
            st.code(content, language='text')
        
        if len(content) >= 10000:
            st.info("📝 Showing first 10KB. File may be larger.")
            
    except Exception as e:
        st.error(f"Could not read file: {e}")
