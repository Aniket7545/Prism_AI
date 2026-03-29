"""
REST API for BrandGuard AI - n8n Integration
Exposes workflow endpoints for external automation platforms
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import asyncio
from datetime import datetime
from workflow import create_workflow
from services.database import audit_db

# Initialize FastAPI
app = FastAPI(
    title="BrandGuard AI - Enterprise Content Operations API",
    description="Multi-agent AI system for content generation, compliance checking, and publishing",
    version="1.0.0"
)

# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class ContentRequest(BaseModel):
    """Input model for content processing"""
    raw_content: str
    topic: str
    target_channel: str = "Blog"
    target_region: str = "Global"
    content_type: str = "Article"
    urgency: str = "Medium"
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        example = {
            "raw_content": "Our new product innovation revolutionizes the market",
            "topic": "Product Launch Announcement",
            "target_channel": "Blog",
            "target_region": "US",
            "content_type": "Article",
            "urgency": "High"
        }


class WorkflowResponse(BaseModel):
    """Output model for workflow execution"""
    session_id: str
    status: str
    stage: str
    draft_content: Optional[str] = None
    compliance_status: Optional[str] = None
    published_url: Optional[str] = None
    publish_results: Optional[List[Dict]] = None
    timestamp: str
    message: str


class WorkflowStatusResponse(BaseModel):
    """Response for workflow status queries"""
    session_id: str
    status: str
    current_stage: str
    completion_percentage: int
    elapsed_time: float
    results: Optional[Dict[str, Any]] = None


# ============================================
# GLOBAL STATE
# ============================================

workflow_app = None
active_sessions = {}  # Track active workflow executions

def get_workflow():
    """Get or create workflow instance"""
    global workflow_app
    if workflow_app is None:
        workflow_app = create_workflow()
    return workflow_app


# ============================================
# API ENDPOINTS
# ============================================

@app.on_event("startup")
async def startup_event():
    """Initialize workflow on startup"""
    print("[API] BrandGuard AI API Starting...")
    get_workflow()
    print("[API] Workflow initialized successfully")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "BrandGuard AI Content Operations",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/v1/process", response_model=WorkflowResponse)
async def process_content(request: ContentRequest, background_tasks: BackgroundTasks):
    """
    Process content through the full workflow
    Returns immediate response with session ID for polling
    """
    try:
        session_id = str(uuid.uuid4())
        
        # Initialize state
        initial_state = {
            "session_id": session_id,
            "input_file_path": "api_input",
            "raw_content": request.raw_content,
            "topic": request.topic,
            "target_channel": request.target_channel,
            "target_region": request.target_region,
            "draft_content": "",
            "compliance_report": {},
            "localization_content": "",
            "published_url": "",
            "audit_log": [],
            "iteration_count": 0,
            "human_approval": "pending",
            "human_feedback": "",
            "needs_revision": False,
            "start_time": datetime.now().timestamp(),
            "end_time": 0.0,
            "content_metadata": {},
            "content_type": request.content_type,
            "structured_data": {},
            "engagement_metrics": {},
            "performance_analysis": {},
            "insights": {},
            "human_feedback_severity": "medium"
        }
        
        # Track session
        active_sessions[session_id] = {
            "status": "processing",
            "stage": "intake",
            "start_time": datetime.now().timestamp(),
            "request": request.dict()
        }
        
        # Run workflow in background
        background_tasks.add_task(run_workflow_async, session_id, initial_state)
        
        audit_db.log_event(
            session_id,
            "API",
            "Content Processing Started",
            request.topic,
            "",
            "Initiated",
            {"channel": request.target_channel, "region": request.target_region}
        )
        
        return WorkflowResponse(
            session_id=session_id,
            status="processing",
            stage="intake",
            timestamp=datetime.now().isoformat(),
            message=f"Workflow started. Use session_id to check status: {session_id}"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {str(e)}")


@app.get("/api/v1/status/{session_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(session_id: str):
    """
    Get current status of a workflow execution
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    session = active_sessions[session_id]
    elapsed = datetime.now().timestamp() - session.get("start_time", datetime.now().timestamp())
    
    # Calculate completion percentage based on current stage
    stage_progress = {
        "intake": 15,
        "draft": 35,
        "compliance": 55,
        "localize": 70,
        "publish": 85,
        "analytics": 95,
        "completed": 100
    }
    
    completion = stage_progress.get(session.get("stage", "intake"), 50)
    
    return WorkflowStatusResponse(
        session_id=session_id,
        status=session.get("status", "processing"),
        current_stage=session.get("stage", "unknown"),
        completion_percentage=completion,
        elapsed_time=elapsed,
        results=session.get("results")
    )


@app.get("/api/v1/result/{session_id}")
async def get_workflow_result(session_id: str):
    """
    Get final results of a completed workflow
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    session = active_sessions[session_id]
    
    if session.get("status") != "completed":
        raise HTTPException(
            status_code=202,
            detail=f"Workflow still processing. Current stage: {session.get('stage')}"
        )
    
    return {
        "session_id": session_id,
        "status": "completed",
        "results": session.get("results", {}),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/v1/publish")
async def direct_publish(request: ContentRequest):
    """
    Publish content directly without full workflow
    Useful for n8n workflows that have already done validation
    """
    try:
        session_id = str(uuid.uuid4())
        
        from agents.publish_agent import publish_agent
        
        state = {
            "session_id": session_id,
            "topic": request.topic,
            "target_channel": request.target_channel,
            "localization_content": request.raw_content,
            "target_region": request.target_region
        }
        
        result = publish_agent(state)
        
        audit_db.log_event(
            session_id,
            "API",
            "Direct Publish",
            request.topic,
            result.get("published_url", ""),
            "Success",
            {"channel": request.target_channel}
        )
        
        return {
            "session_id": session_id,
            "status": "success",
            "published_url": result.get("published_url"),
            "publish_results": result.get("publish_results", []),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Publishing failed: {str(e)}")


@app.get("/api/v1/audit/{session_id}")
async def get_audit_log(session_id: str):
    """
    Get audit trail for a session
    """
    try:
        logs = audit_db.get_session_logs(session_id)
        return {
            "session_id": session_id,
            "log_count": len(logs),
            "logs": logs,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve audit log: {str(e)}")


@app.get("/api/v1/channels")
async def list_channels():
    """
    List available publishing channels
    """
    from agents.publish_agent import PublishingChannels
    
    channels = []
    for channel_name, config in PublishingChannels.CHANNELS.items():
        channels.append({
            "name": channel_name,
            "format": config["format"],
            "path": config["path"]
        })
    
    return {
        "channels": channels,
        "total": len(channels),
        "timestamp": datetime.now().isoformat()
    }


# ============================================
# BACKGROUND TASKS
# ============================================

async def run_workflow_async(session_id: str, initial_state: Dict[str, Any]):
    """
    Execute workflow asynchronously and update session status
    """
    try:
        workflow = get_workflow()
        final_state = None
        
        # Execute workflow
        for step, state_dict in enumerate(workflow.stream(
            initial_state,
            {"recursion_limit": 25, "configurable": {"thread_id": session_id}}
        )):
            # Update current stage based on node execution
            for node_name, node_state in state_dict.items():
                if node_name != "__start__" and isinstance(node_state, dict):
                    active_sessions[session_id]["stage"] = node_name
                    final_state = node_state
        
        # Workflow completed successfully
        active_sessions[session_id]["status"] = "completed"
        active_sessions[session_id]["stage"] = "completed"
        
        if final_state:
            active_sessions[session_id]["results"] = {
                "draft_content": final_state.get("draft_content", "")[:500],
                "compliance_passed": final_state.get("compliance_report", {}).get("passed", False),
                "published_url": final_state.get("published_url", ""),
                "publish_results": final_state.get("publish_results", []),
                "engagement_metrics": final_state.get("engagement_metrics", {}),
                "final_state_keys": list(final_state.keys())
            }
        
        audit_db.log_event(
            session_id,
            "API",
            "Workflow Completed",
            "Processing finished successfully",
            active_sessions[session_id].get("results", {}).get("published_url", ""),
            "Success",
            active_sessions[session_id].get("results", {})
        )
        
    except Exception as e:
        active_sessions[session_id]["status"] = "failed"
        active_sessions[session_id]["error"] = str(e)
        
        audit_db.log_event(
            session_id,
            "API",
            "Workflow Failed",
            f"Error: {str(e)}",
            "",
            "Failed",
            {"error": str(e)}
        )


# ============================================
# N8N WEBHOOK LISTENER
# ============================================

@app.post("/webhooks/n8n/content")
async def n8n_webhook(request: ContentRequest):
    """
    n8n webhook receiver - processes content requests from n8n workflows
    Configure this URL in n8n Webhook node
    """
    return await process_content(request, BackgroundTasks())


@app.post("/webhooks/n8n/publish")
async def n8n_publish_webhook(request: ContentRequest):
    """
    n8n webhook for direct publishing
    """
    return await direct_publish(request)


# ============================================
# DOCS AND METADATA
# ============================================

@app.get("/api/v1/info")
async def system_info():
    """
    Get system information and capabilities
    """
    return {
        "system": "BrandGuard AI - Enterprise Content Operations",
        "version": "1.0.0",
        "capabilities": [
            "Content generation via LLM",
            "Multi-layer compliance checking",
            "Content localization",
            "Multi-channel publishing",
            "Performance analytics",
            "Audit trail tracking"
        ],
        "agents": [
            "intake_agent",
            "drafting_agent",
            "compliance_agent",
            "localization_agent",
            "publish_agent",
            "analytics_agent"
        ],
        "integrations": [
            "n8n",
            "REST API",
            "Webhooks",
            "SQLite Database",
            "ChromaDB Vector Store"
        ],
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)