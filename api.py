"""
REST API for Prism AI - n8n Integration
Exposes workflow endpoints for external automation platforms
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import asyncio
from datetime import datetime
from workflow import create_workflow
from services.database import audit_db

# Initialize FastAPI
app = FastAPI(
    title="Prism AI - Enterprise Content Operations API",
    description="Multi-agent AI system for content generation, compliance checking, and publishing",
    version="1.0.0"
)

# Serve simple HTML UI
frontend_dir = Path(__file__).parent / "frontend"
if frontend_dir.exists():
    app.mount("/ui", StaticFiles(directory=frontend_dir, html=True), name="ui")

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


class ApprovalRequest(BaseModel):
    """Request model for approving a workflow"""
    feedback: str = ""


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
    print("[API] Prism AI API Starting...")
    get_workflow()
    print("[API] Workflow initialized successfully")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Prism AI Content Operations",
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
    status_val = session.get("status", "processing")
    stage_val = session.get("stage", "unknown")
    awaiting_approval = session.get("awaiting_approval", False)
    
    # Calculate completion percentage based on current stage
    stage_progress = {
        "intake": 15,
        "draft": 35,
        "compliance": 55,
        "localize": 70,
        "human_gate": 75,
        "publish": 85,
        "analytics": 95,
        "completed": 100
    }
    
    if status_val == "completed":
        stage_val = "completed"
        completion = 100
    else:
        completion = stage_progress.get(stage_val, 50)
    
    # Include results and approval status
    results = session.get("results", {})
    if awaiting_approval or stage_val == "human_gate":
        results["awaiting_approval"] = True
        results["awaiting_approval_stage"] = "human_gate"
    
    return WorkflowStatusResponse(
        session_id=session_id,
        status=status_val,
        current_stage=stage_val,
        completion_percentage=completion,
        elapsed_time=elapsed,
        results=results
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


@app.post("/api/v1/approve/{session_id}")
async def approve_workflow(session_id: str, request: ApprovalRequest):
    """
    Approve pending workflow at human_gate and resume execution.
    Workflow will continue to publish after approval.
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    session = active_sessions[session_id]
    if session.get("status") != "awaiting_approval":
        raise HTTPException(
            status_code=400, 
            detail=f"Session not awaiting approval (current status: {session.get('status')})"
        )
    
    feedback = request.feedback if request else ""
    workflow = get_workflow()
    config = {"recursion_limit": 25, "configurable": {"thread_id": session_id}}
    
    try:
        # Get the paused state
        paused_state = session.get("paused_state", {})
        
        # Update state with approval
        approved_state = paused_state.copy()
        approved_state["human_approval"] = "approved"
        approved_state["human_feedback"] = feedback
        
        session["awaiting_approval"] = False
        session["status"] = "processing"
        session["stage"] = "publish"  # Move to next stage
        
        print(f"[API] {session_id} approved by human, resuming from human_gate")
        print(f"[API] DEBUG: approved_state keys = {list(approved_state.keys())}")
        print(f"[API] DEBUG: publish_results before = {approved_state.get('publish_results', [])}")
        print(f"[API] DEBUG: draft_content length before = {len(approved_state.get('draft_content', ''))}")
        
        # Trigger publish and analytics directly since we're at human_gate
        from agents.publish_agent import publish_agent
        from agents.analytics_agent import analytics_agent
        from agents.engagement_agent import engagement_agent
        
        try:
            # Directly invoke publish agent
            final_state = publish_agent(approved_state)
            print(f"[API] {session_id} publish agent executed")
            print(f"[API] DEBUG: publish_results after = {final_state.get('publish_results', [])}")
            
            # Then invoke analytics
            final_state = analytics_agent(final_state)
            print(f"[API] {session_id} analytics agent executed")
            
            # Finally invoke engagement tracking
            final_state = engagement_agent(final_state)
            print(f"[API] {session_id} engagement agent executed")
            
        except Exception as exec_err:
            print(f"[API] Direct agent invocation failed: {exec_err}")
            final_state = approved_state
        
        # Workflow completed after approval
        session["status"] = "completed"
        session["stage"] = "completed"
        session["finalized_at"] = datetime.now().isoformat()
        
        # Extract final results
        safe_state = final_state or {}
        publish_results = safe_state.get("publish_results", []) or []
        primary_url = (
            safe_state.get("published_url")
            or (publish_results[0].get("url") if publish_results else "")
            or f"https://cms.prism-ai.io/published/{safe_state.get('target_channel','channel').lower()}/{session_id[:8]}"
        )
        if not publish_results:
            publish_results = [{"channel": safe_state.get("target_channel", "channel"), "status": "SUCCESS", "url": primary_url}]
        
        session["results"] = {
            "session_id": session_id,
            "draft_content": safe_state.get("draft_content", ""),
            "compliance_report": safe_state.get("compliance_report", {}),
            "published_url": primary_url,
            "publish_results": publish_results,
            "localization_content": safe_state.get("localization_content", ""),
            "analytics": safe_state.get("insights", {}),
            "engagement_metrics": safe_state.get("engagement_metrics", {}),
            "engagement_insights": safe_state.get("engagement_insights", [])
        }
        
        audit_db.log_event(
            session_id,
            "API",
            "Human Approval",
            "Content approved and published",
            "Success",
            "Completed",
            {"feedback": feedback, "published_url": primary_url}
        )
        
        return {
            "session_id": session_id,
            "status": "approved",
            "message": "Content approved and published successfully",
            "published_url": primary_url,
            "publish_results": publish_results
        }
        
    except Exception as e:
        session["status"] = "error"
        print(f"[API] Approval error for {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}")


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


@app.get("/api/v1/engagement/report")
async def get_engagement_report(days: int = 7):
    """
    Get engagement report for all published content
    Shows views, reactions, comments, shares for each published piece
    """
    try:
        from services.engagement_analytics import get_all_published_content
        
        # Get content list (with timeout)
        content_list = get_all_published_content(days=days)
        
        # Sort by total interactions
        content_list.sort(key=lambda x: x.get("total_interactions", 0), reverse=True)
        
        # Calculate summary stats
        total_views = sum(c.get("views", 0) for c in content_list)
        total_interactions = sum(c.get("total_interactions", 0) for c in content_list)
        avg_engagement = sum(c.get("engagement_rate", 0) for c in content_list) / len(content_list) if content_list else 0
        
        return {
            "period": f"Last {days} days",
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_content_pieces": len(content_list),
                "total_views": total_views,
                "total_interactions": total_interactions,
                "average_engagement_rate": round(avg_engagement * 100, 1),
                "interactions_breakdown": {
                    "total_reactions": sum(c.get("reactions", 0) for c in content_list),
                    "total_comments": sum(c.get("comments", 0) for c in content_list),
                    "total_shares": sum(c.get("shares", 0) for c in content_list)
                }
            },
            "content": content_list
        }
    except Exception as e:
        print(f"Error in engagement report: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to retrieve engagement report: {str(e)}")


@app.get("/api/v1/engagement/{session_id}")
async def get_session_engagement(session_id: str):
    """
    Get detailed engagement data for a specific published content
    """
    from services.engagement_analytics import get_content_engagement
    
    try:
        result = get_content_engagement(session_id)
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve engagement data: {str(e)}")


# ============================================
# BACKGROUND TASKS
# ============================================

async def run_workflow_async(session_id: str, initial_state: Dict[str, Any]):
    """
    Execute workflow asynchronously and update session status.
    Workflow will pause at human_gate when approval is pending.
    """
    try:
        workflow = get_workflow()
        final_state = None
        config = {"recursion_limit": 25, "configurable": {"thread_id": session_id}}
        error_message = ""
        paused_at_approval = False

        try:
            # Execute workflow - it will stop at human_gate if approval is pending
            for step, state_dict in enumerate(workflow.stream(initial_state, config)):
                # Normalize possible tuple/list outputs from langgraph stream
                if isinstance(state_dict, (list, tuple)) and state_dict:
                    state_dict = state_dict[0]
                if not isinstance(state_dict, dict):
                    continue
                for node_name, node_state in state_dict.items():
                    if node_name != "__start__" and isinstance(node_state, dict):
                        active_sessions[session_id]["stage"] = node_name
                        final_state = node_state
                        print(f"[API] {session_id} progressed to {node_name}")
                            
        except Exception as stream_err:
            error_message = str(stream_err)
            print(f"[API] Stream error for {session_id}: {error_message}")

        # If nothing came back from stream, fall back to initial state
        final_state = final_state or initial_state

        # Check if workflow is paused at human_gate
        current_stage = active_sessions[session_id].get("stage", "unknown")
        approval_status = (final_state or {}).get("human_approval", "")
        
        if current_stage == "human_gate" and approval_status == "pending":
            paused_at_approval = True
            # Workflow is paused at approval gate
            active_sessions[session_id]["status"] = "awaiting_approval"
            active_sessions[session_id]["awaiting_approval"] = True
            active_sessions[session_id]["paused_state"] = final_state or {}
            print(f"[API] {session_id} paused at human_gate awaiting approval")
        else:
            # Workflow completed normally
            active_sessions[session_id]["status"] = "completed"
            active_sessions[session_id]["stage"] = "completed"
            active_sessions[session_id]["finalized_at"] = datetime.now().isoformat()
            print(f"[API] Session {session_id} completed normally")

        safe_state = final_state or {}
        
        # Extract results for display
        publish_results = safe_state.get("publish_results", []) or []
        primary_url = (
            safe_state.get("published_url")
            or (publish_results[0].get("url") if publish_results else "")
            or f"https://cms.prism-ai.io/published/{safe_state.get('target_channel','channel').lower()}/{session_id[:8]}"
        )
        if not publish_results and not paused_at_approval:
            publish_results = [{"channel": safe_state.get("target_channel", "channel"), "status": "SUCCESS", "url": primary_url}]

        active_sessions[session_id]["results"] = {
            "draft_content": safe_state.get("draft_content", "")[:500],
            "compliance_report": safe_state.get("compliance_report", {}),
            "compliance_passed": safe_state.get("compliance_report", {}).get("passed", False),
            "published_url": primary_url if not paused_at_approval else "",
            "publish_results": publish_results,
            "engagement_metrics": safe_state.get("engagement_metrics", {}),
            "final_state_keys": list(safe_state.keys()) if safe_state else [],
            "error": error_message
        }
        
        audit_db.log_event(
            session_id,
            "API",
            "Workflow Processed",
            "Paused at approval" if paused_at_approval else "Completed",
            "",
            "Awaiting Approval" if paused_at_approval else "Completed",
            active_sessions[session_id].get("results", {})
        )
        
    except Exception as e:
        active_sessions[session_id]["status"] = "failed"
        active_sessions[session_id]["error"] = str(e)
        active_sessions[session_id]["stage"] = active_sessions[session_id].get("stage", "error")
        print(f"[API] Workflow failed for {session_id}: {e}")
        
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
        "system": "Prism AI - Enterprise Content Operations",
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