"""
rag/retriever.py
RAG retriever: query ChromaDB and return relevant context + sources.
"""
import os
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

CHROMA_DIR  = Path(__file__).parent / "chroma_db"

SIMILARITY_THRESHOLD = 0.45  # minimum similarity score to include chunk

def _get_embeddings():
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    except Exception:
        return None


def retrieve(query: str, k: int = 5) -> Tuple[str, List[str]]:
    """
    Retrieve relevant context for a query from ChromaDB.

    Returns:
        (context_text, sources_list)
        If the knowledge base is unavailable or no relevant docs found,
        returns ("", [])
    """
    if not CHROMA_DIR.exists():
        logger.warning("[retriever] ChromaDB not found. Run `python rag/ingest.py` first.")
        return "", []

    embeddings = _get_embeddings()
    if embeddings is None:
        return "", []

    try:
        from langchain_chroma import Chroma
        vectorstore = Chroma(
            persist_directory=str(CHROMA_DIR),
            embedding_function=embeddings,
            collection_name="healthcare_kb",
        )
        results = vectorstore.similarity_search_with_score(query, k=k)
    except Exception as e:
        logger.error(f"[retriever] ChromaDB query failed: {e}")
        return "", []

    # Filter by similarity threshold
    relevant = [(doc, score) for doc, score in results if score <= SIMILARITY_THRESHOLD]
    if not relevant:
        logger.info(f"[retriever] No results above threshold for: {query[:80]}")
        return "", []

    context_parts = []
    sources = []
    for doc, score in relevant:
        context_parts.append(doc.page_content)
        src = doc.metadata.get("source", "Unknown")
        if src not in sources:
            sources.append(src)

    context = "\n\n---\n\n".join(context_parts)
    logger.info(f"[retriever] Retrieved {len(relevant)} chunks from: {sources}")
    return context, sources
