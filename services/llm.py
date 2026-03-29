import os
from langchain_groq import ChatGroq
from config import Config

class LLMService:
    def __init__(self):
        if not Config.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not found in .env")
        self.main_model = ChatGroq(model=Config.GROQ_MODEL, temperature=0.7, api_key=Config.GROQ_API_KEY)
        self.compliance_model = ChatGroq(model=Config.GROQ_MODEL, temperature=0.0, api_key=Config.GROQ_API_KEY)

    def get_main_llm(self):
        return self.main_model

    def get_compliance_llm(self):
        return self.compliance_model

llm_service = LLMService()