# workflow.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any
from agents.drafting_agent import drafting_agent
from agents.compliance_agent import compliance_agent
from agents.localization_agent import localization_agent
from datetime import datetime

# Define State
class AgentState(TypedDict):
    input_topic: str
    input_raw_data: str
    target_channel: str
    target_audience: str
    target_region: str
    draft_content: str
    compliance_report: Dict
    needs_revision: bool
    audit_log: List[Dict]
    iteration_count: int
    start_time: float
    end_time: float

# Human Approval Node (Interrupt)
def human_approval(state):
    print("\n--- ⏸️ HUMAN APPROVAL GATE ---")
    print("Workflow paused for human review.")
    print(f"Compliance Status: {state['compliance_report'].get('passed')}")
    # In real UI, this would wait for input. For CLI, we assume approved if passed.
    return {"approval_status": "pending"}

def create_workflow():
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("draft", drafting_agent)
    workflow.add_node("compliance", compliance_agent)
    workflow.add_node("localize", localization_agent)
    workflow.add_node("human_gate", human_approval)
    
    # Edges
    workflow.set_entry_point("draft")
    workflow.add_edge("draft", "compliance")
    
    # Conditional Edge: Compliance Check
    def route_after_compliance(state):
        if state.get("needs_revision", False) and state.get("iteration_count", 0) < 3:
            return "draft" # Loop back to drafting
        elif state.get("needs_revision", False):
            return "human_gate" # Escalate to human if auto-fix fails
        else:
            return "localize" # Proceed if compliant
            
    workflow.add_conditional_edges("compliance", route_after_compliance)
    
    workflow.add_edge("localize", "human_gate")
    workflow.add_edge("human_gate", END)
    
    # Compile with interrupt_before for Human-in-the-Loop
    app = workflow.compile(interrupt_before=["human_gate"])
    return app