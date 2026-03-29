import os
import time
from langchain_groq import ChatGroq
from config import Config

class LLMService:
    def __init__(self):
        if not Config.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not found in .env")
        
        # Primary model (better quality, higher cost)
        primary_model = Config.GROQ_MODEL or "llama-3.3-70b-versatile"
        # Fallback model (cheaper, faster)
        fallback_model = "mixtral-8x7b-32768"
        
        self.main_model = ChatGroq(model=primary_model, temperature=0.7, api_key=Config.GROQ_API_KEY)
        self.fallback_main_model = ChatGroq(model=fallback_model, temperature=0.7, api_key=Config.GROQ_API_KEY)
        
        self.compliance_model = ChatGroq(model=primary_model, temperature=0.0, api_key=Config.GROQ_API_KEY)
        self.fallback_compliance_model = ChatGroq(model=fallback_model, temperature=0.0, api_key=Config.GROQ_API_KEY)
        
        self.rate_limit_retry_count = 3
        self.rate_limit_wait_time = 2

    def _invoke_with_fallback(self, chain, use_fallback_model=False):
        """Invoke LLM with fallback strategy for rate limits"""
        try:
            return chain.invoke({})
        except Exception as e:
            error_msg = str(e)
            if "rate_limit_exceeded" in error_msg or "429" in error_msg:
                if self.rate_limit_retry_count > 0:
                    self.rate_limit_retry_count -= 1
                    print(f"   ⚠️ Rate limit hit, retrying in {self.rate_limit_wait_time}s...")
                    time.sleep(self.rate_limit_wait_time)
                    return self._invoke_with_fallback(chain, use_fallback_model=True)
                else:
                    print(f"   ⚠️ Rate limit exceeded - using fallback response")
                    return None
            raise

    def get_main_llm(self):
        return self.main_model
    
    def get_fallback_main_llm(self):
        return self.fallback_main_model

    def get_compliance_llm(self):
        return self.compliance_model
    
    def get_fallback_compliance_llm(self):
        return self.fallback_compliance_model

llm_service = LLMService()