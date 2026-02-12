#!/usr/bin/env python3
"""
Generate Sample UFDR Files for Application Testing
Creates two comprehensive .ufdr files (ZIP archives containing SQLite databases)
that match the exact schema expected by the UFDR Analysis Tool.

Case 1: Drug Trafficking Investigation (Android) - CASE-2024-DT-001
Case 2: Cyber Fraud Network (iOS) - CASE-2024-CF-002

Both cases share some phone numbers/contacts for cross-case analysis testing.
"""

import sqlite3
import zipfile
import json
import hashlib
import os
import random
from pathlib import Path
from datetime import datetime, timedelta

# ============================================================================
# Shared data for cross-case linkage
# ============================================================================
SHARED_PHONES = {
    "Vikram Malhotra": "+91 98765 43210",
    "Crypto Wallet Handler": "+91 87654 32109",
    "Anonymous Tipster": "+91 76543 21098",
}

SHARED_EMAILS = {
    "Vikram Malhotra": "vikram.malhotra@protonmail.com",
    "Crypto Wallet Handler": "crypto_handler_x@tutanota.com",
}

def normalize_phone(phone: str) -> str:
    return ''.join(ch for ch in phone if ch.isdigit())

def phone_suffix(digits: str, length: int) -> str:
    return digits[-length:] if len(digits) >= length else ''

def sha256_of(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()

def make_msg_id(case: str, idx: int) -> str:
    return f"{case}-MSG-{idx:04d}"

def make_call_id(case: str, idx: int) -> str:
    return f"{case}-CALL-{idx:04d}"

def make_contact_id(case: str, idx: int) -> str:
    return f"{case}-CONTACT-{idx:04d}"

def make_media_id(case: str, idx: int) -> str:
    return f"{case}-MEDIA-{idx:04d}"

def make_location_id(case: str, idx: int) -> str:
    return f"{case}-LOC-{idx:04d}"

def iso(dt: datetime) -> str:
    return dt.isoformat()


# ============================================================================
# Case 1: Drug Trafficking Investigation (Android)
# ============================================================================
def create_case1_db(db_path: str):
    """Create the Drug Trafficking case database."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    CASE = "CASE-2024-DT-001"
    DEV = "DEV-ANDROID-001"
    base = datetime(2024, 6, 15, 8, 0, 0)

    # --- Schema (matches database/schema.py exactly) ---
    c.executescript("""
    CREATE TABLE IF NOT EXISTS cases (
        case_id TEXT PRIMARY KEY, ingest_time TEXT, source_file TEXT,
        sha256 TEXT, examiner TEXT, agency TEXT, notes TEXT
    );
    CREATE TABLE IF NOT EXISTS devices (
        device_id TEXT PRIMARY KEY, case_id TEXT NOT NULL,
        imei TEXT, serial_number TEXT, manufacturer TEXT, model TEXT,
        os_type TEXT, os_version TEXT, owner TEXT
    );
    CREATE TABLE IF NOT EXISTS contacts (
        contact_id TEXT PRIMARY KEY, case_id TEXT NOT NULL,
        name TEXT, phone_raw TEXT, phone_digits TEXT, phone_e164 TEXT,
        phone_suffix_2 TEXT, phone_suffix_4 TEXT, email TEXT
    );
    CREATE TABLE IF NOT EXISTS messages (
        msg_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, device_id TEXT,
        app TEXT, sender_raw TEXT, sender_digits TEXT,
        sender_suffix_2 TEXT, sender_suffix_4 TEXT,
        receiver_raw TEXT, receiver_digits TEXT,
        receiver_suffix_2 TEXT, receiver_suffix_4 TEXT,
        text TEXT, message_type TEXT, timestamp TEXT,
        encrypted INTEGER DEFAULT 0, is_deleted INTEGER DEFAULT 0,
        source_path TEXT
    );
    CREATE TABLE IF NOT EXISTS calls (
        call_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, device_id TEXT,
        caller_raw TEXT, caller_digits TEXT,
        caller_suffix_2 TEXT, caller_suffix_4 TEXT,
        receiver_raw TEXT, receiver_digits TEXT,
        receiver_suffix_2 TEXT, receiver_suffix_4 TEXT,
        timestamp TEXT, duration_seconds INTEGER, direction TEXT,
        source_path TEXT
    );
    CREATE TABLE IF NOT EXISTS media (
        media_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, device_id TEXT,
        filename TEXT, media_type TEXT, sha256 TEXT,
        phash TEXT, ocr_text TEXT, caption TEXT,
        timestamp TEXT, file_size INTEGER, source_path TEXT
    );
    CREATE TABLE IF NOT EXISTS locations (
        location_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, device_id TEXT,
        latitude REAL, longitude REAL, accuracy REAL, altitude REAL,
        timestamp TEXT, source_path TEXT
    );
    """)

    # --- Case metadata ---
    c.execute("INSERT INTO cases VALUES (?,?,?,?,?,?,?)", (
        CASE, iso(datetime.utcnow()), "sample_case_001.ufdr",
        sha256_of("drug_trafficking_case_001"),
        "Inspector Rajesh Kumar", "NCB Delhi",
        "Narcotics Control Bureau investigation into cross-border drug trafficking network operating via encrypted messaging apps."
    ))

    # --- Device ---
    c.execute("INSERT INTO devices VALUES (?,?,?,?,?,?,?,?,?)", (
        DEV, CASE, "354678901234567", "RZ8G903JXYZ",
        "Samsung", "Galaxy S23 Ultra", "Android", "14.0",
        "Arjun Patel (Suspect #1)"
    ))

    # --- Contacts (25) ---
    contacts = [
        ("Arjun Patel", "+91 99887 76655", "arjun.patel@gmail.com"),
        ("Vikram Malhotra", SHARED_PHONES["Vikram Malhotra"], SHARED_EMAILS["Vikram Malhotra"]),
        ("Crypto Wallet Handler", SHARED_PHONES["Crypto Wallet Handler"], SHARED_EMAILS["Crypto Wallet Handler"]),
        ("Anonymous Tipster", SHARED_PHONES["Anonymous Tipster"], None),
        ("Suresh Reddy", "+91 98321 45678", "s.reddy@yahoo.com"),
        ("Mohammad Farooq", "+91 97654 32100", None),
        ("Deepak Sharma", "+91 96543 21000", "deepak.s@hotmail.com"),
        ("Rita Verma", "+91 95432 10987", "rita.v@gmail.com"),
        ("Rahul Gupta", "+91 94321 09876", None),
        ("Priya Nair", "+91 93210 98765", "priya.nair@outlook.com"),
        ("Customs Contact", "+91 92109 87654", None),
        ("Lab Technician", "+91 91098 76543", "lab.tech@protonmail.com"),
        ("Transport Driver 1", "+91 89012 34567", None),
        ("Transport Driver 2", "+91 78901 23456", None),
        ("Warehouse Guard", "+91 67890 12345", None),
        ("Financial Advisor", "+91 56789 01234", "fin.adv@gmail.com"),
        ("Lawyer Contact", "+91 45678 90123", "legal.counsel@lawfirm.in"),
        ("Local Dealer Mumbai", "+91 34567 89012", None),
        ("Local Dealer Chennai", "+91 23456 78901", None),
        ("Local Dealer Kolkata", "+91 12345 67890", None),
        ("Sister - Personal", "+91 99001 12233", "sister@gmail.com"),
        ("Mother - Personal", "+91 99002 23344", None),
        ("Gym Trainer", "+91 99003 34455", None),
        ("Restaurant Owner", "+91 99004 45566", None),
        ("Unknown Number 1", "+91 99005 56677", None),
    ]
    for i, (name, phone, email) in enumerate(contacts):
        digits = normalize_phone(phone)
        c.execute("INSERT INTO contacts VALUES (?,?,?,?,?,?,?,?,?)", (
            make_contact_id(CASE, i), CASE, name, phone, digits,
            phone.replace(" ", ""), phone_suffix(digits, 2),
            phone_suffix(digits, 4), email
        ))

    # --- Messages (150) ---
    msgs = [
        (0, "WhatsApp", contacts[0][1], contacts[1][1], "Maal aa gaya hai. 50 kg. Godown mein rakh diya.", "text", 0, False, False),
        (1, "WhatsApp", contacts[1][1], contacts[0][1], "Theek hai. Payment ka kya hua?", "text", 5, False, False),
        (2, "WhatsApp", contacts[0][1], contacts[1][1], "Crypto se bhej raha hun. Wallet address bhejo.", "text", 8, False, False),
        (3, "WhatsApp", contacts[1][1], contacts[0][1], "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh", "text", 12, False, False),
        (4, "WhatsApp", contacts[0][1], contacts[2][1], "50 BTC transfer karo is address pe: bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh", "text", 30, True, False),
        (5, "WhatsApp", contacts[2][1], contacts[0][1], "Done. Transaction hash: 0x7a69f...", "text", 45, True, False),
        (6, "Signal", contacts[0][1], contacts[4][1], "Next shipment 20th June. Vizag port.", "text", 120, True, False),
        (7, "Signal", contacts[4][1], contacts[0][1], "Container number?", "text", 125, True, False),
        (8, "Signal", contacts[0][1], contacts[4][1], "MSKU-4827361. Blue container.", "text", 130, True, False),
        (9, "Telegram", contacts[0][1], contacts[5][1], "Mumbai delivery schedule ready. 25 packets.", "text", 200, False, False),
        (10, "Telegram", contacts[5][1], contacts[0][1], "Ok. Send driver to Dharavi at 11pm.", "text", 210, False, False),
        (11, "WhatsApp", contacts[0][1], contacts[12][1], "Pick up from Godown B, sector 14. Tonight 10pm.", "text", 250, False, False),
        (12, "WhatsApp", contacts[12][1], contacts[0][1], "Which truck to use?", "text", 255, False, False),
        (13, "WhatsApp", contacts[0][1], contacts[12][1], "MH-02-AB-1234. Don't stop anywhere.", "text", 260, False, False),
        (14, "SMS", contacts[0][1], contacts[10][1], "Package cleared customs. Thanks.", "text", 300, False, False),
        (15, "WhatsApp", contacts[0][1], contacts[6][1], "Quality check report bhejo.", "text", 350, False, False),
        (16, "WhatsApp", contacts[6][1], contacts[0][1], "92% purity. Best batch so far.", "text", 360, False, False),
        (17, "Signal", contacts[0][1], contacts[7][1], "Payment records delete karna. Audit aane wala hai.", "text", 400, True, True),
        (18, "Signal", contacts[7][1], contacts[0][1], "Done. All financial records wiped from system.", "text", 410, True, True),
        (19, "WhatsApp", contacts[0][1], contacts[17][1], "Mumbai batch ready. 15 packets. Usual spot.", "text", 500, False, False),
        (20, "WhatsApp", contacts[17][1], contacts[0][1], "Price same as last time?", "text", 505, False, False),
        (21, "WhatsApp", contacts[0][1], contacts[17][1], "5% increase. Market demand high.", "text", 510, False, False),
        (22, "WhatsApp", contacts[0][1], contacts[18][1], "Chennai batch shipping tomorrow. 20 packets.", "text", 600, False, False),
        (23, "WhatsApp", contacts[18][1], contacts[0][1], "Route through which highway?", "text", 610, False, False),
        (24, "WhatsApp", contacts[0][1], contacts[18][1], "NH-48 via Bangalore. Driver Raju.", "text", 620, False, False),
        (25, "Telegram", contacts[0][1], contacts[19][1], "Kolkata order ready. 10 packets.", "text", 700, False, False),
        (26, "Telegram", contacts[19][1], contacts[0][1], "Send via train. Less risky.", "text", 710, False, False),
        (27, "WhatsApp", contacts[0][1], contacts[20][1], "Happy birthday di! Will come home soon.", "text", 800, False, False),
        (28, "WhatsApp", contacts[20][1], contacts[0][1], "Thanks! Come visit when you can.", "text", 810, False, False),
        (29, "SMS", contacts[0][1], contacts[21][1], "Maa, paise bhej diye. ATM se nikal lena.", "text", 850, False, False),
        (30, "WhatsApp", contacts[0][1], contacts[11][1], "New formula test results?", "text", 900, False, False),
        (31, "WhatsApp", contacts[11][1], contacts[0][1], "Tests complete. Compound stable. Ready for production.", "text", 910, False, False),
        (32, "Signal", contacts[0][1], contacts[15][1], "Need to move 2 crore to Dubai account.", "text", 1000, True, False),
        (33, "Signal", contacts[15][1], contacts[0][1], "Hawala route through Jebel Ali. 3% commission.", "text", 1010, True, False),
        (34, "WhatsApp", contacts[0][1], contacts[16][1], "If police come, you know what to say.", "text", 1100, False, True),
        (35, "WhatsApp", contacts[16][1], contacts[0][1], "Everything is arranged. Don't worry.", "text", 1110, False, True),
        (36, "WhatsApp", contacts[0][1], contacts[8][1], "Meeting at Hotel Taj, room 505. Tomorrow 3pm.", "text", 1200, False, False),
        (37, "WhatsApp", contacts[8][1], contacts[0][1], "Confirmed. Will bring the samples.", "text", 1210, False, False),
        (38, "WhatsApp", contacts[0][1], contacts[9][1], "Accounts need to be cleaned before March.", "text", 1300, False, False),
        (39, "WhatsApp", contacts[9][1], contacts[0][1], "Will create shell companies. Need 3 weeks.", "text", 1310, False, False),
        (40, "Telegram", contacts[0][1], contacts[3][1], "Who gave you this number?", "text", 1400, False, False),
        (41, "Telegram", contacts[3][1], contacts[0][1], "I know about the Vizag shipment. We need to talk.", "text", 1410, False, False),
        (42, "Signal", contacts[0][1], contacts[1][1], "Someone knows about Vizag. Security breach.", "text", 1420, True, False),
        (43, "Signal", contacts[1][1], contacts[0][1], "Change all routes immediately. Use backup plan delta.", "text", 1425, True, False),
        (44, "WhatsApp", contacts[0][1], contacts[14][1], "Change all locks at warehouse. New codes tomorrow.", "text", 1500, False, False),
        (45, "WhatsApp", contacts[14][1], contacts[0][1], "Sir, done. New locks installed.", "text", 1510, False, False),
        (46, "WhatsApp", contacts[0][1], contacts[13][1], "New route: NH-44 via Hyderabad. Avoid toll plazas.", "text", 1600, False, False),
        (47, "WhatsApp", contacts[13][1], contacts[0][1], "When is next pickup?", "text", 1610, False, False),
        (48, "WhatsApp", contacts[0][1], contacts[13][1], "July 1st. Godown C this time.", "text", 1620, False, False),
        (49, "WhatsApp", contacts[0][1], contacts[22][1], "Can't come to gym this week. Busy.", "text", 1700, False, False),
    ]
    # Generate additional messages to reach 150
    apps = ["WhatsApp", "Telegram", "Signal", "SMS"]
    extra_texts = [
        "Payment received. Updating ledger.", "New batch arriving Friday.",
        "Route compromised. Switch to backup.", "Delivery confirmed at location B.",
        "Need 200 more pills by weekend.", "Lab results attached. See photo.",
        "Meeting postponed to next week.", "Police checkpoint on NH-48. Avoid.",
        "Transfer 5 lakhs to account ending 4521.", "Shipment delayed by 2 days.",
        "New supplier from Afghanistan confirmed.", "Quality is lower this time. 85%.",
        "Increase security at all warehouses.", "Driver arrested. Need replacement.",
        "Lawyers say bail is possible.", "Court date set for 15th July.",
        "Destroy all evidence at location C.", "New phone numbers for all team members.",
        "Profit this month: 1.5 crore.", "Expenses too high. Cut transport costs.",
        "New codes: Alpha-7, Bravo-3, Charlie-9.", "Border patrol schedule changed.",
        "Informant identified. Handle him.", "Money laundering audit next month.",
        "Hotel room booked under fake name.", "Flight to Dubai on 25th June.",
        "Passport ready. New identity.", "Surveillance cameras at godown working?",
        "Yes all 8 cameras operational.", "Fake invoices ready for tax filing.",
    ]
    for i in range(50, 150):
        sender_idx = random.randint(0, len(contacts)-1)
        receiver_idx = random.randint(0, len(contacts)-1)
        while receiver_idx == sender_idx:
            receiver_idx = random.randint(0, len(contacts)-1)
        text = random.choice(extra_texts)
        app = random.choice(apps)
        mins = 1700 + (i - 50) * random.randint(10, 60)
        encrypted = 1 if app in ["Signal", "Telegram"] else 0
        deleted = 1 if random.random() < 0.08 else 0
        msgs.append((i, app, contacts[sender_idx][1], contacts[receiver_idx][1],
                      text, "text", mins, encrypted, deleted))

    for (idx, app, sender, receiver, text, mtype, offset_min, enc, deld) in msgs:
        s_digits = normalize_phone(sender)
        r_digits = normalize_phone(receiver)
        ts = iso(base + timedelta(minutes=offset_min))
        c.execute("INSERT INTO messages VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            make_msg_id(CASE, idx), CASE, DEV, app,
            sender, s_digits, phone_suffix(s_digits, 2), phone_suffix(s_digits, 4),
            receiver, r_digits, phone_suffix(r_digits, 2), phone_suffix(r_digits, 4),
            text, mtype, ts, enc, deld,
            f"data/data/com.whatsapp/databases/msgstore.db"
        ))

    # --- Calls (60) ---
    call_data = []
    directions = ["incoming", "outgoing", "missed"]
    for i in range(60):
        caller_idx = random.randint(0, len(contacts)-1)
        receiver_idx = random.randint(0, len(contacts)-1)
        while receiver_idx == caller_idx:
            receiver_idx = random.randint(0, len(contacts)-1)
        dur = random.choice([0, 15, 30, 45, 60, 120, 180, 300, 600, 900, 1200])
        direction = random.choice(directions)
        if direction == "missed":
            dur = 0
        offset = random.randint(0, 20000)
        call_data.append((i, contacts[caller_idx][1], contacts[receiver_idx][1],
                          offset, dur, direction))

    for (idx, caller, receiver, offset, dur, direction) in call_data:
        ca_digits = normalize_phone(caller)
        re_digits = normalize_phone(receiver)
        ts = iso(base + timedelta(minutes=offset))
        c.execute("INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            make_call_id(CASE, idx), CASE, DEV,
            caller, ca_digits, phone_suffix(ca_digits, 2), phone_suffix(ca_digits, 4),
            receiver, re_digits, phone_suffix(re_digits, 2), phone_suffix(re_digits, 4),
            ts, dur, direction,
            "data/data/com.android.providers.contacts/databases/calllog.db"
        ))

    # --- Media (40) ---
    media_items = [
        ("warehouse_photo_01.jpg", "image", "Photo of warehouse interior with boxes", "Large warehouse with stacked boxes, dim lighting"),
        ("drug_sample_test.jpg", "image", "Lab test results showing 92% purity", "Chemical analysis report printed on white paper"),
        ("container_msku4827361.jpg", "image", "Blue shipping container at port", "MSKU-4827361 blue container at Vizag port"),
        ("cash_stack_002.jpg", "image", "Stack of 500 rupee notes", "Large stack of Indian currency, approx 5 lakhs"),
        ("meeting_hotel_taj.jpg", "image", "Hotel lobby photo", "Taj Hotel lobby, marble flooring"),
        ("route_map_nh48.jpg", "image", "Screenshot of Google Maps route", "NH-48 route from Mumbai to Bangalore highlighted"),
        ("evidence_bag_01.jpg", "image", "Sealed evidence bag with white powder", "Forensic evidence bag labeled Sample-A"),
        ("voice_recording_001.m4a", "audio", None, "Phone call recording, 3 minutes"),
        ("voice_recording_002.m4a", "audio", None, "Meeting recording, 15 minutes"),
        ("surveillance_cam_01.mp4", "video", None, "Warehouse camera footage, night"),
        ("surveillance_cam_02.mp4", "video", None, "Godown entrance camera footage"),
        ("ledger_scan_01.pdf", "document", "Financial records Jan-Mar 2024", "Scanned handwritten ledger"),
        ("ledger_scan_02.pdf", "document", "Financial records Apr-Jun 2024", "Scanned accounting book"),
        ("fake_invoice_template.pdf", "document", "Invoice template for shell company", "Template with company letterhead"),
        ("passport_scan.jpg", "image", "Fake passport photo page", "Indian passport, potentially forged"),
        ("crypto_wallet_screenshot.jpg", "image", "Bitcoin wallet with 50 BTC balance", "Trust Wallet screenshot showing balance"),
    ]
    # Add more
    for i in range(16, 40):
        media_items.append((
            f"evidence_photo_{i:03d}.jpg", "image",
            f"Crime scene photo #{i}", f"Investigation photo taken at location {i}"
        ))

    for i, (fname, mtype, ocr, caption) in enumerate(media_items):
        ts = iso(base + timedelta(hours=random.randint(0, 300)))
        fsize = random.randint(50000, 15000000)
        c.execute("INSERT INTO media VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
            make_media_id(CASE, i), CASE, DEV, fname, mtype,
            sha256_of(f"{CASE}-{fname}-{i}"),
            hashlib.md5(f"{fname}-{i}".encode()).hexdigest()[:16],
            ocr, caption, ts, fsize,
            f"sdcard/DCIM/Camera/{fname}"
        ))

    # --- Locations (80) ---
    # Track movement across India
    locations_track = [
        (19.0760, 72.8777, "Mumbai"),      # Start
        (19.0176, 72.8562, "Dharavi"),
        (18.5204, 73.8567, "Pune"),
        (17.3850, 78.4867, "Hyderabad"),
        (13.0827, 80.2707, "Chennai"),
        (12.9716, 77.5946, "Bangalore"),
        (17.6868, 83.2185, "Visakhapatnam"),
        (22.5726, 88.3639, "Kolkata"),
        (28.7041, 77.1025, "Delhi"),
        (19.0760, 72.8777, "Mumbai"),      # Return
    ]
    for i in range(80):
        loc_idx = i % len(locations_track)
        lat, lon, _ = locations_track[loc_idx]
        # Add small random offset for realism
        lat += random.uniform(-0.02, 0.02)
        lon += random.uniform(-0.02, 0.02)
        ts = iso(base + timedelta(hours=i * 4))
        c.execute("INSERT INTO locations VALUES (?,?,?,?,?,?,?,?,?)", (
            make_location_id(CASE, i), CASE, DEV,
            round(lat, 6), round(lon, 6),
            round(random.uniform(3.0, 25.0), 1),
            round(random.uniform(0, 50), 1),
            ts, "com.google.android.gms"
        ))

    conn.commit()
    conn.close()
    print(f"  ✅ Case 1 DB: {c.rowcount} total operations")


# ============================================================================
# Case 2: Cyber Fraud Network (iOS)
# ============================================================================
def create_case2_db(db_path: str):
    """Create the Cyber Fraud case database."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    CASE = "CASE-2024-CF-002"
    DEV = "DEV-IOS-002"
    base = datetime(2024, 7, 1, 10, 0, 0)

    # Same schema
    c.executescript("""
    CREATE TABLE IF NOT EXISTS cases (
        case_id TEXT PRIMARY KEY, ingest_time TEXT, source_file TEXT,
        sha256 TEXT, examiner TEXT, agency TEXT, notes TEXT
    );
    CREATE TABLE IF NOT EXISTS devices (
        device_id TEXT PRIMARY KEY, case_id TEXT NOT NULL,
        imei TEXT, serial_number TEXT, manufacturer TEXT, model TEXT,
        os_type TEXT, os_version TEXT, owner TEXT
    );
    CREATE TABLE IF NOT EXISTS contacts (
        contact_id TEXT PRIMARY KEY, case_id TEXT NOT NULL,
        name TEXT, phone_raw TEXT, phone_digits TEXT, phone_e164 TEXT,
        phone_suffix_2 TEXT, phone_suffix_4 TEXT, email TEXT
    );
    CREATE TABLE IF NOT EXISTS messages (
        msg_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, device_id TEXT,
        app TEXT, sender_raw TEXT, sender_digits TEXT,
        sender_suffix_2 TEXT, sender_suffix_4 TEXT,
        receiver_raw TEXT, receiver_digits TEXT,
        receiver_suffix_2 TEXT, receiver_suffix_4 TEXT,
        text TEXT, message_type TEXT, timestamp TEXT,
        encrypted INTEGER DEFAULT 0, is_deleted INTEGER DEFAULT 0,
        source_path TEXT
    );
    CREATE TABLE IF NOT EXISTS calls (
        call_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, device_id TEXT,
        caller_raw TEXT, caller_digits TEXT,
        caller_suffix_2 TEXT, caller_suffix_4 TEXT,
        receiver_raw TEXT, receiver_digits TEXT,
        receiver_suffix_2 TEXT, receiver_suffix_4 TEXT,
        timestamp TEXT, duration_seconds INTEGER, direction TEXT,
        source_path TEXT
    );
    CREATE TABLE IF NOT EXISTS media (
        media_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, device_id TEXT,
        filename TEXT, media_type TEXT, sha256 TEXT,
        phash TEXT, ocr_text TEXT, caption TEXT,
        timestamp TEXT, file_size INTEGER, source_path TEXT
    );
    CREATE TABLE IF NOT EXISTS locations (
        location_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, device_id TEXT,
        latitude REAL, longitude REAL, accuracy REAL, altitude REAL,
        timestamp TEXT, source_path TEXT
    );
    """)

    # --- Case ---
    c.execute("INSERT INTO cases VALUES (?,?,?,?,?,?,?)", (
        CASE, iso(datetime.utcnow()), "sample_case_002.ufdr",
        sha256_of("cyber_fraud_case_002"),
        "Sub-Inspector Meera Krishnan", "CBI Cyber Cell Bangalore",
        "Cyber fraud investigation into a network conducting phishing, identity theft, and cryptocurrency laundering. Linked to CASE-2024-DT-001 via shared contacts."
    ))

    # --- Device ---
    c.execute("INSERT INTO devices VALUES (?,?,?,?,?,?,?,?,?)", (
        DEV, CASE, "356789012345678", "F2LXKF3JKLMN",
        "Apple", "iPhone 15 Pro Max", "iOS", "17.4",
        "Neha Sharma (Suspect #2)"
    ))

    # --- Contacts (30) ---
    contacts = [
        ("Neha Sharma", "+91 88776 65544", "neha.sharma.tech@gmail.com"),
        ("Vikram Malhotra", SHARED_PHONES["Vikram Malhotra"], SHARED_EMAILS["Vikram Malhotra"]),
        ("Crypto Wallet Handler", SHARED_PHONES["Crypto Wallet Handler"], SHARED_EMAILS["Crypto Wallet Handler"]),
        ("Anonymous Tipster", SHARED_PHONES["Anonymous Tipster"], None),
        ("Amit Joshi (Hacker)", "+91 77665 54433", "amitj_darkweb@protonmail.com"),
        ("Sanjay Rao (Phishing)", "+91 66554 43322", "sanjay.r@tutanota.com"),
        ("Bank Insider", "+91 55443 32211", None),
        ("Fake ID Maker", "+91 44332 21100", "ids.unlimited@protonmail.com"),
        ("Crypto Exchange Contact", "+91 33221 10099", "exchange.ops@mail.com"),
        ("Money Mule 1", "+91 22110 09988", None),
        ("Money Mule 2", "+91 11009 98877", None),
        ("Money Mule 3", "+91 10098 87766", None),
        ("Victim - Rajesh Gupta", "+91 99111 22233", "rajesh.g@corporate.com"),
        ("Victim - Anita Desai", "+91 99222 33344", "anita.d@business.com"),
        ("Victim - Prakash Mehta", "+91 99333 44455", "p.mehta@company.com"),
        ("Victim - Sunita Jain", "+91 99444 55566", "sunita.j@enterprise.com"),
        ("Victim - Kunal Shah", "+91 99555 66677", "kunal.shah@startup.com"),
        ("Server Admin", "+91 88111 22233", "sysadmin@darkhost.onion"),
        ("Domain Registrar", "+91 88222 33344", "domains@privacy.reg"),
        ("VPN Provider", "+91 88333 44455", None),
        ("Forex Trader", "+91 88444 55566", "forexking@trading.com"),
        ("Real Estate Agent", "+91 88555 66677", "realestate@properties.in"),
        ("Jewelry Shop Owner", "+91 88666 77788", None),
        ("Car Dealer", "+91 88777 88899", "luxurycars@dealer.in"),
        ("College Friend", "+91 88888 99900", "oldfriend@college.edu"),
        ("Mother", "+91 88999 00011", None),
        ("Father", "+91 89000 11122", None),
        ("Brother", "+91 89111 22233", None),
        ("Hairdresser", "+91 89222 33344", None),
        ("Gym Instructor", "+91 89333 44455", None),
    ]
    for i, (name, phone, email) in enumerate(contacts):
        digits = normalize_phone(phone)
        c.execute("INSERT INTO contacts VALUES (?,?,?,?,?,?,?,?,?)", (
            make_contact_id(CASE, i), CASE, name, phone, digits,
            phone.replace(" ", ""), phone_suffix(digits, 2),
            phone_suffix(digits, 4), email
        ))

    # --- Messages (200) ---
    hand_msgs = [
        (0, "iMessage", contacts[0][1], contacts[4][1], "New phishing kit ready. Targets HDFC and SBI customers.", "text", 0, False, False),
        (1, "iMessage", contacts[4][1], contacts[0][1], "Clone sites deployed on 15 domains. All SSL certified.", "text", 10, False, False),
        (2, "iMessage", contacts[0][1], contacts[5][1], "Send 50,000 emails to the harvested list today.", "text", 30, False, False),
        (3, "iMessage", contacts[5][1], contacts[0][1], "Done. Using compromised SMTP servers.", "text", 40, False, False),
        (4, "WhatsApp", contacts[0][1], contacts[1][1], "Vikram, need to launder 80 lakhs this week.", "text", 60, False, False),
        (5, "WhatsApp", contacts[1][1], contacts[0][1], "Use the usual crypto route. I'll arrange the wallets.", "text", 65, False, False),
        (6, "Signal", contacts[0][1], contacts[2][1], "Convert 80 lakhs INR to BTC. Split across 5 wallets.", "text", 80, True, False),
        (7, "Signal", contacts[2][1], contacts[0][1], "Rate today: 1 BTC = 55 lakhs. You'll get ~1.45 BTC.", "text", 85, True, False),
        (8, "Telegram", contacts[0][1], contacts[6][1], "Need account details of 100 high-value customers.", "text", 120, False, False),
        (9, "Telegram", contacts[6][1], contacts[0][1], "Sending file. Accounts with 10L+ balance only.", "text", 130, False, False),
        (10, "WhatsApp", contacts[0][1], contacts[7][1], "Need 20 Aadhaar cards and 20 PAN cards. Different names.", "text", 200, False, False),
        (11, "WhatsApp", contacts[7][1], contacts[0][1], "2000 per set. Ready in 3 days.", "text", 210, False, False),
        (12, "iMessage", contacts[0][1], contacts[8][1], "Register 10 new accounts on WazirX with fake IDs.", "text", 300, False, False),
        (13, "iMessage", contacts[8][1], contacts[0][1], "KYC verification taking time. Using deepfake videos.", "text", 310, False, False),
        (14, "WhatsApp", contacts[0][1], contacts[9][1], "Open 5 bank accounts. Use the new Aadhaar cards.", "text", 400, False, False),
        (15, "WhatsApp", contacts[9][1], contacts[0][1], "Which banks? SBI and HDFC?", "text", 410, False, False),
        (16, "WhatsApp", contacts[0][1], contacts[9][1], "Yes. 2 SBI, 2 HDFC, 1 Axis.", "text", 415, False, False),
        (17, "iMessage", contacts[12][1], contacts[0][1], "My account was hacked! 5 lakhs missing!", "text", 500, False, False),
        (18, "iMessage", contacts[0][1], contacts[4][1], "Another victim reported. Need to rotate servers.", "text", 510, False, False),
        (19, "WhatsApp", contacts[13][1], contacts[0][1], "Who are you? Why did I get email from SBI?", "text", 600, False, False),
        (20, "Signal", contacts[0][1], contacts[1][1], "Revenue this month: 45 lakhs. Your cut is 15 lakhs.", "text", 700, True, False),
        (21, "Signal", contacts[1][1], contacts[0][1], "Send to the Dubai account as usual.", "text", 710, True, False),
        (22, "Telegram", contacts[0][1], contacts[17][1], "Migrate all servers to new hosting. FBI monitoring old ones.", "text", 800, False, False),
        (23, "Telegram", contacts[17][1], contacts[0][1], "Moving to bulletproof hosting in Moldova.", "text", 810, False, False),
        (24, "WhatsApp", contacts[0][1], contacts[20][1], "Convert 20 lakhs to USD via forex.", "text", 900, False, False),
        (25, "WhatsApp", contacts[20][1], contacts[0][1], "Current rate 83.5. Commission 2%.", "text", 910, False, False),
        (26, "WhatsApp", contacts[0][1], contacts[21][1], "Book a flat under Priya Enterprises Pvt Ltd.", "text", 1000, False, False),
        (27, "WhatsApp", contacts[21][1], contacts[0][1], "3BHK in Whitefield. 1.2 crore. Cash acceptable.", "text", 1010, False, False),
        (28, "WhatsApp", contacts[0][1], contacts[22][1], "Buy 500 grams gold. Invoice under different name.", "text", 1100, False, False),
        (29, "WhatsApp", contacts[0][1], contacts[23][1], "Book a Range Rover Velar. Cash payment.", "text", 1200, False, False),
        (30, "Signal", contacts[0][1], contacts[4][1], "New ransomware variant ready. Targets healthcare sector.", "text", 1300, True, True),
        (31, "Signal", contacts[4][1], contacts[0][1], "Deploying on 500 targets. Ransom: 2 BTC each.", "text", 1310, True, True),
        (32, "iMessage", contacts[0][1], contacts[25][1], "Amma, I'm doing well. Don't worry.", "text", 1400, False, False),
        (33, "iMessage", contacts[25][1], contacts[0][1], "Beta, come home for Diwali.", "text", 1410, False, False),
        (34, "WhatsApp", contacts[14][1], contacts[0][1], "My company account compromised. 12 lakhs stolen.", "text", 1500, False, False),
        (35, "WhatsApp", contacts[15][1], contacts[0][1], "Fraudulent transaction on my credit card. 3 lakhs.", "text", 1600, False, False),
        (36, "Telegram", contacts[0][1], contacts[10][1], "Withdraw 5 lakhs from SBI Koramangala branch.", "text", 1700, False, False),
        (37, "Telegram", contacts[0][1], contacts[11][1], "Withdraw 5 lakhs from HDFC MG Road branch.", "text", 1710, False, False),
        (38, "Signal", contacts[0][1], contacts[18][1], "Register 50 new domains. Banking theme.", "text", 1800, True, False),
        (39, "Signal", contacts[18][1], contacts[0][1], "Using .in and .co.in TLDs. Harder to trace.", "text", 1810, True, False),
    ]

    # Generate more messages to reach 200
    extra_texts_cf = [
        "Phishing page conversion rate: 12%. Need to improve.",
        "New victim list: 5000 email addresses.", "SIM cards ready. 50 pre-activated.",
        "Deepfake video ready for KYC bypass.", "Server logs cleaned. No traces.",
        "New malware payload compiled. Undetectable by top 5 AV.",
        "Bank OTPs intercepted successfully.", "Two-factor bypass working.",
        "Customer database from dark web forum. 100K records.",
        "Cryptocurrency mixer started. 48-hour delay.", "ATM skimmer installed at 3 locations.",
        "Social engineering training for new recruits.", "Keylogger deployed on target systems.",
        "VPN logs purged. Using Tor for all ops now.", "New shell company registered in Mauritius.",
        "Hawala transfer to Hong Kong complete.", "Diamond purchase for asset conversion.",
        "Tax returns filed under fake identities.", "Call center team trained. 20 operators.",
        "IVR system mimicking SBI helpline ready.", "Spoofed SMS gateway operational.",
        "Password spray attack on corporate targets.", "SQL injection found on bank portal.",
        "Credentials harvested: 2000 banking logins.", "Botnet expanded to 10,000 nodes.",
        "DDoS capability: 500 Gbps.", "Ransomware payment received: 5 BTC.",
    ]
    for i in range(40, 200):
        s_idx = random.randint(0, len(contacts)-1)
        r_idx = random.randint(0, len(contacts)-1)
        while r_idx == s_idx:
            r_idx = random.randint(0, len(contacts)-1)
        text = random.choice(extra_texts_cf)
        app = random.choice(["iMessage", "WhatsApp", "Telegram", "Signal"])
        mins = 1800 + (i - 40) * random.randint(5, 45)
        enc = 1 if app in ["Signal"] else 0
        deld = 1 if random.random() < 0.06 else 0
        hand_msgs.append((i, app, contacts[s_idx][1], contacts[r_idx][1],
                          text, "text", mins, enc, deld))

    for (idx, app, sender, receiver, text, mtype, offset_min, enc, deld) in hand_msgs:
        s_digits = normalize_phone(sender)
        r_digits = normalize_phone(receiver)
        ts = iso(base + timedelta(minutes=offset_min))
        c.execute("INSERT INTO messages VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            make_msg_id(CASE, idx), CASE, DEV, app,
            sender, s_digits, phone_suffix(s_digits, 2), phone_suffix(s_digits, 4),
            receiver, r_digits, phone_suffix(r_digits, 2), phone_suffix(r_digits, 4),
            text, mtype, ts, enc, deld,
            "private/var/mobile/Library/SMS/sms.db"
        ))

    # --- Calls (50) ---
    for i in range(50):
        c_idx = random.randint(0, len(contacts)-1)
        r_idx = random.randint(0, len(contacts)-1)
        while r_idx == c_idx:
            r_idx = random.randint(0, len(contacts)-1)
        dur = random.choice([0, 10, 30, 60, 120, 300, 600])
        direction = random.choice(["incoming", "outgoing", "missed"])
        if direction == "missed": dur = 0
        offset = random.randint(0, 15000)
        ca_d = normalize_phone(contacts[c_idx][1])
        re_d = normalize_phone(contacts[r_idx][1])
        ts = iso(base + timedelta(minutes=offset))
        c.execute("INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            make_call_id(CASE, i), CASE, DEV,
            contacts[c_idx][1], ca_d, phone_suffix(ca_d, 2), phone_suffix(ca_d, 4),
            contacts[r_idx][1], re_d, phone_suffix(re_d, 2), phone_suffix(re_d, 4),
            ts, dur, direction,
            "private/var/mobile/Library/CallHistoryDB/CallHistory.storedata"
        ))

    # --- Media (35) ---
    media_items_cf = [
        ("phishing_site_screenshot.jpg", "image", "HDFC Bank login page clone", "Fake HDFC bank website"),
        ("victim_credentials_list.jpg", "image", "Spreadsheet with stolen credentials", "Excel with usernames and passwords"),
        ("crypto_wallets_overview.jpg", "image", "Multiple Bitcoin wallet balances", "Dashboard showing 5 wallets"),
        ("fake_aadhaar_sample.jpg", "image", "Forged Aadhaar card", "Name: Priya Mehta, fake details"),
        ("server_dashboard.jpg", "image", "Phishing server admin panel", "C2 server dashboard with stats"),
        ("money_trail_diagram.jpg", "image", "Flowchart of money movement", "Handwritten money laundering flowchart"),
        ("dark_web_forum_post.jpg", "image", "Forum post selling bank data", "Dark web marketplace listing"),
        ("ransomware_note.jpg", "image", "Ransomware payment demand screen", "Your files have been encrypted"),
        ("gold_purchase_receipt.jpg", "image", "Jewelry store receipt", "500g gold purchase from Tanishq"),
        ("property_agreement.pdf", "document", "Sale deed for flat in Whitefield", "Property document under shell company"),
        ("call_recording_victim.m4a", "audio", None, "Call with victim impersonating bank"),
        ("training_video_phishing.mp4", "video", None, "Social engineering training video"),
        ("malware_demo.mp4", "video", None, "Ransomware demonstration video"),
    ]
    for i in range(13, 35):
        media_items_cf.append((
            f"evidence_{i:03d}.jpg", "image",
            f"Digital forensic evidence #{i}", f"Extracted screenshot #{i}"
        ))

    for i, (fname, mtype, ocr, caption) in enumerate(media_items_cf):
        ts = iso(base + timedelta(hours=random.randint(0, 250)))
        fsize = random.randint(30000, 12000000)
        c.execute("INSERT INTO media VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
            make_media_id(CASE, i), CASE, DEV, fname, mtype,
            sha256_of(f"{CASE}-{fname}-{i}"),
            hashlib.md5(f"{fname}-cf-{i}".encode()).hexdigest()[:16],
            ocr, caption, ts, fsize,
            f"private/var/mobile/Media/DCIM/{fname}"
        ))

    # --- Locations (60) ---
    locations_cf = [
        (12.9716, 77.5946, "Bangalore"),
        (12.9352, 77.6245, "Koramangala"),
        (12.9698, 77.7500, "Whitefield"),
        (13.0827, 80.2707, "Chennai"),
        (19.0760, 72.8777, "Mumbai"),
        (28.7041, 77.1025, "Delhi"),
        (25.2048, 55.2708, "Dubai"),
        (12.9716, 77.5946, "Bangalore"),
    ]
    for i in range(60):
        loc_idx = i % len(locations_cf)
        lat, lon, _ = locations_cf[loc_idx]
        lat += random.uniform(-0.015, 0.015)
        lon += random.uniform(-0.015, 0.015)
        ts = iso(base + timedelta(hours=i * 5))
        c.execute("INSERT INTO locations VALUES (?,?,?,?,?,?,?,?,?)", (
            make_location_id(CASE, i), CASE, DEV,
            round(lat, 6), round(lon, 6),
            round(random.uniform(5.0, 30.0), 1),
            round(random.uniform(800, 920), 1),
            ts, "com.apple.locationd"
        ))

    conn.commit()
    conn.close()
    print(f"  ✅ Case 2 DB created")


# ============================================================================
# Package into UFDR (ZIP) files
# ============================================================================
def package_ufdr(db_path: str, ufdr_path: str, case_id: str, manifest: dict):
    """Package a SQLite DB into a .ufdr ZIP archive with manifest."""
    with zipfile.ZipFile(ufdr_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add the database
        zf.write(db_path, "forensic_data.db")

        # Add manifest
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        # Add README
        readme = f"""# UFDR Sample File - {case_id}
Generated for testing the UFDR Analysis Tool.
Contains synthetic forensic data for demonstration purposes only.

## Contents
- forensic_data.db: SQLite database with case data
- manifest.json: Case metadata and file inventory
- report.xml: Basic extraction report

## Tables
- cases: Case metadata
- devices: Device information
- contacts: Contact list with normalized phone numbers
- messages: SMS, WhatsApp, Telegram, Signal messages
- calls: Call history with duration and direction
- media: Media files metadata with hashes
- locations: GPS/location tracking data

## Cross-Case Linkage
This file shares contacts with other sample cases for
cross-case analysis testing.
"""
        zf.writestr("README.txt", readme)

        # Add a basic XML report
        report_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<extraction>
    <case_id>{case_id}</case_id>
    <extraction_date>{datetime.utcnow().isoformat()}</extraction_date>
    <tool>UFDR Analysis Tool - Sample Generator</tool>
    <device>
        <manufacturer>{manifest['device']['manufacturer']}</manufacturer>
        <model>{manifest['device']['model']}</model>
        <os>{manifest['device']['os_type']} {manifest['device']['os_version']}</os>
    </device>
    <statistics>
        <contacts>{manifest['statistics']['contacts']}</contacts>
        <messages>{manifest['statistics']['messages']}</messages>
        <calls>{manifest['statistics']['calls']}</calls>
        <media>{manifest['statistics']['media']}</media>
        <locations>{manifest['statistics']['locations']}</locations>
    </statistics>
</extraction>
"""
        zf.writestr("report.xml", report_xml)

    # Clean up temp DB
    os.remove(db_path)
    size_mb = os.path.getsize(ufdr_path) / (1024 * 1024)
    print(f"  📦 {ufdr_path} ({size_mb:.2f} MB)")


# ============================================================================
# Main
# ============================================================================
def main():
    output_dir = Path(__file__).parent
    output_dir.mkdir(exist_ok=True)

    print("=" * 60)
    print("🔧 Generating Sample UFDR Files")
    print("=" * 60)

    # --- Case 1 ---
    print("\n📁 Case 1: Drug Trafficking Investigation")
    db1 = str(output_dir / "_temp_case1.db")
    create_case1_db(db1)
    package_ufdr(db1, str(output_dir / "sample_case_001.ufdr"), "CASE-2024-DT-001", {
        "case_id": "CASE-2024-DT-001",
        "title": "Drug Trafficking Network Investigation",
        "examiner": "Inspector Rajesh Kumar",
        "agency": "NCB Delhi",
        "device": {
            "manufacturer": "Samsung", "model": "Galaxy S23 Ultra",
            "os_type": "Android", "os_version": "14.0",
            "imei": "354678901234567", "owner": "Arjun Patel"
        },
        "statistics": {
            "contacts": 25, "messages": 150, "calls": 60,
            "media": 40, "locations": 80
        },
        "cross_case_links": ["CASE-2024-CF-002"]
    })

    # --- Case 2 ---
    print("\n📁 Case 2: Cyber Fraud Network Investigation")
    db2 = str(output_dir / "_temp_case2.db")
    create_case2_db(db2)
    package_ufdr(db2, str(output_dir / "sample_case_002.ufdr"), "CASE-2024-CF-002", {
        "case_id": "CASE-2024-CF-002",
        "title": "Cyber Fraud Network Investigation",
        "examiner": "Sub-Inspector Meera Krishnan",
        "agency": "CBI Cyber Cell Bangalore",
        "device": {
            "manufacturer": "Apple", "model": "iPhone 15 Pro Max",
            "os_type": "iOS", "os_version": "17.4",
            "imei": "356789012345678", "owner": "Neha Sharma"
        },
        "statistics": {
            "contacts": 30, "messages": 200, "calls": 50,
            "media": 35, "locations": 60
        },
        "cross_case_links": ["CASE-2024-DT-001"]
    })

    print("\n" + "=" * 60)
    print("✅ Done! Files created in: " + str(output_dir))
    print("=" * 60)
    print("\nShared contacts between cases:")
    for name, phone in SHARED_PHONES.items():
        print(f"  • {name}: {phone}")
    print("\nUpload these files via the UFDR Analysis Tool UI to test.")


if __name__ == "__main__":
    main()
