"""
Localization Agent - Content Adaptation for Regional Markets
Adapts approved content for specific regions, languages, and cultural contexts
"""
from langchain_core.prompts import ChatPromptTemplate
from services.llm import llm_service
from services.database import audit_db

def localization_agent(state):
    """
    Localize content for target region
    Context from: compliance (ensures content is compliant)
    Provides to: publish_agent (localized content)
    """
    print("\n" + "=" * 80)
    print("[LOCALIZE] Content Localization Agent")
    print("=" * 80)
    
    session_id = state.get("session_id", "unknown")
    region = state.get("target_region", "Global")
    draft = state.get("draft_content", "")
    topic = state.get("topic", "")
    channel = state.get("target_channel", "")
    
    print(f"\n[INPUT] Localization Request")
    print(f"   Region: {region}")
    print(f"   Channel: {channel}")
    print(f"   Draft Length: {len(draft)} characters")
    
    if not draft:
        print("[ERROR] No draft content to localize!")
        return {"localization_content": ""}
    
    # If Global region, no localization needed
    if region == "Global":
        print(f"\n[DECISION] Global region selected - no localization needed")
        audit_db.log_event(
            session_id,
            "LocalizationAgent",
            "Skipped (Global)",
            topic,
            "Not applicable",
            "Passed through",
            {"region": region, "action": "bypass"}
        )
        print("=" * 80 + "\n")
        return {"localization_content": draft}
    
    # For regional content, apply localization
    print(f"\n[STEP 1] Analyzing content for {region} market")
    llm = llm_service.get_main_llm()
    
    # First, detect cultural elements that need adaptation
    analysis_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a cultural localization expert.
        Analyze this content for {region} market and identify:
        1. Cultural references that need adaptation
        2. Idioms or phrases that don't translate well
        3. Regional preferences for content style
        4. Any compliance requirements specific to {region}
        
        Respond with JSON: {{"considerations": ["item1", "item2"], "style_preference": "description"}}"""),
        ("human", "{content}")
    ])
    
    try:
        analysis = (analysis_prompt | llm).invoke({
            "region": region,
            "content": draft[:1000]  # Analyze first 1000 chars
        })
        print(f"   [OK] Content analysis complete")
    except Exception as e:
        print(f"   [WARN] Analysis failed, proceeding with basic localization: {e}")
        analysis = None
    
    # Now localize the content
    print(f"\n[STEP 2] Adapting content for {region} market preferences")
    
    localize_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert translator and cultural adaptation specialist.
        Localize this content for {region}.
        
        Requirements:
        - Maintain compliance standards
        - Adapt cultural references
        - Use locale-appropriate tone
        - Keep original meaning and message
        - Format: {channel}
        
        CRITICAL: Return ONLY the localized content, no explanations."""),
        ("human", "{content}")
    ])
    
    try:
        localization_result = (localize_prompt | llm).invoke({
            "region": region,
            "channel": channel,
            "content": draft
        })
        
        localized_content = localization_result.content
        print(f"   [OK] Content localized ({len(localized_content)} characters)")
        
    except Exception as e:
        print(f"   [ERROR] Localization failed, using original: {e}")
        localized_content = draft
    
    # Verify localization maintained content integrity
    if len(localized_content) < len(draft) * 0.3:
        print(f"   [WARN] Localized content significantly shorter than original")
    
    print(f"\n[SUMMARY] Localization complete for {region}")
    print(f"   Original Length: {len(draft)} chars")
    print(f"   Localized Length: {len(localized_content)} chars")
    
    # Log to audit
    audit_db.log_event(
        session_id,
        "LocalizationAgent",
        "Content Localized",
        topic,
        f"{region} - {len(localized_content)} chars",
        "Success",
        {
            "region": region,
            "original_length": len(draft),
            "localized_length": len(localized_content),
            "channel": channel
        }
    )
    
    print("=" * 80 + "\n")
    
    return {
        "localization_content": localized_content,
        "localization_region": region,
        "localization_timestamp": __import__('datetime').datetime.now().isoformat()
    }
