"""
AI Awareness Module Router:
Endpoints for retrieving legal rights topics and asking interactive questions
regarding protections under the Transgender Persons Act 2019, NALSA judgment,
and Indian legal aid provisions.
"""
from typing import List, Optional
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

    return awareness.query_awareness(
        query_in.query,
        category=query_in.category,
        language=query_in.language or "en",
    )


@router.post("/chat", response_model=schemas.AwarenessChatResponse)
def chat_awareness_endpoint(chat_in: schemas.AwarenessChatRequest):
    """
    Conversational AI Awareness Assistant supporting both Chat Form and Talking (Voice) Form.
    Processes multi-turn conversations and returns formatted guidance along with speech-optimized
    text for audio playback in English, Hindi, or Tamil.
    """
    if not chat_in.messages:
        raise HTTPException(status_code=400, detail="Messages list cannot be empty")
    return awareness.chat_awareness(
        messages=chat_in.messages,
        voice_mode=chat_in.voice_mode,
        category=chat_in.category,
        language=chat_in.language or "en",
    )


@router.get("/qa/categories", response_model=List[str])
def list_qa_categories():
    """List all categories available in the 220+ Transgender Q&A knowledge base."""
    from app.data import get_categories
    return get_categories()


@router.get("/qa", response_model=schemas.QAListResponse)
def list_qa_items(
    q: Optional[str] = None,
    category: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
):
    """
    Search or browse the 220+ Indian Transgender Q&A knowledge base,
    including the dedicated Transgender Parents & Family Protections domain.
    """
    from app.data import get_all_qa, search_qa

    page = max(1, page)
    limit = max(1, min(100, limit))

    if q and q.strip():
        items = search_qa(query=q.strip(), category=category, limit=220)
    else:
        items = get_all_qa(category=category)

    total = len(items)
    start_idx = (page - 1) * limit
    paginated_items = items[start_idx : start_idx + limit]

    return schemas.QAListResponse(
        total=total,
        page=page,
        limit=limit,
        items=[
            schemas.QAKnowledgeItem(
                id=item["id"],
                category=item["category"],
                question=item["question"],
                answer=item["answer"],
                applicable_law=item["applicable_law"],
                keywords=item["keywords"],
            )
            for item in paginated_items
        ],
    )


@router.get("/qa/{qa_id}", response_model=schemas.QAKnowledgeItem)
def get_single_qa_item(qa_id: int):
    """Retrieve a single Q&A knowledge item by ID."""
    from app.data import get_qa_by_id
    item = get_qa_by_id(qa_id)
    if not item:
        raise HTTPException(status_code=404, detail="Q&A item not found")
    return schemas.QAKnowledgeItem(
        id=item["id"],
        category=item["category"],
        question=item["question"],
        answer=item["answer"],
        applicable_law=item["applicable_law"],
        keywords=item["keywords"],
    )
