# utils/vector_store.py
import chromadb
from chromadb.config import Settings
from config import Config

def get_vector_store():
    """Initialize ChromaDB and seed with enterprise guidelines if empty."""
    client = chromadb.Client(Settings(
        persist_directory=Config.VECTOR_DB_PATH,
        anonymized_telemetry=False
    ))
    
    collection = client.get_or_create_collection(name="enterprise_policies")
    
    # Seed data if empty (Simulates loading from enterprise CMS)
    if collection.count() == 0:
        collection.add(
            documents=Config.DEFAULT_GUIDELINES,
            ids=[f"policy_{i}" for i in range(len(Config.DEFAULT_GUIDELINES))],
            metadatas=[{"category": "general"} for _ in Config.DEFAULT_GUIDELINES]
        )
        print("✅ Vector Store initialized with enterprise policies.")
    
    return collection

def retrieve_guidelines(collection, query: str, n_results: int = 3):
    """Retrieve relevant policies for the specific content context."""
    results = collection.query(query_texts=[query], n_results=n_results)
    return "\n".join(results['documents'][0]) if results['documents'] else ""