# main_graph.py
from langgraph.graph import StateGraph, END
from state import ContentState
from agents.compliance_agent import compliance_agent
from datetime import datetime

# Mock Draft Agent for Commit 2 (We will build real one in Commit 3)
def drafting_agent(state):
    print("--- DRAFTING AGENT STARTED ---")
    # Simple mock generation for testing compliance
    draft = f"Here is a draft about {state['input_topic']}. It is risk-free and guarantees 100% profit." 
    # ^ Intentionally included prohibited terms to test compliance agent
    
    audit_entry = {
        "timestamp": datetime.now().isoformat(),
        "agent_name": "DraftingAgent",
        "action": "Generate Draft",
        "input_summary": state['input_topic'],
        "output_summary": "Draft generated",
        "status": "Success"
    }
    
    return {
        "draft_content": draft,
        "audit_log": state["audit_log"] + [audit_entry]
    }

def create_workflow():
    workflow = StateGraph(ContentState)
    
    # Add Nodes
    workflow.add_node("draft", drafting_agent)
    workflow.add_node("compliance", compliance_agent)
    
    # Add Edges
    workflow.set_entry_point("draft")
    workflow.add_edge("draft", "compliance")
    workflow.add_edge("compliance", END)
    
    return workflow.compile()

# Test Run
if __name__ == "__main__":
    from state import ContentState
    app = create_workflow()
    
    initial_state = {
        "input_topic": "Investment Scheme",
        "input_raw_data": "Data...",
        "target_channel": "LinkedIn",
        "messages": [],
        "draft_content": "",
        "compliance_report": {},
        "next_step": "",
        "approval_status": "pending",
        "human_feedback": "",
        "audit_log": [],
        "start_time": 0,
        "end_time": 0
    }
    
    result = app.invoke(initial_state)
    print("\n--- FINAL COMPLIANCE REPORT ---")
    print(result['compliance_report'])
    print("\n--- AUDIT LOG ---")
    print(result['audit_log'])