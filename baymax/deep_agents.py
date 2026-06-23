from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.prompts import ChatPromptTemplate
from .mcp_client import fetch_patient_profile_mcp, search_interactions_mcp
from .utils import get_skill

llm = ChatNVIDIA(model="meta/llama-3.1-8b-instruct")

def long_horizon_reasoning(patient_id: str, query: str) -> str:
    """
    Performs long-horizon reasoning over a patient's historical data.
    E.g., 'Analyze patient over last 6 months', 'Detect worsening pattern'.
    """
    profile = fetch_patient_profile_mcp(patient_id)
    if not profile:
        return "Patient profile not found."
    
    # Retrieve only semantically relevant past interactions
    relevant_interactions = search_interactions_mcp(patient_id, query=query, limit=3)
    
    history_str = f"Conditions: {profile.history.past_conditions}\n"
    history_str += f"Allergies: {profile.history.allergies}\n"
    history_str += f"Medications: {profile.history.current_medications}\n\n"
    history_str += "Relevant Past Interactions (Semantic Search Results):\n"
    
    if not relevant_interactions:
        history_str += "No directly relevant past interactions found.\n"
    else:
        for ix in relevant_interactions:
            history_str += f"- {ix.get('date', 'Unknown Date')}: {ix.get('notes', '')}\n"
        
    system_prompt = get_skill("Deep Agent")
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "Patient History:\n{history}\n\nQuery: {query}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"history": history_str, "query": query})
    
    return response.content
