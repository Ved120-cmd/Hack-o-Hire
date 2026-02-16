import os
import json
import uuid
import hashlib
import datetime
from typing import List
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL_NAME = "intfloat/e5-base-v2"

CHROMA_DB_PATH = r"/Users/shravnithakur/Desktop/Hack-o-Hire/rag-pipeline/vector_store"

# Collections for different DBs
COLLECTIONS = {
    "guidelines": "sar_guidelines_chunks",
    "sars": "sar_reports_chunks",
    "templates": "sar_templates_chunks"
}

# Folder paths for different chunk types
CHUNKS_FOLDERS = {
    "guidelines": r"/Users/shravnithakur/Desktop/Hack-o-Hire/rag-pipeline/docs/guidance-chunks",
    "sars": r"/Users/shravnithakur/Desktop/Hack-o-Hire/rag-pipeline/docs/suspicious-activity-narrative-chunks",
    "templates": r"/Users/shravnithakur/Desktop/Hack-o-Hire/rag-pipeline/docs/templates-chunks"
}

BATCH_SIZE = 32
UPSERT_BATCH_SIZE = 500

# ==========================================================
# LOAD MODEL
# ==========================================================

print("Loading embedding model...")
model = SentenceTransformer(EMBEDDING_MODEL_NAME, device="cpu")
print("Model loaded.")

# ==========================================================
# INIT PERSISTENT CHROMA CLIENT
# ==========================================================

chroma_client = chromadb.PersistentClient(
    path=CHROMA_DB_PATH,
    settings=Settings(anonymized_telemetry=False)
)

# Create or get collections for each DB
collections = {}
for db_name, coll_name in COLLECTIONS.items():
    collections[db_name] = chroma_client.get_or_create_collection(
        name=coll_name,
        metadata={"hnsw:space": "cosine"}
    )

# ==========================================================
# HELPERS
# ==========================================================

def generate_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def prepare_text(text: str) -> str:
    """
    E5 requires 'passage:' prefix for stored docs.
    """
    return f"passage: {text.strip()}"

def load_all_chunks(folder_path: str) -> List[dict]:

    if not os.path.isdir(folder_path):
        raise ValueError(f"{folder_path} is not a valid directory")

    all_chunks = []

    for filename in os.listdir(folder_path):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(folder_path, filename)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

                if isinstance(data, list):
                    all_chunks.extend(data)
                elif isinstance(data, dict):
                    all_chunks.append(data)

        except Exception as e:
            print(f"Error reading {filename}: {e}")

    return all_chunks

def get_existing_hashes(collection, hashes: List[str]) -> set:
    """
    Prevent duplicate inserts.
    """
    existing = collection.get(
        where={"content_hash": {"$in": hashes}},
        include=["metadatas"]
    )

    if not existing["metadatas"]:
        return set()

    return {
        m["content_hash"]
        for m in existing["metadatas"]
        if "content_hash" in m
    }

# ==========================================================
# EMBEDDING + STORAGE
# ==========================================================

def embed_and_store(chunks: List[dict], collection):

    texts = []
    documents = []
    metadatas = []
    hashes = []

    for chunk in chunks:

        content = chunk.get("content")
        metadata = chunk.get("metadata", {})

        if not content:
            continue

        prepared = prepare_text(content)
        content_hash = generate_hash(prepared)

        texts.append(prepared)
        documents.append(content)
        hashes.append(content_hash)

        metadatas.append({
            "source_file": metadata.get("source_file"),
            "chunk_index": metadata.get("chunk_index"),
            "content_hash": content_hash,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "embedding_model": EMBEDDING_MODEL_NAME
        })

    print(f"Total valid chunks: {len(texts)}")

    if not texts:
        print("No valid chunks found.")
        return

    # Remove duplicates
    existing_hashes = get_existing_hashes(collection, hashes)

    new_texts = []
    new_documents = []
    new_metadatas = []
    new_ids = []

    for i in range(len(texts)):
        if hashes[i] in existing_hashes:
            continue

        new_texts.append(texts[i])
        new_documents.append(documents[i])
        new_metadatas.append(metadatas[i])
        new_ids.append(str(uuid.uuid4()))

    print(f"New chunks to embed: {len(new_texts)}")

    if not new_texts:
        print("No new chunks to insert.")
        return

    print("Generating embeddings...")

    embeddings = model.encode(
        new_texts,
        batch_size=BATCH_SIZE,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=True
    )

    print("Storing in Chroma...")

    for i in range(0, len(new_ids), UPSERT_BATCH_SIZE):
        collection.upsert(
            ids=new_ids[i:i + UPSERT_BATCH_SIZE],
            documents=new_documents[i:i + UPSERT_BATCH_SIZE],
            embeddings=embeddings[i:i + UPSERT_BATCH_SIZE].tolist(),
            metadatas=new_metadatas[i:i + UPSERT_BATCH_SIZE],
        )

    print("Stored successfully.")

# ==========================================================
# MAIN
# ==========================================================

if __name__ == "__main__":

    for db_name, folder_path in CHUNKS_FOLDERS.items():
        print(f"\nProcessing {db_name.upper()} chunks from folder: {folder_path}")
        chunks = load_all_chunks(folder_path)
        print(f"Total chunks found for {db_name}: {len(chunks)}")
        embed_and_store(chunks, collections[db_name])

    print("\nAll DBs processed successfully.")