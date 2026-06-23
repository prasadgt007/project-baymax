from typing import Annotated, TypedDict, List, Optional
from pydantic import BaseModel, Field
import operator

# --- Pydantic Models for Domain Entities ---

class RouterIntent(BaseModel):
    intent: str = Field(description="The user's intent. Must be 'chitchat', 'medical', 'scheduling', or 'out_of_scope'. Use 'out_of_scope' for generic requests unrelated to healthcare (e.g., food recipes, coding). Use 'chitchat' for basic greetings. Use 'medical' for symptoms. Use 'scheduling' ONLY for direct requests to book an appointment.")

class Symptom(BaseModel):
    name: str = Field(description="Name of the symptom")
    severity: str = Field(description="Severity (e.g., mild, moderate, severe)")
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

# --- Graph State ---

class BaymaxState(TypedDict):
    """The state dictionary for the LangGraph."""
    patient_id: str
    user_input: str
    
    # Routing
    intent: Optional[str]
    
    # State fields updated by agents
    structured_symptoms: Optional[List[Symptom]]
    patient_profile: Optional[PatientProfile]
    
    risk_flag: bool
    escalation_reason: Optional[str]
    
    proposed_guidance: Optional[str]
    compliance_passed: bool
    
    final_response: str
