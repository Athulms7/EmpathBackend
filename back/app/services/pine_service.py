import logging

from sentence_transformers import SentenceTransformer
from app.core.config import settings
from pinecone import Pinecone

logger = logging.getLogger(__name__)

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
    except Exception:
        logger.exception("Embedding generation failed")
        return []
    
def build_legal_search_query(incident_data: dict) -> str:
    internal_fields = {"asked_fields", "question_attempts", "final_question_asked"}
    query_fields = {
        key: value
        for key, value in incident_data.items()
        if key not in internal_fields
        and value is not None
        and value != ""
        and value != []
        and value != {}
        and not (isinstance(value, str) and value.lower() == "unknown")
    }
    return "; ".join(f"{key.replace('_', ' ')}: {value}" for key, value in query_fields.items())


def retrieve_legal_context(incident_data: dict) -> str:
    """
    Generate semantic search query → embed → retrieve top legal contexts.
    """

    # Build the query directly to avoid an extra model round trip.
    query_text = build_legal_search_query(incident_data)

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