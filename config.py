import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = "llama-3.3-70b-versatile"
    VECTOR_DB_PATH = "./chroma_db"
    AUDIT_DB_PATH = "./logs/audit.db"
    DATA_INPUT_PATH = "./data/inputs"
    
    # Ensure directories exist
    os.makedirs("./logs", exist_ok=True)
    os.makedirs("./data/inputs", exist_ok=True)