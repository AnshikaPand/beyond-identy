"""
AI Chatbot Router:
Provides endpoints for the interactive 24/7 Beyond Identity AI Assistant Chatbox.
Supports multi-turn conversational querying, live database listing search,
legal rights guidance, health triage, and crisis management.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from app import schemas, models
from app.database import get_db
from app.services import chatbot
from app.auth import SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/chatbot", tags=["ai-chatbot"])


def get_optional_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[models.User]:
    """Helper to optionally authenticate a user from the Authorization header without raising 401."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            return None
        return db.query(models.User).filter(models.User.email == email).first()
    except (JWTError, Exception):
        return None


@router.post("/query", response_model=schemas.ChatbotQueryResponse)
def handle_chatbot_query(
    request: schemas.ChatbotQueryRequest,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user),
):
    """
    Primary endpoint for the AI Chatbox widget.
    Processes user queries across legal rights, verified database listings,
    healthcare triage, and 24/7 crisis support.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    return chatbot.answer_chatbot_query(db=db, request=request, current_user=current_user)


@router.get("/prompts")
def get_chatbot_prompts():
    """Returns curated starter prompts for 1-click consultation in the AI Chatbox."""
    return {
        "categories": [
            {
                "id": "jobs",
                "label": "💼 Jobs & Employment",
                "prompts": [
                    "Find verified inclusive jobs in Mumbai or Remote",
                    "What are workplace non-discrimination rights under TG Act 2019?",
                    "How to file a complaint with a company Complaints Officer?",
                ],
            },
            {
                "id": "housing",
                "label": "🏠 Housing & Shelters",
                "prompts": [
                    "Can a landlord evict me without notice for being trans?",
                    "Where can I find a Garima Greh emergency transit shelter?",
                    "Find verified trans-friendly rental apartments",
                ],
            },
            {
                "id": "healthcare",
                "label": "🩺 Healthcare & HRT",
                "prompts": [
                    "What blood tests are required before starting HRT?",
                    "How does Ayushman Bharat ₹5 Lakh transgender package work?",
                    "Find gender-affirming healthcare clinics",
                ],
            },
            {
                "id": "legal",
                "label": "⚖️ Legal Rights & ID",
                "prompts": [
                    "How do I apply for a TG Certificate on the National Portal?",
                    "How to get free legal counsel under NALSA Section 12?",
                    "Can trans parents legally adopt in India under CARA rules?",
                ],
            },
            {
                "id": "crisis",
                "label": "🚨 Crisis & Helplines",
                "prompts": [
                    "What is the 24/7 Transgender Community Helpline number?",
                    "I am facing physical threats and need immediate protection",
                    "Connect me to Tele-MANAS mental health support (14416)",
                ],
            },
        ]
    }


@router.get("/stats")
def get_chatbot_stats(db: Session = Depends(get_db)):
    """Returns statistics of resources available through the AI assistant."""
    verified_listings = db.query(models.Listing).filter(
        models.Listing.status == models.VerificationStatus.verified
    ).count()

    from app.data import ALL_QA
    return {
        "verified_listings": verified_listings,
        "legal_qa_items": len(ALL_QA),
        "emergency_helpline": "868989330",
        "tele_manas": "14416",
        "nalsa_legal_aid": "15100",
        "national_portal": "https://transgender.dosje.gov.in",
    }
