"""
Generate a dummy case for testing RAG and training XGBoost.
Creates: data/cases/case_dummy/
Populates: unified_db.sqlite and ChromaDB index.
"""

import os
import sqlite3
import shutil
import logging
from rag.faiss_store import FAISSStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CASE_ID = "case_dummy"
CASE_DIR = os.path.join("data", "cases", CASE_ID)
DB_PATH = os.path.join(CASE_DIR, "unified_db.sqlite")

def create_dummy_data():
    if os.path.exists(CASE_DIR):
        shutil.rmtree(CASE_DIR)
    os.makedirs(CASE_DIR, exist_ok=True)
    
    # 1. Create SQLite DB
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("CREATE TABLE IF NOT EXISTS contacts (contact_id TEXT, name TEXT, number TEXT, source_app TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS messages (msg_id TEXT, sender TEXT, receiver TEXT, content TEXT, timestamp TEXT, source_app TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS calls (call_id TEXT, caller TEXT, receiver TEXT, duration INTEGER, timestamp TEXT, type TEXT)")
    
    # Insert Data
    contacts = [
        ("c1", "Alice", "1234567890", "whatsapp"),
        ("c2", "Bob Malicious", "9876543210", "telegram"),
        ("c3", "Charlie", "5551234567", "signal"),
    ]
    cursor.executemany("INSERT INTO contacts VALUES (?,?,?,?)", contacts)
    
    messages = [
        ("m1", "Alice", "Me", "Hey, are we still meeting for lunch?", "2024-01-01 12:00:00", "whatsapp"),
        ("m2", "Bob", "Me", "I have the package. Bring the money.", "2024-01-02 14:00:00", "telegram"),
        ("m3", "Charlie", "Me", "Did you see the news about the crash?", "2024-01-03 09:00:00", "signal"),
        ("m4", "Unknown", "Me", "Your verification code is 123456", "2024-01-04 10:00:00", "sms"),
        ("m5", "Bob", "Me", "Don't be late. The drop is at the usual spot.", "2024-01-02 15:00:00", "telegram"),
        ("m6", "Alice", "Me", "Happy Birthday!", "2024-05-10 00:01:00", "whatsapp"),
    ]
    cursor.executemany("INSERT INTO messages VALUES (?,?,?,?,?,?)", messages)
    
    calls = [
        ("cl1", "1234567890", "Me", 120, "2024-01-01 11:00:00", "incoming"),
        ("cl2", "9876543210", "Me", 30, "2024-01-02 13:50:00", "missed"),
    ]
    cursor.executemany("INSERT INTO calls VALUES (?,?,?,?,?,?)", calls)
    
    conn.commit()
    conn.close()
    logger.info(f"Created SQLite DB at {DB_PATH}")
    
    # 2. Index into ChromaDB
    store = FAISSStore()
    
    docs = []
    ids = []
    metadatas = []
    
    for c in contacts:
        text = f"Contact: {c[1]} | Number: {c[2]} | App: {c[3]}"
        docs.append(text)
        ids.append(f"doc_{c[0]}")
        metadatas.append({"case_id": CASE_ID, "data_type": "contact", "source": "dummy"})
        
    for m in messages:
        text = f"Message from {m[1]} to {m[2]}: {m[3]}"
        docs.append(text)
        ids.append(f"doc_{m[0]}")
        metadatas.append({"case_id": CASE_ID, "data_type": "message", "source": "dummy"})
        
    store.add_documents(case_id=CASE_ID, documents=docs, ids=ids, metadatas=metadatas)
    logger.info(f"Indexed {len(docs)} documents into ChromaDB for case {CASE_ID}")

if __name__ == "__main__":
    create_dummy_data()
