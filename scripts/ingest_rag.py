"""
RAG Ingestion Script
=====================
Chunks documents, embeds with sentence-transformers, stores in ChromaDB.
Processes: SAR templates, regulatory guidance, historical SAR examples.
"""

import os
import json
import hashlib
import logging
from typing import List, Dict
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configuration
CHUNK_SIZE_TOKENS = 750       # Target chunk size (600-900 range)
OVERLAP_TOKENS = 75           # ~10% overlap
APPROX_CHARS_PER_TOKEN = 4   # Rough estimate for English text
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Source directories  (relative to project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "rag-pipeline" / "docs"
CHROMA_DB_PATH = str(PROJECT_ROOT / "chroma_db")

COLLECTION_MAP = {
    "guidance-chunks": "sar_guidelines_chunks",
    "templates-chunks": "sar_templates_chunks",
    "suspicious-activity-narrative-chunks": "sar_reports_chunks",
}


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_TOKENS, overlap: int = OVERLAP_TOKENS) -> List[str]:
    """Split text into overlapping chunks of approximately chunk_size tokens."""
    char_chunk = chunk_size * APPROX_CHARS_PER_TOKEN
    char_overlap = overlap * APPROX_CHARS_PER_TOKEN

    if len(text) <= char_chunk:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + char_chunk
        chunk = text[start:end]

        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind(". ")
            if last_period > char_chunk * 0.5:
                chunk = chunk[:last_period + 1]
                end = start + last_period + 1

        chunks.append(chunk.strip())
        start = end - char_overlap

    return [c for c in chunks if c]


def load_documents(folder: Path) -> List[Dict]:
    """Load .json chunk files or .txt/.md documents from a folder."""
    docs = []
    if not folder.exists():
        logger.warning("Folder not found: %s", folder)
        return docs

    for fpath in sorted(folder.iterdir()):
        if fpath.suffix == ".json":
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        content = item.get("content", "")
                        if content:
                            docs.append({"content": content, "source": fpath.name})
                elif isinstance(data, dict) and data.get("content"):
                    docs.append({"content": data["content"], "source": fpath.name})
            except Exception as e:
                logger.error("Error loading %s: %s", fpath, e)
        elif fpath.suffix in (".txt", ".md"):
            try:
                content = fpath.read_text(encoding="utf-8")
                if content.strip():
                    docs.append({"content": content, "source": fpath.name})
            except Exception as e:
                logger.error("Error reading %s: %s", fpath, e)

    return docs


def ingest():
    """Main ingestion pipeline."""
    try:
        import chromadb
        from chromadb.config import Settings
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        logger.error("Missing dependency: %s. Install with: pip install chromadb sentence-transformers", e)
        return

    logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
    model = SentenceTransformer(EMBEDDING_MODEL)

    logger.info("Initialising ChromaDB at: %s", CHROMA_DB_PATH)
    client = chromadb.PersistentClient(
        path=CHROMA_DB_PATH,
        settings=Settings(anonymized_telemetry=False),
    )

    for folder_name, collection_name in COLLECTION_MAP.items():
        folder = DOCS_DIR / folder_name
        logger.info("Processing %s → %s", folder_name, collection_name)

        docs = load_documents(folder)
        if not docs:
            logger.warning("No documents found in %s", folder)
            continue

        # Chunk all documents
        all_chunks = []
        for doc in docs:
            chunks = chunk_text(doc["content"])
            for i, chunk in enumerate(chunks):
                all_chunks.append({
                    "content": chunk,
                    "source": doc["source"],
                    "chunk_index": i,
                })

        logger.info("Created %d chunks from %d documents", len(all_chunks), len(docs))

        # Create collection
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        # Embed and store
        batch_size = 32
        for batch_start in range(0, len(all_chunks), batch_size):
            batch = all_chunks[batch_start:batch_start + batch_size]
            texts = [c["content"] for c in batch]
            ids = [hashlib.sha256(t.encode()).hexdigest()[:16] + f"-{i}" for i, t in enumerate(texts, batch_start)]
            metadatas = [{"source_file": c["source"], "chunk_index": c["chunk_index"]} for c in batch]

            embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()

            collection.upsert(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )

        logger.info("Stored %d chunks in collection '%s'", len(all_chunks), collection_name)

    logger.info("Ingestion complete!")


if __name__ == "__main__":
    ingest()
