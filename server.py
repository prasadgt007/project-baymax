"""
FastAPI server for Project Baymax.
Exposes the LangGraph multi-agent workflow as an HTTP API
so the React frontend can send messages and receive responses.

Run with:
    uv run uvicorn server:app --reload --port 8000
"""

import asyncio
import concurrent.futures
import threading
import sys
import io
import os

# Force UTF-8 output on Windows (same fix as cli.py)
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

from baymax.graph import build_graph
from baymax.briefs import generate_pre_consultation_brief

# ────────────────────────────────────────────────────────────────
# App Setup
# ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Project Baymax API",
    description="AI Healthcare Companion — Multi-Agent Backend",
    version="1.0.0",
)

# CORS — allow the Vite dev server
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

# ────────────────────────────────────────────────────────────────
# Build the LangGraph once at startup
# ────────────────────────────────────────────────────────────────

print("[Server] Initializing Multi-Agent Graph...")
graph = build_graph()
print("[Server] Graph Initialized.")

# LangSmith info
if os.environ.get("LANGCHAIN_TRACING_V2") == "true":
    project = os.environ.get("LANGCHAIN_PROJECT", "default")
    print(f"[Server] 🔗 LangSmith Tracing ENABLED for project: {project}")

# ────────────────────────────────────────────────────────────────
# Request / Response Models
# ────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    user_message: str = Field(..., min_length=1, description="The user's message text")
    patient_id: str = Field(..., min_length=1, description="Patient identifier, e.g. P001")


class ChatResponse(BaseModel):
    response: str = Field(..., description="Baymax's response text")
    intent: Optional[str] = Field(None, description="Detected intent (medical, chitchat, scheduling, out_of_scope)")
    risk_flag: bool = Field(False, description="Whether high-risk was detected")
    doctor_brief: Optional[str] = Field(None, description="Pre-consultation brief for the doctor (only for medical intents)")


# ────────────────────────────────────────────────────────────────
# Endpoints
# ────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "project-baymax"}


def _run_in_clean_thread(fn, *args, **kwargs):
    """
    Run *fn* in a brand-new OS thread that has NO asyncio event loop set.

    Why not asyncio.to_thread?
    asyncio.to_thread reuses threads from the default ThreadPoolExecutor.
    On Windows (ProactorEventLoop), those threads can inherit loop state,
    causing `asyncio.run()` inside the MCP client to raise:
        RuntimeError: This event loop is already running

    By creating a dedicated thread and explicitly clearing its event loop
    we replicate the clean context that the CLI enjoys.
    """
    result_holder = [None]
    error_holder = [None]

    def _worker():
        # Wipe any inherited event-loop so asyncio.run() works cleanly
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


def _invoke_graph(patient_id: str, user_message: str) -> dict:
    """
    Run the LangGraph synchronously inside a clean-thread context.

    The baymax MCP client calls asyncio.run() internally which requires
    there to be NO running event loop on the current thread.
    _run_in_clean_thread ensures exactly that — same as cli.py.
    """
    state = {
        "patient_id": patient_id,
        "user_input": user_message,
    }

    config = {
        "configurable": {"thread_id": patient_id},
        "run_name": f"Baymax | {patient_id}",
        "metadata": {"patient_id": patient_id, "user_input": user_message},
    }

    return graph.invoke(state, config=config)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Send a message to the Baymax multi-agent graph.
    Uses the patient_id as the LangGraph thread_id for memory isolation.
    """
    patient_id = req.patient_id.strip().upper()
    user_message = req.user_message.strip()

    try:
        # Run in a dedicated clean thread so asyncio.run() inside the MCP
        # client doesn't conflict with uvicorn's running event loop.
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: _run_in_clean_thread(_invoke_graph, patient_id, user_message)
        )
    except Exception as e:
        print(f"[Server] Graph invocation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}",
        )

    final_response = result.get("final_response", "No response generated.")
    intent = result.get("intent", "medical")
    risk_flag = result.get("risk_flag", False)

    # Generate doctor's brief for medical intents
    doctor_brief = None
    if intent == "medical":
        try:
            symptoms = result.get("structured_symptoms", [])
            # Also run brief generation in a clean thread (it calls asyncio.run() too)
            doctor_brief = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: _run_in_clean_thread(
                    generate_pre_consultation_brief,
                    patient_id,
                    symptoms,
                    risk_flag,
                    result.get("escalation_reason", ""),
                )
            )
        except Exception as e:
            print(f"[Server] Brief generation error: {e}")

    return ChatResponse(
        response=final_response,
        intent=intent,
        risk_flag=risk_flag,
        doctor_brief=doctor_brief,
    )
