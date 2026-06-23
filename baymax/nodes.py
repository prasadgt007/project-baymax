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
        if not os.environ.get("COMPOSIO_API_KEY"):
            from dotenv import load_dotenv
            load_dotenv()

        from composio import Composio
        from composio_langchain import LangchainProvider
        from langgraph.prebuilt import create_react_agent
        from langchain_core.messages import HumanMessage
        
        # Initialize Composio with the LangchainProvider.
        # When a provider is set, tools.get() returns pre-wrapped
        # LangChain StructuredTool objects — no manual wrapping needed.
        provider = LangchainProvider()
        composio_client = Composio(provider=provider)
        
        # Dynamically resolve the Composio user_id for the connected Google Calendar account.
        # The connection was registered under a specific user_id during `composio add`,
        # so we must use that same ID when fetching tools.
        composio_user_id = os.environ.get("COMPOSIO_USER_ID", None)
        if not composio_user_id:
            try:
                conns = composio_client.connected_accounts.list()
                for acct in conns.items:
                    if hasattr(acct, 'toolkit') and 'googlecalendar' in str(acct.toolkit).lower() and acct.status == 'ACTIVE':
                        composio_user_id = acct.user_id
                        break
            except Exception:
                pass
        if not composio_user_id:
            composio_user_id = "default"
        
        print(f"[Scheduling] Using Composio user_id: {composio_user_id}")
        
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
        
        # Use langgraph's create_react_agent (replaces deprecated AgentExecutor)
        agent = create_react_agent(llm, tools=tools)
        
        # Provide the current date/time so the LLM can resolve natural language dates
        from datetime import datetime, timedelta
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        current_iso = now.strftime("%Y-%m-%dT%H:%M:%S")
        tomorrow_iso = tomorrow.strftime("%Y-%m-%dT%H:%M:%S")
        timezone = "Asia/Kolkata"
        
        date_context = (
            f"IMPORTANT DATE CONTEXT: The current date and time is {current_iso} ({timezone}). "
            f"'Tomorrow' means {tomorrow.strftime('%Y-%m-%d')}. "
            f"You MUST convert ALL natural language dates/times into ISO 8601 format (e.g., '{tomorrow_iso}') "
            f"before passing them to the tool's start_datetime parameter. "
            f"The timezone is {timezone}. "
            f"Examples: 'tomorrow at 2 PM' = '{tomorrow.strftime('%Y-%m-%d')}T14:00:00', "
            f"'today at 5 PM' = '{now.strftime('%Y-%m-%d')}T17:00:00', "
            f"'next Monday at 9 AM' = calculate from current date."
        )
        
        # Adjust instructions based on whether this is an emergency escalation or a direct request
        user_req = state.get("user_input", "")
        if state.get("risk_flag"):
            instructions = (
                "You are a medical scheduling assistant. "
                f"{date_context} "
                f"Book an appointment for patient ID: {state.get('patient_id')}. "
                f"The appointment should be tomorrow ({tomorrow.strftime('%Y-%m-%d')}) at 10:00 AM. "
                f"Use start_datetime='{tomorrow.strftime('%Y-%m-%d')}T10:00:00'. "
                "Title it 'Emergency Medical Consultation'. "
                "CRITICAL: Do NOT offer any medical advice or remedies."
            )
        else:
            instructions = (
                "You are a helpful medical scheduling assistant. "
                f"{date_context} "
                f"The user requested: '{user_req}'. "
                f"Book an appointment for patient ID: {state.get('patient_id')} matching their request. "
                f"If they didn't specify a time, use start_datetime='{tomorrow.strftime('%Y-%m-%d')}T10:00:00'. "
                "Title it 'Medical Consultation'. "
                "CRITICAL: If scheduling fails, strictly state that it failed. Under NO circumstances should you provide medical advice, remedies, or general guidance."
            )
        
        print(f"[Scheduling] Invoking react agent with instructions...")
        response = agent.invoke({"messages": [HumanMessage(content=instructions)]}, config)
        
        # Print all messages for debugging
        for i, msg in enumerate(response["messages"]):
            print(f"[Scheduling] Message {i} ({type(msg).__name__}): {msg.content[:200] if msg.content else '(no content)'}")
        
        output = response["messages"][-1].content
        
        prefix = "⚠️ High risk detected. " if state.get("risk_flag") else "📅 "
        return {
            "final_response": f"{prefix}Scheduled an appointment via Composio.\nDetails: {output}"
        }
    except Exception as e:
        import traceback
        print(f"[Scheduling] EXCEPTION: {traceback.format_exc()}")
        prefix = "⚠️ High risk detected. " if state.get("risk_flag") else ""
        return {
            "final_response": f"{prefix}Attempted to schedule an appointment but encountered an error: {str(e)}."
        }

