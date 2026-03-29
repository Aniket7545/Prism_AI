# agents/intake_agent.py
"""
Intake Agent: Processes raw input files (PDF, TXT, images) and extracts structured content.
- Validates file formats
- Extracts text and metadata
- Identifies content type (blog, social, email, etc.)
- Structures data for downstream agents
"""

from langchain_core.prompts import ChatPromptTemplate
from services.llm import llm_service
from services.database import audit_db
from datetime import datetime
import json
import re

def intake_agent(state):
    """
    Process raw input and structure it for the workflow.
    """
    print("\n" + "="*60)
    print("INTAKE AGENT - Content Parsing & Structuring")
    print("="*60)
    
    session_id = state.get("session_id", "unknown")
    input_file = state.get("input_file_path", "")
    raw_content = state.get("raw_content", "")
    topic = state.get("topic", "")
    channel = state.get("target_channel", "")
    region = state.get("target_region", "")
    
    print(f"[INPUT] File='{input_file}', Topic='{topic}', Channel='{channel}'")
    
    # Step 1: Detect content type
    content_type = detect_content_type(raw_content, channel)
    print(f"   [OK] Detected content type: {content_type}")
    
    # Step 2: Extract metadata
    metadata = extract_metadata(raw_content, topic)
    print(f"   [OK] Extracted metadata: {metadata}")
    
    # Step 3: Clean and normalize content
    normalized_content = normalize_content(raw_content, content_type)
    print(f"   [OK] Content normalized: {len(normalized_content)} characters")
    
    # Step 4: Use LLM to structure content
    try:
        structured_data = llm_structure_content(normalized_content, topic, content_type, channel)
        print(f"   [OK] LLM structured content: {list(structured_data.keys())}")
    except Exception as e:
        print(f"   ⚠️  LLM structuring failed: {e}")
        structured_data = {
            "title": topic,
            "summary": normalized_content[:200],
            "keywords": extract_keywords(normalized_content),
            "tone": "professional"
        }
    
    # Step 5: Validation
    is_valid, validation_errors = validate_content(normalized_content, content_type)
    print(f"   {'[OK]' if is_valid else '[FAIL]'} Validation: {'PASS' if is_valid else f'FAIL - {len(validation_errors)} errors'}")
    
    # Audit logging
    audit_db.log_event(
        session_id,
        "IntakeAgent",
        "Parse Input",
        f"File: {input_file}, Type: {content_type}",
        f"Content normalized: {len(normalized_content)} chars, Validity: {is_valid}",
        "Success" if is_valid else "Warning",
        {
            "content_type": content_type,
            "metadata": metadata,
            "validation_errors": validation_errors
        }
    )
    
    # Save to database
    version = state.get("iteration_count", 0) + 1
    audit_db.save_content_asset(
        session_id, 
        version, 
        content_type, 
        normalized_content,
        structured_data.get("prepared_content", normalized_content),
        "IntakeAgent"
    )
    
    # Return updated state
    return {
        "raw_content": normalized_content,
        "topic": structured_data.get("title", topic),
        "content_metadata": metadata,
        "content_type": content_type,
        "structured_data": structured_data,
        "audit_log": state.get("audit_log", []) + [{
            "timestamp": datetime.now().isoformat(),
            "agent": "IntakeAgent",
            "action": "Parse and structure input",
            "status": "Success" if is_valid else "Warning"
        }]
    }


def detect_content_type(content: str, channel: str) -> str:
    """Detect the type of content based on channel and length."""
    word_count = len(content.split())
    
    if channel.lower() in ["linkedin", "twitter", "x"]:
        return "social_post"
    elif channel.lower() == "blog":
        return "blog_article"
    elif channel.lower() == "email":
        return "email_newsletter"
    elif channel.lower() == "press release":
        return "press_release"
    elif word_count < 100:
        return "short_form"
    elif word_count < 1000:
        return "medium_form"
    else:
        return "long_form"


def extract_metadata(content: str, topic: str) -> dict:
    """Extract metadata from content."""
    words = content.split()
    sentences = [s.strip() for s in content.split('.') if s.strip()]
    
    return {
        "word_count": len(words),
        "sentence_count": len(sentences),
        "paragraph_count": len([p for p in content.split('\n\n') if p.strip()]),
        "avg_sentence_length": len(words) / max(len(sentences), 1),
        "topic": topic,
        "language": "english",
        "readability_score": estimate_readability(content)
    }


def normalize_content(content: str, content_type: str) -> str:
    """Normalize and clean content."""
    # Remove extra whitespace
    content = re.sub(r'\s+', ' ', content).strip()
    
    # Remove special characters that might interfere with processing
    content = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', content)
    
    # Normalize quotes
    content = content.replace('"', '"').replace('"', '"')
    content = content.replace(''', "'").replace(''', "'")
    
    return content


def extract_keywords(content: str, num_keywords: int = 5) -> list:
    """Extract keywords from content using simple frequency analysis."""
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
        'of', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had'
    }
    
    words = [w.lower() for w in content.split() if len(w) > 3 and w.lower() not in stop_words]
    
    # Get most common words
    from collections import Counter
    word_freq = Counter(words)
    keywords = [word for word, _ in word_freq.most_common(num_keywords)]
    
    return keywords


def estimate_readability(content: str) -> float:
    """Estimate readability score (simplified Flesch-Kincaid)."""
    sentences = [s for s in content.split('.') if s.strip()]
    words = content.split()
    
    if len(sentences) == 0 or len(words) == 0:
        return 50.0
    
    # Simplified readability: penalize long words and sentence length
    long_words = sum(1 for w in words if len(w) > 6)
    score = 206.835 - 1.015 * (len(words) / max(len(sentences), 1)) - 84.6 * (long_words / max(len(words), 1))
    
    return max(0, min(100, score))


def llm_structure_content(content: str, topic: str, content_type: str, channel: str) -> dict:
    """Use LLM to intelligently structure content."""
    llm = llm_service.get_main_llm()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a Content Structuring Expert.
        
Your task: Analyze the input content and structure it optimally for {channel} distribution.
Content Type: {content_type}
Topic: {topic}

Output ONLY valid JSON with these fields:
{{
    "title": "compelling title",
    "summary": "short summary",
    "key_points": ["point1", "point2", "point3"],
    "tone": "professional/casual/formal",
    "target_audience": "description",
    "suggested_keywords": ["kw1", "kw2"],
    "prepared_content": "content ready for drafting agent",
    "recommendations": ["rec1", "rec2"]
}}
        """),
        ("human", "Content to structure:\n\n{content}")
    ])
    
    try:
        response = (prompt | llm).invoke({
            "content": content[:2000],  # Limit to avoid token issues
            "topic": topic,
            "content_type": content_type,
            "channel": channel
        })
        
        response_text = response.content.strip()
        if "```" in response_text:
            response_text = re.sub(r'```(?:json)?\n?', '', response_text).strip('`').strip()
        
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"   Error in LLM structuring: {e}")
    
    return {}


def validate_content(content: str, content_type: str) -> tuple:
    """Validate content meets minimum requirements."""
    errors = []
    
    # Check minimum length
    min_length = {
        "social_post": 10,
        "email_newsletter": 100,
        "blog_article": 300,
        "press_release": 200
    }
    
    min_chars = min_length.get(content_type, 50)
    if len(content) < min_chars:
        errors.append(f"Content too short. Minimum {min_chars} characters required.")
    
    # Check if content has meaningful text (not just numbers/special chars)
    alpha_chars = sum(1 for c in content if c.isalpha())
    if alpha_chars < len(content) * 0.6:
        errors.append("Content appears to be mostly special characters or numbers.")
    
    # Check for common issues
    if content.count('\n\n') == 0 and content.count('\n') == 0:
        if len(content.split()) > 100:
            errors.append("Long content should have paragraph breaks.")
    
    return len(errors) == 0, errors
