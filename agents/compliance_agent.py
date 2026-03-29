# agents/compliance_agent.py
from langchain_core.prompts import ChatPromptTemplate
from services.llm import llm_service
from services.vector_store import policy_store
from services.database import audit_db
import json
import re

# === HARD-CODED PROHIBITED TERMS (Case-insensitive) ===
PROHIBITED_TERMS = [
    "risk-free", "risk free", "guaranteed return", "guaranteed returns",
    "guarantee", "assured profit", "100% profit", "no risk", "zero risk",
    "fixed return", "sure shot", "without loss", "capital protection",
    "principal guaranteed", "no downside", "safe investment", "profit guaranteed"
]

FINANCE_TOPICS = ["investment", "finance", "stock", "market", "fund", "portfolio", "trading", "wealth", "return", "profit"]

def compliance_agent(state):
    print("\n" + "="*60)
    print("🛡️ COMPLIANCE AGENT - DEBUG MODE")
    print("="*60)
    
    draft = state.get("draft_content", "")
    topic = state.get("topic", "").lower()
    session_id = state.get("session_id", "unknown")
    
    print(f"📋 Input: Topic='{topic}', Draft preview='{draft[:100]}...'")
    
    # === LAYER 1: HARD KEYWORD MATCH (Cannot be overridden) ===
    print("\n🔍 Layer 1: Keyword Scan...")
    flags = []
    draft_lower = draft.lower()
    
    for term in PROHIBITED_TERMS:
        if term in draft_lower:
            flags.append(f"Prohibited term: '{term}'")
            print(f"   ❌ FOUND: '{term}'")
    
    if flags:
        print(f"   → Keyword check: FAIL ({len(flags)} violations)")
    else:
        print(f"   → Keyword check: PASS (0 violations)")
    
    # === LAYER 2: FINANCE TOPIC + DISCLAIMER CHECK ===
    print("\n🔍 Layer 2: Finance Disclaimer Check...")
    is_finance = any(ft in topic for ft in FINANCE_TOPICS)
    has_disclaimer = any(phrase in draft_lower for phrase in [
        "disclaimer", "past performance", "not investment advice", 
        "subject to market risks", "sebi", "regulatory"
    ])
    
    disclaimer_issue = None
    if is_finance and not has_disclaimer:
        disclaimer_issue = "Missing SEBI-style disclaimer for financial content"
        print(f"   ❌ Finance topic detected, NO disclaimer found")
    else:
        print(f"   → Disclaimer check: {'PASS' if not disclaimer_issue else 'FAIL'}")
    
    # === LAYER 3: LLM EVALUATION (Advisory only) ===
    print("\n🔍 Layer 3: LLM Semantic Review...")
    llm = llm_service.get_compliance_llm()
    policies = policy_store.retrieve_relevant_policies("financial compliance disclaimer risk")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a STRICT financial compliance reviewer.

MANDATORY RULES:
1. If content contains "guarantee", "risk-free", "assured", "fixed return" → MUST fail
2. Financial content without disclaimer → MUST fail  
3. Any absolute claim without qualification → MUST fail

Policies: {policies}

Output ONLY valid JSON:
{{
    "llm_passed": false,
    "llm_risk": "HIGH",
    "llm_issues": ["specific issues"],
    "llm_fixes": ["specific fixes"]
}}"""),
        ("human", "Content: {content}\nTopic: {topic}")
    ])
    
    try:
        response = (prompt | llm).invoke({
            "policies": policies,
            "content": draft,
            "topic": topic
        })
        
        # Parse JSON
        response_text = response.content.strip()
        if "```" in response_text:
            response_text = re.sub(r'```(?:json)?\n?', '', response_text).strip('`').strip()
        
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        llm_report = json.loads(json_match.group()) if json_match else {}
        print(f"   → LLM result: passed={llm_report.get('llm_passed')}, risk={llm_report.get('llm_risk')}")
        
    except Exception as e:
        print(f"   ⚠️ LLM error: {e}")
        llm_report = {"llm_passed": False, "llm_risk": "HIGH", "llm_issues": [f"LLM error: {str(e)}"], "llm_fixes": []}
    
    # === LAYER 4: FINAL DECISION LOGIC (Keyword flags OVERRIDE everything) ===
    print("\n🔍 Layer 4: Final Decision...")
    
    # Start with keyword results (most authoritative)
    final_passed = len(flags) == 0 and disclaimer_issue is None
    final_risk = "LOW" if final_passed else "HIGH"
    final_issues = flags.copy()
    if disclaimer_issue:
        final_issues.append(disclaimer_issue)
        final_passed = False
        final_risk = "HIGH"
    
    # Add LLM issues if LLM also flagged something
    llm_issues = llm_report.get("llm_issues", [])
    if llm_issues and not llm_report.get("llm_passed", True):
        for issue in llm_issues:
            if issue not in final_issues:
                final_issues.append(f"[LLM] {issue}")
    
    # CRITICAL: If keyword flags exist, FORCE FAIL regardless of LLM
    if flags:
        final_passed = False
        final_risk = "HIGH"
        print(f"   ⚠️ FORCE FAIL: Keyword violations override LLM result")
    
    # Generate SPECIFIC, ACTIONABLE fixes based on detected issues
    specific_fixes = []
    
    # Fix for prohibited terms
    for flag in flags:
        if "Prohibited term:" in flag:
            term = flag.split("'")[1]  # Extract term from "Prohibited term: 'term'"
            specific_fixes.append(f"Remove or replace the prohibited term: '{term}'")
    
    # Fix for missing disclaimer
    if disclaimer_issue:
        specific_fixes.append(
            "Add financial disclaimer: 'Past performance is not indicative of future results. "
            "This is not investment advice. Please consult a financial advisor. "
            "Investments are subject to market risks.'"
        )
    
    # Use LLM fixes if available, otherwise use specific ones
    final_fixes = llm_report.get("llm_fixes", []) or specific_fixes
    
    print(f"\n📊 FINAL RESULT:")
    print(f"   passed: {final_passed}")
    print(f"   risk_level: {final_risk}")
    print(f"   issues ({len(final_issues)}): {final_issues}")
    print(f"   fixes ({len(final_fixes)}): {final_fixes}")
    print("="*60 + "\n")
    
    # Build report
    report = {
        "passed": final_passed,
        "risk_level": final_risk,
        "issues": final_issues,
        "fixes": final_fixes,
        "requires_disclaimer": is_finance and not has_disclaimer,
        "_debug": {
            "keyword_flags": flags,
            "disclaimer_issue": disclaimer_issue,
            "llm_raw": llm_report
        }
    }
    
    # Audit log
    audit_db.log_event(
        session_id, "ComplianceAgent", "Compliance Check",
        draft[:50], f"Passed:{final_passed}, Risk:{final_risk}",
        "Flagged" if not final_passed else "Cleared", report
    )
    
    return {
        "compliance_report": report,
        "needs_revision": not final_passed
    }