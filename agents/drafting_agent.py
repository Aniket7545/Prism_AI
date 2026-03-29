# agents/drafting_agent.py
from langchain_core.prompts import ChatPromptTemplate
from services.llm import llm_service
from services.vector_store import policy_store
from services.database import audit_db
from datetime import datetime

def drafting_agent(state):
    print("🤖 Drafting Agent Working...")
    llm = llm_service.get_main_llm()
    policies = policy_store.retrieve_relevant_policies(state["topic"])
    
    # Determine revision type and collect feedback
    compliance_report = state.get("compliance_report", {})
    has_compliance_issues = state.get("needs_revision", False) and compliance_report
    has_human_feedback = state.get("human_approval") == "rejected" and state.get("human_feedback", "")
    
    is_revision = has_compliance_issues or has_human_feedback
    revision_reason = ""
    feedback_content = ""
    
    if has_compliance_issues:
        # Revision triggered by compliance issues
        issues = compliance_report.get("issues", [])
        fixes = compliance_report.get("fixes", [])
        revision_reason = "COMPLIANCE FEEDBACK"
        
        issues_str = ', '.join(issues) if issues else 'Generic compliance violations'
        fixes_list = '\n'.join('- ' + str(f) for f in fixes) if fixes else '- Remove prohibited terms\n- Add regulatory disclaimer if required\n- Ensure brand compliance'
        feedback_content = f"COMPLIANCE ISSUES FOUND:\nIssues: {issues_str}\n\nREQUIRED FIXES:\n{fixes_list}"
    elif has_human_feedback:
        # Revision triggered by human feedback
        revision_reason = "HUMAN FEEDBACK"
        feedback_content = f"HUMAN FEEDBACK:\n{state.get('human_feedback', '')}"
    
    if is_revision:
        print(f"   ↻ Revising draft based on: {revision_reason}")
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an Enterprise Content Strategist.
            REVISE the content to address all feedback points.
            
            Brand Policies:
            {policies}
            
            Channel: {channel}, Region: {region}
            Iteration: {iteration}
            
            CRITICAL: 
            - Address EVERY issue mentioned
            - Ensure compliance with regulations
            - Maintain professional tone
            - Do not lose important information
            """),
            ("human", """Original Raw Data:
            {raw_data}
            
            Topic: {topic}
            
            Previous Draft:
            {previous_draft}
            
            {feedback_section}
            
            Revised Content (address all issues above):""")
        ])
        
        response = (prompt | llm).invoke({
            "policies": policies,
            "channel": state["target_channel"],
            "region": state["target_region"],
            "iteration": state.get("iteration_count", 0) + 1,
            "raw_data": state["raw_content"],
            "topic": state["topic"],
            "previous_draft": state.get("draft_content", ""),
            "feedback_section": feedback_content
        })
    else:
        # First draft (no feedback yet)
        print(f"   ✍️ Generating initial draft...")
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an Enterprise Content Strategist.
            Draft content based on the provided raw data.
            
            Brand Policies:
            {policies}
            
            Channel: {channel}, Region: {region}
            Ensure tone is professional and compliant.
            """),
            ("human", "Raw Data:\n{raw_data}\n\nTopic: {topic}\n\nDraft Content:")
        ])
        
        response = (prompt | llm).invoke({
            "policies": policies,
            "channel": state["target_channel"],
            "region": state["target_region"],
            "raw_data": state["raw_content"],
            "topic": state["topic"]
        })
    
    audit_db.log_event(
        state["session_id"], 
        "DraftingAgent", 
        "Generated Draft" if not is_revision else "Revised Draft", 
        state["topic"], 
        response.content[:100], 
        "Success", 
        {"length": len(response.content), "iteration": state.get("iteration_count", 0) + 1, "has_feedback": is_revision}
    )
    
    print(f"   → Draft generated ({len(response.content)} chars), Iteration: {state.get('iteration_count', 0) + 1}")
    
    # Return updated state - clear needs_revision flag so next iteration is fresh
    # Don't clear human_feedback/approval as those may be needed by human_gate later
    return {
        "draft_content": response.content,
        "iteration_count": state.get("iteration_count", 0) + 1,
        "needs_revision": False  # Clear the revision flag - compliance will set it again if needed
    }