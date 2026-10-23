"""
Video Interviews & LGBTQ+ Community Voices Router.
Provides endpoints for retrieving, posting, and searching video interviews
featuring LGBTQ+ individuals, advocates, and community leaders across India.
"""
import re
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.database import get_db
from app.models import VideoInterview, User
from app.schemas import VideoInterviewCreate, VideoInterviewOut
from app.auth import SECRET_KEY, ALGORITHM
from jose import jwt

router = APIRouter(prefix="/api/videos", tags=["Video Interviews & Community Voices"])


def get_current_user_optional(
    authorization: Optional[str] = None, db: Session = Depends(get_db)
) -> Optional[User]:
    """Extracts user from Authorization Bearer token if present."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_sub = payload.get("sub")
        if user_sub and str(user_sub).isdigit():
            return db.query(User).filter(User.id == int(user_sub)).first()
    except Exception:
        return None
    return None


def normalize_video_embed(url: str) -> tuple[str, str]:
    """
    Normalizes video URLs (YouTube, Vimeo, etc.) into playable iframe embed URLs
    and extracts a representative thumbnail image.
    Returns (embed_url, thumbnail_url).
    """
    clean_url = (url or "").strip()
    if not clean_url:
        return "", ""

    # YouTube regex (regular watch, short, youtu.be, embed)
    yt_pattern = r"(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/|youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})"
    yt_match = re.search(yt_pattern, clean_url)
    if yt_match:
        video_id = yt_match.group(1)
        embed_url = f"https://www.youtube.com/embed/{video_id}?rel=0"
        thumb_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        return embed_url, thumb_url

    # Vimeo regex
    vimeo_pattern = r"vimeo\.com\/(?:channels\/(?:\w+\/)?|groups\/([^\/]*)\/videos\/|album\/(\d+)\/video\/|)(\d+)"
    vimeo_match = re.search(vimeo_pattern, clean_url)
    if vimeo_match:
        video_id = vimeo_match.group(3)
        embed_url = f"https://player.vimeo.com/video/{video_id}"
        thumb_url = "https://images.unsplash.com/photo-1579208575657-c595a05383b7?auto=format&fit=crop&w=640&q=80"
        return embed_url, thumb_url

    # Direct embed link or fallback
    return clean_url, "https://images.unsplash.com/photo-1579208575657-c595a05383b7?auto=format&fit=crop&w=640&q=80"


INITIAL_SEED_INTERVIEWS = [
    {
        "title": "From Rejection to Inspiration: Clinical Transition & Transgender Representation",
        "interviewee_name": "Dr. Trinetra Haldar Gummaraju",
        "identity_tag": "Transgender Woman & Surgeon (she/her)",
        "category": "Healthcare & Transition",
        "video_url": "https://www.youtube.com/watch?v=jW2m3_Y8hU0",
        "embed_url": "https://www.youtube.com/embed/jW2m3_Y8hU0?rel=0",
        "thumbnail_url": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=640&q=80",
        "key_quote": "Living authentically is the most revolutionary act of self-preservation.",
        "duration": "18 mins",
        "location": "Bengaluru, Karnataka",
        "description": "Doctor, activist, and creator Dr. Trinetra discusses clinical transition protocols, legal TG identity cards, and overcoming social discrimination in Indian medical institutions.",
    },
    {
        "title": "Breaking Barriers in Bodybuilding: India's First Transgender Male Champion",
        "interviewee_name": "Aryan Pasha",
        "identity_tag": "Transgender Man & Advocate (he/him)",
        "category": "Workplace & Sports",
        "video_url": "https://www.youtube.com/watch?v=kYJzX9a9R6I",
        "embed_url": "https://www.youtube.com/embed/kYJzX9a9R6I?rel=0",
        "thumbnail_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=640&q=80",
        "key_quote": "The weights never asked for my gender — only my dedication and resilience.",
        "duration": "14 mins",
        "location": "New Delhi, Delhi",
        "description": "Aryan Pasha recounts his journey coming out, undergoing gender-affirming surgery, fighting for legal identity recognition, and winning silver at Musclemania India.",
    },
    {
        "title": "Garima Greh: A Mother’s Mission for Shelter & Dignity in Maharashtra",
        "interviewee_name": "Gauri Sawant",
        "identity_tag": "Transgender Rights Pioneer (she/her)",
        "category": "Housing & Garima Greh",
        "video_url": "https://www.youtube.com/watch?v=Vl3j-6S9u6c",
        "embed_url": "https://www.youtube.com/embed/Vl3j-6S9u6c?rel=0",
        "thumbnail_url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=640&q=80",
        "key_quote": "Motherhood is an emotion, not a gender assignment dictated by society.",
        "duration": "22 mins",
        "location": "Mumbai, Maharashtra",
        "description": "NALSA (2014) petitioner Gauri Sawant speaks on community shelter homes, adopting trans youth in crisis, and building permanent elder care facilities for trans women.",
    },
    {
        "title": "Corporate Equality & Rainbow Leadership: Workplace Inclusion in Tech",
        "interviewee_name": "Neel Ghosh",
        "identity_tag": "Non-Binary / Queer HR Lead (they/them)",
        "category": "Workplace Equality",
        "video_url": "https://www.youtube.com/watch?v=8m9gR5p4Q9w",
        "embed_url": "https://www.youtube.com/embed/8m9gR5p4Q9w?rel=0",
        "thumbnail_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=640&q=80",
        "key_quote": "True inclusion means equal health insurance, gender-neutral restrooms, and psychological safety.",
        "duration": "15 mins",
        "location": "Hyderabad, Telangana",
        "description": "Leading tech diversity specialist explains how Indian IT companies and MNCs can implement Section 9 equal opportunity mandates under the Transgender Persons Act 2019.",
    },
]


def ensure_seed_videos(db: Session):
    """Seeds starter video interviews if table is empty."""
    count = db.query(VideoInterview).count()
    if count == 0:
        for seed in INITIAL_SEED_INTERVIEWS:
            vid = VideoInterview(
                title=seed["title"],
                interviewee_name=seed["interviewee_name"],
                identity_tag=seed["identity_tag"],
                category=seed["category"],
                video_url=seed["video_url"],
                embed_url=seed["embed_url"],
                thumbnail_url=seed["thumbnail_url"],
                key_quote=seed["key_quote"],
                duration=seed["duration"],
                location=seed["location"],
                description=seed["description"],
                is_verified=True,
            )
            db.add(vid)
        db.commit()


@router.get("", response_model=List[VideoInterviewOut])
def get_video_interviews(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by title, interviewee or keyword"),
    db: Session = Depends(get_db),
):
    """
    Retrieve all published LGBTQ+ video interviews.
    Supports filtering by category and full-text keyword search.
    """
    ensure_seed_videos(db)
    query = db.query(VideoInterview).filter(VideoInterview.is_verified == True)

    if category and category.lower() != "all":
        query = query.filter(VideoInterview.category.ilike(f"%{category}%"))

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                VideoInterview.title.ilike(search_term),
                VideoInterview.interviewee_name.ilike(search_term),
                VideoInterview.description.ilike(search_term),
                VideoInterview.key_quote.ilike(search_term),
                VideoInterview.location.ilike(search_term),
            )
        )

    return query.order_by(desc(VideoInterview.created_at)).all()


@router.post("", response_model=VideoInterviewOut, status_code=status.HTTP_201_CREATED)
def post_video_interview(
    payload: VideoInterviewCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Post a new LGBTQ+ video interview.
    Automatically parses YouTube, Vimeo, or direct embed links and thumbnails.
    """
    if not payload.title or not payload.title.strip():
        raise HTTPException(status_code=400, detail="Interview title is required")
    if not payload.interviewee_name or not payload.interviewee_name.strip():
        raise HTTPException(status_code=400, detail="Interviewee name is required")
    if not payload.video_url or not payload.video_url.strip():
        raise HTTPException(status_code=400, detail="Video URL is required")

    embed_url, thumb_url = normalize_video_embed(payload.video_url)

    new_interview = VideoInterview(
        title=payload.title.strip(),
        interviewee_name=payload.interviewee_name.strip(),
        identity_tag=(payload.identity_tag or "LGBTQ+ Community").strip(),
        category=(payload.category or "Personal Story").strip(),
        video_url=payload.video_url.strip(),
        embed_url=embed_url,
        thumbnail_url=thumb_url,
        description=(payload.description or "").strip(),
        key_quote=(payload.key_quote or "").strip(),
        duration=(payload.duration or "10 mins").strip(),
        location=(payload.location or "India").strip(),
        submitted_by_id=current_user.id if current_user else None,
        is_verified=True,
    )

    db.add(new_interview)
    db.commit()
    db.refresh(new_interview)
    return new_interview


@router.get("/{video_id}", response_model=VideoInterviewOut)
def get_video_interview_by_id(video_id: int, db: Session = Depends(get_db)):
    """Retrieve details of a single video interview by ID."""
    interview = db.query(VideoInterview).filter(VideoInterview.id == video_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Video interview not found")
    return interview


@router.delete("/{video_id}", status_code=status.HTTP_200_OK)
def delete_video_interview(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Delete a video interview by ID."""
    interview = db.query(VideoInterview).filter(VideoInterview.id == video_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Video interview not found")

    db.delete(interview)
    db.commit()
    return {"message": "Video interview successfully deleted", "id": video_id}
