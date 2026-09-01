"""
agents/rag_agent.py
RAG Knowledge Agent: retrieves from ChromaDB and synthesizes with LLM.
Explicitly states when knowledge base lacks information.
"""
import os
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

GROQ_KEY = os.getenv("GROQ_API_KEY", "")
NOT_FOUND_MSG = (
    "I could not find sufficient information in the provided knowledge base "
    "to answer this question. Please consult appropriate clinical or regulatory resources."
)


def run_rag_agent(question: str) -> Dict[str, Any]:
    """
    Query the knowledge base and synthesize an answer.
    Always cites sources. Explicitly admits knowledge gaps.
    """
    result = {
        "question": question,
        "answer":   "",
        "sources":  [],
        "error":    ""
    }

    try:
        from rag.retriever import retrieve
        context, sources = retrieve(question, k=5)

        if not context:
            result["answer"] = NOT_FOUND_MSG
            return result

        result["sources"] = sources

        if not (GROQ_KEY and GROQ_KEY.startswith("gsk_")):
            # Offline: return raw context
            result["answer"] = (
                f"[AI explanation unavailable — no Groq key]\n\n"
                f"Retrieved context from knowledge base:\n\n{context[:1500]}..."
            )
            return result

        from groq import Groq
        client = Groq(api_key=GROQ_KEY)

        prompt = f"""You are a healthcare knowledge assistant for a medication adherence platform.
Answer the question using ONLY the provided knowledge base context below.
If the context does not contain sufficient information, say:
"I could not find sufficient information in the provided knowledge base."

Do not invent or fabricate any information not present in the context.
Do not make clinical recommendations or medical diagnoses.
Cite the relevant document sections in your answer.

KNOWLEDGE BASE CONTEXT:
{context}

QUESTION: {question}

Provide a concise, professional answer (3–6 sentences).
This is analysis of synthetic healthcare content for portfolio demonstration."""

        response = client.chat.completions.create(
            model="groq/compound",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=400,
        )
        result["answer"] = response.choices[0].message.content.strip()

    except Exception as e:
        result["error"] = str(e)
        result["answer"] = NOT_FOUND_MSG
        logger.error(f"[rag_agent] Error: {e}")

    return result
