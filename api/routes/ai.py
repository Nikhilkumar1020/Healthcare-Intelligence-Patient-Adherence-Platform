"""api/routes/ai.py"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class AIQuery(BaseModel):
    question: str

@router.post("/query", summary="GenAI analytics assistant (SQL-grounded)")
def ai_query(req: AIQuery):
    from agents.sql_agent import run_sql_agent
    return run_sql_agent(req.question)

@router.post("/rag/query", summary="RAG knowledge base assistant")
def rag_query(req: AIQuery):
    from agents.rag_agent import run_rag_agent
    return run_rag_agent(req.question)

@router.post("/agent/query", summary="Multi-agent orchestrator")
def agent_query(req: AIQuery):
    from agents.orchestrator import run_orchestrator
    return run_orchestrator(req.question)
