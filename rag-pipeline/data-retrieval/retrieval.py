import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# ==========================================================
# CONFIGURATION
# ==========================================================
CHROMA_DB_PATH = r"/Users/shravnithakur/Desktop/Hack-o-Hire/rag-pipeline/vector_store"   # Persistent ChromaDB path
COLLECTION_NAME = "sar_regulatory_chunks"
EMBEDDING_MODEL_NAME = "intfloat/e5-base-v2"
TOP_K = 5  # Number of results to retrieve

# ==========================================================
# LOAD MODEL
# ==========================================================
print("Loading embedding model...")
model = SentenceTransformer(EMBEDDING_MODEL_NAME, device="cpu")
print("Model loaded.")

# ==========================================================
# CONNECT TO CHROMA
# ==========================================================
chroma_client = chromadb.PersistentClient(
    path=CHROMA_DB_PATH,
    settings=Settings(anonymized_telemetry=False)
)

collection = chroma_client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}  # Optional, same as embedding
)
print(f"Connected to collection: {COLLECTION_NAME}")

# ==========================================================
# RETRIEVAL FUNCTION
# ==========================================================
def prepare_text(text: str) -> str:
    """E5 requires 'passage:' prefix."""
    return f"passage: {text.strip()}"


def retrieve(query: str, top_k: int = TOP_K):
    query_embedding = model.encode(
        prepare_text(query),
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    results = collection.query(
        query_embeddings=query_embedding.tolist(),
        n_results=top_k,
        include=["documents", "metadatas"]
    )

    hits = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        hits.append({
            "document": doc,
            "metadata": meta
        })
    return hits


# ==========================================================
# TEST
# ==========================================================
if __name__ == "__main__":
    query = "regulatory guidelines for SARS reporting"
    print(f"Retrieving top {TOP_K} results for query: '{query}'\n")
    results = retrieve(query, top_k=TOP_K)

    for i, hit in enumerate(results, 1):
        print(f"--- Result {i} ---")
        print(f"Source file: {hit['metadata']['source_file']}")
        print(f"Chunk index: {hit['metadata']['chunk_index']}")
        print(f"Content: {hit['document'][:300]}...\n")