import streamlit as st
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# ==========================================================
# CONFIGURATION
# ==========================================================
CHROMA_DB_PATH = r"/Users/shravnithakur/Desktop/Hack-o-Hire/rag-pipeline/vector_store"
COLLECTION_NAME = "sar_regulatory_chunks"
EMBEDDING_MODEL_NAME = "intfloat/e5-base-v2"
TOP_K = 5

# ==========================================================
# LOAD MODEL
# ==========================================================
@st.cache_resource
def load_model():
    st.info("Loading embedding model...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME, device="cpu")
    st.success("Model loaded.")
    return model

model = load_model()

# ==========================================================
# CONNECT TO CHROMA
# ==========================================================
@st.cache_resource
def get_collection():
    client = chromadb.PersistentClient(
        path=CHROMA_DB_PATH,
        settings=Settings(anonymized_telemetry=False)
    )
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )
    return collection

collection = get_collection()

# ==========================================================
# UTILS
# ==========================================================
def prepare_text(text: str) -> str:
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
# STREAMLIT UI
# ==========================================================
st.title("📄 SARS Regulatory Document Retrieval")
st.write("Enter a query and get the most relevant chunks from your SARS documents.")

query = st.text_input("Enter your query:", "")

if st.button("Retrieve") and query.strip():
    with st.spinner("Retrieving..."):
        results = retrieve(query, top_k=TOP_K)

    if not results:
        st.warning("No results found. Make sure the collection has embedded data.")
    else:
        st.success(f"Top {len(results)} results:")
        for i, hit in enumerate(results, 1):
            st.markdown(f"### Result {i}")
            st.markdown(f"**Source file:** {hit['metadata']['source_file']}")
            st.markdown(f"**Chunk index:** {hit['metadata']['chunk_index']}")
            st.markdown(f"**Content:** {hit['document']}")
            st.divider()