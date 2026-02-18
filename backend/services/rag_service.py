"""
RAG Service
============
Retrieves relevant context from ChromaDB for SAR narrative generation.
Uses sentence-transformers for query embedding.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Lazy-loaded globals
_chroma_client = None
_embedding_fn = None


def _get_chroma():
    """Lazy-init ChromaDB client and embedding function."""
    global _chroma_client, _embedding_fn
    if _chroma_client is None:
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            from backend.core.config import settings

            _chroma_client = chromadb.PersistentClient(
                path=settings.CHROMA_DB_PATH,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            logger.info("ChromaDB client initialised at %s", settings.CHROMA_DB_PATH)
        except Exception as e:
            logger.warning("ChromaDB unavailable: %s – RAG will return empty context", e)
    return _chroma_client


def _get_embedding_fn():
    """Lazy-load sentence-transformer embedding function."""
    global _embedding_fn
    if _embedding_fn is None:
        try:
            from sentence_transformers import SentenceTransformer
            from backend.core.config import settings
            _embedding_fn = SentenceTransformer(settings.EMBEDDING_MODEL)
            logger.info("Embedding model loaded: %s", settings.EMBEDDING_MODEL)
        except Exception as e:
            logger.warning("Embedding model unavailable: %s", e)
    return _embedding_fn


class RAGService:
    """Retrieve top-k context chunks from ChromaDB."""

    COLLECTION_NAMES = {
        "guidelines": "sar_guidelines_chunks",
        "templates": "sar_templates_chunks",
        "sars": "sar_reports_chunks",
    }

    def retrieve_context(
        self,
        claim_object: Dict[str, Any],
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Query ChromaDB for relevant SAR templates, guidance, and examples.

        Returns
        -------
        dict with keys: guidelines, templates, sars, query_text
        Each value is a list of {content, metadata, distance} dicts.
        """
        query_text = self._build_query(claim_object)
        logger.info("RAG retrieval: query length=%d chars, top_k=%d", len(query_text), top_k)

        client = _get_chroma()
        model = _get_embedding_fn()

        results: Dict[str, List[Dict]] = {}

        for source, coll_name in self.COLLECTION_NAMES.items():
            results[source] = self._query_collection(client, model, coll_name, query_text, top_k)

        logger.info(
            "RAG retrieved: guidelines=%d, templates=%d, sars=%d",
            len(results.get("guidelines", [])),
            len(results.get("templates", [])),
            len(results.get("sars", [])),
        )

        return {
            "guidelines": results.get("guidelines", []),
            "templates": results.get("templates", []),
            "sars": results.get("sars", []),
            "query_text": query_text,
        }

    def _build_query(self, claim: Dict[str, Any]) -> str:
        """Build a natural-language query string from the claim object."""
        parts = []

        typologies = claim.get("typologies", [])
        if typologies:
            parts.append(f"Suspicious activity typologies: {', '.join(typologies)}")

        for ev in claim.get("evidence_summary", [])[:5]:
            parts.append(f"Rule {ev.get('rule', '')}: {ev.get('reasoning', '')}")

        kyc = claim.get("kyc_flags", {})
        if kyc.get("pep"):
            parts.append("Subject is a Politically Exposed Person")
        if kyc.get("sanctions"):
            parts.append("Subject matches sanctions list")

        agg = claim.get("aggregates", {})
        if agg.get("total_credit", 0) > 0:
            parts.append(f"Total credits: {agg['total_credit']}")

        return " | ".join(parts) if parts else "SAR suspicious activity report template"

    def _query_collection(
        self,
        client,
        model,
        collection_name: str,
        query_text: str,
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """Query a single ChromaDB collection."""
        if client is None:
            return self._fallback_context(collection_name)

        try:
            collection = client.get_collection(collection_name)
        except Exception:
            logger.warning("Collection '%s' not found – using fallback", collection_name)
            return self._fallback_context(collection_name)

        try:
            if model is not None:
                embedding = model.encode([query_text], normalize_embeddings=True).tolist()
                response = collection.query(
                    query_embeddings=embedding,
                    n_results=min(top_k, collection.count() or top_k),
                    include=["documents", "metadatas", "distances"],
                )
            else:
                response = collection.query(
                    query_texts=[query_text],
                    n_results=min(top_k, collection.count() or top_k),
                    include=["documents", "metadatas", "distances"],
                )
        except Exception as e:
            logger.warning("ChromaDB query failed for %s: %s", collection_name, e)
            return self._fallback_context(collection_name)

        docs = response.get("documents", [[]])[0]
        metas = response.get("metadatas", [[]])[0]
        dists = response.get("distances", [[]])[0]

        return [
            {"content": doc, "metadata": meta, "distance": dist}
            for doc, meta, dist in zip(docs, metas, dists)
        ]

    def _fallback_context(self, source: str) -> List[Dict[str, Any]]:
        """Provide minimal context when ChromaDB is unavailable."""
        fallbacks = {
            "templates": [{
                "content": (
                    "SUSPICIOUS ACTIVITY REPORT\n\n"
                    "1. SUBJECT INFORMATION\n"
                    "2. SUSPICIOUS ACTIVITY DESCRIPTION\n"
                    "   a. Date and nature of suspicious activity\n"
                    "   b. Accounts and transactions involved\n"
                    "   c. Amount and currency\n"
                    "3. NARRATIVE\n"
                    "   Chronological description of the suspicious activity, "
                    "including all relevant transactions, parties, jurisdictions.\n"
                    "4. SUPPORTING EVIDENCE\n"
                    "5. RECOMMENDATION\n"
                ),
                "metadata": {"source": "fallback_template"},
                "distance": 0.0,
            }],
            "guidelines": [{
                "content": (
                    "SAR FILING GUIDANCE:\n"
                    "- Use formal third-person language\n"
                    "- Present facts chronologically\n"
                    "- Reference specific transaction amounts and dates\n"
                    "- Cite relevant POCA sections where applicable\n"
                    "- Do not include internal system names or model scores\n"
                    "- State 'Information not available' for missing data\n"
                    "- Include all relevant typology indicators\n"
                ),
                "metadata": {"source": "fallback_guidance"},
                "distance": 0.0,
            }],
            "sars": [],
        }
        return fallbacks.get(source, [])
