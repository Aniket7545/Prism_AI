from typing import TypedDict, List, Dict, Any

class ContentState(TypedDict):
    """
    Complete state management for Prism AI content workflow
    Tracks all data through the 6-agent pipeline
    """
    # Essential identifiers
    session_id: str
    input_file_path: str
    
    # Content pipeline stages
    raw_content: str
    topic: str
    draft_content: str
    compliance_report: Dict[str, Any]
    localization_content: str
    
    # Targeting parameters
    target_channel: str
    target_region: str
    content_type: str
    
    # Publishing results
    published_url: str
    publish_results: List[Dict[str, Any]]
    publish_status: str
    publish_timestamp: str
    total_channels_published: int
    
    # Localization tracking
    localization_region: str
    localization_timestamp: str
    
    # Control flow
    audit_log: List[Dict[str, Any]]
    iteration_count: int
    needs_revision: bool
    human_approval: str
    human_feedback: str
    human_feedback_severity: str
    
    # Timing
    start_time: float
    end_time: float
    
    # Intake Agent outputs
    content_metadata: Dict[str, Any]
    structured_data: Dict[str, Any]
    
    # Analytics Agent outputs
    engagement_metrics: Dict[str, Any]
    performance_analysis: Dict[str, Any]
    insights: Dict[str, Any]