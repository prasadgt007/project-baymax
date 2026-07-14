"""
database_mcp_server.py
───────────────────────
MCP server for Project Baymax patient data.

Uses Supabase/pgvector via asynchronous psycopg3.
Tools exposed via MCP (FastMCP / stdio):

  Patient data:
    - get_patient_profile(patient_id)
    - search_interactions(patient_id, query, limit=3)
    - search_patient_documents(patient_id, query, limit=5)
    - initialize_patient_session(patient_id)

  Document ingestion (hospital employees only — enforced at server.py layer):
    - ingest_document(patient_id, text_content, document_type)

  Appointment scheduling:
    - get_available_slots(date)
    - book_slot(slot_id, patient_id)
"""

import json
import os
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import List
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from dotenv import load_dotenv
import psycopg
from pgvector.psycopg import register_vector_async

load_dotenv()

# ── Embedder (lazy init) ─────────────────────────────────────────────────────
_embedder = None


def get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = NVIDIAEmbeddings(model="nvidia/nv-embedqa-e5-v5")
    return _embedder


# ── DB URI guard ─────────────────────────────────────────────────────────────
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


# ── Supabase async connection ────────────────────────────────────────────────
async def _get_supabase_conn():
    """Open an async psycopg3 connection with pgvector support registered."""
    print("[DB] Connecting to Supabase (Async)...", file=sys.stderr, flush=True)
    conn = await psycopg.AsyncConnection.connect(_db_uri, connect_timeout=10)
    await register_vector_async(conn)
    print("[DB] Connected OK.", file=sys.stderr, flush=True)
    return conn


# ── MCP server ───────────────────────────────────────────────────────────────
mcp = FastMCP("BaymaxDatabase")


# ────────────────────────────────────────────────────────────────────────────
# Tool 1: get_patient_profile
# ────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def get_patient_profile(patient_id: str) -> str:
    """Retrieve patient profile (history, medications, allergies) as JSON."""
    if not _db_uri:
        return "{}"

    try:
        conn = await _get_supabase_conn()
        async with conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT patient_id, name, age, past_conditions, allergies, current_medications "
                    "FROM patients WHERE patient_id = %s;",
                    (patient_id,),
                )
                row = await cur.fetchone()
                if not row:
                    return "{}"

                pid, name, age, conditions, allergies, meds = row

                await cur.execute(
                    "SELECT interaction_date::text, notes "
                    "FROM patient_interactions "
                    "WHERE patient_id = %s "
                    "ORDER BY interaction_date;",
                    (patient_id,),
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


# ────────────────────────────────────────────────────────────────────────────
# Tool 2: search_interactions
# ────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def search_interactions(patient_id: str, query: str, limit: int = 3) -> str:
    """Semantic search over a patient's past interaction notes using pgvector embeddings."""
    if not _db_uri:
        return "[]"

    try:
        query_embedding = get_embedder().embed_query(query)

        conn = await _get_supabase_conn()
        async with conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT interaction_date::text, notes
                    FROM patient_interactions
                    WHERE patient_id = %s AND embedding IS NOT NULL
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s;
                    """,
                    (patient_id, query_embedding, limit),
                )
                rows = await cur.fetchall()
                results = [{"date": r[0], "notes": r[1]} for r in rows]
                return json.dumps(results)
    except Exception as e:
        print(f"[DB][Supabase] search_interactions error: {e}", file=sys.stderr, flush=True)
        return "[]"


# ────────────────────────────────────────────────────────────────────────────
# Tool 3: search_patient_documents  (NEW — vector search over typed docs)
# ────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def search_patient_documents(patient_id: str, query: str, limit: int = 5) -> str:
    """
    Semantic vector search over a patient's uploaded documents
    (reports, x-rays, blood tests, prescriptions) in the patient_documents table.
    Returns JSON array: [{id, document_type, content_text, created_at}]
    """
    if not _db_uri:
        return "[]"

    try:
        query_embedding = get_embedder().embed_query(query)

        conn = await _get_supabase_conn()
        async with conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id::text, document_type::text, content_text, created_at::text
                    FROM patient_documents
                    WHERE patient_id = %s AND embedding IS NOT NULL
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s;
                    """,
                    (patient_id, query_embedding, limit),
                )
                rows = await cur.fetchall()
                results = [
                    {
                        "id": r[0],
                        "document_type": r[1],
                        "content_text": r[2][:2000],  # Enough for lab values & prescriptions
                        "created_at": r[3],
                    }
                    for r in rows
                ]
                return json.dumps(results)
    except Exception as e:
        print(f"[DB][Supabase] search_patient_documents error: {e}", file=sys.stderr, flush=True)
        return "[]"


# ────────────────────────────────────────────────────────────────────────────
# Tool 4: initialize_patient_session  (NEW — proactive context loading)
# ────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def initialize_patient_session(patient_id: str) -> str:
    """
    Fetch baseline data for a patient at session start:
      - Profile (name, age, conditions, allergies, medications)
      - Recent documents (last 3 from patient_documents)
      - Next upcoming appointment slot (if any)

    Returns a JSON object with {profile, baseline_documents, upcoming_slot}.
    """
    if not _db_uri:
        return json.dumps({"profile": None, "baseline_documents": [], "upcoming_slot": None})

    try:
        conn = await _get_supabase_conn()
        async with conn:
            async with conn.cursor() as cur:
                # 1. Patient profile
                await cur.execute(
                    "SELECT patient_id, name, age, past_conditions, allergies, current_medications "
                    "FROM patients WHERE patient_id = %s;",
                    (patient_id,),
                )
                row = await cur.fetchone()
                if not row:
                    return json.dumps({"profile": None, "baseline_documents": [], "upcoming_slot": None})

                pid, name, age, conditions, allergies, meds = row
                profile = {
                    "patient_id": pid,
                    "name": name,
                    "age": age,
                    "past_conditions": list(conditions or []),
                    "allergies": list(allergies or []),
                    "current_medications": list(meds or []),
                }

                # 2. Recent uploaded documents (baseline)
                await cur.execute(
                    """
                    SELECT id::text, document_type::text, content_text, created_at::text
                    FROM patient_documents
                    WHERE patient_id = %s
                    ORDER BY created_at DESC
                    LIMIT 3;
                    """,
                    (patient_id,),
                )
                doc_rows = await cur.fetchall()
                baseline_docs = [
                    {
                        "id": r[0],
                        "document_type": r[1],
                        "content_text": r[2][:1000],  # Baseline-length snippet
                        "created_at": r[3],
                    }
                    for r in doc_rows
                ]

                # 3. Next upcoming appointment
                await cur.execute(
                    """
                    SELECT slot_id::text, slot_datetime, duration_minutes
                    FROM hospital_slots
                    WHERE booked_patient_id = %s
                      AND slot_datetime > NOW()
                    ORDER BY slot_datetime
                    LIMIT 1;
                    """,
                    (patient_id,),
                )
                slot_row = await cur.fetchone()
                upcoming_slot = None
                if slot_row:
                    upcoming_slot = {
                        "slot_id": slot_row[0],
                        "slot_datetime": slot_row[1].isoformat(),
                        "duration_minutes": slot_row[2],
                        "label": slot_row[1].strftime("%A, %B %d at %I:%M %p"),
                    }

                return json.dumps({
                    "profile": profile,
                    "baseline_documents": baseline_docs,
                    "upcoming_slot": upcoming_slot,
                })
    except Exception as e:
        print(f"[DB][Supabase] initialize_patient_session error: {e}", file=sys.stderr, flush=True)
        return json.dumps({"profile": None, "baseline_documents": [], "upcoming_slot": None})


# ────────────────────────────────────────────────────────────────────────────
# Tool 5: ingest_document  (UPDATED — now writes to patient_documents)
# ────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def ingest_document(patient_id: str, text_content: str, document_type: str = "report") -> str:
    """
    Embed a text document and store it in the patient_documents table.

    Args:
        patient_id:    Patient identifier.
        text_content:  Extracted text content from the uploaded file.
        document_type: One of 'report', 'xray', 'blood_test', 'prescription'.

    The RBAC guardrail (only hospital_employee may call this) is enforced
    at the FastAPI server layer before this tool is ever invoked.
    """
    if not _db_uri:
        return json.dumps({"success": False, "error": "No DB connection"})

    # Validate document_type
    valid_types = ("report", "xray", "blood_test", "prescription")
    if document_type not in valid_types:
        return json.dumps({"success": False, "error": f"Invalid document_type. Must be one of: {valid_types}"})

    try:
        # Truncate to 5000 chars to stay within token limits
        content = text_content[:5000]
        embedding = get_embedder().embed_query(content)

        conn = await _get_supabase_conn()
        async with conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO patient_documents
                        (patient_id, document_type, content_text, embedding)
                    VALUES (%s, %s::document_type, %s, %s::vector)
                    RETURNING id::text;
                    """,
                    (patient_id, document_type, content, embedding),
                )
                row = await cur.fetchone()
                return json.dumps({
                    "success": True,
                    "patient_id": patient_id,
                    "record_id": row[0] if row else None,
                    "document_type": document_type,
                    "chars_ingested": len(content),
                })
    except Exception as e:
        print(f"[DB][Supabase] ingest_document error: {e}", file=sys.stderr, flush=True)
        return json.dumps({"success": False, "error": str(e)})


# ────────────────────────────────────────────────────────────────────────────
# Tool 6: get_available_slots
# ────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def get_available_slots(date: str = "", number_of_days: int = 7) -> str:
    """
    Get all unbooked appointment slots.

    Args:
        date:            Optional start date (YYYY-MM-DD). Defaults to today.
        number_of_days:  How many days ahead to search (1-14). Defaults to 7.

    Returns a JSON array of slot objects:
      [{slot_id, slot_datetime, duration_minutes, label, doctor_name}, ...]
    """
    if not _db_uri:
        return "[]"

    # Clamp days to a safe range
    number_of_days = max(1, min(14, number_of_days))

    try:
        conn = await _get_supabase_conn()
        async with conn:
            async with conn.cursor() as cur:
                if date:
                    # Single-date query (backward compat)
                    await cur.execute(
                        """
                        SELECT slot_id::text, slot_datetime, duration_minutes, doctor_name
                        FROM hospital_slots
                        WHERE DATE(slot_datetime) = %s::date
                          AND is_booked = false
                        ORDER BY slot_datetime;
                        """,
                        (date,),
                    )
                else:
                    # Range query: from today through number_of_days
                    await cur.execute(
                        """
                        SELECT slot_id::text, slot_datetime, duration_minutes, doctor_name
                        FROM hospital_slots
                        WHERE slot_datetime >= NOW()
                          AND slot_datetime < NOW() + make_interval(days => %s)
                          AND is_booked = false
                        ORDER BY slot_datetime;
                        """,
                        (number_of_days,),
                    )
                rows = await cur.fetchall()
                slots = []
                for row in rows:
                    slot_id, slot_dt, duration, doctor = row
                    label = slot_dt.strftime("%B %d at %I:%M %p")
                    slots.append({
                        "slot_id": slot_id,
                        "slot_datetime": slot_dt.isoformat(),
                        "duration_minutes": duration,
                        "label": label,
                        "doctor_name": doctor,
                    })
                return json.dumps(slots)
    except Exception as e:
        print(f"[DB][Supabase] get_available_slots error: {e}", file=sys.stderr, flush=True)
        return "[]"


# ────────────────────────────────────────────────────────────────────────────
# Tool 7: book_slot
# ────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def book_slot(slot_id: str, patient_id: str) -> str:
    """
    Mark a hospital slot as booked for a specific patient.
    Returns JSON: {success, slot_id, patient_id}
    """
    if not _db_uri:
        return json.dumps({"success": False, "error": "No DB connection"})

    try:
        conn = await _get_supabase_conn()
        async with conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE hospital_slots
                    SET is_booked = true, booked_patient_id = %s
                    WHERE slot_id = %s::uuid AND is_booked = false;
                    """,
                    (patient_id, slot_id),
                )
                affected = cur.rowcount
                return json.dumps({
                    "success": affected > 0,
                    "slot_id": slot_id,
                    "patient_id": patient_id,
                })
    except Exception as e:
        print(f"[DB][Supabase] book_slot error: {e}", file=sys.stderr, flush=True)
        return json.dumps({"success": False, "error": str(e)})


# ────────────────────────────────────────────────────────────────────────────
# Tool 8: get_patient_appointments
# ────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def get_patient_appointments(patient_id: str) -> str:
    """
    Get all booked appointments for a specific patient (upcoming only).
    Returns a JSON array of appointment objects:
      [{slot_id, slot_datetime, duration_minutes, label, doctor_name}, ...]
    """
    if not _db_uri:
        return "[]"

    try:
        conn = await _get_supabase_conn()
        async with conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT slot_id::text, slot_datetime, duration_minutes, doctor_name
                    FROM hospital_slots
                    WHERE booked_patient_id = %s
                      AND is_booked = true
                      AND slot_datetime >= NOW()
                    ORDER BY slot_datetime;
                    """,
                    (patient_id,),
                )
                rows = await cur.fetchall()
                appointments = []
                for row in rows:
                    slot_id, slot_dt, duration, doctor = row
                    label = slot_dt.strftime("%A, %B %d at %I:%M %p")
                    appointments.append({
                        "slot_id": slot_id,
                        "slot_datetime": slot_dt.isoformat(),
                        "duration_minutes": duration,
                        "label": label,
                        "doctor_name": doctor,
                    })
                return json.dumps(appointments)
    except Exception as e:
        print(f"[DB][Supabase] get_patient_appointments error: {e}", file=sys.stderr, flush=True)
        return "[]"


# ────────────────────────────────────────────────────────────────────────────
# Tool 9: cancel_slot
# ────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def cancel_slot(slot_id: str, patient_id: str) -> str:
    """
    Cancel (unbook) an appointment slot for a specific patient.
    The slot becomes available again for other patients.
    Returns JSON: {success, slot_id, patient_id}

    Security: Only the patient who booked the slot can cancel it
    (enforced by the WHERE clause matching booked_patient_id).
    """
    if not _db_uri:
        return json.dumps({"success": False, "error": "No DB connection"})

    try:
        conn = await _get_supabase_conn()
        async with conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE hospital_slots
                    SET is_booked = false, booked_patient_id = NULL
                    WHERE slot_id = %s::uuid
                      AND booked_patient_id = %s
                      AND is_booked = true;
                    """,
                    (slot_id, patient_id),
                )
                affected = cur.rowcount
                if affected > 0:
                    return json.dumps({
                        "success": True,
                        "slot_id": slot_id,
                        "patient_id": patient_id,
                    })
                else:
                    return json.dumps({
                        "success": False,
                        "error": "Appointment not found or does not belong to this patient.",
                    })
    except Exception as e:
        print(f"[DB][Supabase] cancel_slot error: {e}", file=sys.stderr, flush=True)
        return json.dumps({"success": False, "error": str(e)})


# ────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
