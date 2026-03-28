# agents/compliance_agent.py
"""
Compliance Guardrail Agent
- Checks content against prohibited terms (keyword matching)
- Evaluates brand voice and regulatory compliance via LLM
- Retrieves relevant guidelines from Vector Store (ChromaDB)
- Returns structured compliance report with audit trail
"""

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from config import Config
from utils.vector_store import get_vector_store
from datetime import datetime
import json
import re
from typing import Dict, List, Any

def compliance_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates content against brand guidelines and regulatory rules.
    
    Args:
        state: ContentState dictionary containing draft_content, input_topic, etc.
    
    Returns:
        Updated state with compliance_report, audit_log, and next_step
    """
    print("--- COMPLIANCE AGENT STARTED ---")
    
    # 1. Initialize components
    llm = ChatGroq(
        model=Config.GROQ_MODEL, 
        temperature=0,  # Deterministic for compliance checks
        api_key=Config.GROQ_API_KEY
    )
    vector_store = get_vector_store()
    
    draft = state.get("draft_content", "")
    input_topic = state.get("input_topic", "general content")
    target_channel = state.get("target_channel", "general")
    
    # 2. Hardcoded Guardrails: Keyword Matching (Fast, Deterministic)
    flags: List[str] = []
    draft_lower = draft.lower()
    
    for term in Config.PROHIBITED_TERMS:
        if term.lower() in draft_lower:
            flags.append(f"Prohibited term: '{term}'")
    
    # Channel-specific rules
    if target_channel.lower() in ["linkedin", "twitter", "social"] and len(draft) > 280:
        flags.append(f"Content exceeds {target_channel} character limit")
    
    # 3. Retrieve Relevant Guidelines from Vector Store
    try:
        relevant_guidelines = vector_store.query(
            query_texts=[f"{input_topic} {target_channel} compliance"],
            n_results=3
        )
        guideline_context = "\n• ".join(relevant_guidelines['documents'][0])
    except Exception as e:
        guideline_context = "Unable to retrieve guidelines. Use general brand voice."
        print(f"⚠️ Vector store query failed: {e}")
    
    # 4. LLM-Based Compliance Evaluation
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a Senior Brand Compliance Officer for an enterprise media company.
        
        YOUR TASK:
        Review the content draft against these Brand Guidelines:
        • {guidelines}
        
        Channel Context: {channel}
        Topic Context: {topic}
        
        Pre-screening Flags (from keyword check): {pre_flags}
        
        EVALUATION CRITERIA:
        1. Regulatory Compliance: No unverified financial claims, proper disclaimers for finance content
        2. Brand Voice: Professional, data-driven, objective tone (no sensationalism)
        3. Terminology: Avoid prohibited terms, use approved language
        4. Channel Fit: Appropriate length and format for {channel}
        
        OUTPUT FORMAT (STRICT JSON):
        {{
            "status": "PASS" | "FAIL" | "REVIEW_REQUIRED",
            "risk_score": 0.0 to 1.0,
            "reasoning": "Brief explanation of decision",
            "flags": ["list of specific issues found"],
            "suggested_fixes": ["actionable recommendations"],
            "requires_disclaimer": true/false
        }}
        
        RULES:
        - If ANY pre-screening flags exist, status MUST be "FAIL" or "REVIEW_REQUIRED"
        - Financial/investment content ALWAYS requires disclaimer
        - Risk score >0.7 = FAIL, 0.4-0.7 = REVIEW_REQUIRED, <0.4 = PASS
        """),
        ("human", """Content Draft to Review:
        {content}
        
        Return ONLY valid JSON.""")
    ])
    
    chain = prompt | llm
    
    # 5. Execute LLM Call with Robust Error Handling
    try:
        response = chain.invoke({
            "guidelines": guideline_context,
            "channel": target_channel,
            "topic": input_topic,
            "pre_flags": str(flags) if flags else "None",
            "content": draft
        })
        
        # Parse JSON from response (handle markdown code blocks)
        response_text = response.content.strip()
        
        # Remove markdown code fences if present
        if response_text.startswith("```"):
            response_text = re.sub(r'^```(?:json)?\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)
        
        # Extract JSON object
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            report_data = json.loads(json_match.group())
        else:
            raise ValueError("No valid JSON found in LLM response")
        
        # Merge pre-screening flags into report
        if flags:
            existing_flags = report_data.get("flags", [])
            report_data["flags"] = list(set(existing_flags + flags))
            # Ensure status reflects hard flags
            if report_data.get("status") == "PASS":
                report_data["status"] = "REVIEW_REQUIRED"
                report_data["reasoning"] = f"Keyword flags detected: {flags}. " + report_data.get("reasoning", "")
        
        # Validate required fields
        required_fields = ["status", "risk_score", "reasoning"]
        for field in required_fields:
            if field not in report_data:
                report_data[field] = "REVIEW_REQUIRED" if field == "status" else 0.5 if field == "risk_score" else "Missing field in evaluation"
        
    except Exception as e:
        error_msg = str(e)[:300]  # Truncate long errors
        print(f"⚠️ Compliance LLM error: {error_msg}")
        
        # Fallback: Keyword-only evaluation
        if flags:
            report_data = {
                "status": "FAIL",
                "risk_score": 1.0,
                "reasoning": f"Prohibited terms detected: {flags}",
                "flags": flags,
                "suggested_fixes": ["Remove or rephrase flagged terms"],
                "requires_disclaimer": "investment" in input_topic.lower() or "finance" in input_topic.lower()
            }
        else:
            report_data = {
                "status": "REVIEW_REQUIRED",
                "risk_score": 0.5,
                "reasoning": f"Compliance evaluation unavailable: {error_msg}. Manual review recommended.",
                "flags": [],
                "suggested_fixes": ["Verify content manually", "Retry compliance check"],
                "requires_disclaimer": False
            }
    
    # 6. Determine Next Step Based on Compliance Result
    status = report_data.get("status", "REVIEW_REQUIRED")
    if status == "PASS" and report_data.get("risk_score", 1.0) < 0.4:
        next_step = "publish"  # Auto-approve low-risk, compliant content
    else:
        next_step = "human_review"  # Route to human for approval
    
    # 7. Create Audit Log Entry
    audit_entry = {
        "timestamp": datetime.now().isoformat(),
        "agent_name": "ComplianceAgent",
        "action": "Content Review",
        "input_summary": f"Topic: {input_topic}, Channel: {target_channel}",
        "output_summary": f"Status: {status}, Risk: {report_data.get('risk_score')}",
        "details": {
            "flags_count": len(report_data.get("flags", [])),
            "requires_human": next_step == "human_review"
        },
        "status": "Completed"
    }
    
    # 8. Return Updated State
    return {
        "compliance_report": report_data,
        "audit_log": state.get("audit_log", []) + [audit_entry],
        "next_step": next_step,
        "approval_status": "pending" if next_step == "human_review" else "auto_approved"
    }


def quick_compliance_check(content: str, topic: str = "") -> Dict[str, Any]:
    """
    Standalone function for testing compliance logic without full state.
    Useful for unit tests or quick validation.
    """
    mock_state = {
        "input_topic": topic or "test",
        "draft_content": content,
        "target_channel": "test",
        "audit_log": []
    }
    return compliance_agent(mock_state)


# Test block for direct execution
if __name__ == "__main__":
    print("🧪 Testing Compliance Agent...")
    
    # Test 1: Content with prohibited terms
    test_draft_1 = "This investment is risk-free and guarantees 100% profit with no downside."
    result_1 = quick_compliance_check(test_draft_1, "Investment Scheme")
    print(f"\n✅ Test 1 (Prohibited Terms):")
    print(f"   Status: {result_1['compliance_report']['status']}")
    print(f"   Flags: {result_1['compliance_report'].get('flags', [])}")
    
    # Test 2: Compliant content
    test_draft_2 = "Market analysis shows diversified portfolios historically reduce volatility. Past performance doesn't guarantee future results."
    result_2 = quick_compliance_check(test_draft_2, "Investment Education")
    print(f"\n✅ Test 2 (Compliant Content):")
    print(f"   Status: {result_2['compliance_report']['status']}")
    print(f"   Risk Score: {result_2['compliance_report'].get('risk_score')}")
    
    # Test 3: Finance content needing disclaimer
    test_draft_3 = "Tech stocks rallied 5% today on strong earnings reports."
    result_3 = quick_compliance_check(test_draft_3, "Stock Market Update")
    print(f"\n✅ Test 3 (Market Update):")
    print(f"   Status: {result_3['compliance_report']['status']}")
    print(f"   Requires Disclaimer: {result_3['compliance_report'].get('requires_disclaimer')}")
    
    print(f"\n📋 Audit Log Entries: {len(result_1['audit_log']) + len(result_2['audit_log']) + len(result_3['audit_log'])}")