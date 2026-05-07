import os
import sys
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
from dotenv import load_dotenv

# Add the server directory to sys.path so 'app.services' can be resolved
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langchain_core.messages import HumanMessage
from app.services.ai import agent, EmergencyState

# Load .env file
load_dotenv()

# Verify API key
if not os.getenv("GROQ_API_KEY"):
    print("WARNING: GROQ_API_KEY is not set correctly in your .env file!")
    print("Please set it before running this script.")
    sys.exit(1)

def run_chat_simulation():
    print("=== Emergency Hub Chat Simulation ===")
    
    # Initialize the state
    state: EmergencyState = {
        "messages": [],
        "location": {"latitude": 17.6134, "longitude": 121.7269, "city": "Tuguegarao City"},
        "extracted_details": {},
        "routed_hotlines": [],
        "status": "gathering_info"
    }

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ['exit', 'quit']:
            break
            
        state["messages"].append(HumanMessage(content=user_input))
        
        print("\nAgent is thinking...")
        # Invoke the graph
        result = agent.invoke(state)
        
        # Update our local state with the graph's resulting state
        state = result
        
        # Check if the graph ended and successfully routed
        if state.get("status") == "Routed":
            print("\n[SYSTEM] Call routed successfully!")
            print(f"Extracted Details: {state.get('extracted_details')}")
            hotlines = state.get('routed_hotlines', [])
            print(f"\nDispatched {len(hotlines)} unit(s):")
            for i, h in enumerate(hotlines, 1):
                print(f"  {i}. {h['name']} ({h['type']}) — {h['contact']} — {h.get('distance_km', '?')} km away")
            break
            
        # Otherwise, print the AI's response and loop
        last_message = state["messages"][-1]
        print(f"\nOperator: {last_message.content}")

if __name__ == "__main__":
    run_chat_simulation()
