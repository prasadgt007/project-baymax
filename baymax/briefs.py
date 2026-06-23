from typing import Dict, Any
from .mcp_client import fetch_patient_profile_mcp
from .models import BaymaxState

def generate_pre_consultation_brief(patient_id: str, current_symptoms: list, risk_flag: bool, escalation_reason: str) -> str:
    """Generates a summary brief for the doctor before they see the patient."""
    profile = fetch_patient_profile_mcp(patient_id)
    if not profile:
        return "Patient Profile Not Found."

    brief = f"--- PRE-CONSULTATION BRIEF ---\n"
    brief += f"Patient ID: {profile.patient_id}\n"
    brief += f"Name: {profile.name} (Age: {profile.age})\n\n"
    
    brief += f"[ MEDICAL HISTORY ]\n"
    brief += f"Past Conditions: {', '.join(profile.history.past_conditions)}\n"
    brief += f"Allergies: {', '.join(profile.history.allergies)}\n"
    brief += f"Current Medications: {', '.join(profile.history.current_medications)}\n\n"
    
    brief += f"[ CURRENT SYMPTOMS ]\n"
    for s in current_symptoms:
        brief += f"- {s.name} (Severity: {s.severity}, Duration: {s.duration})\n"
        
    brief += "\n[ RISK ASSESSMENT ]\n"
    if risk_flag:
        brief += f"⚠️ HIGH RISK DETECTED ⚠️\nReason: {escalation_reason}\n"
    else:
        brief += "Status: SAFE (No immediate red flags detected)\n"
        
    return brief
