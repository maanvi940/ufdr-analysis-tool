"""Test for unified RAG query routing (detect_data_type + is_broad_query)."""
from rag.retriever import detect_data_type, is_broad_query

test_cases = [
    # (query, expected_data_type, expected_broad)
    ("show me contacts", "contact", True),
    ("contacts", "contact", True),
    ("list all messages", "message", True),
    ("show me calls", "call", True),
    ("contacts ending with A", "contact", True),       # filtered - goes to RAG
    ("messages about drugs", "message", False),         # semantic - RAG
    ("phone number 1234567890", "contact", False),      # RAG will handle
    ("who called last week?", "call", False),            # semantic - RAG
    ("show me photos", "media", True),
    ("suspicious activity", None, False),                # broad semantic
    ("location data", "location", True),
]

print(f"{'Query':<35} | {'Exp Type':<10} | {'Act Type':<10} | {'Exp Broad':<10} | {'Act Broad':<10} | {'Result'}")
print("-" * 100)

for query, exp_type, exp_broad in test_cases:
    act_type = detect_data_type(query)
    act_broad = is_broad_query(query)
    type_ok = act_type == exp_type
    broad_ok = act_broad == exp_broad
    result = "✅" if (type_ok and broad_ok) else "❌"
    print(f"{query:<35} | {str(exp_type):<10} | {str(act_type):<10} | {str(exp_broad):<10} | {str(act_broad):<10} | {result}")
