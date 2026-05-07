from typing import Annotated, TypedDict, Dict, Any, List
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class EmergencyState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    location: Dict[str, Any]           # Raw GPS from the caller's device: {latitude, longitude}
    resolved_location: Dict[str, Any]  # Authoritative coords after geocoding: {latitude, longitude, source}
                                       # source is "extracted" (from speech) or "gps" (fallback)
    extracted_details: Dict[str, Any]
    routed_hotlines: List[Dict[str, Any]]  # Multiple hotlines can be dispatched
    pending_review: bool
    review_status: str  # pending | approved | rejected
    review_notes: str
    status: str
