"""
mcp_client.py
─────────────
Synchronous wrappers around the MCP stdio server tools.

Each wrapper:
  1. Opens a fresh stdio_client subprocess (the MCP server).
  2. Calls the tool via MCP protocol.
  3. Parses the JSON result and returns a Python object.
  4. Must be called from a thread with NO running asyncio event loop
     (use server._run_in_clean_thread for uvicorn compatibility).
"""

import asyncio
import os
import sys
import json
from typing import List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from .models import PatientProfile

# Resolve the venv Python so the MCP server subprocess has all packages available
_VENV_PYTHON = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".venv", "Scripts", "python.exe",
)
_PYTHON = _VENV_PYTHON if os.path.exists(_VENV_PYTHON) else sys.executable


def _make_server_params() -> StdioServerParameters:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    server_path = os.path.join(base_dir, "database_mcp_server.py")
    return StdioServerParameters(
        command=_PYTHON,
        args=[server_path],
        env=dict(os.environ),
    )


# ── Tool 1: get_patient_profile ───────────────────────────────────────────────

def fetch_patient_profile_mcp(patient_id: str) -> Optional[PatientProfile]:
    """Fetch the full patient profile. Returns PatientProfile or None."""
    async def _fetch():
        async with stdio_client(_make_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "get_patient_profile", arguments={"patient_id": patient_id}
                )
                if result.content and len(result.content) > 0:
                    json_str = result.content[0].text
                    if json_str == "{}":
                        return None
                    return PatientProfile.model_validate_json(json_str)
                return None

    return asyncio.run(_fetch())


# ── Tool 2: search_interactions ───────────────────────────────────────────────

def search_interactions_mcp(patient_id: str, query: str, limit: int = 3) -> List[dict]:
    """Semantic vector search over a patient's past interactions. Returns List[dict]."""
    async def _search():
        async with stdio_client(_make_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "search_interactions",
                    arguments={"patient_id": patient_id, "query": query, "limit": limit},
                )
                if result.content and len(result.content) > 0:
                    return json.loads(result.content[0].text)
                return []

    return asyncio.run(_search())


# ── Tool 3: search_patient_documents ──────────────────────────────────────────

def search_patient_documents_mcp(patient_id: str, query: str, limit: int = 5) -> List[dict]:
    """
    Semantic vector search over a patient's uploaded documents
    (reports, x-rays, blood tests, prescriptions).
    Returns List[dict]: [{id, document_type, content_text, created_at}]
    """
    async def _search():
        async with stdio_client(_make_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "search_patient_documents",
                    arguments={"patient_id": patient_id, "query": query, "limit": limit},
                )
                if result.content and len(result.content) > 0:
                    return json.loads(result.content[0].text)
                return []

    return asyncio.run(_search())


# ── Tool 4: initialize_session ────────────────────────────────────────────────

def initialize_session_mcp(patient_id: str) -> dict:
    """
    Fetch baseline session data for a patient (profile, recent documents,
    upcoming appointment). Returns dict with {profile, baseline_documents, upcoming_slot}.
    """
    async def _init():
        async with stdio_client(_make_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "initialize_patient_session",
                    arguments={"patient_id": patient_id},
                )
                if result.content and len(result.content) > 0:
                    return json.loads(result.content[0].text)
                return {"profile": None, "baseline_documents": [], "upcoming_slot": None}

    return asyncio.run(_init())


# ── Tool 5: ingest_document ──────────────────────────────────────────────────

def ingest_document_mcp(patient_id: str, text_content: str, document_type: str = "report") -> dict:
    """
    Embed text_content and insert it into the patient_documents table.
    RBAC enforced at the server layer; this function itself is unrestricted.
    Returns dict: {success, patient_id, record_id, document_type, chars_ingested}
    """
    async def _ingest():
        async with stdio_client(_make_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "ingest_document",
                    arguments={
                        "patient_id": patient_id,
                        "text_content": text_content,
                        "document_type": document_type,
                    },
                )
                if result.content and len(result.content) > 0:
                    return json.loads(result.content[0].text)
                return {"success": False}

    return asyncio.run(_ingest())


# ── Tool 6: get_available_slots ───────────────────────────────────────────────

def fetch_available_slots_mcp(date_str: str = "", number_of_days: int = 7) -> List[dict]:
    """
    Return available (unbooked) hospital appointment slots.
    If date_str is provided, returns slots for that specific date.
    Otherwise, returns all available slots for the next number_of_days days.
    Returns List[dict]: [{slot_id, slot_datetime, duration_minutes, label, doctor_name}, ...]
    """
    async def _fetch():
        async with stdio_client(_make_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                args = {"date": date_str, "number_of_days": number_of_days}
                result = await session.call_tool(
                    "get_available_slots", arguments=args
                )
                if result.content and len(result.content) > 0:
                    return json.loads(result.content[0].text)
                return []

    return asyncio.run(_fetch())


# ── Tool 7: book_slot ─────────────────────────────────────────────────────────

def book_slot_mcp(slot_id: str, patient_id: str) -> dict:
    """
    Mark a slot as booked for a patient.
    Returns dict: {success, slot_id, patient_id}
    """
    async def _book():
        async with stdio_client(_make_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "book_slot",
                    arguments={"slot_id": slot_id, "patient_id": patient_id},
                )
                if result.content and len(result.content) > 0:
                    return json.loads(result.content[0].text)
                return {"success": False}

    return asyncio.run(_book())


# ── Tool 8: get_patient_appointments ──────────────────────────────────────────

def fetch_patient_appointments_mcp(patient_id: str) -> List[dict]:
    """
    Return all upcoming booked appointments for a patient.
    Returns List[dict]: [{slot_id, slot_datetime, duration_minutes, label, doctor_name}, ...]
    """
    async def _fetch():
        async with stdio_client(_make_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "get_patient_appointments",
                    arguments={"patient_id": patient_id},
                )
                if result.content and len(result.content) > 0:
                    return json.loads(result.content[0].text)
                return []

    return asyncio.run(_fetch())


# ── Tool 9: cancel_slot ──────────────────────────────────────────────────────

def cancel_slot_mcp(slot_id: str, patient_id: str) -> dict:
    """
    Cancel (unbook) an appointment slot for a patient.
    Returns dict: {success, slot_id, patient_id}
    """
    async def _cancel():
        async with stdio_client(_make_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "cancel_slot",
                    arguments={"slot_id": slot_id, "patient_id": patient_id},
                )
                if result.content and len(result.content) > 0:
                    return json.loads(result.content[0].text)
                return {"success": False}

    return asyncio.run(_cancel())


# ── Tool 10: set_slot_calendar_event ──────────────────────────────────────────

def set_slot_calendar_event_mcp(slot_id: str, event_id: str) -> dict:
    """Persist the Google Calendar event_id for a booked slot. Returns {success}."""
    async def _set():
        async with stdio_client(_make_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "set_slot_calendar_event",
                    arguments={"slot_id": slot_id, "event_id": event_id},
                )
                if result.content and len(result.content) > 0:
                    return json.loads(result.content[0].text)
                return {"success": False}

    return asyncio.run(_set())
