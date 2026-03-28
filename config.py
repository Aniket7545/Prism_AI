# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = "llama-3.3-70b-versatile"  # Current stable model
    VECTOR_DB_PATH = "./chroma_db"
    
    # Industry Agnostic Settings
    # These are defaults, but the system should rely on Vector Store for specific rules
    DEFAULT_GUIDELINES = [
        "Maintain professional tone suitable for enterprise communication.",
        "Avoid sensitive data leakage (PII, passwords, internal secrets).",
        "Ensure content is inclusive and non-discriminatory.",
        "Adhere to local regulatory requirements for the target region.",
        "Verify facts before making claims about product capabilities."
    ]