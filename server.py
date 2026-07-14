"""
server.py
─────────
FastAPI server for Project Baymax (DeepAgent Architecture).

Exposes the LangGraph DeepAgent workflow as an HTTP API.
Implements Role-Based Access Control (RBAC):
  - /api/chat               : Both roles. pre_consultation_brief stripped for patients.
  - /api/initialize_session  : Both roles. Proactive context loading at login.
  - /api/ingest             : Hospital employees only. Patients receive HTTP 403.
  - /api/brief              : Hospital employees only. Standalone brief generation.
  - /api/health             : Public.

Run with:
    uv run uvicorn server:app --reload --port 8000
"""

import asyncio
import io
import os
import sys
import threading
from typing import List, Literal, Optional

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from baymax.graph import build_graph
from baymax.mcp_client import ingest_document_mcp, initialize_session_mcp
from baymax.briefs import generate_pre_consultation_brief

# ─────────────────────────────────────────────────────────────────────────────
# App Setup
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Project Baymax API",
    description="AI Healthcare Companion — DeepAgent Architecture with RBAC",
    version="4.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Build LangGraph once at startup
# ─────────────────────────────────────────────────────────────────────────────

print("[Server] Initialising DeepAgent Graph...")
graph = build_graph()
print("[Server] Graph Initialised.")

if os.environ.get("LANGCHAIN_TRACING_V2") == "true":
    project = os.environ.get("LANGCHAIN_PROJECT", "default")
    print(f"[Server] 🔗 LangSmith Tracing ENABLED for project: {project}")

# ─────────────────────────────────────────────────────────────────────────────
# Session Cache — stores patient baseline per patient_id
# ─────────────────────────────────────────────────────────────────────────────

_session_cache: dict[str, dict] = {}
"""
Server-side cache: patient_id → session baseline data.
Populated by /api/initialize_session, consumed by /api/chat.
This ensures the DeepAgent always has the patient's context.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    user_message: str = Field(..., min_length=1, description="The user's message text")
    patient_id: str = Field(..., min_length=1, description="Patient identifier, e.g. P001")
    user_role: Literal["patient", "hospital_employee"] = Field(
        default="patient",
        description="Role determines what data is surfaced in the response",
    )


class ChatResponse(BaseModel):
    response: str = Field(..., description="Baymax's response text")
    risk_flag: bool = Field(False, description="Whether high-risk was detected")
    available_slots: List[dict] = Field(
        default_factory=list,
        description="Open appointment slots to render as chip buttons in the UI",
    )
    doctor_brief: Optional[str] = Field(
        None,
        description="Pre-consultation brief — only present when user_role == 'hospital_employee'",
    )


class SessionRequest(BaseModel):
    patient_id: str = Field(..., min_length=1, description="Patient identifier")
    user_role: Literal["patient", "hospital_employee"] = Field(default="patient")


class SessionResponse(BaseModel):
    patient_name: Optional[str] = Field(None, description="Patient's display name")
    age: Optional[int] = Field(None, description="Patient's age")
    chronic_conditions: List[str] = Field(default_factory=list, description="Known chronic conditions")
    allergies: List[str] = Field(default_factory=list, description="Known allergies")
    medications: List[str] = Field(default_factory=list, description="Current medications")
    baseline_documents: List[dict] = Field(default_factory=list, description="Recent uploaded documents")
    upcoming_slot: Optional[dict] = Field(None, description="Next booked appointment, if any")
    greeting: str = Field("", description="Personalised greeting message")


class IngestResponse(BaseModel):
    success: bool
    patient_id: str
    document_type: str
    chars_ingested: int
    message: str


class BriefResponse(BaseModel):
    patient_id: str
    brief: str


# ─────────────────────────────────────────────────────────────────────────────
# Thread isolation helper (prevents asyncio conflicts with MCP client)
# ─────────────────────────────────────────────────────────────────────────────

def _run_in_clean_thread(fn, *args, **kwargs):
    """
    Run fn in a brand-new OS thread with no asyncio event loop.
    Required because the MCP client calls asyncio.run() internally,
    which conflicts with uvicorn's running ProactorEventLoop on Windows.
    """
    result_holder = [None]
    error_holder = [None]

    def _worker():
        asyncio.set_event_loop(None)
        try:
            result_holder[0] = fn(*args, **kwargs)
        except Exception as exc:
            error_holder[0] = exc

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join()

    if error_holder[0] is not None:
        raise error_holder[0]
    return result_holder[0]


def _invoke_graph(patient_id: str, user_message: str, user_role: str) -> dict:
    """Run the LangGraph synchronously inside a clean-thread context."""

    # Retrieve the cached baseline data for this patient
    baseline = _session_cache.get(patient_id)

    state = {
        "patient_id": patient_id,
        "user_input": user_message,
        "user_role": user_role,
        "patient_baseline": baseline,
    }
    config = {
        "configurable": {"thread_id": f"{patient_id}:{user_role}"},
        "run_name": f"Baymax | {patient_id} | {user_role}",
        "metadata": {"patient_id": patient_id, "user_role": user_role},
    }
    return graph.invoke(state, config=config)


# ─────────────────────────────────────────────────────────────────────────────
# PDF Text Extraction
# ─────────────────────────────────────────────────────────────────────────────

def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract plain text from a PDF file using pypdf."""
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text_parts = []
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text_parts.append(extracted)
    return "\n\n".join(text_parts)


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "project-baymax", "version": "4.0.0"}


@app.post("/api/initialize_session", response_model=SessionResponse)
async def initialize_session(req: SessionRequest):
    """
    Proactive context loading at login.
    Fetches baseline patient data (profile, recent documents, upcoming slot)
    and generates a personalised greeting. Caches the baseline server-side
    so it's available on every subsequent /api/chat call.
    """
    patient_id = req.patient_id.strip().upper()

    try:
        session_data = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: _run_in_clean_thread(initialize_session_mcp, patient_id),
        )
    except Exception as e:
        print(f"[Server] Session init error: {e}")
        raise HTTPException(status_code=500, detail=f"Session initialization error: {str(e)}")

    profile = session_data.get("profile")
    baseline_docs = session_data.get("baseline_documents", [])
    upcoming_slot = session_data.get("upcoming_slot")

    # Cache the baseline for use in subsequent /api/chat calls
    _session_cache[patient_id] = {
        "profile": profile,
        "baseline_documents": baseline_docs,
        "upcoming_slot": upcoming_slot,
    }

    if not profile:
        # Unknown patient — return a generic greeting
        return SessionResponse(
            greeting=(
                "Hello! I'm **Baymax**, your personal healthcare companion. 🏥\n\n"
                "I couldn't find your profile in our records, but I'm still here to help.\n\n"
                "How are you feeling today?"
            ),
        )

    # Build personalised greeting
    name = profile.get("name", "there")
    conditions = profile.get("past_conditions", [])
    upcoming_note = ""
    if upcoming_slot:
        upcoming_note = f"\n\n📅 You have an upcoming appointment on **{upcoming_slot.get('label', 'soon')}**."

    if conditions:
        condition_mention = conditions[0]  # Mention the primary condition
        greeting = (
            f"Hello **{name}**! I'm **Baymax**, your personal healthcare companion. 🏥\n\n"
            f"I can see from your records that you have a history of **{condition_mention}**. "
            f"How has that been lately?{upcoming_note}\n\n"
            f"Feel free to tell me about any symptoms or concerns you have today."
        )
    else:
        greeting = (
            f"Hello **{name}**! I'm **Baymax**, your personal healthcare companion. 🏥\n\n"
            f"Great to see you.{upcoming_note}\n\n"
            f"How are you feeling today?"
        )

    return SessionResponse(
        patient_name=name,
        age=profile.get("age"),
        chronic_conditions=conditions,
        allergies=profile.get("allergies", []),
        medications=profile.get("current_medications", []),
        baseline_documents=baseline_docs,
        upcoming_slot=upcoming_slot,
        greeting=greeting,
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Send a message to the Baymax DeepAgent.

    RBAC: pre_consultation_brief is stripped from the response payload
    when user_role == 'patient'. Available slots are always surfaced.
    """
    patient_id = req.patient_id.strip().upper()
    user_message = req.user_message.strip()
    user_role = req.user_role

    try:
        result = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: _run_in_clean_thread(_invoke_graph, patient_id, user_message, user_role),
        )
    except Exception as e:
        print(f"[Server] Graph invocation error: {e}")
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    # ── RBAC: only expose brief to hospital employees ─────────────────────────
    doctor_brief = None
    if user_role == "hospital_employee":
        doctor_brief = result.get("pre_consultation_brief")

    return ChatResponse(
        response=result.get("final_response", "No response generated."),
        risk_flag=False,  # Risk assessment is now embedded in the agent's reasoning
        available_slots=result.get("available_slots", []),
        doctor_brief=doctor_brief,
    )


@app.post("/api/ingest", response_model=IngestResponse)
async def ingest_document(
    patient_id: str = Form(..., description="Patient ID to associate the document with"),
    user_role: str = Form(..., description="Must be 'hospital_employee'"),
    document_type: str = Form(default="report", description="One of: report, xray, blood_test, prescription"),
    file: UploadFile = File(..., description="PDF file to ingest"),
):
    """
    Upload and embed a PDF document into the patient's vector store.

    RBAC: Only hospital_employee sessions are permitted.
    Patient attempts receive HTTP 403.
    """
    # ── RBAC guardrail ────────────────────────────────────────────────────────
    if user_role != "hospital_employee":
        raise HTTPException(
            status_code=403,
            detail="Access denied: Only hospital employees can ingest documents.",
        )

    # ── Validate document_type ────────────────────────────────────────────────
    valid_types = ("report", "xray", "blood_test", "prescription")
    if document_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document_type. Must be one of: {', '.join(valid_types)}",
        )

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    pdf_bytes = await file.read()

    try:
        text = _extract_pdf_text(pdf_bytes)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse PDF: {str(e)}")

    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="No extractable text found in the PDF. Ensure it is not a scanned image.",
        )

    try:
        result = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: _run_in_clean_thread(
                ingest_document_mcp,
                patient_id.strip().upper(),
                text,
                document_type,
            ),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion error: {str(e)}")

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Unknown ingestion error"),
        )

    chars = result.get("chars_ingested", len(text))
    return IngestResponse(
        success=True,
        patient_id=patient_id.strip().upper(),
        document_type=document_type,
        chars_ingested=chars,
        message=f"Document ({document_type}) successfully ingested ({chars:,} characters embedded into vector store).",
    )


@app.get("/api/brief/{patient_id}", response_model=BriefResponse)
async def get_brief(patient_id: str, user_role: str = "hospital_employee"):
    """
    Generate a pre-consultation brief for a given patient.

    RBAC: Only hospital_employee sessions are permitted.
    """
    if user_role != "hospital_employee":
        raise HTTPException(
            status_code=403,
            detail="Access denied: Pre-consultation briefs are for hospital staff only.",
        )

    pid = patient_id.strip().upper()

    try:
        # Fetch upcoming appointment for context
        appointment_label = ""
        try:
            from baymax.mcp_client import fetch_patient_appointments_mcp
            appointments = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: _run_in_clean_thread(fetch_patient_appointments_mcp, pid),
            )
            if appointments:
                next_appt = appointments[0]
                doctor = next_appt.get("doctor_name", "")
                appointment_label = next_appt.get("label", "")
                if doctor:
                    appointment_label += f" with {doctor}"
        except Exception:
            pass

        brief = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: _run_in_clean_thread(
                generate_pre_consultation_brief,
                pid,
                [],   # no current symptoms for a standalone lookup
                False,
                "",
                [],
                appointment_label,
            ),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Brief generation error: {str(e)}")

    return BriefResponse(patient_id=pid, brief=brief)
