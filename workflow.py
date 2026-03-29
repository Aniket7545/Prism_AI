# workflow.py
from langgraph.graph import StateGraph, END
from state import ContentState
from agents.intake_agent import intake_agent
from agents.drafting_agent import drafting_agent
from agents.compliance_agent import compliance_agent
from agents.localization_agent import localization_agent
from agents.publish_agent import publish_agent
from agents.analytics_agent import analytics_agent
from services.database import audit_db
from langgraph.checkpoint.memory import MemorySaver

def create_workflow():
    workflow = StateGraph(ContentState)
    
    # Add all nodes
    workflow.add_node("intake", intake_agent)
    workflow.add_node("draft", drafting_agent)
    workflow.add_node("compliance", compliance_agent)
    workflow.add_node("localize", localization_agent)
    workflow.add_node("publish", publish_agent)
    workflow.add_node("analytics", analytics_agent)
    
    # Human gate node
    def human_gate(state):
        audit_db.log_event(
            state["session_id"], 
            "System", 
            "Human Gate", 
            f"Approval: {state.get('human_approval', 'pending')}", 
            "Pending", 
            "Paused", 
            {"iteration": state.get("iteration_count", 0)}
        )
        return state
    
    workflow.add_node("human_gate", human_gate)
    
    # Set entry point
    workflow.set_entry_point("intake")
    
    # Build edges - Sequential flow with features
    workflow.add_edge("intake", "draft")
    
    def route_after_compliance(state):
        if state.get("needs_revision", False) and state.get("iteration_count", 0) < 5:
            return "draft"
        elif state.get("needs_revision", False):
            return "human_gate"
        else:
            return "localize"
    
    workflow.add_edge("draft", "compliance")
    workflow.add_conditional_edges("compliance", route_after_compliance)
    workflow.add_edge("localize", "human_gate")
    
    def route_after_human(state):
        approval = state.get("human_approval", "")
        
        if approval == "approved":
            return "publish"
        elif approval == "rejected":
            # Reset needs_revision for the new draft cycle
            return "draft"
        else:
            # Stay at human_gate if no decision yet
            return "human_gate"
    
    workflow.add_conditional_edges("human_gate", route_after_human)
    workflow.add_edge("publish", "analytics")
    workflow.add_edge("analytics", END)
    
    # Compile with memory
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory, interrupt_before=["human_gate"])
    return app