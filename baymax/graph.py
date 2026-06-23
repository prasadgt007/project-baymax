from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from .models import BaymaxState
from .nodes import (
    supervisor_agent,
    greeting_agent,
    guardrail_agent,
    symptom_agent,
    history_agent,
    risk_agent,
    guidance_agent,
    compliance_agent,
    scheduling_agent
)

def build_graph() -> StateGraph:
    """Builds and compiles the LangGraph for Project Baymax."""
    
    # 1. Initialize StateGraph
    workflow = StateGraph(BaymaxState)
    
    # 2. Add nodes
    workflow.add_node("supervisor", supervisor_agent)
    workflow.add_node("greeting", greeting_agent)
    workflow.add_node("guardrail", guardrail_agent)
    workflow.add_node("history", history_agent)
    workflow.add_node("symptom", symptom_agent)
    workflow.add_node("risk", risk_agent)
    workflow.add_node("guidance", guidance_agent)
    workflow.add_node("compliance", compliance_agent)
    workflow.add_node("scheduling", scheduling_agent)
    
    # 3. Define the edges
    workflow.set_entry_point("supervisor")
    
    # Conditional routing from supervisor
    def route_supervisor(state: BaymaxState) -> Literal["greeting", "history", "scheduling", "guardrail"]:
        intent = state.get("intent")
        if intent == "chitchat":
            return "greeting"
        elif intent == "scheduling":
            return "scheduling"
        elif intent == "out_of_scope":
            return "guardrail"
        return "history"
        
    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "greeting": "greeting",
            "history": "history",
            "scheduling": "scheduling",
            "guardrail": "guardrail"
        }
    )
    
    workflow.add_edge("history", "symptom")
    workflow.add_edge("symptom", "risk")
    
    # Conditional routing after Risk Agent
    def route_risk(state: BaymaxState) -> Literal["scheduling", "guidance"]:
        if state.get("risk_flag"):
            # If high risk, bypass guidance and go to scheduling
            return "scheduling"
        return "guidance"
        
    workflow.add_conditional_edges(
        "risk",
        route_risk,
        {
            "scheduling": "scheduling",
            "guidance": "guidance"
        }
    )
    
    workflow.add_edge("guidance", "compliance")
    workflow.add_edge("compliance", END)
    workflow.add_edge("scheduling", END)
    workflow.add_edge("greeting", END)
    workflow.add_edge("guardrail", END)
    
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)
