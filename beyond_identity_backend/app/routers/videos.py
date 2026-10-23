"""
Video Interviews & LGBTQ+ Community Voices Router.
Provides endpoints for retrieving, posting, and searching video interviews
featuring LGBTQ+ individuals, advocates, and community leaders across India.
"""
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, Header, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.database import get_db
from app.models import VideoInterview, User
from app.schemas import VideoInterviewCreate, VideoInterviewOut
from app.auth import SECRET_KEY, ALGORITHM
from jose import jwt

router = APIRouter(prefix="/api/videos", tags=["Video Interviews & Community Voices"])

# Directory where uploaded phone and device video files are stored
UPLOADS_DIR = Path(__file__).resolve().parent.parent / "static" / "uploads" / "videos"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

ALT_UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "beyond_identity_backend" / "app" / "static" / "uploads" / "videos"
if ALT_UPLOADS_DIR.parent.parent.exists():
    try:
        ALT_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def get_current_user_optional(
    authorization: Optional[str] = Header(None), db: Session = Depends(get_db)
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
        "title": "Claiming My Identity & Workplace Rights in Tech",
        "interviewee_name": "Aarohi Sen",
        "identity_tag": "Transgender Advocate & Software Engineer (she/her)",
        "category": "Workplace Equality",
        "video_url": "/static/uploads/videos/community_phone_interview_sample.mp4",
        "embed_url": "/static/uploads/videos/community_phone_interview_sample.mp4",
        "thumbnail_url": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=640&q=80",
        "key_quote": "True transition isn't just medical or legal — it's claiming your rightful place in society without fear.",
        "duration": "Phone Video",
        "location": "Bengaluru, Karnataka",
        "description": "Aarohi shares a direct mobile video interview discussing transition protocols, legal TG card procedures, and overcoming discrimination in Indian corporations.",
    },
    {
        "title": "Garima Greh: A Mother’s Mission for Shelter & Dignity in Maharashtra",
        "interviewee_name": "Gauri Sawant",
        "identity_tag": "Transgender Rights Pioneer & NALSA Petitioner (she/her)",
        "category": "Housing & Garima Greh",
        "video_url": "https://www.youtube.com/watch?v=8VKlWQgSYyA",
        "embed_url": "https://www.youtube.com/embed/8VKlWQgSYyA?rel=0",
        "thumbnail_url": "https://img.youtube.com/vi/8VKlWQgSYyA/hqdefault.jpg",
        "key_quote": "Motherhood is an emotion, not a gender assignment dictated by society.",
        "duration": "3 mins",
        "location": "Mumbai, Maharashtra",
        "description": "NALSA (2014) petitioner Gauri Sawant speaks on community shelter homes, adopting trans youth in crisis, and building permanent elder care facilities for trans women.",
    },
    {
        "title": "Indian, Trans, A Unique Stance: Clinical Transition & Representation",
        "interviewee_name": "Dr. Trinetra Haldar Gummaraju",
        "identity_tag": "Transgender Woman, Surgeon & Creator (she/her)",
        "category": "Healthcare & Transition",
        "video_url": "https://www.youtube.com/watch?v=VRKiCpcJ-ag",
        "embed_url": "https://www.youtube.com/embed/VRKiCpcJ-ag?rel=0",
        "thumbnail_url": "https://img.youtube.com/vi/VRKiCpcJ-ag/hqdefault.jpg",
        "key_quote": "Living authentically is the most revolutionary act of self-preservation.",
        "duration": "16 mins",
        "location": "Bengaluru, Karnataka",
        "description": "Doctor, activist, and creator Dr. Trinetra discusses clinical transition protocols, legal TG identity cards, and overcoming social discrimination in Indian medical institutions.",
    },
    {
        "title": "Stories Can Change the Law: The Battle Overturning Section 377",
        "interviewee_name": "Arundhati Katju & Dr. Menaka Guruswamy",
        "identity_tag": "Supreme Court Advocates & Human Rights Defenders",
        "category": "Legal Rights & TG ID",
        "video_url": "https://www.youtube.com/watch?v=k5jGq5_w2g0",
        "embed_url": "https://www.youtube.com/embed/k5jGq5_w2g0?rel=0",
        "thumbnail_url": "https://img.youtube.com/vi/k5jGq5_w2g0/hqdefault.jpg",
        "key_quote": "When personal stories enter the courtroom, the law is compelled to recognize our shared humanity.",
        "duration": "13 mins",
        "location": "New Delhi, Delhi",
        "description": "Lead Supreme Court advocates recount the historic litigation that struck down Section 377, affirming the fundamental right to love, equality, and dignity across India.",
    },
]


def ensure_seed_videos(db: Session):
    """Seeds or refreshes starter video interviews if table is empty or has obsolete seed entries."""
    count = db.query(VideoInterview).count()
    has_broken_seeds = db.query(VideoInterview).filter(VideoInterview.video_url.like("%jW2m3_Y8hU0%")).count() > 0

    if count == 0 or has_broken_seeds:
        if has_broken_seeds:
            db.query(VideoInterview).filter(VideoInterview.video_url.like("%jW2m3_Y8hU0%")).delete(synchronize_session=False)
            db.query(VideoInterview).filter(VideoInterview.video_url.like("%kYJzX9a9R6I%")).delete(synchronize_session=False)
            db.query(VideoInterview).filter(VideoInterview.video_url.like("%Vl3j-6S9u6c%")).delete(synchronize_session=False)
            db.query(VideoInterview).filter(VideoInterview.video_url.like("%8m9gR5p4Q9w%")).delete(synchronize_session=False)
            db.commit()

        existing_urls = {v.video_url for v in db.query(VideoInterview).all()}
        for seed in INITIAL_SEED_INTERVIEWS:
            if seed["video_url"] not in existing_urls:
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


@router.post("/upload-file")
async def upload_phone_video_file(file: UploadFile = File(...)):
    """
    Direct file upload endpoint for videos recorded on or picked from mobile phones & tablets.
    Accepts video formats (mp4, mov, webm, m4v, 3gp) and saves to static uploads directory.
    """
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No video file provided")

    ext = Path(file.filename).suffix.lower()
    allowed_exts = {".mp4", ".mov", ".webm", ".m4v", ".3gp", ".avi", ".mkv"}
    if ext not in allowed_exts:
        # Default to mp4 if phone browser sent video blob without explicit extension
        ext = ".mp4"

    unique_filename = f"phone_video_{uuid.uuid4().hex[:12]}{ext}"
    dest_path = UPLOADS_DIR / unique_filename

    try:
        with dest_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Mirror file to secondary root if it exists
        if ALT_UPLOADS_DIR.exists():
            try:
                shutil.copyfile(dest_path, ALT_UPLOADS_DIR / unique_filename)
            except Exception:
                pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save phone video: {str(e)}")

    video_url = f"/static/uploads/videos/{unique_filename}"
    return {
        "video_url": video_url,
        "filename": unique_filename,
        "content_type": file.content_type,
    }


@router.post("/upload", response_model=VideoInterviewOut, status_code=status.HTTP_201_CREATED)
async def post_video_interview_upload(
    file: UploadFile = File(...),
    title: str = Form(...),
    interviewee_name: str = Form(...),
    identity_tag: Optional[str] = Form("LGBTQ+ Community"),
    category: Optional[str] = Form("Personal Story"),
    key_quote: Optional[str] = Form(None),
    location: Optional[str] = Form("India"),
    duration: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Combined mobile upload: Accepts video recorded on phone or selected from phone gallery
    along with interview details, saves the file and publishes the interview.
    """
    if not title or not title.strip():
        raise HTTPException(status_code=400, detail="Interview title is required")
    if not interviewee_name or not interviewee_name.strip():
        raise HTTPException(status_code=400, detail="Interviewee name is required")
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Video file is required")

    ext = Path(file.filename).suffix.lower()
    allowed_exts = {".mp4", ".mov", ".webm", ".m4v", ".3gp", ".avi", ".mkv"}
    if ext not in allowed_exts:
        ext = ".mp4"

    unique_filename = f"phone_video_{uuid.uuid4().hex[:12]}{ext}"
    dest_path = UPLOADS_DIR / unique_filename

    try:
        with dest_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        if ALT_UPLOADS_DIR.exists():
            try:
                shutil.copyfile(dest_path, ALT_UPLOADS_DIR / unique_filename)
            except Exception:
                pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save video file: {str(e)}")

    video_url = f"/static/uploads/videos/{unique_filename}"
    embed_url = video_url
    thumb_url = "https://images.unsplash.com/photo-1579208575657-c595a05383b7?auto=format&fit=crop&w=640&q=80"

    new_interview = VideoInterview(
        title=title.strip(),
        interviewee_name=interviewee_name.strip(),
        identity_tag=(identity_tag or "LGBTQ+ Community").strip(),
        category=(category or "Personal Story").strip(),
        video_url=video_url,
        embed_url=embed_url,
        thumbnail_url=thumb_url,
        description=(description or "").strip(),
        key_quote=(key_quote or "").strip(),
        duration=(duration or "Phone Video").strip(),
        location=(location or "India").strip(),
        submitted_by_id=current_user.id if current_user else None,
        is_verified=True,
    )

    db.add(new_interview)
    db.commit()
    db.refresh(new_interview)
    return new_interview
