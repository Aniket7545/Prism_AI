# agents/localization_agent.py
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from config import Config
from datetime import datetime

def localization_agent(state):
    """Adapts content for specific regions/languages."""
    print("\n--- 🌍 LOCALIZATION AGENT ---")
    
    if state.get("target_region", "Global") == "Global":
        return {"audit_log": state["audit_log"]} # Skip if global
    
    llm = ChatGroq(model=Config.GROQ_MODEL, temperature=0.7)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a Localization Expert. Adapt content for {region} considering cultural nuances and language."),
        ("human", "Original Content:\n{content}\n\nAdapted Content:")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"region": state["target_region"], "content": state["draft_content"]})
    
    audit_entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": "LocalizationAgent",
        "action": "Localized Content",
        "details": f"Region: {state['target_region']}"
    }
    
    return {
        "draft_content": response.content,
        "audit_log": state["audit_log"] + [audit_entry]
    }