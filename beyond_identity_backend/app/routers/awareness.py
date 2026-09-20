"""
AI Awareness Module Router:
Endpoints for retrieving legal rights topics and asking interactive questions
regarding protections under the Transgender Persons Act 2019, NALSA judgment,
and Indian legal aid provisions.
"""
from typing import List
from fastapi import APIRouter, HTTPException

from app import schemas
from app.services import awareness

router = APIRouter(prefix="/awareness", tags=["ai-awareness"])


@router.get("/topics", response_model=List[schemas.AwarenessTopicOut])
def list_awareness_topics():
    """Returns curated guides on Indian constitutional, statutory, and documentation rights."""
    return awareness.get_all_topics()


@router.get("/topics/{topic_id}", response_model=schemas.AwarenessTopicOut)
def get_awareness_topic(topic_id: str):
    """Get details of a specific legal topic."""
    topic = awareness.get_topic_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic


@router.post("/query", response_model=schemas.AwarenessQueryResponse)
def ask_awareness_query(query_in: schemas.AwarenessQueryRequest):
    """
    Query the AI Legal Awareness knowledge base.
    Analyzes questions on discrimination, workplace issues, housing rights, police harassment,
    or documentation, returning legal citations, plain-language rights, actionable steps,
    and official portal links.
    """
    if not query_in.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    return awareness.query_awareness(query_in.query, query_in.category)
