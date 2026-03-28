# agents/drafting_agent.py
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from config import Config
from utils.vector_store import get_vector_store, retrieve_guidelines
from datetime import datetime

def drafting_agent(state):
    """Generates content based on input and retrieved brand guidelines."""
    print("\n--- 🤖 DRAFTING AGENT ---")
    
    llm = ChatGroq(model=Config.GROQ_MODEL, temperature=0.7)
    collection = get_vector_store()
    
    # Retrieve relevant guidelines for the topic
    guidelines = retrieve_guidelines(collection, state["input_topic"])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an Enterprise Content Creator.
        Create content based on the user request.
        
        Brand Guidelines & Policies:
        {guidelines}
        
        Target Channel: {channel}
        Target Audience: {audience}
        
        Ensure the tone is professional and aligned with the guidelines.
        """),
        ("human", "Topic: {topic}\nRaw Input: {raw_input}\n\nCreate the content draft:")
    ])
    
    chain = prompt | llm
    response = chain.invoke({
        "guidelines": guidelines,
        "channel": state["target_channel"],
        "audience": state["target_audience"],
        "topic": state["input_topic"],
        "raw_input": state["input_raw_data"]
    })
    
    # Log audit trail
    audit_entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": "DraftingAgent",
        "action": "Generated Draft",
        "details": f"Length: {len(response.content)} chars"
    }
    
    return {
        "draft_content": response.content,
        "audit_log": state["audit_log"] + [audit_entry],
        "iteration_count": state.get("iteration_count", 0) + 1
    }