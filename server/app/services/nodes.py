from typing import Literal, List
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage
from langgraph.graph import END
from app.core.llm import get_operator_llm

from app.services.state import EmergencyState
from app.services.schema import EmergencyDetails
from app.services.utils import haversine_distance


def _load_raw_toon(filename: str) -> str:
    """Load a TOON file as raw text for direct injection into LLM prompts."""
    from pathlib import Path
    data_dir = Path(__file__).parent.parent / "data"
    with open(data_dir / filename, "r", encoding="utf-8") as f:
        return f.read()


# Load raw TOON content once at import time — already token-efficient
_KNOWLEDGE_TOON = _load_raw_toon("emergency_knowledge.toon")

# System Prompt for the Operator
OPERATOR_PROMPT = f"""You are a highly professional, calm, and efficient 911 Emergency First Responder Dispatcher acting as an AI operator.
Your primary goal is to assess the caller's emergency, gather critical information, and dispatch the correct hotline.

You must communicate naturally, empathetically, and efficiently. You can speak English, Tagalog, or Taglish, matching the caller's language.

EMERGENCY INTELLIGENCE (use this to INFER details — do NOT ask the caller for info you can deduce):
Format: keywords, responder types, default_severity, people_affected, is_ongoing
{_KNOWLEDGE_TOON}

CRITICAL INFORMATION NEEDED FOR DISPATCH:
1. What is the emergency? (To determine type)
2. Location details (landmarks, street, barangay — always confirm)
3. Severity (infer from the intelligence table above if the emergency type is obvious)
4. People affected (infer from the intelligence table above if possible)
5. Is it ongoing? (infer from the intelligence table above if possible)

ABSOLUTE RULES (NEVER BREAK THESE):
- You MUST know WHAT the emergency is before dispatching. If the caller only says "help", "tulong", or something vague without specifying what is happening, you MUST ask: "Ano po ang nangyari?" or "What is the emergency?". NEVER dispatch without knowing the emergency type.
- You MUST ask for location details before dispatching. If the caller hasn't mentioned where they are, ask.
- When using the EmergencyDetails tool, the emergency_types field must be COMMA-separated (e.g. "Police, Medical"), NOT pipe-separated.

SMART DISPATCH RULES:
- Use the Emergency Intelligence table to INFER severity, people_affected, and is_ongoing whenever the emergency type is clear. DO NOT ask the caller redundant questions.
- Once you know WHAT the emergency is and WHERE, you may dispatch. Use the intelligence table to fill in severity, people_affected, and is_ongoing.
- For HIGH severity emergencies (bomb, shooting, fire, flood, earthquake, accident):
  → Confirm the emergency type + ask for location, then DISPATCH using the EmergencyDetails tool.
  → Do NOT ask "how many people are affected" or "is it life-threatening" — you already know.
- For MEDIUM/LOW severity emergencies (robbery, missing person):
  → You may ask 1-2 follow-up questions to clarify before dispatching.
- NEVER ask more than 2 questions total before dispatching.
- When dispatching, include ALL relevant responder types from the intelligence table. For example:
  - A vehicle accident needs BOTH Police AND Medical.
  - A building fire needs BOTH Fire AND Rescue.
- DO NOT invent information. But DO use the intelligence table to fill in what is obvious.
- Only invoke the EmergencyDetails tool when you have BOTH the emergency type and location details.
- After invoking the tool, the case will be reviewed by the command center before dispatch.
- Once you invoke the tool, do NOT add conversational filler. A separate confirmation step will follow.
"""

def operator_node(state: EmergencyState):
    """The conversational LLM node that decides whether to reply or invoke the tool."""
    # Get the configured LLM from core config
    llm = get_operator_llm()

    # Bind the extraction tool
    llm_with_tools = llm.bind_tools([EmergencyDetails])

    # Ensure system prompt is first
    messages = state.get("messages", [])
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=OPERATOR_PROMPT)] + messages

    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

def operator_router(state: EmergencyState) -> Literal["extract_details", END]:
    """Routes the graph based on whether the operator called a tool or just replied."""
    last_message = state["messages"][-1]
    # If the LLM made a tool call, we transition to extracting details
    if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
        return "extract_details"
    return END

def extract_details_node(state: EmergencyState):
    """Parses the tool call arguments into the extracted_details state."""
    last_message = state["messages"][-1]

    # Extract the arguments from the first tool call
    tool_call = last_message.tool_calls[0]
    args = tool_call["args"]

    # Create a ToolMessage to satisfy LangGraph's message sequence rules
    tool_message = ToolMessage(
        content="Emergency details successfully extracted and logged.",
        tool_call_id=tool_call["id"]
    )

    return {
        "messages": [tool_message],
        "extracted_details": args,
        "status": "ready_to_route"
    }

def _missing_critical_fields(extracted: dict) -> List[str]:
    """Return a list of missing critical fields needed before routing."""
    missing = []
    emergency_types = str(extracted.get("emergency_types", "")).strip()
    location_details = str(extracted.get("location_details", "")).strip()

    if not emergency_types:
        missing.append("emergency_types")
    if not location_details:
        missing.append("location_details")

    return missing

def readiness_check_node(state: EmergencyState):
    """Ensure emergency type and location details are present before routing."""
    extracted = state.get("extracted_details", {})
    missing = _missing_critical_fields(extracted)

    if not missing:
        return {"status": "ready_to_route"}

    if "emergency_types" in missing:
        message = "Ano po ang nangyari?"
    else:
        message = "Saan po ito nangyari?"

    return {
        "messages": [AIMessage(content=message)],
        "status": "needs_more_info"
    }

def admin_review_node(state: EmergencyState):
    """Pause the flow for human-in-the-middle review."""
    return {
        "messages": [AIMessage(content=(
            "Salamat. Na-receive na ang report. "
            "Our command center is reviewing the details and will confirm the response shortly."
        ))],
        "pending_review": True,
        "review_status": "pending",
        "review_notes": "",
        "status": "pending_review"
    }

def _resolve_preferred_types(emergency_types_str: str) -> List[str]:
    """Parse emergency types (comma or pipe separated) into a list of canonical hotline types."""
    # Support both comma and pipe separators (LLM may use either)
    import re
    types = [t.strip().lower() for t in re.split(r'[,|]', emergency_types_str)]
    preferred = []
    for t in types:
        if "fire" in t:
            preferred.append("Fire")
        elif "police" in t or "crime" in t:
            preferred.append("Police")
        elif "medical" in t or "health" in t or "ambulance" in t:
            preferred.append("Medical")
        elif "rescue" in t:
            preferred.append("Rescue")
    # Deduplicate while preserving order
    seen = set()
    return [x for x in preferred if not (x in seen or seen.add(x))]

def geo_router_node(state: EmergencyState):
    """Calculates the nearest appropriate hotline(s) based on GPS location and emergency types."""
    from app.database import SessionLocal
    from app.models.schema import Hotline

    user_loc = state.get("location", {})
    user_lat = user_loc.get("latitude", 17.6134)
    user_lon = user_loc.get("longitude", 121.7269)

    extracted = state.get("extracted_details", {})
    emergency_types_str = extracted.get("emergency_types", "Rescue")

    preferred_types = _resolve_preferred_types(emergency_types_str)
    if not preferred_types:
        preferred_types = ["Rescue"]  # fallback

    db = SessionLocal()
    routed_hotlines = []
    
    try:
        # Find the nearest hotline for EACH preferred type
        for ptype in preferred_types:
            best_hotline = None
            shortest_dist = float('inf')
            
            # Query the database for hotlines matching this type
            hotlines = db.query(Hotline).filter(Hotline.type == ptype).all()
            
            for hotline in hotlines:
                dist = haversine_distance(user_lat, user_lon, hotline.lat, hotline.lon)
                if dist < shortest_dist:
                    shortest_dist = dist
                    best_hotline = hotline
            
            if best_hotline:
                routed_hotlines.append({
                    "id": best_hotline.id,
                    "name": best_hotline.name,
                    "type": best_hotline.type,
                    "lat": best_hotline.lat,
                    "lon": best_hotline.lon,
                    "contact": best_hotline.contact,
                    "distance_km": round(shortest_dist, 2)
                })
    finally:
        db.close()

    return {"routed_hotlines": routed_hotlines}

def build_dispatch_confirmation(routed_hotlines: List[dict]) -> str:
    """Build a confirmation message for approved dispatch."""
    if not routed_hotlines:
        return "Confirmed. Dispatching responders now. Please stay calm and keep your line open."

    types = [h.get("type") for h in routed_hotlines if h.get("type")]
    deduped = []
    for t in types:
        if t not in deduped:
            deduped.append(t)

    type_list = ", ".join(deduped) if deduped else "responders"
    return f"Confirmed. Dispatching {type_list} now. Please stay calm and keep your line open."

def dispatch_confirmation_node(state: EmergencyState):
    """Provide a clear confirmation that help has been dispatched."""
    routed_hotlines = state.get("routed_hotlines", [])
    message = build_dispatch_confirmation(routed_hotlines)
    return {"messages": [AIMessage(content=message)]}

def simulation_node(state: EmergencyState):
    """Finalizes the workflow payload."""
    return {"status": "Routed"}
