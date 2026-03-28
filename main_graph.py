# main_graph.py
from langgraph.graph import StateGraph, END
from state import ContentState
from config import Config

def create_workflow():
    # Initialize the graph
    workflow = StateGraph(ContentState)
    
    # We will add nodes here in future commits
    # workflow.add_node("intake", intake_agent)
    # workflow.add_node("draft", drafting_agent)
    
    # Set entry point
    workflow.set_entry_point("intake")
    
    return workflow.compile()

# Test import
if __name__ == "__main__":
    print("Workflow skeleton created successfully.")