# agents/compliance_agent.py
from langchain_core.prompts import ChatPromptTemplate
from services.llm import llm_service
from services.vector_store import policy_store
from services.database import audit_db
import json
import re

FINANCE_TERMS = [
    "risk-free", "risk free", "guaranteed return", "guaranteed returns",
    "guarantee", "assured profit", "100% profit", "no risk", "zero risk",
    "fixed return", "sure shot", "without loss", "capital protection",
    "principal guaranteed", "no downside", "safe investment", "profit guaranteed"
]

# Backward compatibility for other agents still importing PROHIBITED_TERMS
PROHIBITED_TERMS = FINANCE_TERMS

CATEGORY_KEYWORDS = {
    "finance": ["investment", "finance", "stock", "market", "fund", "portfolio", "trading", "wealth", "return", "profit", "loan", "credit"],
    "health": ["health", "medical", "therapy", "drug", "treatment", "symptom", "diagnosis", "clinical", "doctor", "patient"],
    "security": ["cyber", "security", "encryption", "breach", "vulnerability", "zero-day", "ransomware"],
    "hr": ["hiring", "recruit", "payroll", "benefits", "employee", "candidate"],
    "marketing": ["campaign", "seo", "brand", "ad", "click", "conversion", "growth"],
}

def compliance_agent(state):
    print("\n" + "="*60)
    print("🛡️ COMPLIANCE AGENT - DEBUG MODE")
    print("="*60)
    
    draft = state.get("draft_content", "")
    topic = state.get("topic", "").lower()
    session_id = state.get("session_id", "unknown")
    
    print(f"📋 Input: Topic='{topic}', Draft preview='{draft[:100]}...'")
    
    # Detect category
    def detect_category(topic_text: str, draft_text: str) -> str:
        combined = f"{topic_text} {draft_text}".lower()
        for cat, keys in CATEGORY_KEYWORDS.items():
            if any(k in combined for k in keys):
                return cat
        return "general"

    category = detect_category(topic, draft)
    print(f"   → Detected category: {category}")

    # === LAYER 1: HARD KEYWORD MATCH (Category-scoped) ===
    print("\n🔍 Layer 1: Keyword Scan (category-scoped)...")
    flags = []
    draft_lower = draft.lower()
    if category == "finance":
        for term in FINANCE_TERMS:
            if term in draft_lower:
                flags.append(f"Prohibited term: '{term}'")
                print(f"   ❌ FOUND: '{term}'")
    else:
        print("   (Skipping finance-only keyword scan for non-finance content)")

    if flags:
        print(f"   → Keyword check: FAIL ({len(flags)} violations)")
    else:
        print(f"   → Keyword check: PASS (0 violations)")
    
    # === LAYER 2: FINANCE TOPIC + DISCLAIMER CHECK ===
    print("\n🔍 Layer 2: Finance Disclaimer Check (only if finance)...")
    is_finance = category == "finance"
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
    fallback_llm = llm_service.get_fallback_compliance_llm()
    policies = policy_store.retrieve_relevant_policies("financial compliance disclaimer risk")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a STRICT compliance reviewer.

Category: {category}
Policies: {policies}

Rules by category:
- finance: forbid guaranteed/zero-risk claims; require clear disclaimers; flag performance promises.
- health/medical: forbid treatment/diagnosis claims without professional advice; no guaranteed outcomes; avoid unsafe guidance.
- security: avoid revealing exploits/credentials; no false security claims.
- hr: avoid bias/discrimination; respect privacy.
- marketing/general: avoid false absolutes; keep claims evidence-based.

Output ONLY valid JSON:
{{
    "llm_passed": false,
    "llm_risk": "HIGH",
    "llm_issues": ["specific issues"],
    "llm_fixes": ["specific fixes"]
}}"""),
        ("human", "Content: {content}\nTopic: {topic}\nCategory: {category}")
    ])
    
    prompt_data = {
        "policies": policies,
        "content": draft,
        "topic": topic,
        "category": category
    }
    
    try:
        response = (prompt | llm).invoke(prompt_data)
        
        # Parse JSON
        response_text = response.content.strip()
        if "```" in response_text:
            response_text = re.sub(r'```(?:json)?\n?', '', response_text).strip('`').strip()
        
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        llm_report = json.loads(json_match.group()) if json_match else {}
        print(f"   → LLM result: passed={llm_report.get('llm_passed')}, risk={llm_report.get('llm_risk')}")
        
    except Exception as e:
        error_msg = str(e)
        if "rate_limit" in error_msg.lower() or "429" in error_msg:
            print(f"   ⚠️ Rate limit hit, trying fallback model...")
            try:
                response = (prompt | fallback_llm).invoke(prompt_data)
                response_text = response.content.strip()
                if "```" in response_text:
                    response_text = re.sub(r'```(?:json)?\n?', '', response_text).strip('`').strip()
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                llm_report = json.loads(json_match.group()) if json_match else {}
                print(f"   → Fallback LLM result: passed={llm_report.get('llm_passed')}, risk={llm_report.get('llm_risk')}")
            except:
                print(f"   ⚠️ LLM rate limit - skipping semantic review")
                llm_report = {}
        else:
            print(f"   ⚠️ LLM error: {e}")
            llm_report = {}
    
    # === LAYER 4: FINAL DECISION LOGIC (Keyword flags OVERRIDE everything) ===
    print("\n🔍 Layer 4: Final Decision...")
    
    # Start with keyword results (most authoritative)
    final_passed = len(flags) == 0 and disclaimer_issue is None
    final_risk = "LOW" if final_passed else "MEDIUM"
    final_issues = flags.copy()
    if disclaimer_issue:
        final_issues.append(disclaimer_issue)
        # Don't force fail on missing disclaimer - just flag it
        final_risk = "MEDIUM"
    
    # Add LLM issues if LLM also flagged something
    llm_issues = llm_report.get("llm_issues", [])
    if llm_issues and not llm_report.get("llm_passed", True):
        for issue in llm_issues:
            if issue not in final_issues:
                final_issues.append(f"[LLM] {issue}")
    
    # CRITICAL: Only FORCE FAIL on hard violations (prohibited terms)
    # Tone/style issues don't require revision
    hard_violations = [flag for flag in flags if "Prohibited term:" in flag]
    if hard_violations:
        final_passed = False
        final_risk = "HIGH"
        print(f"   ⚠️ HARD VIOLATION: Prohibited terms found - requires revision")
    elif not final_passed and final_risk != "HIGH":
        # Soft warnings don't need revision - just flag as medium risk
        final_passed = True  # Allow publication with warnings
        print(f"   ⚠️ SOFT WARNINGS: Will publish with compliance notes")
    
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
        "category": category,
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
        "needs_revision": not final_passed  # Only revise on hard violations
    }