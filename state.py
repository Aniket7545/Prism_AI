# state.py
from typing import Annotated, List, Dict, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

class ContentState(TypedDict):
    input_topic: str
    input_raw_data: str
    target_channel: str
    messages: Annotated[List[Any], add_messages]
    draft_content: str
    compliance_report: Dict[str, Any]
    next_step: str
    approval_status: str
    human_feedback: str
    audit_log: List[Dict[str, Any]]
    start_time: float
    end_time: float