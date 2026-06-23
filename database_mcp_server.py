import json
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import List, Optional
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from dotenv import load_dotenv

load_dotenv()

# We still use the embedder to do local in-memory semantic search!
embedder = NVIDIAEmbeddings(model="nvidia/nv-embedqa-e5-v5")

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

MOCK_PATIENTS = {
    "P001": PatientProfile(
        patient_id="P001",
        name="John Doe",
        age=45,
        history=PatientHistory(
            patient_id="P001",
            past_conditions=["Hypertension", "Asthma"],
            allergies=["Penicillin"],
            current_medications=["Lisinopril", "Albuterol Inhaler"]
        ),
        past_interactions=[
            Interaction(date="2023-01-15", notes="Routine checkup. BP stable."),
            Interaction(date="2023-05-20", notes="Complained of mild shortness of breath. Recommended continuing inhaler."),
            Interaction(date="2023-11-02", notes="Reported chest tightness during exercise. Scheduled stress test."),
            Interaction(date="2024-02-14", notes="Follow-up on asthma. Lungs clear today.")
        ]
    ),
    "P002": PatientProfile(
        patient_id="P002",
        name="Jane Smith",
        age=30,
        history=PatientHistory(
            patient_id="P002",
            past_conditions=["Migraines"],
            allergies=[],
            current_medications=["Ibuprofen as needed"]
        ),
        past_interactions=[
            Interaction(date="2023-08-10", notes="Discussed frequency of migraines. Advised keeping a trigger journal."),
            Interaction(date="2024-01-05", notes="Migraines improved. Prescribed sumatriptan for acute attacks.")
        ]
    )
}

mcp = FastMCP("BaymaxMockDatabase")

@mcp.tool()
def get_patient_profile(patient_id: str) -> str:
    """Retrieve patient profile from the mock database as a JSON string."""
    profile = MOCK_PATIENTS.get(patient_id)
    if not profile:
        return "{}"
    return profile.model_dump_json()

def cosine_similarity(v1, v2):
    import math
    dot = sum(x*y for x, y in zip(v1, v2))
    mag1 = math.sqrt(sum(x*x for x in v1))
    mag2 = math.sqrt(sum(y*y for y in v2))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)

@mcp.tool()
def search_interactions(patient_id: str, query: str, limit: int = 3) -> str:
    """Search a patient's past interactions using local in-memory semantic search."""
    profile = MOCK_PATIENTS.get(patient_id)
    if not profile or not profile.past_interactions:
        return "[]"
    
    try:
        # Embed the query
        query_embedding = embedder.embed_query(query)
        
        # We will embed each interaction note on the fly for testing
        # In a real app, these are pre-computed in pgvector.
        scored_interactions = []
        for interaction in profile.past_interactions:
            note_embedding = embedder.embed_query(interaction.notes)
            score = cosine_similarity(query_embedding, note_embedding)
            scored_interactions.append((score, interaction))
            
        # Sort by highest similarity
        scored_interactions.sort(key=lambda x: x[0], reverse=True)
        
        # Take top 'limit'
        top_interactions = [ix.model_dump() for score, ix in scored_interactions[:limit]]
        return json.dumps(top_interactions)
        
    except Exception as e:
        print(f"Error during in-memory semantic search: {e}")
        return "[]"

if __name__ == "__main__":
    mcp.run(transport='stdio')
