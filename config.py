# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    
    # UPDATED: Use currently supported Groq models
    GROQ_MODEL = "llama-3.3-70b-versatile"  # Latest 70B model
    # Fallback options if needed:
    # GROQ_MODEL = "llama-3.1-8b-instant"  # Faster, cheaper
    # GROQ_MODEL = "mixtral-8x7b-32768"    # Alternative
    
    VECTOR_DB_PATH = "./chroma_db"
    AUDIT_DB_PATH = "./audit_logs.db"
    
    # Brand Guidelines
    BRAND_VOICE = "Professional, Concise, Data-Driven, Compliant with SEBI regulations."
    PROHIBITED_TERMS = ["guaranteed returns", "risk-free", "100% profit", "assured", "no risk"]