# agents/compliance_agent.py
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from config import Config
from utils.vector_store import get_vector_store, retrieve_guidelines
from datetime import datetime
import json
import re

def compliance_agent(state):
    """Reviews content against enterprise policies and regulatory rules."""
    print("\n--- 🛡️ COMPLIANCE AGENT ---")
    
    llm = ChatGroq(model=Config.GROQ_MODEL, temperature=0) # Deterministic
    collection = get_vector_store()
    
    # Retrieve specific compliance rules
    policies = retrieve_guidelines(collection, f"compliance risk {state['input_topic']}")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a Chief Compliance Officer.
        Review the content against these Enterprise Policies:
        {policies}
        
        Output STRICT JSON:
        {{
            "passed": boolean,
            "risk_level": "LOW" | "MEDIUM" | "HIGH",
            "issues": ["list of specific policy violations"],
            "fix_suggestions": ["list of actionable fixes"]
        }}
        """),
        ("human", "Content to Review:\n{content}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"policies": policies, "content": state["draft_content"]})
    
    # Parse JSON
    try:
        json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
        report = json.loads(json_match.group()) if json_match else {"passed": False, "risk_level": "HIGH", "issues": ["Parse error"], "fix_suggestions": []}
    except:
        report = {"passed": False, "risk_level": "HIGH", "issues": ["Evaluation error"], "fix_suggestions": ["Manual review"]}
    
    audit_entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": "ComplianceAgent",
        "action": "Compliance Check",
        "details": f"Result: {report['passed']}, Risk: {report['risk_level']}"
    }
    
    return {
        "compliance_report": report,
        "audit_log": state["audit_log"] + [audit_entry],
        "needs_revision": not report["passed"]
    }