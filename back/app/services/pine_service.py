import json
from app.services.ai_service import call_groq
from sentence_transformers import SentenceTransformer
import os
from app.core.config import settings
from pinecone import Pinecone

# Initialize Pinecone
pc = Pinecone(
    api_key=settings.PINECONE_API_KEY
)

# Connect to existing index
index = pc.Index("bns-law2")
# Load once globally
model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_text(text: str) -> list[float]:
    """
    Generate 384-dimension embedding
    Compatible with Pinecone 384 index
    """
    try:
        vector = model.encode(text)
        return vector.tolist()
    except Exception as e:
        print("⚠️ Embedding failed:", e)
        return []
    
def generate_vector_query_with_gemini(incident_data: dict) -> str:
    prompt = f"""
You are a legal information retrieval assistant.

Convert structured incident data into a strong semantic legal search query.

Rules:
- Use legal terminology
- Do NOT invent missing information
- Ignore unknown/null fields
- 1–3 sentences only

Incident Data:
{json.dumps({k: v for k, v in incident_data.items() if v is not None}, indent=2)}

Output only the search query text.
"""

    query_text = call_groq(prompt, temperature=0.2)

    if not query_text:
        query_text = "Relevant legal provisions for reported incident."

    return query_text




def retrieve_legal_context(incident_data: dict) -> str:
    """
    Generate semantic search query → embed → retrieve top legal contexts.
    """

    # Step 1: Smart legal query from Gemini
    query_text = generate_vector_query_with_gemini(incident_data)

    # Step 2: Convert to embedding
    vector = embed_text(query_text)

    # Step 3: Query Pinecone
    results = index.query(
        vector=vector,
        top_k=5,
        include_metadata=True
    )

    contexts = []
    for match in results.get("matches", []):
        text = match["metadata"].get("text")
        if text:
            contexts.append(text)

    return "\n\n".join(contexts)