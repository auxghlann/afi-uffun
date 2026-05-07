from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.services.agent import agent
from app.services.state import EmergencyState
from app.services.nodes import geo_router_node, build_dispatch_confirmation
from app.services.review_store import upsert_review, get_review
from app.services.report_store import upsert_emergency_report

router = APIRouter()

class MessageDict(BaseModel):
    role: str
    content: str

class LocationDict(BaseModel):
    latitude: float
    longitude: float

class CallRequest(BaseModel):
    call_id: str
    message: str
    location: LocationDict

class CallResponse(BaseModel):
    response_text: str
    routed_hotlines: Optional[List[Dict[str, Any]]] = None
    review_status: Optional[str] = None
    pending_review: Optional[bool] = None

@router.post("/message", response_model=CallResponse)
async def process_call_message(request: CallRequest):
    try:
        # 1. Config with thread_id for LangGraph checkpointer
        config = {"configurable": {"thread_id": request.call_id}}

        # 2. Add only the latest User message along with location
        # The memory checkpointer will load the rest of the history automatically.
        inputs = {
            "messages": [HumanMessage(content=request.message)],
            "location": {
                "latitude": request.location.latitude,
                "longitude": request.location.longitude
            }
        }

        # 3. Invoke the LangGraph agent
        final_state = agent.invoke(inputs, config)

        # 4. Extract the final response text
        final_messages = final_state.get("messages", [])
        response_text = ""
        if final_messages:
            last_message = final_messages[-1]
            if isinstance(last_message, AIMessage):
                response_text = last_message.content
            else:
                # If the last message is a ToolMessage, the AI has routed the call.
                # Find the last AIMessage content before the tool call for context,
                # or just provide a generic routing message if it dispatched successfully.
                for msg in reversed(final_messages):
                    if isinstance(msg, AIMessage) and msg.content:
                        response_text = msg.content
                        break
                
                if final_state.get("status") == "Routed" and not response_text:
                    response_text = "Help is on the way. Please stay calm."

        # 5. Extract routed hotlines if any
        routed_hotlines = final_state.get("routed_hotlines", [])
        review_status = final_state.get("review_status")
        pending_review = final_state.get("pending_review")

        if final_state.get("status") == "Routed":
            upsert_emergency_report(
                call_id=request.call_id,
                status="auto_routed",
                extracted_details=final_state.get("extracted_details", {}),
                location=final_state.get("location", {}),
                routed_hotlines=routed_hotlines
            )

        if final_state.get("status") == "pending_review":
            extracted = final_state.get("extracted_details", {})
            location = final_state.get("location", {})
            recommendations = geo_router_node({
                "location": location,
                "extracted_details": extracted
            }).get("routed_hotlines", [])

            upsert_review(request.call_id, {
                "call_id": request.call_id,
                "review_status": "pending",
                "extracted_details": extracted,
                "location": location,
                "recommended_hotlines": recommendations,
                "review_notes": ""
            })

        return CallResponse(
            response_text=response_text,
            routed_hotlines=routed_hotlines if final_state.get("status") == "Routed" else None,
            review_status=review_status,
            pending_review=pending_review
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=CallResponse)
async def get_call_status(call_id: str):
    review = get_review(call_id)
    if not review:
        return CallResponse(response_text="", review_status=None, pending_review=None)

    if review.get("review_status") == "approved":
        routed_hotlines = review.get("approved_hotlines", [])
        return CallResponse(
            response_text=build_dispatch_confirmation(routed_hotlines),
            routed_hotlines=routed_hotlines,
            review_status="approved",
            pending_review=False
        )

    if review.get("review_status") == "rejected":
        return CallResponse(
            response_text="Your report was reviewed and needs clarification. Please provide more details.",
            review_status="rejected",
            pending_review=False
        )

    return CallResponse(
        response_text="",
        review_status="pending",
        pending_review=True
    )
