"""
seed_supabase.py
─────────────────
Generates NVIDIA embeddings for every patient_interaction row that
has a NULL embedding column, then writes them back to Supabase.

Run AFTER running supabase_schema.sql in the SQL Editor:
  uv run python seed_supabase.py
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

PLACEHOLDER = "YOUR_PROJECT_REF"
db_uri = os.environ.get("SUPABASE_DB_URI", "")

if not db_uri or PLACEHOLDER in db_uri:
    print("❌ SUPABASE_DB_URI is not set or still a placeholder. Update .env first.")
    sys.exit(1)

print("Initialising embedder (NVIDIA nv-embedqa-e5-v5)…")
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
embedder = NVIDIAEmbeddings(model="nvidia/nv-embedqa-e5-v5")

print("Connecting to Supabase…")
import psycopg
from pgvector.psycopg import register_vector

conn = psycopg.connect(db_uri)
register_vector(conn)

with conn:
    cur = conn.cursor()

    # Find all interactions without embeddings
    cur.execute(
        "SELECT id, notes FROM patient_interactions WHERE embedding IS NULL;"
    )
    rows = cur.fetchall()

    if not rows:
        print("✅ All interactions already have embeddings — nothing to do.")
        sys.exit(0)

    print(f"Found {len(rows)} interaction(s) without embeddings. Generating…")

    for row_id, notes in rows:
        embedding = embedder.embed_query(notes)
        cur.execute(
            "UPDATE patient_interactions SET embedding = %s WHERE id = %s;",
            (embedding, row_id)
        )
        print(f"  ✓ {row_id} — {notes[:60]}…")

    conn.commit()

print(f"\n✅ Done! {len(rows)} embedding(s) written to Supabase.\n")
