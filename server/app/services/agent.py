from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.services.state import EmergencyState
from app.services.nodes import (
    operator_node,
    operator_router,
    extract_details_node,
    readiness_check_node,
    admin_review_node,
    geo_router_node,
    dispatch_confirmation_node,
    simulation_node
)

# --- Graph Compilation ---
workflow = StateGraph(EmergencyState)

# Add nodes
workflow.add_node("operator", operator_node)
workflow.add_node("extract_details", extract_details_node)
workflow.add_node("readiness_check", readiness_check_node)
workflow.add_node("admin_review", admin_review_node)
workflow.add_node("geo_router", geo_router_node)
workflow.add_node("dispatch_confirmation", dispatch_confirmation_node)
workflow.add_node("simulation", simulation_node)

# Set entry point
workflow.set_entry_point("operator")

# Add edges
workflow.add_conditional_edges("operator", operator_router)
workflow.add_edge("extract_details", "readiness_check")
workflow.add_conditional_edges(
    "readiness_check",
    lambda state: "admin_review" if state.get("status") == "ready_to_route" else END
)
workflow.add_edge("admin_review", END)
workflow.add_edge("geo_router", "dispatch_confirmation")
workflow.add_edge("dispatch_confirmation", "simulation")
workflow.add_edge("simulation", END)

# Compile graph with MemorySaver for stateless API handling
memory = MemorySaver()
agent = workflow.compile(checkpointer=memory)

