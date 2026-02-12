"""
UFDR Analysis Tool - Production Frontend
Complete forensic analysis interface with all features integrated

Features:
- Dashboard with case overview and statistics
- UFDR Upload with automatic image processing  
- Unified Query Search with text, image, and hybrid queries
- Network & Timeline Analysis with 8 visualization tabs
- Export capabilities (CSV, Excel, JSON)
- AI-powered reports generation
"""

import streamlit as st
import sys
import os
# Disable ChromaDB telemetry immediately
os.environ["ANONYMIZED_TELEMETRY"] = "False"
from pathlib import Path

# CRITICAL: Add project root to Python path FIRST (before any other imports)
# This ensures backend and visualization modules can be imported

# Get absolute path to project root - works even if Streamlit changes working directory
try:
    # Try to get the absolute path of the current file
    current_file = Path(__file__).resolve()
    # Frontend folder
    frontend_dir = current_file.parent
    # Project root is parent of frontend
    project_root = frontend_dir.parent
except:
    # Fallback: use current working directory
    project_root = Path(os.getcwd()).resolve()

# Add to path if not already there
project_root_str = str(project_root)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)
else:
    sys.path.remove(project_root_str)
    sys.path.insert(0, project_root_str)

# Also add current working directory as a fallback
cwd = os.getcwd()
if cwd not in sys.path:
    sys.path.insert(1, cwd)

import pandas as pd
from datetime import datetime
import json
import logging
import sqlite3
from dotenv import load_dotenv

# Load .env file BEFORE anything checks env vars
load_dotenv(project_root / ".env")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# Main Helper Functions
# ============================================================================

def show_hero_header():
    """Render the premium hero header."""
    st.markdown("""
    <div class="hero-container">
        <div class="hero-glow"></div>
        <div class="hero-content">
            <h1 class="hero-title">UFDR FORENSIC SUITE <span style="color:var(--primary-500)">PRO</span></h1>
            <p class="hero-subtitle">Advanced mobile forensic extraction, analysis, and intelligence platform.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

def show_home_page():
    """Render the modern home dashboard."""
    show_hero_header()
    
    # Feature Grid
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="glass-card">
            <div class="glass-header">📁 Case Management</div>
            <p style="color:var(--text-secondary)">Upload and manage forensic UFDR exports. Automatic parsing and indexing.</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="glass-card">
            <div class="glass-header">🔍 Deep Search</div>
            <p style="color:var(--text-secondary)">AI-powered semantic search across messages, calls, and media evidence.</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown("""
        <div class="glass-card">
            <div class="glass-header">🕸️ Intelligence Graph</div>
            <p style="color:var(--text-secondary)">Visualize communication networks, communities, and key influencers.</p>
        </div>
        """, unsafe_allow_html=True)

    # Quick Stats (Placeholder or Real)
    st.markdown("### 📊 System Status")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Active Cases", "3", "+1")
    m2.metric("Indexed Items", "12,450", "+540")
    m3.metric("AI Status", "Online",delta="Ready", delta_color="normal") 
    m4.metric("Storage", "45.2 GB", "-1.2%")

# ============================================================================
# Environment Variable Validation
# ============================================================================
# Validate environment configuration on startup
try:
    from utils.env_validator import validate_environment, check_env_file_exists
    
    # Check if .env file exists
    env_exists, env_message = check_env_file_exists()
    if not env_exists and env_message:
        logger.warning(env_message)
    
    # Validate environment variables
    env_valid, env_validation_message = validate_environment()
    
    if not env_valid:
        logger.error("Environment validation failed!")
        logger.error(env_validation_message)
        # Display error in Streamlit UI
        st.error("Configuration Error")
        st.error(env_validation_message)
        st.stop()
    elif env_validation_message:
        # Show warnings if any
        logger.warning(env_validation_message)
        
except ImportError as e:
    logger.warning(f"Could not import environment validator: {e}")
except Exception as e:
    logger.error(f"Error during environment validation: {e}")

# Import visualization modules at top level (after path config)
vis_import_errors = []
try:
    from visualization.network_viz import NetworkVisualizer
    NETWORK_VIZ_AVAILABLE = True
except ImportError as e:
    NetworkVisualizer = None
    NETWORK_VIZ_AVAILABLE = False
    vis_import_errors.append(f"NetworkVisualizer: {e}")

try:
    from visualization.timeline_viz import TimelineVisualizer
    TIMELINE_VIZ_AVAILABLE = True
except ImportError as e:
    TimelineVisualizer = None
    TIMELINE_VIZ_AVAILABLE = False
    vis_import_errors.append(f"TimelineVisualizer: {e}")

try:
    from visualization.geo_viz import GeoVisualizer
    GEO_VIZ_AVAILABLE = True
except ImportError as e:
    GeoVisualizer = None
    GEO_VIZ_AVAILABLE = False
    vis_import_errors.append(f"GeoVisualizer: {e}")

try:
    from visualization.advanced_network_viz import AdvancedNetworkAnalyzer
    ADVANCED_VIZ_AVAILABLE = True
except ImportError as e:
    AdvancedNetworkAnalyzer = None
    ADVANCED_VIZ_AVAILABLE = False
    vis_import_errors.append(f"AdvancedNetworkAnalyzer: {e}")

try:
    from visualization.communication_patterns_viz import CommunicationPatternAnalyzer
    PATTERNS_VIZ_AVAILABLE = True
except ImportError as e:
    CommunicationPatternAnalyzer = None
    PATTERNS_VIZ_AVAILABLE = False
    vis_import_errors.append(f"CommunicationPatternAnalyzer: {e}")

try:
    from visualization.anomaly_detection_viz import AnomalyDetector
    ANOMALY_VIZ_AVAILABLE = True
except ImportError as e:
    AnomalyDetector = None
    ANOMALY_VIZ_AVAILABLE = False
    vis_import_errors.append(f"AnomalyDetector: {e}")

try:
    from visualization.centrality_dashboard_viz import CentralityDashboard
    CENTRALITY_VIZ_AVAILABLE = True
except ImportError as e:
    CentralityDashboard = None
    CENTRALITY_VIZ_AVAILABLE = False
    vis_import_errors.append(f"CentralityDashboard: {e}")

try:
    from visualization.graph_export import GraphExporter
    EXPORT_AVAILABLE = True
except ImportError as e:
    GraphExporter = None
    EXPORT_AVAILABLE = False
    vis_import_errors.append(f"GraphExporter: {e}")

# Only log viz import issues at DEBUG level — these are optional modules
if vis_import_errors:
    logger.debug(f"Optional visualization modules not available: {vis_import_errors}")

# Load Custom CSS - Premium Theme
def load_css():
    css_file = project_root / "frontend" / "assets" / "premium_theme.css"
    if css_file.exists():
        with open(css_file, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ Theme file not found")

# Initialize Session State
if 'first_load' not in st.session_state:
    st.session_state.first_load = True

# Page Configuration
st.set_page_config(
    page_title="UFDR Analysis Pro",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/yourusername/ufdr-analysis-tool',
        'Report a bug': "https://github.com/yourusername/ufdr-analysis-tool/issues",
        'About': "# UFDR Forensic Analysis Tool\nAdvanced extraction and analysis suite."
    }
)

# Load Theme
load_css()

# Loading Animation (Simulated for UX)
if st.session_state.first_load:
    placeholder = st.empty()
    with placeholder.container():
        st.markdown("""
        <div class="loader-container">
            <div class="loader-ring"></div>
            <div class="loading-text">INITIALIZING FORENSIC CORE...</div>
        </div>
        """, unsafe_allow_html=True)
        import time
        time.sleep(1.5)  # UX pause
    placeholder.empty()
    st.session_state.first_load = False

# Main App Container
st.markdown('<div class="main-fade-in">', unsafe_allow_html=True)


# Initialize session state
if 'case_id' not in st.session_state:
    st.session_state.case_id = None
if 'selected_cases' not in st.session_state:
    st.session_state.selected_cases = []
if 'query_history' not in st.session_state:
    st.session_state.query_history = []
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Dashboard"


def get_db_connection(db_path=None):
    """Get database connection"""
    if db_path is None:
        db_path = project_root / "forensic_data.db"
    try:
        conn = sqlite3.connect(str(db_path))
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None


def ensure_db_schema(conn):
    """Create required tables if they don't exist (first-run initialization)."""
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS cases (
            case_id TEXT PRIMARY KEY,
            ingest_time TEXT,
            source_file TEXT,
            sha256 TEXT,
            examiner TEXT,
            agency TEXT,
            notes TEXT
        );
        CREATE TABLE IF NOT EXISTS devices (
            device_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            imei TEXT,
            serial_number TEXT,
            manufacturer TEXT,
            model TEXT,
            os_type TEXT,
            os_version TEXT,
            owner TEXT
        );
        CREATE TABLE IF NOT EXISTS contacts (
            contact_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            name TEXT,
            phone_raw TEXT,
            phone_digits TEXT,
            phone_e164 TEXT,
            phone_suffix_2 TEXT,
            phone_suffix_4 TEXT,
            email TEXT
        );
        CREATE TABLE IF NOT EXISTS messages (
            msg_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            device_id TEXT,
            app TEXT,
            sender_raw TEXT,
            sender_digits TEXT,
            sender_suffix_2 TEXT,
            sender_suffix_4 TEXT,
            receiver_raw TEXT,
            receiver_digits TEXT,
            receiver_suffix_2 TEXT,
            receiver_suffix_4 TEXT,
            text TEXT,
            message_type TEXT,
            timestamp TEXT,
            encrypted INTEGER DEFAULT 0,
            is_deleted INTEGER DEFAULT 0,
            source_path TEXT
        );
        CREATE TABLE IF NOT EXISTS calls (
            call_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            device_id TEXT,
            caller_raw TEXT,
            caller_digits TEXT,
            caller_suffix_2 TEXT,
            caller_suffix_4 TEXT,
            receiver_raw TEXT,
            receiver_digits TEXT,
            receiver_suffix_2 TEXT,
            receiver_suffix_4 TEXT,
            timestamp TEXT,
            duration_seconds INTEGER,
            direction TEXT,
            source_path TEXT
        );
        CREATE TABLE IF NOT EXISTS media (
            media_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            device_id TEXT,
            filename TEXT,
            media_type TEXT,
            sha256 TEXT,
            phash TEXT,
            ocr_text TEXT,
            caption TEXT,
            timestamp TEXT,
            file_size INTEGER,
            source_path TEXT
        );
        CREATE TABLE IF NOT EXISTS locations (
            location_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            device_id TEXT,
            latitude REAL,
            longitude REAL,
            accuracy REAL,
            altitude REAL,
            timestamp TEXT,
            source_path TEXT
        );
    """)
    conn.commit()


def get_case_list():
    """Get list of all cases from database"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        ensure_db_schema(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT case_id FROM cases ORDER BY case_id")
        cases = [row[0] for row in cursor.fetchall()]
        return cases
    except Exception as e:
        logger.debug(f"No cases yet: {e}")
        return []
    finally:
        conn.close()


def get_case_statistics(case_id):
    """Get statistics for a specific case"""
    conn = get_db_connection()
    if not conn:
        return {}
    
    try:
        cursor = conn.cursor()
        stats = {}
        
        # Count messages
        cursor.execute("SELECT COUNT(*) FROM messages WHERE case_id = ?", (case_id,))
        stats['messages'] = cursor.fetchone()[0]
        
        # Count calls
        cursor.execute("SELECT COUNT(*) FROM calls WHERE case_id = ?", (case_id,))
        stats['calls'] = cursor.fetchone()[0]
        
        # Count contacts
        cursor.execute("SELECT COUNT(*) FROM contacts WHERE case_id = ?", (case_id,))
        stats['contacts'] = cursor.fetchone()[0]
        
        # Count media
        cursor.execute("SELECT COUNT(*) FROM media WHERE case_id = ?", (case_id,))
        stats['media'] = cursor.fetchone()[0]
        
        # Get date range
        cursor.execute("""
            SELECT MIN(timestamp), MAX(timestamp) 
            FROM (
                SELECT timestamp FROM messages WHERE case_id = ?
                UNION ALL
                SELECT timestamp FROM calls WHERE case_id = ?
            )
        """, (case_id, case_id))
        date_range = cursor.fetchone()
        stats['date_range'] = date_range if date_range[0] else (None, None)
        
        return stats
    except Exception as e:
        logger.error(f"Error fetching case stats: {e}")
        return {}
    finally:
        conn.close()



def render_header():
    """Render main application header - deprecated in favor of hero header"""
    pass


def page_dashboard():
    """Dashboard page with overview and statistics"""
    
    # Get case list
    cases = get_case_list()
    
    if not cases:
        # Show premium home page if no cases
        show_home_page()
        st.info("👋 Upload a UFDR file to get started.")
        return
    
    # Custom dashboard header for active session
    st.markdown("""
    <div class="glass-card">
        <div class="glass-header">📊 Dashboard</div>
        <p style="color:var(--text-secondary)">Case overview, statistics, and platform status.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Case selection
    st.subheader("📁 Case Selection")
    selected_case = st.selectbox(
        "Select a case to view details",
        options=["-- Select a case --"] + cases,
        index=0  # Default to placeholder
    )
    
    # Check if placeholder is selected
    if selected_case == "-- Select a case --":
        show_home_page()
        return
    

    if selected_case:
        st.session_state.case_id = selected_case
        
        # Get statistics
        stats = get_case_statistics(selected_case)
        
        # Display statistics in columns
        st.subheader(f"📈 Case Statistics: {selected_case}")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📱 Messages", f"{stats.get('messages', 0):,}")
        with col2:
            st.metric("📞 Calls", f"{stats.get('calls', 0):,}")
        with col3:
            st.metric("👥 Contacts", f"{stats.get('contacts', 0):,}")
        with col4:
            st.metric("🖼️ Media Files", f"{stats.get('media', 0):,}")
        
        # Date range
        if stats.get('date_range') and stats['date_range'][0]:
            st.info(f"📅 Date Range: {stats['date_range'][0]} to {stats['date_range'][1]}")
        
        # Quick actions
        st.subheader("🚀 Quick Actions")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔍 Start Search", use_container_width=True):
                st.session_state.current_page = "Unified Search"
                st.rerun()
        
        with col2:
            if st.button("🕸️ View Network", use_container_width=True):
                st.session_state.current_page = "Network & Graphs"
                st.rerun()
        
        with col3:
            if st.button("📥 Export Data", use_container_width=True):
                st.session_state.current_page = "Network & Graphs"
                st.rerun()
        
        # Recent activity
        st.subheader("📝 Recent Query History")
        if st.session_state.query_history:
            for i, query in enumerate(st.session_state.query_history[-5:]):
                st.markdown(f"{i+1}. {query}")
        else:
            st.info("No queries yet. Go to Unified Search to start investigating!")


def page_upload():
    """UFDR Upload page with automatic processing"""
    st.title("📤 UFDR Upload")
    
    st.markdown("""
    Upload UFDR files for analysis. The system will automatically:
    - Extract and parse the UFDR file
    - Process all media files (images with YOLO, BLIP, DeepFace)
    - Build search indices
    - Make everything ready for investigation
    """)
    
    # Import upload component
    try:
        sys.path.append(str(Path(__file__).parent / "components"))
        from ufdr_upload_component import render_ufdr_upload
        
        # Render the upload component
        render_ufdr_upload()
        
    except ImportError as e:
        st.error(f"Upload component not available: {e}")
        st.info("Please ensure frontend/components/ufdr_upload_component.py exists")
        
        # Fallback basic upload
        st.subheader("📁 Upload UFDR File")
        uploaded_file = st.file_uploader("Choose a UFDR file", type=["ufdr"])
        
        if uploaded_file:
            st.success(f"File uploaded: {uploaded_file.name}")
            st.info("Processing functionality requires the upload component module")


def page_unified_search():
    """Unified Query Search page — powered by offline RAG + optional Gemini"""
    st.title("🔍 Unified Query Search")
    
    # Case selection
    cases = get_case_list()
    if not cases:
        st.warning("No cases available. Please upload a UFDR file first.")
        return
    
    st.session_state.selected_cases = st.multiselect(
        "Select cases to search",
        options=cases,
        default=[]
    )
    
    if not st.session_state.selected_cases:
        st.info("Please select at least one case to search")
        return
    
    st.markdown("---")
    
    # Search section
    st.subheader("💬 Enter Your Query")
    query = st.text_area(
        "Ask anything about the case data",
        placeholder="Examples:\n- Show me all contacts\n- Find messages about cryptocurrency\n- How many calls were made?\n- Messages from number 9876543210",
        height=100
    )
    
    # Search options
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        data_type_filter = st.selectbox(
            "Filter by data type",
            ["All Types", "Messages", "Contacts", "Calls", "Media", "Locations"],
            index=0
        )
    with col_opt2:
        use_llm = st.checkbox(
            "🤖 Use AI Analysis (Gemini)",
            value=True,
            help="Uses Gemini API for intelligent analysis of results. Requires GEMINI_API_KEY in .env"
        )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        search_button = st.button("🔍 Search", type="primary", use_container_width=True)
    
    if search_button and query:
        st.session_state.query_history.append(query)
        
        # Map filter
        dtype_map = {
            "All Types": None, "Messages": "message", "Contacts": "contact",
            "Calls": "call", "Media": "media", "Locations": "location"
        }
        dtype = dtype_map.get(data_type_filter)
        
        with st.spinner("🔍 Searching with hybrid retrieval (semantic + keyword + SQL)..."):
            try:
                from rag.query_engine import QueryEngine
                
                engine = QueryEngine()
                result = engine.query(
                    query_text=query,
                    case_ids=st.session_state.selected_cases,
                    n_results=30,
                    data_type_filter=dtype,
                    use_llm=use_llm,
                )
                
                # Show query classification
                query_type_emoji = {
                    "semantic": "🧠", "exact": "🎯", "statistical": "📊"
                }.get(result["query_type"], "🔍")
                
                st.info(f"{query_type_emoji} Query type: **{result['query_type']}** | "
                        f"{'🤖 AI analysis' if result['llm_used'] else '📋 Raw results'} | "
                        f"**{len(result['citations'])}** results found")
                
                # Display AI answer
                if result["answer"]:
                    st.markdown("### 💡 Analysis")
                    st.markdown(result["answer"])
                
                # Display citations/evidence
                if result["citations"]:
                    st.markdown("---")
                    st.markdown(f"### 📋 Evidence ({len(result['citations'])} records)")
                    
                    for c in result["citations"][:20]:
                        dtype_emoji = {
                            "message": "💬", "contact": "👤", "call": "📞",
                            "media": "🖼️", "location": "📍", "statistics": "📊"
                        }.get(c["data_type"], "📄")
                        
                        with st.expander(f"{dtype_emoji} {c['text'][:100]}{'...' if len(c['text']) > 100 else ''}", expanded=False):
                            st.markdown(f"**Full Content:** {c['text']}")
                            st.caption(f"Type: {c['data_type']} | Case: {c['case_id']}")
                            
                            # Show additional metadata
                            meta = c.get("metadata", {})
                            meta_display = {k: v for k, v in meta.items() 
                                          if v and k not in ("data_type", "case_id") and v != ""}
                            if meta_display:
                                meta_items = list(meta_display.items())
                                cols = st.columns(min(len(meta_items), 3))
                                for i, (k, v) in enumerate(meta_items):
                                    with cols[i % len(cols)]:
                                        st.caption(f"**{k.replace('_', ' ').title()}**: {v}")
                    
                    if len(result["citations"]) > 20:
                        st.info(f"Showing top 20 of {len(result['citations'])} results")
                elif not result["answer"]:
                    st.warning("No results found. Try a different query or check that data has been indexed.")
                    
            except ImportError as e:
                st.error(f"❌ RAG engine not available: {e}")
                st.info("💡 Run from venv: `source venv/bin/activate && streamlit run frontend/app.py`")
            except Exception as e:
                st.error(f"❌ Search error: {e}")
                logger.error(f"Search error: {e}", exc_info=True)
    
    st.markdown("---")
    
    # AI Reports section
    st.subheader("🤖 AI-Powered Reports")
    
    report_type = st.selectbox(
        "Select report type",
        ["case_summary", "communication_analysis", "timeline", "cross_case"],
        format_func=lambda x: {
            "case_summary": "📊 Case Summary",
            "communication_analysis": "💬 Communication Analysis",
            "timeline": "📅 Timeline Reconstruction",
            "cross_case": "🔗 Cross-Case Linkage"
        }.get(x, x)
    )
    
    custom_instructions = st.text_input(
        "Additional instructions (optional)",
        placeholder="e.g., Focus on crypto-related communications"
    )
    
    if st.button("📄 Generate Report", type="primary"):
        with st.spinner("Generating report with AI..."):
            try:
                from rag.report_generator import ReportGenerator
                
                gen = ReportGenerator()
                if not gen.is_llm_available:
                    st.warning("⚠️ No LLM API key configured. Set `GEMINI_API_KEY` in `.env`.")
                else:
                    report = gen.generate(
                        report_type=report_type,
                        case_ids=st.session_state.selected_cases,
                        custom_instructions=custom_instructions,
                    )
                    
                    st.markdown(f"## {report['title']}")
                    st.markdown(report["content"])
                    
                    # Download
                    st.download_button(
                        label="📥 Download Report",
                        data=report["content"],
                        file_name=f"{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                        mime="text/markdown"
                    )
            except ImportError as e:
                st.error(f"Report generator not available: {e}")
            except Exception as e:
                st.error(f"Error generating report: {e}")
                logger.error(f"Report generation error: {e}", exc_info=True)



def page_network_graphs():
    """Network & Timeline Analysis page with 8 tabs"""
    st.title("🕸️ Network & Timeline Analysis")
    
    # Case selection
    cases = get_case_list()
    if not cases:
        st.warning("No cases available. Please upload a UFDR file first.")
        return
    
    selected_case = st.selectbox(
        "Select case for analysis",
        options=["-- Select a case --"] + cases,
        index=0  # Default to placeholder
    )
    
    # Check if placeholder is selected
    if not selected_case or selected_case == "-- Select a case --":
        st.info("👉 Please select a case from the dropdown above to start analysis")
        return
    
    st.session_state.case_id = selected_case
    
    st.markdown("---")
    st.info("💡 Tip: Scroll horizontally to see all tabs →")
    
    # Create 8 tabs with scrollable support
    tabs = st.tabs([
        "🕸️ Network",
        "📅 Timeline", 
        "🎯 Ego Net",
        "🗺️ Geo Maps",
        "🔬 Advanced",
        "📞 Patterns",
        "🚨 Anomaly",
        "🎯 Centrality"
    ])
    
    # Check if visualization modules are available (imported at top level)
    if vis_import_errors:
        st.warning("⚠️ Some visualization modules could not be loaded. Check logs for details.")
        with st.expander("See import errors"):
            for error in vis_import_errors:
                st.code(error)
    
    # Tab 1: Network Graph
    with tabs[0]:
        st.subheader("🕸️ Communication Network")
        if NETWORK_VIZ_AVAILABLE:
            st.markdown("""
            Visualize the communication network showing relationships between contacts.
            - **Nodes**: Contacts (size = incoming connections)
            - **Edges**: Communication (color = strength)
            - **Layout**: Uniform spatial for >500 nodes, force-directed for smaller
            """)
            
            st.subheader("⚙️ Network Settings")
            
            col1, col2 = st.columns(2)
            with col1:
                min_interactions = st.slider(
                    "Minimum Interactions",
                    min_value=1,
                    max_value=50,
                    value=1,
                    help="Filter edges with fewer interactions. Increase for cleaner network.",
                    key="net_min_inter"
                )
            with col2:
                physics = st.checkbox(
                    "Enable Physics Simulation",
                    value=True,
                    help="Turn OFF for large networks (faster). Turn ON for animated layout.",
                    key="net_physics"
                )
            
            col1, col2 = st.columns(2)
            with col1:
                color_by = st.selectbox(
                    "Color Nodes By",
                    ["community", "centrality", "tier"],
                    help="community = detected groups, centrality = importance (red=high)",
                    key="net_color"
                )
            with col2:
                size_by = st.selectbox(
                    "Size Nodes By",
                    ["degree", "pagerank", "betweenness"],
                    help="Note: Backend currently uses in-degree (incoming connections)",
                    key="net_size"
                )
            
            # Info about what will happen
            if min_interactions > 10:
                st.info(f"💡 High filter ({min_interactions}) = cleaner network showing only strong connections")
            elif min_interactions <= 2:
                st.warning(f"⚠️ Low filter ({min_interactions}) = may show many nodes. Consider using higher value for large cases.")
            
            if st.button("🎨 Generate Network Visualization", type="primary", key="net_gen_btn"):
                with st.spinner("🎨 Generating network graph... This may take 10-30 seconds..."):
                    try:
                        # Use absolute database path
                        db_path = str(project_root / "forensic_data.db")
                        viz = NetworkVisualizer(db_path=db_path)
                        
                        # Call with correct parameters (as per backend signature)
                        html_path = viz.create_communication_network(
                            case_id=selected_case,
                            min_interactions=min_interactions,
                            color_by=color_by,
                            size_by=size_by,  # Note: Backend uses in-degree, but accepts parameter
                            physics=physics,
                            width='100%',
                            height='800px'
                        )
                        
                        if html_path and os.path.exists(html_path):
                            with open(html_path, 'r', encoding='utf-8') as f:
                                html_content = f.read()
                            st.components.v1.html(html_content, height=800, scrolling=True)
                            st.success("✅ Network visualization generated!")
                            
                            # Show tips
                            with st.expander("💡 How to use the visualization"):
                                st.markdown("""
                                **Navigation:**
                                - **Zoom**: Mouse wheel or pinch
                                - **Pan**: Click and drag background
                                - **Node info**: Hover over nodes
                                - **Select**: Click nodes/edges
                                
                                **Colors:**
                                - Different colors = Different communities
                                - Red edges = Strong connections (50+ interactions)
                                - Orange edges = Medium connections (20-50)
                                - Gray edges = Weak connections (<20)
                                
                                **Size:**
                                - Larger nodes = More incoming connections
                                - Smaller nodes = Fewer incoming connections
                                """)
                        else:
                            st.error("❌ Failed to generate visualization")
                            st.info("💡 Check if the case has sufficient data (messages/calls)")
                            
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        logger.error(f"Network viz error: {e}", exc_info=True)
                        with st.expander("🔧 Debug Info"):
                            st.code(f"Error details: {e}")
                            st.code(f"Case ID: {selected_case}")
                            st.code(f"Min interactions: {min_interactions}")
                            st.code(f"Physics: {physics}")
        else:
            st.warning("⚠️ Network visualizer not available")
            st.info("Check if visualization/network_viz.py exists and imports correctly")
    
    # Tab 2: Timeline
    with tabs[1]:
        st.subheader("📅 Temporal Analysis")
        if TIMELINE_VIZ_AVAILABLE:
            st.markdown("""
            Analyze communication patterns over time:
            - **Activity Heatmap**: Day of week × hour of day matrix showing when activity occurs
            - **Activity Timeline**: Time series of messages, calls, and locations
            - **Call Duration Timeline**: Bubble chart showing call durations over time
            """)
            
            viz_type = st.selectbox(
                "Select visualization type",
                ["Activity Heatmap", "Activity Timeline", "Call Duration Timeline"],
                help="Choose the temporal analysis type",
                key="timeline_type"
            )
            
            # Additional options for Activity Timeline
            if viz_type == "Activity Timeline":
                time_window = st.selectbox(
                    "Time Window",
                    ["day", "hour", "week", "month"],
                    help="Aggregation window for the timeline",
                    key="timeline_window"
                )
            else:
                time_window = "day"
            
            if st.button("📆 Generate Timeline", type="primary", key="timeline_gen_btn"):
                with st.spinner(f"📊 Generating {viz_type}... Please wait..."):
                    try:
                        # Use absolute database path
                        db_path = str(project_root / "forensic_data.db")
                        viz = TimelineVisualizer(db_path=db_path)
                        
                        # Call correct backend methods
                        if viz_type == "Activity Heatmap":
                            # Backend method: create_heatmap_timeline(case_id)
                            html_path = viz.create_heatmap_timeline(case_id=selected_case)
                        elif viz_type == "Activity Timeline":
                            # Backend method: create_activity_timeline(case_id, time_window)
                            html_path = viz.create_activity_timeline(
                                case_id=selected_case,
                                time_window=time_window
                            )
                        elif viz_type == "Call Duration Timeline":
                            # Backend method: create_call_duration_timeline(case_id)
                            html_path = viz.create_call_duration_timeline(case_id=selected_case)
                        else:
                            html_path = None
                        
                        if html_path and os.path.exists(html_path):
                            with open(html_path, 'r', encoding='utf-8') as f:
                                html_content = f.read()
                            st.components.v1.html(html_content, height=800, scrolling=True)
                            st.success("✅ Timeline visualization generated!")
                            
                            # Show interpretation tips
                            with st.expander("💡 How to interpret this visualization"):
                                if viz_type == "Activity Heatmap":
                                    st.markdown("""
                                    **Heatmap Interpretation:**
                                    - **Darker colors** = More activity during that day/hour
                                    - **Lighter colors** = Less activity
                                    - Look for patterns: Late-night activity, weekend patterns, regular schedules
                                    - **Hover** over cells to see exact counts
                                    """)
                                elif viz_type == "Activity Timeline":
                                    st.markdown("""
                                    **Timeline Interpretation:**
                                    - **Blue line** = Messages
                                    - **Red line** = Calls
                                    - **Green line** = Location updates
                                    - **Spikes** indicate periods of high activity
                                    - **Gaps** indicate periods of silence
                                    - **Hover** over points to see exact values
                                    """)
                                elif viz_type == "Call Duration Timeline":
                                    st.markdown("""
                                    **Call Duration Interpretation:**
                                    - **Bubble size** = Call duration (larger = longer)
                                    - **X-axis** = Time when call occurred
                                    - **Y-axis** = Duration in minutes
                                    - Look for unusually long calls
                                    - **Hover** over bubbles for details
                                    """)
                        else:
                            st.error("❌ Failed to generate visualization")
                            st.info("💡 Check if the case has messages/calls with timestamps")
                            
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        logger.error(f"Timeline viz error: {e}", exc_info=True)
                        with st.expander("🔧 Debug Info"):
                            st.code(f"Error details: {e}")
                            st.code(f"Case ID: {selected_case}")
                            st.code(f"Visualization type: {viz_type}")
                            if viz_type == "Activity Timeline":
                                st.code(f"Time window: {time_window}")
        else:
            st.warning("⚠️ Timeline visualizer not available")
            st.info("Check if visualization/timeline_viz.py exists and imports correctly")
    
    # Tab 3: Ego Network
    with tabs[2]:
        st.subheader("🎯 Ego Network Analysis")
        if NETWORK_VIZ_AVAILABLE:  # Ego network uses NetworkVisualizer
            st.markdown("""
            Analyze individual contact networks:
            - **Select a contact** to see their direct and indirect connections
            - **Network radius** controls how many hops to explore (1-3)
            - **Hierarchical layout** shows relationships clearly
            - **Target node** is highlighted in red with a star ⭐
            """)
            
            # Get contacts for selection - query from messages and calls since contacts may not have phone numbers
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    # Get unique phone numbers from messages and calls, with names from contacts if available
                    cursor.execute("""
                        WITH all_phones AS (
                            SELECT DISTINCT sender_digits as phone FROM messages WHERE case_id = ? AND sender_digits IS NOT NULL AND sender_digits != ''
                            UNION
                            SELECT DISTINCT receiver_digits as phone FROM messages WHERE case_id = ? AND receiver_digits IS NOT NULL AND receiver_digits != ''
                            UNION
                            SELECT DISTINCT caller_digits as phone FROM calls WHERE case_id = ? AND caller_digits IS NOT NULL AND caller_digits != ''
                            UNION
                            SELECT DISTINCT receiver_digits as phone FROM calls WHERE case_id = ? AND receiver_digits IS NOT NULL AND receiver_digits != ''
                        )
                        SELECT DISTINCT ap.phone, COALESCE(c.name, 'Unknown') as name
                        FROM all_phones ap
                        LEFT JOIN contacts c ON ap.phone = c.phone_digits AND c.case_id = ?
                        ORDER BY name
                        LIMIT 200
                    """, (selected_case, selected_case, selected_case, selected_case, selected_case))
                    contacts = cursor.fetchall()
                    conn.close()
                    
                    if contacts:
                        # Create display options with name and phone
                        contact_options = [f"{row[1] or 'Unknown'} ({row[0]})" for row in contacts]
                        selected_contact = st.selectbox(
                            "Select contact to analyze",
                            contact_options,
                            help="Choose a contact to see their network connections",
                            key="ego_contact"
                        )
                        
                        # Extract phone number from selection
                        import re
                        phone_match = re.search(r'\(([^)]+)\)$', selected_contact)
                        contact_phone = phone_match.group(1) if phone_match else contacts[0][0]
                        
                        # Only radius parameter (no min_weight in backend)
                        radius = st.slider(
                            "Network Radius (hops)",
                            min_value=1,
                            max_value=3,
                            value=2,
                            help="1 = direct connections only, 2 = friends of friends, 3 = extended network",
                            key="ego_radius"
                        )
                        
                        # Info about what radius means
                        if radius == 1:
                            st.info("👥 Radius 1: Shows only direct contacts (1 hop away)")
                        elif radius == 2:
                            st.info("👥 Radius 2: Shows contacts + their contacts (2 hops away)")
                        else:
                            st.info("👥 Radius 3: Shows extended network (3 hops away) - may be large!")
                        
                        if st.button("🎯 Generate Ego Network", type="primary", key="ego_gen_btn"):
                            with st.spinner(f"🎯 Generating ego network for {contact_phone}... This may take a moment..."):
                                try:
                                    # Use absolute database path
                                    db_path = str(project_root / "forensic_data.db")
                                    viz = NetworkVisualizer(db_path=db_path)
                                    
                                    # Call with CORRECT parameters (target_phone, radius)
                                    html_path = viz.create_ego_network(
                                        case_id=selected_case,
                                        target_phone=contact_phone,  # ✅ Correct parameter name
                                        radius=radius                 # ✅ Correct parameter
                                        # NO min_weight parameter!
                                    )
                                    
                                    if html_path and os.path.exists(html_path):
                                        with open(html_path, 'r', encoding='utf-8') as f:
                                            html_content = f.read()
                                        st.components.v1.html(html_content, height=800, scrolling=True)
                                        st.success("✅ Ego network generated!")
                                        
                                        # Show interpretation tips
                                        with st.expander("💡 How to interpret this ego network"):
                                            st.markdown("""
                                            **Understanding the Visualization:**
                                            
                                            **Nodes:**
                                            - ⭐ **Red node with star** = Target contact (the one you selected)
                                            - 🔵 **Blue nodes** = Connected contacts
                                            - **Size** indicates importance in the network
                                            
                                            **Edges (Lines):**
                                            - 🔴 **Red** = Strong connection (20+ interactions)
                                            - 🟠 **Orange** = Medium connection (10-20 interactions)
                                            - ⚪ **Gray** = Weak connection (<10 interactions)
                                            - **Arrows** show direction of communication
                                            
                                            **Layout:**
                                            - Uses hierarchical layout for clarity
                                            - Target is typically at the center or top
                                            - Connected nodes arranged by distance
                                            
                                            **Interactions:**
                                            - **Hover** over nodes to see details
                                            - **Hover** over edges to see interaction counts
                                            - **Zoom** and **pan** to explore
                                            - **Click** nodes to select them
                                            """)
                                    else:
                                        st.error("❌ Failed to generate ego network")
                                        st.info("💡 This could mean the contact has no connections in the network")
                                        
                                except Exception as e:
                                    st.error(f"❌ Error: {str(e)}")
                                    logger.error(f"Ego network error: {e}", exc_info=True)
                                    with st.expander("🔧 Debug Info"):
                                        st.code(f"Error details: {e}")
                                        st.code(f"Case ID: {selected_case}")
                                        st.code(f"Target phone: {contact_phone}")
                                        st.code(f"Radius: {radius}")
                    else:
                        st.warning("⚠️ No contacts found in this case")
                        st.info("💡 Make sure the case has contacts with phone numbers")
                except Exception as e:
                    st.error(f"❌ Error loading contacts: {str(e)}")
                    logger.error(f"Contact loading error: {e}", exc_info=True)
                    with st.expander("🔧 Debug Info"):
                        st.code(f"Error: {e}")
                        st.code(f"Case ID: {selected_case}")
            else:
                st.error("❌ Database connection failed")
                st.info("Check if forensic_data.db exists and is accessible")
        else:
            st.warning("⚠️ Ego network visualizer not available")
            st.info("Check if visualization/network_viz.py exists and imports correctly")
    
    # Tab 4: Geographic Maps
    with tabs[3]:
        st.subheader("🗺️ Geographic Visualization")
        if GEO_VIZ_AVAILABLE:
            st.markdown("""
            Visualize location data:
            - Movement paths
            - Location clusters
            - Geographic hotspots
            """)
            
            viz_type = st.selectbox(
                "Select map type",
                ["Location Points", "Movement Paths", "Location Heatmap"],
                key="geo_type"
            )
            
            if st.button("🗺️ Generate Map", key="geo_gen_btn"):
                with st.spinner("Generating geographic visualization..."):
                    try:
                        # Use absolute database path
                        db_path = str(project_root / "forensic_data.db")
                        viz = GeoVisualizer(db_path=db_path)
                        
                        if viz_type == "Location Points":
                            html_path = viz.create_location_map(case_id=selected_case)
                        elif viz_type == "Movement Paths":
                            html_path = viz.create_movement_paths(case_id=selected_case)
                        elif viz_type == "Location Heatmap":
                            html_path = viz.create_location_heatmap(case_id=selected_case)
                        
                        if html_path and os.path.exists(html_path):
                            with open(html_path, 'r', encoding='utf-8') as f:
                                html_content = f.read()
                            st.components.v1.html(html_content, height=600, scrolling=True)
                            st.success("✅ Geographic visualization generated!")
                        else:
                            st.error("Failed to generate map")
                            
                    except Exception as e:
                        st.error(f"Error: {e}")
                        logger.error(f"Geo viz error: {e}", exc_info=True)
        else:
            st.warning("Geographic visualizer not available")
    
    # Tab 5: Advanced Analysis
    with tabs[4]:
        st.subheader("🔬 Advanced Network Analysis")
        if ADVANCED_VIZ_AVAILABLE:
            st.markdown("""
            Explore advanced network structures and patterns:
            
            - **Hierarchical Structure**: Identify leaders, coordinators, and receivers based on communication flow
            - **Network Bridges**: Find nodes that connect different communities (key intermediaries)
            - **Shortest Paths**: Visualize communication paths from the most central node
            - **Network Evolution**: Track how the network changes over time
            """)
            
            viz_type = st.selectbox(
                "Select analysis type",
                ["Hierarchical Structure", "Network Bridges", "Shortest Paths", "Network Evolution"],
                key="adv_type",
                help="Choose the type of advanced network analysis to perform"
            )
            
            # Show description based on selection
            if viz_type == "Hierarchical Structure":
                st.info("🏛️ **Hierarchical Structure** analyzes communication flow to identify top-level nodes (leaders with high outbound communication), middle-level nodes (coordinators), and bottom-level nodes (receivers).")
            elif viz_type == "Network Bridges":
                st.info("🌉 **Network Bridges** identifies nodes that connect different parts of the network. These nodes are critical for information flow and their removal would fragment the network.")
            elif viz_type == "Shortest Paths":
                st.info("🛤️ **Shortest Paths** shows the most efficient communication routes from the most central node to others. Useful for understanding network reach and accessibility.")
            elif viz_type == "Network Evolution":
                st.info("⏳ **Network Evolution** tracks how the network grows and changes over time, showing patterns in network formation and activity levels.")
            
            if st.button("🔬 Generate Analysis", type="primary", key="adv_gen_btn"):
                with st.spinner(f"Analyzing {viz_type.lower()}... This may take a moment..."):
                    try:
                        # Use absolute database path
                        db_path = str(project_root / "forensic_data.db")
                        viz = AdvancedNetworkAnalyzer(db_path=db_path)
                        
                        html_path = None
                        if viz_type == "Hierarchical Structure":
                            html_path = viz.create_hierarchical_visualization(case_id=selected_case)
                        elif viz_type == "Network Bridges":
                            html_path = viz.identify_bridges(case_id=selected_case)
                        elif viz_type == "Shortest Paths":
                            html_path = viz.visualize_shortest_paths(case_id=selected_case)
                        elif viz_type == "Network Evolution":
                            html_path = viz.create_network_evolution(case_id=selected_case)
                        
                        if html_path and os.path.exists(html_path):
                            with open(html_path, 'r', encoding='utf-8') as f:
                                html_content = f.read()
                            st.components.v1.html(html_content, height=850, scrolling=True)
                            st.success(f"✅ {viz_type} analysis complete!")
                            
                            # Add interpretation guide
                            with st.expander("💡 How to Interpret This Analysis"):
                                if viz_type == "Hierarchical Structure":
                                    st.markdown("""
                                    **Understanding the Hierarchy:**
                                    - **Top Layer (Red)**: Leaders/influencers with high outbound communication
                                    - **Middle Layer (Orange)**: Coordinators who both send and receive
                                    - **Bottom Layer (Blue)**: Receivers with primarily inbound communication
                                    - **Hierarchy Score**: Ratio of outbound to total communication (1.0 = pure leader, 0.0 = pure receiver)
                                    """)
                                elif viz_type == "Network Bridges":
                                    st.markdown("""
                                    **Understanding Bridge Nodes:**
                                    - **Bridge Score**: High betweenness relative to degree (connects communities efficiently)
                                    - **Betweenness**: How often a node appears on shortest paths between others
                                    - **Degree**: Number of direct connections
                                    - **Key Insight**: High bridge nodes are critical for network connectivity
                                    """)
                                elif viz_type == "Shortest Paths":
                                    st.markdown("""
                                    **Understanding Path Visualization:**
                                    - **Red Node**: Source node (most central)
                                    - **Orange Nodes**: Target nodes
                                    - **Colored Lines**: Different paths (colors distinguish paths)
                                    - **Hops**: Number of intermediaries in the path
                                    - **Key Insight**: Shorter paths indicate closer relationships
                                    """)
                                elif viz_type == "Network Evolution":
                                    st.markdown("""
                                    **Understanding Evolution Patterns:**
                                    - **Nodes/Edges Over Time**: Network growth or contraction
                                    - **Density**: How connected the network is (higher = more interconnected)
                                    - **Communication Volume**: Activity levels over time
                                    - **Key Insight**: Spikes indicate increased activity periods
                                    """)
                        else:
                            st.error("❌ Failed to generate analysis. The visualization returned no data.")
                            st.info("💡 This might happen if there's insufficient data for this analysis type.")
                            
                    except Exception as e:
                        st.error(f"❌ Error generating analysis: {e}")
                        with st.expander("🔍 Debug Information"):
                            st.code(str(e))
                            logger.error(f"Advanced viz error: {e}", exc_info=True)
        else:
            st.warning("Advanced visualizer not available")
    
    # Tab 6: Communication Patterns
    with tabs[5]:
        st.subheader("📞 Communication Patterns")
        if PATTERNS_VIZ_AVAILABLE:
            st.markdown("""
            Analyze communication patterns:
            - Peak hours heatmap
            - Frequency charts
            - Response time analysis
            - Communication flow (Sankey)
            """)
            
            viz_type = st.selectbox(
                "Select pattern type",
                ["Peak Hours Heatmap", "Frequency Chart", "Response Times", "Communication Flow"],
                key="pattern_type"
            )
            
            if st.button("📞 Generate Pattern Analysis", type="primary", key="pattern_gen_btn"):
                with st.spinner(f"Generating {viz_type}..."):
                    try:
                        # Use absolute database path
                        db_path = str(project_root / "forensic_data.db")
                        viz = CommunicationPatternAnalyzer(db_path=db_path)
                        
                        html_path = None
                        if viz_type == "Peak Hours Heatmap":
                            html_path = viz.create_peak_hours_heatmap(case_id=selected_case)
                        elif viz_type == "Frequency Chart":
                            html_path = viz.create_frequency_chart(case_id=selected_case, time_window='day')
                        elif viz_type == "Response Times":
                            html_path = viz.create_response_time_analysis(case_id=selected_case)
                        elif viz_type == "Communication Flow":
                            html_path = viz.create_sankey_diagram(case_id=selected_case, top_n=15)
                        
                        if html_path and os.path.exists(html_path):
                            # Check file size
                            file_size = os.path.getsize(html_path)
                            file_size_mb = file_size / (1024 * 1024)
                            
                            # Provide download button
                            with open(html_path, 'rb') as f:
                                file_data = f.read()
                            
                            # Provide download button for all visualizations
                            st.download_button(
                                label="📥 Download Visualization (HTML)",
                                data=file_data,
                                file_name=os.path.basename(html_path),
                                mime="text/html",
                                key="pattern_download",
                                help="Download to view in browser or save for later"
                            )
                            
                            # Try inline rendering
                            if viz_type == "Communication Flow":
                                st.info("🌊 **Communication Flow (Sankey Diagram)**: Top contacts and their communication patterns")
                            
                            try:
                                with open(html_path, 'r', encoding='utf-8') as f:
                                    html_content = f.read()
                                
                                # Try to render inline
                                st.components.v1.html(html_content, height=800, scrolling=True)
                                st.success(f"✅ Pattern analysis complete! (File: {file_size_mb:.2f} MB)")
                                
                            except Exception as render_error:
                                st.warning(f"⚠️ Could not render inline: {render_error}")
                                st.info("💡 Please use the download button above to view the visualization in your browser.")
                                st.success(f"✅ Visualization generated successfully! File: {html_path}")
                            
                            # Add interpretation guide for Sankey
                            if viz_type == "Communication Flow":
                                with st.expander("💡 Understanding the Sankey Diagram"):
                                    st.markdown("""
                                    **What it shows:**
                                    - **Nodes**: Individual contacts (phone numbers/names)
                                    - **Flows**: Communication volume between contacts  
                                    - **Width**: Thicker flows = more communications
                                    - **Direction**: Shows who communicated with whom
                                    
                                    **How to interact:**
                                    - **Hover**: See exact communication counts
                                    - **Drag**: Rearrange nodes for better view
                                    - **Scroll/Pinch**: Zoom in/out
                                    
                                    **Use cases:**
                                    - Identify hub contacts (many connections)
                                    - Find communication clusters
                                    - Discover key intermediaries
                                    - Visualize information flow patterns
                                    
                                    **Note**: If the diagram doesn't display above, use the download button to open in your browser.
                                    """)
                            
                        else:
                            st.error("❌ Failed to generate analysis")
                            
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
                        with st.expander("🔍 Debug Information"):
                            st.code(str(e))
                        logger.error(f"Pattern viz error: {e}", exc_info=True)
        else:
            st.warning("Pattern visualizer not available")
    
    # Tab 7: Anomaly Detection
    with tabs[6]:
        st.subheader("🚨 Anomaly Detection")
        if ANOMALY_VIZ_AVAILABLE:
            st.markdown("""
            Detect unusual patterns and suspicious activity:
            - Communication spikes
            - Unusual contacts
            - Behavioral changes
            - Late-night activity
            """)
            
            analysis_type = st.selectbox(
                "Select analysis type",
                ["Communication Spikes", "Unusual Contacts", "Behavioral Changes", "Anomaly Dashboard"],
                key="anom_type"
            )
            
            if st.button("🔍 Generate Analysis", key="anom_gen_btn"):
                with st.spinner(f"Generating {analysis_type}..."):
                    try:
                        # Use absolute database path
                        db_path = str(project_root / "forensic_data.db")
                        detector = AnomalyDetector(db_path=db_path)
                        
                        if analysis_type == "Communication Spikes":
                            html_path = detector.detect_communication_spikes(
                                case_id=selected_case,
                                time_window='day',
                                threshold_std=2.0
                            )
                        elif analysis_type == "Unusual Contacts":
                            html_path = detector.detect_unusual_contacts(
                                case_id=selected_case,
                                min_interactions=5
                            )
                        elif analysis_type == "Behavioral Changes":
                            html_path = detector.detect_behavioral_changes(
                                case_id=selected_case,
                                window_days=7
                            )
                        elif analysis_type == "Anomaly Dashboard":
                            html_path = detector.create_anomaly_dashboard(
                                case_id=selected_case
                            )
                        
                        if html_path and os.path.exists(html_path):
                            with open(html_path, 'r', encoding='utf-8') as f:
                                html_content = f.read()
                            st.components.v1.html(html_content, height=1000, scrolling=True)
                            st.success("✅ Anomaly detection complete!")
                        else:
                            st.error("Failed to generate analysis")
                            
                    except Exception as e:
                        st.error(f"Error: {e}")
                        logger.error(f"Anomaly detection error: {e}", exc_info=True)
        else:
            st.warning("Anomaly detector not available")
    
    # Tab 8: Centrality Dashboard
    with tabs[7]:
        st.subheader("🎯 Centrality Dashboard")
        if CENTRALITY_VIZ_AVAILABLE:
            st.markdown("""
            Identify key players in the network:
            - Multi-metric centrality analysis
            - Importance rankings
            - Individual profiles
            """)
            
            # Add explanation expander
            with st.expander("💡 Understanding Centrality Metrics", expanded=False):
                st.markdown("""
                ### 📊 Composite Score (Purple Bar)
                
                **What it shows:** Overall importance combining all 5 metrics
                
                **Formula:** Average of (Degree + Betweenness + Closeness + PageRank + Eigenvector)
                
                **Range:** 0.0 (unimportant) to 1.0 (critical)
                
                **Interpretation:**
                - 🔴 **0.80-1.00**: Extremely important → Top priority investigation
                - 🟠 **0.60-0.79**: Very important → Investigate thoroughly
                - 🟡 **0.40-0.59**: Moderately important → Monitor regularly
                - 🟢 **0.20-0.39**: Somewhat important → Background check
                - ⚪ **0.00-0.19**: Peripheral → Minor player
                
                ---
                
                ### 📈 The Five Metrics Explained:
                
                1. **📍 Degree Centrality** (Blue)
                   - Measures: Number of direct connections
                   - High = "Well-connected" or "Popular"
                   - Example: Person who talks to 50 people vs 5 people
                
                2. **🌉 Betweenness Centrality** (Red)
                   - Measures: How often person lies on shortest path between others
                   - High = "Broker" or "Bridge" connecting different groups
                   - Example: Only link between two separate groups
                
                3. **🎯 Closeness Centrality**
                   - Measures: Average distance to all other people
                   - High = "Central" or "Accessible" to everyone
                   - Example: Can reach anyone in 1-2 hops vs 5-6 hops
                
                4. **📊 PageRank** (Green)
                   - Measures: Importance based on who connects to you (Google's algorithm)
                   - High = "Influential" with quality connections
                   - Example: Connected by "bosses" vs "foot soldiers"
                
                5. **⭐ Eigenvector Centrality**
                   - Measures: Connections to well-connected people
                   - High = "Elite" or "Inner circle"
                   - Example: Few connections but to highly-connected people
                
                ---
                
                ### 🎯 Investigation Strategy:
                
                **Start with Top 3 Composite Score contacts:**
                1. Monitor their communications closely
                2. Map their connections (use Ego Network tab)
                3. Analyze temporal patterns (use Timeline tab)
                4. Cross-reference with other cases
                
                **High composite score person is likely:**
                - ✅ Key player / coordinator
                - ✅ Has influence over others
                - ✅ Connects different groups
                - ✅ Can spread information quickly
                - ✅ **Priority target for investigation**
                
                ---
                
                📚 **Full documentation:** See `CENTRALITY_METRICS_EXPLAINED.md`
                """)
            
            centrality_type = st.selectbox(
                "Select analysis type",
                ["Centrality Overview", "Metric Comparison Heatmap", "Individual Contact Profile"],
                key="cent_type"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                top_n = st.slider("Top N Contacts", 10, 50, 20, key="cent_topn")
            with col2:
                if centrality_type == "Individual Contact Profile":
                    # Get contact list for selector
                    conn = get_db_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            # Get phone_digits (not phone) and names for display
                            cursor.execute("""
                                SELECT phone_digits, COALESCE(name, phone_raw, phone_digits) as display_name
                                FROM contacts 
                                WHERE case_id = ? AND phone_digits IS NOT NULL AND phone_digits != ''
                                ORDER BY name
                                LIMIT 100
                            """, (selected_case,))
                            contacts_data = cursor.fetchall()
                            conn.close()
                            if contacts_data:
                                # Create display options with name
                                contact_options = {f"{row[1]} ({row[0]})": row[0] for row in contacts_data}
                                selected_display = st.selectbox(
                                    "Select Contact", 
                                    list(contact_options.keys()), 
                                    key="cent_contact"
                                )
                                contact_phone = contact_options[selected_display]
                            else:
                                st.warning("No contacts found with phone numbers")
                                contact_phone = None
                        except Exception as e:
                            st.error(f"Error loading contacts: {e}")
                            logger.error(f"Contact loading error: {e}", exc_info=True)
                            contact_phone = None
                    else:
                        contact_phone = None
            
            if st.button("📊 Generate Analysis", key="cent_gen_btn"):
                with st.spinner(f"Generating {centrality_type}..."):
                    try:
                        # Use absolute database path
                        db_path = str(project_root / "forensic_data.db")
                        
                        # Check if database exists
                        if not os.path.exists(db_path):
                            st.error(f"❌ Database not found: {db_path}")
                            st.info("💡 Please ensure you have uploaded at least one UFDR file")
                        else:
                            dashboard = CentralityDashboard(db_path=db_path)
                            
                            # Validate inputs
                            if centrality_type == "Individual Contact Profile" and not contact_phone:
                                st.error("❌ Please select a contact first")
                                html_path = None
                            else:
                                # Generate visualization
                                if centrality_type == "Centrality Overview":
                                    html_path = dashboard.create_centrality_overview(
                                        case_id=selected_case,
                                        top_n=top_n
                                    )
                                elif centrality_type == "Metric Comparison Heatmap":
                                    html_path = dashboard.create_metric_comparison_heatmap(
                                        case_id=selected_case,
                                        top_n=top_n
                                    )
                                elif centrality_type == "Individual Contact Profile":
                                    html_path = dashboard.create_individual_profile(
                                        case_id=selected_case,
                                        contact_digits=contact_phone  # ✅ Correct parameter name
                                    )
                                else:
                                    html_path = None
                            
                            if html_path and os.path.exists(html_path):
                                with open(html_path, 'r', encoding='utf-8') as f:
                                    html_content = f.read()
                                st.components.v1.html(html_content, height=1200, scrolling=True)
                                st.success("✅ Centrality analysis complete!")
                            elif html_path is None:
                                st.error("❌ Failed to generate analysis - No data returned")
                                st.info("💡 **Possible causes:**")
                                st.markdown("""
                                - Case has insufficient network data (needs messages or calls)
                                - Selected contact not found in network
                                - Graph analysis module may have issues
                                """)
                            else:
                                st.error(f"❌ Generated file not found: {html_path}")
                                st.info("💡 Check console logs for detailed error information")
                            
                    except ImportError as e:
                        st.error(f"❌ Required module not available: {e}")
                        st.info("💡 Ensure visualization/centrality_dashboard_viz.py and graph_analytics.py exist")
                        logger.error(f"Centrality import error: {e}", exc_info=True)
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
                        logger.error(f"Centrality dashboard error: {e}", exc_info=True)
                        with st.expander("🔍 Debug Information"):
                            st.code(f"Error type: {type(e).__name__}")
                            st.code(f"Error message: {str(e)}")
                            st.code(f"Case ID: {selected_case}")
                            st.code(f"Analysis type: {centrality_type}")
                            if centrality_type == "Individual Contact Profile":
                                st.code(f"Selected contact: {contact_phone if 'contact_phone' in locals() else 'None'}")
            
            # Export section
            st.markdown("---")
            st.subheader("📥 Export Options")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("📄 Export CSV", key="cent_export_csv"):
                    try:
                        from visualization.graph_export import GraphExporter
                        db_path = str(project_root / "forensic_data.db")
                        exporter = GraphExporter(db_path=db_path)
                        csv_path = exporter.export_centrality_scores(
                            case_id=selected_case,
                            format='csv',
                            top_n=top_n
                        )
                        if csv_path and os.path.exists(csv_path):
                            with open(csv_path, 'rb') as f:
                                st.download_button(
                                    label="Download CSV",
                                    data=f,
                                    file_name=os.path.basename(csv_path),
                                    mime="text/csv",
                                    key="cent_dl_csv"
                                )
                    except Exception as e:
                        st.error(f"Export failed: {e}")
            
            with col2:
                if st.button("📊 Export Excel", key="cent_export_excel"):
                    try:
                        from visualization.graph_export import GraphExporter
                        db_path = str(project_root / "forensic_data.db")
                        exporter = GraphExporter(db_path=db_path)
                        excel_path = exporter.export_centrality_scores(
                            case_id=selected_case,
                            format='excel',
                            top_n=top_n
                        )
                        if excel_path and os.path.exists(excel_path):
                            with open(excel_path, 'rb') as f:
                                st.download_button(
                                    label="Download Excel",
                                    data=f,
                                    file_name=os.path.basename(excel_path),
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key="cent_dl_excel"
                                )
                    except Exception as e:
                        st.error(f"Export failed: {e}")
            
            with col3:
                if st.button("📋 Export JSON", key="cent_export_json"):
                    try:
                        from visualization.graph_export import GraphExporter
                        db_path = str(project_root / "forensic_data.db")
                        exporter = GraphExporter(db_path=db_path)
                        json_path = exporter.export_centrality_scores(
                            case_id=selected_case,
                            format='json',
                            top_n=top_n
                        )
                        if json_path and os.path.exists(json_path):
                            with open(json_path, 'rb') as f:
                                st.download_button(
                                    label="Download JSON",
                                    data=f,
                                    file_name=os.path.basename(json_path),
                                    mime="application/json",
                                    key="cent_dl_json"
                                )
                    except Exception as e:
                        st.error(f"Export failed: {e}")
            
            with col4:
                if st.button("📁 Full Report", key="cent_full_report"):
                    with st.spinner("Generating full investigation report..."):
                        try:
                            from visualization.graph_export import GraphExporter
                            exporter = GraphExporter()
                            report_paths = exporter.create_investigation_report(case_id=selected_case)
                            if report_paths:
                                st.success(f"✅ Generated {len(report_paths)} files!")
                                st.info("Check the exports/ directory for all generated files")
                        except Exception as e:
                            st.error(f"Report generation failed: {e}")
        else:
            st.warning("Centrality dashboard not available")


def page_cross_case_analysis():
    """Cross-Case Analysis page"""
    st.title("🔗 Cross-Case Analysis")
    
    st.markdown("""
    **Find connections between multiple forensic cases using AI-powered analysis.**
    
    This feature uses **DeepSeek 671B** (cloud) to detect:
    - Shared phone numbers & variations
    - Shared email addresses
    - Common contacts across cases
    - Cryptocurrency wallets in messages
    - Name variations and aliases
    - Behavioral and temporal patterns
    """)
    
    # Multi-case selection
    st.markdown("---")
    st.subheader("📋 Select Cases to Analyze")
    
    all_cases = get_case_list()
    if not all_cases or len(all_cases) < 2:
        st.warning("⚠️ You need at least 2 cases in the database for cross-case analysis")
        st.info("📁 Upload more UFDR files to analyze connections between cases")
    else:
        # Multi-select for cross-case analysis
        cross_case_selection = st.multiselect(
            "Select 2 or more cases to analyze connections",
            options=all_cases,
            default=[],
            help="Select multiple cases to find shared entities and connections",
            key="cross_case_select"
        )
        
        if len(cross_case_selection) < 2:
            st.info("👉 Please select at least 2 cases to find connections")
        else:
            st.success(f"✅ Selected {len(cross_case_selection)} cases for analysis")
            
            # Show selected cases
            with st.expander("📊 View Selected Cases", expanded=False):
                for i, case_id in enumerate(cross_case_selection, 1):
                    stats = get_case_statistics(case_id)
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric(f"Case {i}", case_id)
                    with col2:
                        st.metric("Messages", stats.get('messages', 0))
                    with col3:
                        st.metric("Calls", stats.get('calls', 0))
                    with col4:
                        st.metric("Contacts", stats.get('contacts', 0))
                    st.markdown("---")
            
            # Analysis settings
            st.markdown("---")
            st.subheader("⚙️ Analysis Settings")
            
            with st.expander("🧠 AI Model Information", expanded=False):
                st.markdown("""
                **Model Priority:**
                1. 🧠 **DeepSeek V3.1 671B** (Primary) - Free, excellent reasoning
                2. 💰 **OpenAI GPT-4** (Backup) - Requires API key
                3. 🌐 **Anthropic Claude** (Alternative) - Requires API key
                4. 🖥️ **Llama 3.1 8B** (Fallback) - Local model
                
                **Setup:**
                - DeepSeek: `ollama pull deepseek-v3.1:671b-cloud`
                - Or set `OPENAI_API_KEY` environment variable
                - Or set `ANTHROPIC_API_KEY` environment variable
                - Or use local Llama (auto-fallback)
                """)
            
            # Generate analysis button
            st.markdown("---")
            if st.button("🔍 Analyze Connections", type="primary", use_container_width=True, key="cross_case_analyze_btn"):
                with st.spinner("🧠 AI is analyzing connections between cases... This may take 10-30 seconds..."):
                    try:
                        # Import cross-case analyzer
                        from backend.cross_case_analyzer import get_cross_case_analyzer
                        
                        # Progress bar and status
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        def progress_callback(current, total, message):
                            progress_bar.progress(current / total)
                            status_text.text(f"🔍 {message}")
                        
                        # Initialize analyzer
                        db_path = str(project_root / "forensic_data.db")
                        analyzer = get_cross_case_analyzer(db_path=db_path)
                        
                        # Run analysis
                        result = analyzer.analyze_cross_case_links(
                            case_ids=cross_case_selection,
                            progress_callback=progress_callback
                        )
                        
                        # Clear progress indicators
                        progress_bar.empty()
                        status_text.empty()
                        
                        # Display results
                        if result['success']:
                            st.success(f"✅ Analysis Complete! Found {result['total_connections']} connection(s)")
                            st.info(f"⏱️ Processing time: {result['processing_time']:.1f}s")
                            
                            # AI Summary
                            if result.get('analysis_summary'):
                                st.markdown("---")
                                st.subheader("🧠 AI Analysis Summary")
                                st.markdown(result['analysis_summary'])
                            
                            # Connections
                            if result['connections']:
                                st.markdown("---")
                                st.subheader(f"🔗 Connections Found ({len(result['connections'])})")
                                
                                for i, conn in enumerate(result['connections'], 1):
                                    with st.expander(
                                        f"🔗 Connection {i}: {conn['case_1']} ↔️ {conn['case_2']} "
                                        f"(Strength: {conn['connection_strength']:.0%})",
                                        expanded=True
                                    ):
                                        st.markdown(f"**Summary:** {conn['summary']}")
                                        st.markdown(f"**Connection Strength:** {conn['connection_strength']:.0%}")
                                        st.markdown(f"**Shared Entities:** {len(conn['shared_entities'])}")
                                        
                                        # Display shared entities
                                        if conn['shared_entities']:
                                            st.markdown("#### 📦 Shared Entities:")
                                            
                                            for entity in conn['shared_entities']:
                                                entity_type = entity['entity_type']
                                                entity_value = entity['entity_value']
                                                confidence = entity['confidence']
                                                context = entity['context']
                                                cases_list = entity['cases']
                                                
                                                # Icon based on entity type
                                                icon = {
                                                    'phone': '📞',
                                                    'email': '📧',
                                                    'crypto_wallet': '💰',
                                                    'name': '👤',
                                                    'device': '📱',
                                                    'location': '📍'
                                                }.get(entity_type, '🔸')
                                                
                                                # Color based on confidence
                                                if confidence >= 0.8:
                                                    confidence_color = '🟢'  # Green
                                                elif confidence >= 0.5:
                                                    confidence_color = '🟡'  # Yellow
                                                else:
                                                    confidence_color = '🔴'  # Red
                                                
                                                st.markdown(
                                                    f"{icon} **{entity_type.replace('_', ' ').title()}:** `{entity_value}`  "
                                                    f"{confidence_color} {confidence:.0%} confidence  "
                                                    f"\n   📁 Found in: {', '.join(cases_list)}  "
                                                    f"\n   📝 Context: {context}"
                                                )
                                                st.markdown("---")
                            # Export results
                            st.markdown("---")
                            st.subheader("📥 Export Results")
                            
                            # Prepare export data
                            export_json = json.dumps(result, indent=2)
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.download_button(
                                    label="💾 Download JSON",
                                    data=export_json,
                                    file_name=f"cross_case_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                    mime="application/json",
                                    use_container_width=True
                                )
                            
                            with col2:
                                # Create markdown report
                                md_report = f"# Cross-Case Analysis Report\n\n"
                                md_report += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                                md_report += f"**Cases Analyzed:** {', '.join(cross_case_selection)}\n\n"
                                md_report += f"**Connections Found:** {result['total_connections']}\n\n"
                                md_report += f"**Processing Time:** {result['processing_time']:.1f}s\n\n"
                                
                                if result.get('analysis_summary'):
                                    md_report += f"## AI Summary\n\n{result['analysis_summary']}\n\n"
                                
                                md_report += f"## Connections\n\n"
                                for i, conn in enumerate(result['connections'], 1):
                                    md_report += f"### Connection {i}: {conn['case_1']} ↔ {conn['case_2']}\n\n"
                                    md_report += f"- **Summary:** {conn['summary']}\n"
                                    md_report += f"- **Strength:** {conn['connection_strength']:.0%}\n"
                                    md_report += f"- **Shared Entities:** {len(conn['shared_entities'])}\n\n"
                                
                                st.download_button(
                                    label="📝 Download Markdown",
                                    data=md_report,
                                    file_name=f"cross_case_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                                    mime="text/markdown",
                                    use_container_width=True
                                )
                        else:
                            st.error(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
                            st.info("💡 **Tips:**")
                            st.markdown("""
                            - Ensure DeepSeek is installed: `ollama pull deepseek-v3.1:671b-cloud`
                            - Or set OPENAI_API_KEY environment variable
                            - Check logs for detailed error information
                            - Ensure cases have overlapping data (contacts, messages, etc.)
                            """)
                    
                    except ImportError as e:
                        st.error(f"❌ Cross-case analysis module not available: {e}")
                        st.info("💡 Ensure backend modules are properly installed")
                    except Exception as e:
                        st.error(f"❌ Error during analysis: {e}")
                        logger.error(f"Cross-case analysis error: {e}", exc_info=True)
                        st.info("📝 Check the console logs for detailed error information")


def main():
    """Main application"""
    render_header()
    
    # Sidebar navigation
    with st.sidebar:
        st.title("📋 Navigation")
        
        pages = {
            "📊 Dashboard": page_dashboard,
            "📤 UFDR Upload": page_upload,
            "🔍 Unified Search": page_unified_search,
            "🕸️ Network & Graphs": page_network_graphs,
            "🔗 Cross-Case Analysis": page_cross_case_analysis
        }
        
        # Page selection
        selected_page = st.radio(
            "Go to",
            options=list(pages.keys()),
            key="page_selector"
        )
        
        st.session_state.current_page = selected_page
        
        st.markdown("---")
        
        # Case info in sidebar
        if st.session_state.case_id:
            st.info(f"**Current Case:** {st.session_state.case_id}")
        
        st.markdown("---")
        st.markdown("### 📚 Quick Links")
        st.markdown("- [Documentation]()")
        st.markdown("- [User Guide]()")
        st.markdown("- [Support]()")
    
    # Render selected page
    if selected_page in pages:
        pages[selected_page]()


if __name__ == "__main__":
    main()
