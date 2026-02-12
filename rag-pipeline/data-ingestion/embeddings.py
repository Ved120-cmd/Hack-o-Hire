import os
import uuid
import hashlib
import datetime
from typing import List

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# ==========================================================
# CONFIGURATION
# ==========================================================

EMBEDDING_MODEL_NAME = "intfloat/e5-large-v2"
EMBEDDING_VERSION = "v1.0"
EMBEDDING_DIMENSION = 1024

CHROMA_DB_PATH = "./chroma_db"
COLLECTION_NAME = "sar_regulatory_chunks"

# ==========================================================
# LOAD EMBEDDING MODEL (LOCAL / OFFLINE)
# ==========================================================

print("Loading embedding model...")
model = SentenceTransformer(EMBEDDING_MODEL_NAME)
print("Model loaded successfully.")

# ==========================================================
# INITIALIZE CHROMA DB (PERSISTENT)
# ==========================================================

chroma_client = chromadb.Client(
    Settings(
        persist_directory=CHROMA_DB_PATH,
        anonymized_telemetry=False
    )
)

collection = chroma_client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}  # cosine similarity
)

# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def prepare_text(chunk: dict) -> str:
    """
    Construct semantic embedding text.
    """
    return f"Section: {chunk['section_heading']}\n\n{chunk['chunk_text']}"


def generate_content_hash(text: str) -> str:
    """
    Create SHA256 hash for audit compliance.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def generate_embeddings(chunks: List[dict]) -> List[dict]:
    """
    Batch generate embeddings locally.
    """
    texts = [prepare_text(chunk) for chunk in chunks]

    embeddings = model.encode(
        texts,
        batch_size=32,
        normalize_embeddings=True,
        convert_to_numpy=True
    )

    enriched_chunks = []

    for i, chunk in enumerate(chunks):
        text = texts[i]
        content_hash = generate_content_hash(text)

        enriched_chunk = {
            "id": chunk.get("chunk_id", str(uuid.uuid4())),
            "document_id": chunk["document_id"],
            "section_heading": chunk["section_heading"],
            "chunk_text": chunk["chunk_text"],
            "embedding": embeddings[i].tolist(),
            "embedding_model": EMBEDDING_MODEL_NAME,
            "embedding_version": EMBEDDING_VERSION,
            "embedding_dimension": EMBEDDING_DIMENSION,
            "content_hash": content_hash,
            "metadata": chunk.get("metadata", {}),
            "created_at": datetime.datetime.utcnow().isoformat()
        }

        enriched_chunks.append(enriched_chunk)

    return enriched_chunks


def store_in_chroma(chunks: List[dict]):
    """
    Store embeddings in ChromaDB with metadata.
    """
    ids = []
    documents = []
    embeddings = []
    metadatas = []

    for chunk in chunks:
        ids.append(chunk["id"])
        documents.append(chunk["chunk_text"])
        embeddings.append(chunk["embedding"])

        metadata = {
            "document_id": chunk["document_id"],
            "section_heading": chunk["section_heading"],
            "embedding_model": chunk["embedding_model"],
            "embedding_version": chunk["embedding_version"],
            "content_hash": chunk["content_hash"],
            "created_at": chunk["created_at"]
        }

        # Merge optional metadata safely
        metadata.update(chunk.get("metadata", {}))

        metadatas.append(metadata)

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )

    chroma_client.persist()
    print(f"Stored {len(chunks)} chunks in ChromaDB.")


def vector_search(query: str, top_k: int = 5):
    """
    Perform similarity search.
    """
    query_embedding = model.encode(
        query,
        normalize_embeddings=True
    ).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    return results


# ==========================================================
# MAIN EXECUTION
# ==========================================================

if __name__ == "__main__":

    sample_chunks = [
        {
            "chunk_id": "chunk-001",
            "document_id": "fincen_guidance_2023",
            "section_heading": "Structuring Transactions",
            "chunk_text": "Financial institutions must monitor for structuring activity...",
            "metadata": {
                "page_number": 12,
                "source": "fincen_guidance.pdf"
            }
        }
    ]

    print("Generating embeddings...")
    embedded_chunks = generate_embeddings(sample_chunks)

    print("Storing embeddings in ChromaDB...")
    store_in_chroma(embedded_chunks)

    print("\nRunning similarity search...")
    results = vector_search("What is structuring activity?")

    print("\nSearch Results:")
    for i in range(len(results["documents"][0])):
        print("-----")
        print("Text:", results["documents"][0][i])
        print("Metadata:", results["metadatas"][0][i])
