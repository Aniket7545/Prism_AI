# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = "llama-3.1-70b-versatile" # Fast & Powerful
    VECTOR_DB_PATH = "./chroma_db"
    AUDIT_DB_PATH = "./audit_logs.db"
    
    # Brand Guidelines (Mock for now, will move to VectorDB later)
    BRAND_VOICE = "Professional, Concise, Data-Driven, Compliant with SEBI regulations."
    PROHIBITED_TERMS = ["guaranteed returns", "risk-free", "100% profit"]