# state.py
from typing import Annotated, List, Dict, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

class ContentState(TypedDict):
    """
    The central state object passed between all agents.
    """
    # Input Data
    input_topic: str
    input_raw_data: str
    target_channel: str # e.g., LinkedIn, Blog
    
    # Workflow Data
    messages: Annotated[List[Any], add_messages] # Chat history for agents
    draft_content: str
    compliance_report: Dict[str, Any] # {status, flags, reasoning}
    
    # Control Flow
    next_step: str # 'draft', 'compliance', 'human_review', 'publish'
    approval_status: str # 'pending', 'approved', 'rejected'
    human_feedback: str
    
    # Audit & Metrics
    audit_log: List[Dict[str, Any]] # List of {agent, action, timestamp}
    start_time: float
    end_time: float