from typing import TypedDict, List, Optional, Literal, Annotated
from pydantic import BaseModel, Field
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


# ── Pydantic Domain Models ────────────────────────────────────────────────────
# Kept for mcp_client.py and briefs.py compatibility

class Symptom(BaseModel):
    name: str = Field(description="Name of the primary symptom")
    severity: str = Field(description="Severity level (mild, moderate, or severe)")
    duration: str = Field(description="How long the symptom has been present")


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


# ── LangGraph Shared State ────────────────────────────────────────────────────

class BaymaxState(TypedDict):
    """
    Simplified state for the DeepAgent architecture.

    The DeepAgent handles ALL routing, triage, RAG retrieval, and guidance
    internally through its ReAct tool-calling loop. The graph state only
    needs to carry identity/role, the conversation history (messages),
    and outputs for the frontend.
    """

    # ── Identity & Role ───────────────────────────────────────────────────────
    patient_id: str
    """Unique patient identifier (e.g. 'P001'). Used as the DB key."""

    user_role: Literal["patient", "hospital_employee"]
    """Drives RBAC decisions at the server layer."""

    user_input: str
    """The raw message from the user for the current turn."""

    # ── Proactive Context ─────────────────────────────────────────────────────
    patient_baseline: Optional[dict]
    """Injected at session init via /api/initialize_session.
    Contains: {name, age, past_conditions, allergies, medications, baseline_documents, upcoming_slot}.
    Embedded into the DeepAgent's system prompt for personalisation."""

    # ── Conversation Memory ───────────────────────────────────────────────────
    messages: Annotated[list[AnyMessage], add_messages]
    """Full message history for the DeepAgent's ReAct loop.
    Uses LangGraph's add_messages reducer to automatically merge turns."""

    # ── Frontend Outputs ──────────────────────────────────────────────────────
    available_slots: List[dict]
    """Open appointment slots to render as chip buttons in the UI.
    Each element: {slot_id, slot_datetime, duration_minutes, label}."""

    pre_consultation_brief: Optional[str]
    """Markdown-formatted clinical summary generated after appointment booking.
    MUST be stripped from ChatResponse when user_role == 'patient'."""

    final_response: str
    """The final text response returned to the frontend."""
