# services/vector_store.py
import chromadb
from chromadb.config import Settings
from config import Config
import os
import shutil

class PolicyStore:
    def __init__(self):
        os.makedirs(Config.VECTOR_DB_PATH, exist_ok=True)
        
        try:
            self.client = chromadb.PersistentClient(path=Config.VECTOR_DB_PATH)
            self.collection = self.client.get_or_create_collection(name="enterprise_policies")
            self._seed_policies()
        except Exception as e:
            print(f"⚠️ ChromaDB error: {e}. Resetting database...")
            if os.path.exists(Config.VECTOR_DB_PATH):
                shutil.rmtree(Config.VECTOR_DB_PATH)
                os.makedirs(Config.VECTOR_DB_PATH, exist_ok=True)
            self.client = chromadb.PersistentClient(path=Config.VECTOR_DB_PATH)
            self.collection = self.client.get_or_create_collection(name="enterprise_policies")
            self._seed_policies()

    def _seed_policies(self):
        if self.collection.count() == 0:
            # MORE SPECIFIC FINANCIAL COMPLIANCE POLICIES
            policies = [
                "Financial content MUST include SEBI regulatory disclaimers stating 'Past performance is not indicative of future results'.",
                "NEVER use guaranteed return language including: risk-free, assured profit, guaranteed, fixed return, no risk, zero risk, capital protected.",
                "All investment claims must be backed by verifiable data sources and include risk warnings.",
                "Tone must be professional, objective, and data-driven. No sensationalism or absolute claims.",
                "No sensitive customer data (PII, account numbers, passwords) should be exposed in public content.",
                "Localization must respect cultural nuances and local regulatory requirements of the target region.",
                "SEBI guidelines require clear disclosure of all material risks associated with any financial product.",
                "Any mention of returns must include disclaimer that investments are subject to market risks."
            ]
            self.collection.add(
                documents=policies,
                ids=[f"policy_{i}" for i in range(len(policies))],
                metadatas=[{"source": "enterprise_handbook", "category": "compliance"} for _ in policies]
            )
            print("✅ Policy Store Initialized with 8 compliance policies")

    def retrieve_relevant_policies(self, query: str, n_results=5):
        try:
            results = self.collection.query(query_texts=[query], n_results=n_results)
            return "\n".join(results['documents'][0]) if results['documents'] else ""
        except Exception as e:
            print(f"⚠️ Policy retrieval error: {e}")
            return ""

policy_store = PolicyStore()