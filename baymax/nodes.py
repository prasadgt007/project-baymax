import os
from typing import Dict, Any
from langchain_core.runnables import RunnableConfig
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.prompts import ChatPromptTemplate
from .models import BaymaxState, Symptom, RouterIntent
from .utils import get_skill

# Use MCP client for database
from .mcp_client import fetch_patient_profile_mcp

llm = ChatNVIDIA(model="meta/llama-3.1-8b-instruct")

def supervisor_agent(state: BaymaxState, config: RunnableConfig) -> Dict[str, Any]:
    """Strictly classifies the user's intent to act as a router."""
    user_input = state.get("user_input", "")
    
    # Force the LLM to output only the structured intent
    structured_llm = llm.with_structured_output(RouterIntent)
    
    system_prompt = get_skill("Supervisor Agent")
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{input}")
    ])
    
    chain = prompt | structured_llm
    
    try:
        intent_data = chain.invoke({"input": user_input}, config)
        return {"intent": intent_data.intent}
    except Exception as e:
        # Fallback to medical if parsing fails to be safe
        return {"intent": "medical"}

def greeting_agent(state: BaymaxState, config: RunnableConfig) -> Dict[str, Any]:
    """Handles chitchat and greeting without diagnosing."""
    user_input = state.get("user_input", "")
    
    system_prompt = get_skill("Greeting Agent")
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{input}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"input": user_input}, config)
    
    return {"final_response": response.content}

def guardrail_agent(state: BaymaxState) -> Dict[str, Any]:
    """Handles out-of-scope requests rigidly."""
    return {"final_response": "I am Baymax, your personal healthcare companion. I can assist with symptom analysis, health triage, and medical appointment scheduling. However, I cannot assist you with off-topic requests like that."}

def symptom_agent(state: BaymaxState, config: RunnableConfig) -> Dict[str, Any]:
    """Parses raw user input to structure symptoms."""
    user_input = state.get("user_input", "")
    
    # We use LLM with structured output to get symptoms
    structured_llm = llm.with_structured_output(Symptom)
    
    system_prompt = get_skill("Symptom Agent")
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{input}")
    ])
    
    chain = prompt | structured_llm
    
    try:
        symptom_data = chain.invoke({"input": user_input}, config)
        return {"structured_symptoms": [symptom_data]}
    except Exception as e:
        # Fallback if parsing fails
        fallback_symptom = Symptom(name="Unknown", severity="Unknown", duration="Unknown")
        return {"structured_symptoms": [fallback_symptom]}

def history_agent(state: BaymaxState) -> Dict[str, Any]:
    """Fetches patient history based on patient_id via MCP Server."""
    patient_id = state.get("patient_id")
    profile = fetch_patient_profile_mcp(patient_id)
    return {"patient_profile": profile}

def risk_agent(state: BaymaxState, config: RunnableConfig) -> Dict[str, Any]:
    """Analyzes symptoms and history to flag required doctor escalation."""
    symptoms = state.get("structured_symptoms", [])
    profile = state.get("patient_profile")
    
    system_prompt = get_skill("Risk Agent")
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "Symptoms: {symptoms}\nPatient History: {history}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({
        "symptoms": [s.dict() for s in symptoms] if symptoms else "None",
        "history": profile.history.dict() if profile else "Unknown"
    }, config)
    
    content = response.content.strip().upper()
    if "ESCALATE" in content:
        return {
            "risk_flag": True, 
            "escalation_reason": "High risk symptoms detected requiring immediate medical attention."
        }
    return {"risk_flag": False, "escalation_reason": None}

def guidance_agent(state: BaymaxState, config: RunnableConfig) -> Dict[str, Any]:
    """Suggests safe remedies if risk_flag is False."""
    if state.get("risk_flag"):
         return {"proposed_guidance": "Please consult a doctor immediately. We cannot provide remedies for this condition."}
         
    symptoms = state.get("structured_symptoms", [])
    
    system_prompt = get_skill("Guidance Agent")
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "Symptoms: {symptoms}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"symptoms": [s.dict() for s in symptoms] if symptoms else "None"}, config)
    
    return {"proposed_guidance": response.content}

def compliance_agent(state: BaymaxState) -> Dict[str, Any]:
    """Applies privacy and disclaimer rules to the final guidance."""
    guidance = state.get("proposed_guidance", "")
    
    disclaimer = "\n\n*** Disclaimer: This information is for educational purposes only and does not substitute professional medical advice. ***"
    
    final_response = guidance + disclaimer
    return {
        "compliance_passed": True,
        "final_response": final_response
    }

def scheduling_agent(state: BaymaxState, config: RunnableConfig) -> Dict[str, Any]:
    """Books an appointment on Google Calendar using Composio."""
    try:
        import os
        # Ensure env vars are loaded (handles cold-start in some runtimes)
        if not os.environ.get("COMPOSIO_API_KEY"):
            from dotenv import load_dotenv
            load_dotenv()

        from composio import Composio
        from composio_langchain import LangchainProvider
        from langgraph.prebuilt import create_react_agent
        from langchain_core.messages import HumanMessage

        # --- Composio v3: Every tool execution is tied to an Entity (user_id). ---
        # The user_id is the entity under which Google Calendar was connected.
        # Use `uv run python check_composio.py` to rediscover it if needed.
        composio_user_id = os.environ.get("COMPOSIO_USER_ID")
        if not composio_user_id:
            return {
                "final_response": (
                    "⚠️ Scheduling is not configured: COMPOSIO_USER_ID is missing from .env. "
                    "Run `uv run python check_composio.py` to find your entity ID, "
                    "then add COMPOSIO_USER_ID=<your_entity_id> to .env."
                )
            }

        print(f"[Scheduling] Using Composio user_id: {composio_user_id}")

        # Initialize Composio with LangchainProvider so tools.get() returns
        # pre-wrapped LangChain StructuredTool objects.
        provider = LangchainProvider()
        composio_client = Composio(provider=provider)

        try:
            tools = composio_client.tools.get(
                user_id=composio_user_id,
                tools=["GOOGLECALENDAR_CREATE_EVENT"]
            )
            print(f"[Scheduling] Loaded {len(tools)} tool(s): {[t.name for t in tools]}")
        except Exception as tool_err:
            print(f"[Scheduling] ERROR loading tools: {tool_err}")
            prefix = "⚠️ High risk detected. " if state.get("risk_flag") else ""
            return {
                "final_response": f"{prefix}Error loading calendar tools: {tool_err}. Please proceed to the clinic directly if this is an emergency."
            }
        # Pre-compute all datetime values in Python so the LLM never has to do datetime math.
        # The tool explicitly rejects natural language — we give it exact ISO strings.
        agent = create_react_agent(llm, tools=tools)

        from datetime import datetime, timedelta
        import re


        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        timezone = "Asia/Kolkata"

        # Attempt to extract a requested time from user input (e.g. "4pm", "10:30 AM", "14:00")
        user_req = state.get("user_input", "")
        requested_start = None
        time_pattern = re.compile(
            r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b', re.IGNORECASE
        )
        match = time_pattern.search(user_req)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            meridiem = match.group(3).lower()
            if meridiem == "pm" and hour != 12:
                hour += 12
            elif meridiem == "am" and hour == 12:
                hour = 0
            # Default to tomorrow if user said "tomorrow", else today
            base_day = tomorrow if "tomorrow" in user_req.lower() else now
            requested_start = base_day.replace(hour=hour, minute=minute, second=0, microsecond=0)
        else:
            # No time found — default to tomorrow 10 AM
            requested_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

        start_iso = requested_start.strftime("%Y-%m-%dT%H:%M:%S")
        # Default duration: 1 hour
        end_iso = (requested_start + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")

        # Adjust instructions based on risk escalation vs. direct scheduling request
        if state.get("risk_flag"):
            emergency_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
            emergency_end = (emergency_start + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
            emergency_start_iso = emergency_start.strftime("%Y-%m-%dT%H:%M:%S")
            instructions = (
                f"Call GOOGLECALENDAR_CREATE_EVENT with these EXACT parameters:\n"
                f'  summary: "Emergency Medical Consultation - Patient {state.get("patient_id")}"\n'
                f'  start_datetime: "{emergency_start_iso}"\n'
                f'  end_datetime: "{emergency_end}"\n'
                f'  description: "High-priority medical appointment. Patient requires immediate doctor attention."\n'
                f'  calendar_id: "primary"\n'
                f"Do NOT change any values. Do NOT interpret dates. Pass these exact strings."
            )
        else:
            instructions = (
                f"Call GOOGLECALENDAR_CREATE_EVENT with these EXACT parameters:\n"
                f'  summary: "Medical Consultation - Patient {state.get("patient_id")}"\n'
                f'  start_datetime: "{start_iso}"\n'
                f'  end_datetime: "{end_iso}"\n'
                f'  description: "Appointment requested by patient. User request: {user_req}"\n'
                f'  calendar_id: "primary"\n'
                f"Do NOT change any values. Do NOT interpret dates. Pass these exact strings to the tool."
            )

        print(f"[Scheduling] Resolved start_datetime={start_iso}, end_datetime={end_iso}")
        print(f"[Scheduling] Invoking react agent with instructions...")
        response = agent.invoke({"messages": [HumanMessage(content=instructions)]}, config)

        # Print all messages for debugging
        for i, msg in enumerate(response["messages"]):
            print(f"[Scheduling] Message {i} ({type(msg).__name__}): {msg.content[:200] if msg.content else '(no content)'}")

        output = response["messages"][-1].content

        prefix = "⚠️ High risk detected. " if state.get("risk_flag") else "📅 "
        return {
            "final_response": f"{prefix}Appointment scheduled via Google Calendar.\nDetails: {output}"
        }

    except Exception as e:
        import traceback
        print(f"[Scheduling] EXCEPTION: {traceback.format_exc()}")
        prefix = "⚠️ High risk detected. " if state.get("risk_flag") else ""
        return {
            "final_response": f"{prefix}Attempted to schedule an appointment but encountered an error: {str(e)}."
        }

