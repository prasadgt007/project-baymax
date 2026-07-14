"""
nodes.py
────────
LangGraph agent nodes for Project Baymax (DeepAgent Architecture).

There are only two nodes:
  1. baymax_agent   — The DeepAgent node. Uses create_deep_agent with
                      NVIDIA Llama 3.3 70B, 7 medical tools, and a unified
                      system prompt. Handles ALL routing, triage, RAG retrieval,
                      guidance, and scheduling through its ReAct tool-calling loop.
  2. compliance_wrapper — Deterministic post-processing that appends the medical
                          disclaimer to every response.
"""

import os
from typing import Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver
from .models import BaymaxState
from .tools import create_baymax_tools


# ── LLM ──────────────────────────────────────────────────────────────────────
# Initialize LLM with 70B model for reliable tool calling
llm = ChatNVIDIA(model="meta/llama-3.1-70b-instruct")

# ── System Prompt ─────────────────────────────────────────────────────────────
_SYSTEM_PROMPT_CACHE = None


def _load_system_prompt() -> str:
    """Load the unified system prompt from skills.md (cached)."""
    global _SYSTEM_PROMPT_CACHE
    if _SYSTEM_PROMPT_CACHE is None:
        skills_path = os.path.join(os.path.dirname(__file__), "skills.md")
        with open(skills_path, "r", encoding="utf-8") as f:
            _SYSTEM_PROMPT_CACHE = f.read()
    return _SYSTEM_PROMPT_CACHE


def _build_contextual_prompt(baseline: dict | None) -> str:
    """
    Build the full system prompt by injecting the patient's baseline context
    into the core prompt. This ensures the DeepAgent knows the patient's
    name, conditions, allergies, and recent documents from the very first turn.
    """
    base_prompt = _load_system_prompt()

    if not baseline or not baseline.get("profile"):
        return base_prompt

    profile = baseline["profile"]
    name = profile.get("name", "Patient")
    age = profile.get("age", "Unknown")
    conditions = profile.get("past_conditions", [])
    allergies = profile.get("allergies", [])
    meds = profile.get("current_medications", [])

    context_block = (
        f"\n\n## Current Patient Context\n"
        f"- **Name:** {name}\n"
        f"- **Age:** {age}\n"
        f"- **Known Conditions:** {', '.join(conditions) if conditions else 'None on record'}\n"
        f"- **Allergies:** {', '.join(allergies) if allergies else 'None known'}\n"
        f"- **Current Medications:** {', '.join(meds) if meds else 'None'}\n"
    )

    # Add baseline documents if available
    baseline_docs = baseline.get("baseline_documents", [])
    if baseline_docs:
        context_block += "\n**Recent Documents on File:**\n"
        for doc in baseline_docs:
            doc_type = doc.get("document_type", "document")
            date = doc.get("created_at", "Unknown")
            content_preview = doc.get("content_text", "")[:200]
            context_block += f"- [{doc_type}] ({date}): {content_preview}...\n"

    # Add upcoming appointment if any
    upcoming = baseline.get("upcoming_slot")
    if upcoming:
        context_block += f"\n**Upcoming Appointment:** {upcoming.get('label', 'Scheduled')}\n"

    return base_prompt + context_block


# ─────────────────────────────────────────────────────────────────────────────
# Node 1: Baymax DeepAgent — The Core Reasoning Engine
# ─────────────────────────────────────────────────────────────────────────────

def baymax_agent(state: BaymaxState) -> Dict[str, Any]:
    """
    The single DeepAgent node that replaces all previous agents.

    Uses create_deep_agent with:
      - NVIDIA Llama 3.3 70B (tool-calling capable)
      - 5 patient-bound tools (search, profile, slots, book, brief)
      - The unified system prompt with patient baseline injected

    The agent internally runs a ReAct loop: think → call tool → observe →
    think → ... → final response. LangGraph just needs to invoke it once.
    """
    patient_id = state.get("patient_id", "")
    user_input = state.get("user_input", "")
    baseline = state.get("patient_baseline")
    existing_messages = state.get("messages", [])

    # Create patient-bound tools (patient_id injected via closure)
    tools = create_baymax_tools(patient_id)

    # Build the contextual system prompt
    system_prompt = _build_contextual_prompt(baseline)

    # Create the DeepAgent
    agent = create_deep_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=False,  # We manage checkpointing at the outer graph level
        name="baymax",
    )

    # Build message input for the agent
    # Include conversation history so the agent has multi-turn context
    input_messages = list(existing_messages) + [HumanMessage(content=user_input)]

    try:
        result = agent.invoke({"messages": input_messages})

        # Extract the final AI response from the agent's output
        output_messages = result.get("messages", [])
        final_text = ""
        available_slots = []
        brief = None

        # Walk through output messages to find the final AI response
        # and extract any structured data (slots, brief)
        for msg in reversed(output_messages):
            if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                final_text = msg.content
                break

        if not final_text:
            final_text = "I'm here to help. Could you tell me more about what you need?"

        # Check if slots were mentioned in tool calls (parse from tool results)
        for msg in output_messages:
            if hasattr(msg, "content") and isinstance(msg.content, str):
                if "slot_id:" in msg.content and ("available" in msg.content.lower() or "appointment slots" in msg.content.lower()):
                    # Extract slots from the tool output for frontend rendering
                    try:
                        _extract_slots_from_response(msg.content, available_slots)
                    except Exception:
                        pass

        # Check if a brief was generated
        for msg in output_messages:
            if hasattr(msg, "content") and isinstance(msg.content, str):
                if "Pre-Consultation Brief" in msg.content:
                    brief = msg.content

        # Clean the final text so the user doesn't see raw slot_ids
        import re
        # Remove lines that are just slot_id
        final_text = re.sub(r"\n\s*slot_id:\s*[\w-]+", "", final_text)
        # Remove inline slot_ids
        final_text = re.sub(r"\(?slot_id:\s*[\w-]+\)?", "", final_text)
        final_text = re.sub(r"\(\s*\)", "", final_text)
        final_text = final_text.replace("  ", " ").strip()

        return {
            "messages": [HumanMessage(content=user_input), AIMessage(content=final_text)],
            "final_response": final_text,
            "available_slots": available_slots,
            "pre_consultation_brief": brief,
        }

    except Exception as e:
        print(f"[BaymaxAgent] Error: {e}")
        error_response = (
            "I apologise, but I encountered an issue processing your request. "
            "Could you please try rephrasing your message?"
        )
        return {
            "messages": [HumanMessage(content=user_input), AIMessage(content=error_response)],
            "final_response": error_response,
            "available_slots": [],
            "pre_consultation_brief": None,
        }


def _extract_slots_from_response(tool_output: str, slots_list: list) -> None:
    """
    Parse slot data from the get_available_slots tool output.

    New format (each slot is two lines):
        1. 09:00 AM with Dr. Amanda Ross
           slot_id: c5b1b270-853f-4cb8-b38b-08cb65253ae4

    Also handles the old inline format:
        • 2026-07-10 10:00 AM (ID: <uuid>)
    """
    import re

    # Extract the day headers to build full labels
    current_day = ""
    lines = tool_output.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()

        # Detect day headers like "**Monday, July 14:**"
        day_match = re.match(r"\*\*(.+?):\*\*", stripped)
        if day_match:
            current_day = day_match.group(1).strip()
            continue

        # Detect slot_id lines
        slot_id_match = re.match(r"slot_id:\s*([\w-]+)", stripped)
        if slot_id_match:
            slot_id = slot_id_match.group(1).strip()

            # Look back at the previous non-empty line for the time label
            time_label = ""
            for j in range(i - 1, max(i - 3, -1), -1):
                prev = lines[j].strip()
                # Match numbered items like "1. 09:00 AM with Dr. Amanda Ross"
                time_match = re.match(r"\d+\.\s*(.+)", prev)
                if time_match:
                    time_label = time_match.group(1).strip()
                    break

            full_label = f"{current_day} at {time_label}" if current_day and time_label else time_label or slot_id
            slots_list.append({
                "slot_id": slot_id,
                "label": full_label,
                "slot_datetime": "",
                "duration_minutes": 60,
            })
            continue

    # Fallback: old inline format "• label (ID: uuid)"
    if not slots_list:
        pattern = r"[•\-]\s*(.+?)\s*\(ID:\s*([\w-]+)\)"
        for match in re.finditer(pattern, tool_output):
            label = match.group(1).strip()
            slot_id = match.group(2).strip()
            slots_list.append({
                "slot_id": slot_id,
                "label": label,
                "slot_datetime": "",
                "duration_minutes": 60,
            })


# ─────────────────────────────────────────────────────────────────────────────
# Node 2: Compliance Wrapper — Deterministic Disclaimer
# ─────────────────────────────────────────────────────────────────────────────

def compliance_wrapper(state: BaymaxState) -> Dict[str, Any]:
    """
    Deterministic post-processing node that ensures the medical disclaimer
    is appended to every response that contains health guidance.

    This is NOT LLM-driven — it guarantees compliance regardless of the
    agent's output.
    """
    response = state.get("final_response", "")

    disclaimer = (
        "\n\n---\n"
        "*This information is for educational purposes only and does not substitute "
        "professional medical advice. Always consult a qualified healthcare provider "
        "before starting any treatment.*"
    )

    # Only append disclaimer to responses that contain medical content
    # (skip for greetings, out-of-scope declines, booking confirmations, etc.)
    medical_indicators = [
        "remedy", "treatment", "medication", "symptom", "consult a doctor",
        "condition", "recommend", "⚠️", "OTC", "over-the-counter",
        "ibuprofen", "acetaminophen", "rest", "hydrat",
    ]
    contains_medical = any(indicator in response.lower() for indicator in medical_indicators)

    if contains_medical and disclaimer.strip() not in response:
        response = response + disclaimer

    return {"final_response": response}
