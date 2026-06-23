import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from baymax.graph import build_graph
from baymax.briefs import generate_pre_consultation_brief

def main():
    print("="*50)
    print("🤖 Welcome to Project Baymax (CLI Mode) 🤖")
    print("="*50)
    
    # Verify LangSmith
    import os
    if os.environ.get("LANGCHAIN_TRACING_V2") == "true":
        project = os.environ.get("LANGCHAIN_PROJECT", "default")
        print(f"[System] 🔗 LangSmith Tracing is ENABLED for project: {project}")
        print("[System] You can watch your agent flows in real-time at: https://smith.langchain.com/")
    else:
        print("[System] ⚠️ LangSmith Tracing is DISABLED.")
        
    # Initialize Graph
    print("\n[System] Initializing Multi-Agent Graph...")
    app = build_graph()
    print("[System] Graph Initialized.\n")

    patient_id = input("Enter your Patient ID (e.g., P001 or P002): ").strip()
    if not patient_id:
        print("Patient ID is required. Exiting.")
        sys.exit(1)

    print(f"\n[System] Logged in as: {patient_id}")
    print("Type 'exit' or 'quit' to end the session.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break
            
        if user_input.lower() in ['exit', 'quit']:
            break
            
        if not user_input:
            continue

        print("\n[Baymax] Processing your input...")
        
        state = {
            "patient_id": patient_id,
            "user_input": user_input
        }
        
        config = {
            "configurable": {"thread_id": patient_id},
            "run_name": f"Baymax | {patient_id}",
            "metadata": {"patient_id": patient_id, "user_input": user_input},
        }
        
        try:
            # Invoke the graph with the thread isolation config
            result = app.invoke(state, config=config)
            
            final_response = result.get('final_response', "No response generated.")
            print(f"\n[Baymax]: {final_response}\n")
            
            # Print Doctor's Brief behind the scenes if it's a medical request
            intent = result.get("intent", "medical")
            if intent == "medical":
                print("-" * 50)
                print("🏥 [INTERNAL DOCTOR'S BRIEF GENERATED] 🏥")
                symptoms = result.get("structured_symptoms", [])
                brief = generate_pre_consultation_brief(
                    patient_id, 
                    symptoms, 
                    result.get("risk_flag", False),
                    result.get("escalation_reason", "")
                )
                print(brief)
                print("-" * 50 + "\n")
            
        except Exception as e:
            print(f"\n[Error] The agents encountered an issue: {e}\n")

if __name__ == "__main__":
    main()
