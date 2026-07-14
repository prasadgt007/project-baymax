"""
graph.py
────────
Builds and compiles the LangGraph for Project Baymax (DeepAgent Architecture).

The graph is radically simplified:

    Entry → baymax_agent → compliance_wrapper → END

The DeepAgent internally handles ALL:
  - Intent classification (no separate supervisor)
  - RAG retrieval (via search_patient_records tool)
  - Symptom triage (dynamic, not hard-coded turn counts)
  - Risk assessment (embedded in the system prompt logic)
  - Guidance generation (personalised using tool outputs)
  - Appointment scheduling (via get_available_slots + book_appointment tools)
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from .models import BaymaxState
from .nodes import baymax_agent, compliance_wrapper


def build_graph() -> StateGraph:
    """Builds and compiles the simplified DeepAgent LangGraph."""

    workflow = StateGraph(BaymaxState)

    # ── Add nodes ─────────────────────────────────────────────────────────────
    workflow.add_node("baymax_agent", baymax_agent)
    workflow.add_node("compliance_wrapper", compliance_wrapper)

    # ── Entry point ───────────────────────────────────────────────────────────
    workflow.set_entry_point("baymax_agent")

    # ── Linear flow ───────────────────────────────────────────────────────────
    workflow.add_edge("baymax_agent", "compliance_wrapper")
    workflow.add_edge("compliance_wrapper", END)

    # ── Compile with memory for multi-turn conversations ──────────────────────
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)
