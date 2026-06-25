"""
database_mcp_server.py
───────────────────────
MCP server for Project Baymax patient data.

Exclusively uses Supabase/pgvector via asynchronous psycopg3.
Tools exposed via MCP (FastMCP / stdio):
  - get_patient_profile(patient_id)
  - search_interactions(patient_id, query, limit=3)
"""

import json
import os
import sys
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import List
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from dotenv import load_dotenv
import psycopg
from pgvector.psycopg import register_vector_async

load_dotenv()

# ── Embedder — lazy init so startup is instant (no API call on import) ───────
_embedder = None

def get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = NVIDIAEmbeddings(model="nvidia/nv-embedqa-e5-v5")
    return _embedder

# ── Ensure Supabase URI is set ──────────────────────────────────────────────
_db_uri = os.environ.get("SUPABASE_DB_URI", "")
if not _db_uri or "YOUR_PROJECT_REF" in _db_uri:
    print("[DB][ERROR] SUPABASE_DB_URI is missing or invalid in .env", file=sys.stderr, flush=True)

# ── Pydantic models ──────────────────────────────────────────────────────────
class PatientHistory(BaseModel):
    patient_id: str
    past_conditions: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    current_medications: List[str] = Field(default_factory=list)

class Interaction(BaseModel):
    date: str
    notes: str

class PatientProfile(BaseModel):
    patient_id: str
    name: str
    age: int
    history: PatientHistory
    past_interactions: List[Interaction] = Field(default_factory=list)

# ── Supabase Async Helpers ───────────────────────────────────────────────────
async def _get_supabase_conn():
    """Open an async psycopg3 connection with pgvector support registered."""
    print("[DB] Connecting to Supabase (Async)...", file=sys.stderr, flush=True)
    conn = await psycopg.AsyncConnection.connect(_db_uri, connect_timeout=10)
    await register_vector_async(conn)
    print("[DB] Connected OK.", file=sys.stderr, flush=True)
    return conn

# ── MCP server ───────────────────────────────────────────────────────────────
mcp = FastMCP("BaymaxDatabase")

@mcp.tool()
async def get_patient_profile(patient_id: str) -> str:
    """Retrieve patient profile (history, medications, allergies) as JSON."""
    if not _db_uri:
        return "{}"
        
    try:
        conn = await _get_supabase_conn()
        async with conn:
            async with conn.cursor() as cur:
                # Fetch main patient row
                await cur.execute(
                    "SELECT patient_id, name, age, past_conditions, allergies, current_medications "
                    "FROM patients WHERE patient_id = %s;",
                    (patient_id,)
                )
                row = await cur.fetchone()
                if not row:
                    return "{}"

                pid, name, age, conditions, allergies, meds = row

                # Fetch past interactions (no vector needed here)
                await cur.execute(
                    "SELECT interaction_date::text, notes "
                    "FROM patient_interactions "
                    "WHERE patient_id = %s "
                    "ORDER BY interaction_date;",
                    (patient_id,)
                )
                interactions_rows = await cur.fetchall()
                interactions = [{"date": r[0], "notes": r[1]} for r in interactions_rows]

                profile = {
                    "patient_id": pid,
                    "name": name,
                    "age": age,
                    "history": {
                        "patient_id": pid,
                        "past_conditions": list(conditions or []),
                        "allergies": list(allergies or []),
                        "current_medications": list(meds or []),
                    },
                    "past_interactions": interactions,
                }
                return json.dumps(profile)
    except Exception as e:
        print(f"[DB][Supabase] get_patient_profile error: {e}", file=sys.stderr, flush=True)
        return "{}"

@mcp.tool()
async def search_interactions(patient_id: str, query: str, limit: int = 3) -> str:
    """Semantic search over a patient's past interaction notes using embeddings."""
    if not _db_uri:
        return "[]"
        
    try:
        # Note: LangChain embedders are generally synchronous, run it directly
        query_embedding = get_embedder().embed_query(query)
        
        conn = await _get_supabase_conn()
        async with conn:
            async with conn.cursor() as cur:
                # Use cosine distance operator (<=>). Lower = more similar.
                await cur.execute(
                    """
                    SELECT interaction_date::text, notes
                    FROM patient_interactions
                    WHERE patient_id = %s AND embedding IS NOT NULL
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s;
                    """,
                    (patient_id, query_embedding, limit)
                )
                rows = await cur.fetchall()
                results = [{"date": r[0], "notes": r[1]} for r in rows]
                return json.dumps(results)
    except Exception as e:
        print(f"[DB][Supabase] search_interactions error: {e}", file=sys.stderr, flush=True)
        return "[]"

if __name__ == "__main__":
    mcp.run(transport='stdio')
