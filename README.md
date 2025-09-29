# AI-Based UFDR Analysis Tool 🔍

## SIH 2025 - Problem Statement ID: SIH25198

An advanced AI-powered forensic analysis tool for processing Universal Forensic Extraction Device Reports (UFDR) with local LLM integration, semantic search, and knowledge graphs - designed for government security requirements with complete offline capability.

## 🎯 Problem Statement

**Organization:** Ministry of Home Affairs (MHA) - National Security Guard (NSG)

During digital forensic investigations, UFDR reports from seized devices contain massive amounts of data. Manual analysis is time-consuming and delays finding critical evidence. This tool provides investigators with natural language query capabilities to quickly extract actionable insights without requiring deep technical expertise.

## 🚀 Key Features

### Core Capabilities
- **🔐 Completely Offline:** All AI models run locally - no external API calls
- **🔍 Natural Language Queries:** Ask questions like "show me chat records containing crypto addresses"
- **🌐 Multilingual Support:** Handles content in multiple languages
- **📊 Knowledge Graph:** Visualize relationships between entities
- **🔒 Forensic Integrity:** SHA256 hashing and chain-of-custody preservation
- **📈 Semantic Search:** FAISS-based vector indexing for intelligent retrieval

### Security & Compliance
- Air-gapped deployment capability
- Audit logging with cryptographic signatures
- Role-based access control (RBAC)
- AES-256 encryption for sensitive data
- Immutable audit trails

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────┐
│                 Frontend (Streamlit)              │
├──────────────────────────────────────────────────┤
│                  Backend API                      │
├──────────┬──────────┬──────────┬────────────────┤
│   UFDR   │  Vector  │   RAG    │  Knowledge     │
│  Parser  │  Index   │  Engine  │    Graph       │
├──────────┴──────────┴──────────┴────────────────┤
│          Local Infrastructure                    │
│  • FAISS  • Neo4j  • LLaMA  • Embeddings        │
└──────────────────────────────────────────────────┘
```

## 📦 Installation

### Prerequisites
- Python 3.9+
- 16GB RAM minimum (32GB recommended)
- 50GB free disk space
- GPU optional but recommended for LLM inference

### Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/ufdr-analysis-tool.git
cd ufdr-analysis-tool
```

2. **Create virtual environment**
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On Linux/Mac
source venv/bin/activate
```

3. **Install dependencies**
```bash
# Core dependencies
pip install -r requirements.txt

# NLP and vector indexing
pip install -r requirements-nlp.txt

# Graph database
pip install -r requirements-graph.txt

# Media processing
pip install -r requirements-media.txt

# Frontend
pip install -r requirements-frontend.txt
```

4. **Download models (for offline use)**
```bash
# Download embedding model
python scripts/download_models.py --type embeddings

# Download quantized LLM (e.g., LLaMA 2 7B GGUF)
python scripts/download_models.py --type llm
```

5. **Set up Neo4j (Docker)**
```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  -v $PWD/neo4j/data:/data \
  neo4j:latest
```

## 🔧 Usage

### 1. Ingest UFDR File

```bash
python parser/ingest_cli.py evidence.ufdr \
  --case-id CASE001 \
  --operator "Inspector Name"
```

Output:
```
✓ UFDR Ingestion Successful!
  Case ID:     CASE001
  SHA256:      a3b4c5d6e7f8...
  Statistics:
    - Messages: 15,234
    - Calls: 892
    - Contacts: 456
```

### 2. Build Vector Index

```bash
python vector/index_builder.py \
  --case-id CASE001 \
  --parsed-dir data/parsed
```

### 3. Launch Web Interface

```bash
streamlit run frontend/app.py
```

Navigate to `http://localhost:8501`

### 4. Query via CLI

```bash
# Natural language query
python nlp/query.py "show messages with crypto addresses from foreign numbers"

# Find specific patterns
python vector/retriever.py "bitcoin transfer" --crypto --case-id CASE001

# Export results
python vector/retriever.py "suspicious activity" \
  --export results.json \
  --format json
```

## 🔍 Example Queries

### Natural Language Queries
- "Show me all messages containing cryptocurrency addresses"
- "List communications with foreign phone numbers in the last month"
- "Find all contacts who communicated with +1-555-0123"
- "Show deleted messages recovered from WhatsApp"
- "Find images shared between midnight and 6 AM"

### Graph Queries (Cypher)
```cypher
// Find all contacts of a specific person
MATCH (p:Person {phone: "+919876543210"})-[:CONTACT_OF]-(c:Person)
RETURN p, c

// Find message chains involving crypto
MATCH (m:Message)-[:MENTIONS]->(crypto:CryptoAddress)
RETURN m, crypto LIMIT 50
```

## 📊 Project Structure

```
ufdr-analysis-tool/
├── parser/              # UFDR extraction and parsing
│   ├── ufdr_unzip.py   # Secure extraction with SHA256
│   ├── ufdr_parser.py  # Streaming XML parser
│   └── ingest_cli.py   # Unified ingestion pipeline
├── vector/             # Semantic search
│   ├── index_builder.py # FAISS index creation
│   └── retriever.py    # Search and ranking
├── nlp/               # NLP and RAG
│   ├── rag_engine.py  # Local LLM RAG
│   └── prompts/       # Prompt templates
├── graph/             # Knowledge graph
│   ├── schema.cypher  # Neo4j schema
│   ├── ingest_to_neo4j.py
│   └── nl2cypher.py  # Natural language to Cypher
├── frontend/          # User interface
│   └── app.py        # Streamlit application
├── media/            # Media processing
│   ├── ocr_worker.py # OCR for images
│   └── asr_worker.py # Speech-to-text
├── infra/            # Infrastructure
│   ├── docker/       # Container configs
│   ├── models/       # Model storage
│   └── offline_bundle/ # Air-gap installer
└── docs/             # Documentation
```

## 🛡️ Security Features

### Forensic Integrity
- **SHA256 Hashing:** Every ingested file is hashed before processing
- **Audit Trail:** Complete activity logging with timestamps
- **Chain of Custody:** Maintains legal admissibility of evidence
- **Immutable Storage:** Write-once audit logs

### Access Control
- Role-based permissions (Viewer, Analyst, Investigator, Admin)
- JWT-based authentication
- Session management
- Activity monitoring

### Data Protection
- AES-256 encryption at rest
- TLS for internal services
- Secure key management
- No external data transmission

## 🚀 Deployment

### Development
```bash
python run_dev.py
```

### Production (Docker Compose)
```bash
docker-compose up -d
```

### Air-Gapped Installation
```bash
# On internet-connected machine
./scripts/prepare_offline_bundle.sh

# Transfer bundle to air-gapped system
# On air-gapped machine
./infra/offline_installer.sh
```

## 📈 Performance

- **Ingestion Speed:** ~10,000 artifacts/minute
- **Search Latency:** <100ms for semantic search
- **LLM Response:** 2-5 seconds with quantized models
- **Concurrent Users:** Supports 10+ investigators

## 🧪 Testing

```bash
# Run unit tests
pytest tests/unit

# Run integration tests
pytest tests/integration

# Run with coverage
pytest --cov=. tests/
```

## 📝 API Documentation

### REST API Endpoints

```
POST   /api/ingest      # Upload and process UFDR
GET    /api/search      # Semantic search
POST   /api/query       # Natural language query
GET    /api/graph       # Graph visualization data
GET    /api/export      # Export results
```

## 🤝 Contributing

Please read [CONTRIBUTING.md](docs/CONTRIBUTING.md) for development guidelines.

## 📄 License

This project is developed for Smart India Hackathon 2025. 
Usage rights are subject to competition rules and MHA/NSG requirements.

## 👥 Team

- **Team Name:** [Your Team Name]
- **Institution:** [Your Institution]
- **Hackathon:** SIH 2025

## 🙏 Acknowledgments

- Ministry of Home Affairs (MHA)
- National Security Guard (NSG)
- Smart India Hackathon organizers

## 📞 Support

For deployment assistance or technical queries:
- Create an issue on GitHub
- Contact: [your-email]

---

**⚠️ Important:** This tool is designed for authorized law enforcement use only. 
Ensure compliance with local laws and regulations regarding digital forensics and data privacy.

**🔒 Security Note:** Never commit sensitive data, actual case files, or model weights to the repository.