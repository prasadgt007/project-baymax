from dotenv import load_dotenv
load_dotenv()

from baymax.graph import build_graph
from baymax.briefs import generate_pre_consultation_brief

def main():
    print("Initializing Project Baymax Multi-Agent System...")
    app = build_graph()
    
    # Test Case 1: Low Risk
    print("\n--- TEST CASE 1: Low Risk ---")
    state1 = {
        "patient_id": "P002",  # Jane Smith
        "user_input": "I have a mild headache that has been bothering me since morning."
    }
    
    result1 = app.invoke(state1)
    print(f"Final Response:\n{result1.get('final_response')}")
    
    # Generate brief for the doctor
    symptoms = result1.get("structured_symptoms", [])
    brief1 = generate_pre_consultation_brief(
        "P002", 
        symptoms, 
        result1.get("risk_flag", False),
        result1.get("escalation_reason", "")
    )
    print(f"\n{brief1}")


    # Test Case 2: High Risk
    print("\n--- TEST CASE 2: High Risk ---")
    state2 = {
        "patient_id": "P001",  # John Doe
        "user_input": "My chest hurts really bad and my left arm is numb."
    }
    
    result2 = app.invoke(state2)
    print(f"Final Response:\n{result2.get('final_response')}")
    
    symptoms = result2.get("structured_symptoms", [])
    brief2 = generate_pre_consultation_brief(
        "P001", 
        symptoms, 
        result2.get("risk_flag", False),
        result2.get("escalation_reason", "")
    )
    print(f"\n{brief2}")

if __name__ == "__main__":
    main()
