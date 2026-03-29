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
import time

def create_workflow():
    workflow = StateGraph(ContentState)
    
    # Add all nodes
    workflow.add_node("intake", intake_agent)
    workflow.add_node("draft", drafting_agent)
    workflow.add_node("compliance", compliance_agent)
    workflow.add_node("localize", localization_agent)
    workflow.add_node("publish", publish_agent)
    workflow.add_node("analytics", analytics_agent)
    
    # Human gate node - waits for approval before proceeding
    def human_gate(state):
        """
        Log the approval request and signal to pause execution.
        The workflow will remain at this node until manually approved via API.
        """
        approval_status = state.get("human_approval", "pending")
        session_id = state.get("session_id", "unknown")
        print(f"\n[WORKFLOW] {session_id} reached HUMAN_GATE with approval_status='{approval_status}'")
        
        audit_db.log_event(
            state["session_id"], 
            "System", 
            "Human Gate", 
            f"Approval: {approval_status}", 
            "Awaiting" if approval_status == "pending" else approval_status, 
            "Paused", 
            {
                "category": state.get("compliance_report", {}).get("category", "general"),
                "risk_level": state.get("compliance_report", {}).get("risk_level", "low"),
                "issues": len(state.get("compliance_report", {}).get("issues", []))
            }
        )
        
        # If still pending, return state unchanged (will trigger conditional routing)
        # The conditional will keep workflow paused at this node until approval
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
        """
        Route based on human approval decision.
        If pending, exit workflow to pause execution.
        """
        session_id = state.get("session_id", "unknown")
        approval = state.get("human_approval", "")
        
        print(f"[WORKFLOW] {session_id} route_after_human called with approval='{approval}'")
        
        if approval == "approved":
            print(f"[WORKFLOW] {session_id} approval=approved -> routing to 'publish'")
            return "publish"
        elif approval == "rejected":
            # Reset for new draft cycle
            state["needs_revision"] = True
            state["iteration_count"] = state.get("iteration_count", 0) + 1
            print(f"[WORKFLOW] {session_id} approval=rejected -> routing to 'draft'")
            return "draft"
        else:
            # Pending approval - exit workflow to pause
            print(f"[WORKFLOW] {session_id} approval not approved/rejected ('{approval}') -> returning END to pause workflow")
            return END
    
    workflow.add_conditional_edges("human_gate", route_after_human)
    workflow.add_edge("publish", "analytics")
    workflow.add_edge("analytics", END)
    
    # Compile with memory checkpointer
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    return app