# utils/vector_store.py
import chromadb
from chromadb.config import Settings
from config import Config
import os

def get_vector_store():
    """Initialize ChromaDB and load brand guidelines."""
    client = chromadb.Client(Settings(
        persist_directory=Config.VECTOR_DB_PATH,
        anonymized_telemetry=False
    ))
    
    # Create or get collection
    collection = client.get_or_create_collection(name="brand_guidelines")
    
    # Check if empty, if so, populate with default guidelines (Seed Data)
    if collection.count() == 0:
        collection.add(
            documents=[
                "Tone must be professional, data-driven, and objective. Avoid sensationalism.",
                "Financial content must include SEBI compliance disclaimers where applicable.",
                "Do not use guaranteed return language like 'risk-free', '100% profit', 'assured'.",
                "Brand voice: Authoritative yet accessible. Use active voice.",
                "Localization: Ensure cultural sensitivity for Indian markets."
            ],
            ids=["guideline_1", "guideline_2", "guideline_3", "guideline_4", "guideline_5"],
            metadatas=[{"category": "tone"}, {"category": "legal"}, {"category": "legal"}, {"category": "voice"}, {"category": "localization"}]
        )
        print("Vector Store seeded with brand guidelines.")
    
    return collection