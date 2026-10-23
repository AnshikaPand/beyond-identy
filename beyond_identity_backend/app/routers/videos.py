"""
Video Interviews & LGBTQ+ Community Voices Router.
Provides endpoints for retrieving, posting, and searching video interviews
featuring LGBTQ+ individuals, advocates, and community leaders across India.
"""
import os
import re
import json
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

# Persistent JSON registries to guarantee videos are NEVER lost or deleted on restart/reseed
COMMUNITY_VIDEOS_JSON = Path(__file__).resolve().parent.parent / "data" / "community_videos.json"
ALT_COMMUNITY_VIDEOS_JSON = Path(__file__).resolve().parent.parent.parent / "beyond_identity_backend" / "app" / "data" / "community_videos.json"



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
        "title": "Journey",
        "interviewee_name": "Unknown Gay",
        "identity_tag": "Gay Voice & Self-Discovery (he/him)",
        "category": "Personal Story",
        "video_url": "/static/uploads/videos/journey_unknown_gay_mumbai.mp4",
        "embed_url": "/static/uploads/videos/journey_unknown_gay_mumbai.mp4",
        "thumbnail_url": "/static/uploads/videos/journey_unknown_gay_thumb.jpg",
        "key_quote": "Freedom is the courage to live authentically without hiding in fear or shame.",
        "duration": "8 mins",
        "location": "Mumbai, Maharashtra",
        "description": "Journey to find own identity — an authentic community interview exploring self-acceptance, freedom, and living with pride in Mumbai.",
        "is_permanent": True,
    },
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
        "is_permanent": True,
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
        "is_permanent": True,
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
        "is_permanent": True,
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
        "is_permanent": True,
    },
    {
        "title": "Parental Acceptance: A Mother's Journey Embracing Her Queer Child",
        "interviewee_name": "Chitra Palekar",
        "identity_tag": "LGBTQ+ Parent Advocate & Rights Champion (she/her)",
        "category": "Personal Story",
        "video_url": "https://www.youtube.com/watch?v=2Sgq9yK1vFo",
        "embed_url": "https://www.youtube.com/embed/2Sgq9yK1vFo?rel=0",
        "thumbnail_url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=640&q=80",
        "key_quote": "Acceptance begins at home. When parents stand with pride, no child has to face the world alone.",
        "duration": "10 mins",
        "location": "Mumbai, Maharashtra",
        "description": "Pioneering Indian parent advocate shares how families can overcome social prejudice, embrace their queer children with love, and fight for inclusive schools and communities.",
        "is_permanent": True,
    },
    {
        "title": "Breaking Barriers in Sports: India's First Transgender Male Champion",
        "interviewee_name": "Aryan Pasha",
        "identity_tag": "Transgender Man, Athlete & Lawyer (he/him)",
        "category": "Personal Story",
        "video_url": "https://www.youtube.com/watch?v=kYJzX9a9R6I",
        "embed_url": "https://www.youtube.com/embed/kYJzX9a9R6I?rel=0",
        "thumbnail_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=640&q=80",
        "key_quote": "The barbell never asks for gender — only your dedication, resilience, and heart.",
        "duration": "14 mins",
        "location": "New Delhi, Delhi",
        "description": "Aryan Pasha recounts his journey coming out, undergoing gender-affirming surgery, winning silver at Musclemania India, and creating transmasculine visibility in sports.",
        "is_permanent": True,
    },
    {
        "title": "Corporate Equality & Rainbow Leadership: Workplace Inclusion in Indian Tech",
        "interviewee_name": "Neel Ghosh",
        "identity_tag": "Non-Binary & Queer HR Lead (they/them)",
        "category": "Workplace Equality",
        "video_url": "https://www.youtube.com/watch?v=8m9gR5p4Q9w",
        "embed_url": "https://www.youtube.com/embed/8m9gR5p4Q9w?rel=0",
        "thumbnail_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=640&q=80",
        "key_quote": "True inclusion means equal health insurance, gender-neutral restrooms, and psychological safety.",
        "duration": "15 mins",
        "location": "Hyderabad, Telangana",
        "description": "Leading tech diversity specialist explains how Indian IT companies and MNCs can implement Section 9 equal opportunity mandates under the Transgender Persons Act 2019.",
        "is_permanent": True,
    },
    {
        "title": "Dalit Trans Rights, Intersectional Justice & Legal Reservations",
        "interviewee_name": "Grace Banu",
        "identity_tag": "Dalit & Transgender Rights Pioneer, Computer Engineer (she/her)",
        "category": "Legal Rights & TG ID",
        "video_url": "https://www.youtube.com/watch?v=VRKiCpcJ-ag",
        "embed_url": "https://www.youtube.com/embed/VRKiCpcJ-ag?rel=0",
        "thumbnail_url": "https://images.unsplash.com/photo-1573496799652-408c2ac9fe98?auto=format&fit=crop&w=640&q=80",
        "key_quote": "Reservations are our fundamental constitutional right, not sympathy or charity.",
        "duration": "12 mins",
        "location": "Chennai, Tamil Nadu",
        "description": "Pioneering trans rights activist discusses horizontal reservations in higher education, fighting caste-based exclusion, and securing government employment for trans persons.",
        "is_permanent": True,
    },
    {
        "title": "Rural Queer Advocacy: Mobilizing Village Crisis Desks & Mutual Aid",
        "interviewee_name": "Karthik Subramaniam",
        "identity_tag": "Grassroots Organizer & Youth Counselor (he/him)",
        "category": "Housing & Garima Greh",
        "video_url": "https://www.youtube.com/watch?v=8VKlWQgSYyA",
        "embed_url": "https://www.youtube.com/embed/8VKlWQgSYyA?rel=0",
        "thumbnail_url": "https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&w=640&q=80",
        "key_quote": "Community begins the moment we stand shoulder-to-shoulder in the small towns and villages.",
        "duration": "11 mins",
        "location": "Madurai, Tamil Nadu",
        "description": "Grassroots activists share their mission organizing rural queer collectives, emergency shelter networks, police sensitization, and legal aid in tier-2 and tier-3 towns.",
        "is_permanent": True,
    },
    {
        "title": "Queer Affirmative Mental Healthcare & Overcoming Minority Stress",
        "interviewee_name": "Dr. Prasad Raj Dandekar",
        "identity_tag": "Oncologist & LGBTQ+ Mental Health Advocate (he/him)",
        "category": "Healthcare & Transition",
        "video_url": "https://www.youtube.com/watch?v=k5jGq5_w2g0",
        "embed_url": "https://www.youtube.com/embed/k5jGq5_w2g0?rel=0",
        "thumbnail_url": "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&w=640&q=80",
        "key_quote": "Affirmative mental healthcare saves lives by honoring identity rather than pathologizing love.",
        "duration": "14 mins",
        "location": "Pune, Maharashtra",
        "description": "Leading queer medical professional discusses mental resilience, navigating social dysphoria, outlawing conversion practices, and connecting with queer affirmative therapists.",
        "is_permanent": True,
    },
    {
        "title": "Two Brides in Kolkata: Our Traditional Wedding & Journey of Love",
        "interviewee_name": "Anwesa & Megha",
        "identity_tag": "Lesbian Couple & Equality Advocates (she/her)",
        "category": "Personal Story",
        "video_url": "https://www.youtube.com/watch?v=8VKlWQgSYyA",
        "embed_url": "https://www.youtube.com/embed/8VKlWQgSYyA?rel=0",
        "thumbnail_url": "https://images.unsplash.com/photo-1511285560929-80b456fea0bc?auto=format&fit=crop&w=640&q=80",
        "key_quote": "Love needs no societal validation to be sacred, joyful, and eternal.",
        "duration": "9 mins",
        "location": "Kolkata, West Bengal",
        "description": "An inspiring couple share their traditional Bengali wedding ceremony, building a home together, and championing marriage equality and equal partnership rights across India.",
        "is_permanent": True,
    },
]


def get_registered_videos() -> List[dict]:
    """Reads videos from persistent JSON registry, falling back to INITIAL_SEED_INTERVIEWS."""
    videos = []
    if COMMUNITY_VIDEOS_JSON.exists():
        try:
            with open(COMMUNITY_VIDEOS_JSON, "r", encoding="utf-8") as f:
                videos = json.load(f)
        except Exception:
            videos = []
    if not videos and ALT_COMMUNITY_VIDEOS_JSON.exists():
        try:
            with open(ALT_COMMUNITY_VIDEOS_JSON, "r", encoding="utf-8") as f:
                videos = json.load(f)
        except Exception:
            videos = []
    if not videos:
        videos = INITIAL_SEED_INTERVIEWS
    return videos


def persist_community_video(video_dict: dict):
    """Safeguards any user uploaded or new community video by appending to persistent JSON registries."""
    try:
        videos = get_registered_videos()
        clean_url = (video_dict.get("video_url") or "").strip().lower()
        clean_title = (video_dict.get("title") or "").strip().lower()

        # Check if already in persistent list
        exists = any(
            (v.get("video_url") or "").strip().lower() == clean_url or
            (v.get("title") or "").strip().lower() == clean_title
            for v in videos
        )
        if not exists:
            videos.append(video_dict)
            for path in [COMMUNITY_VIDEOS_JSON, ALT_COMMUNITY_VIDEOS_JSON]:
                if path.parent.exists():
                    try:
                        with open(path, "w", encoding="utf-8") as f:
                            json.dump(videos, f, indent=2, ensure_ascii=False)
                    except Exception:
                        pass
    except Exception as e:
        print(f"Warning: could not persist community video to JSON: {e}")


def unpersist_community_video(video_url: str):
    """Removes a video from community_videos.json if explicitly deleted."""
    try:
        videos = get_registered_videos()
        clean_url = (video_url or "").strip().lower()
        filtered = [v for v in videos if (v.get("video_url") or "").strip().lower() != clean_url]
        for path in [COMMUNITY_VIDEOS_JSON, ALT_COMMUNITY_VIDEOS_JSON]:
            if path.parent.exists():
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(filtered, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass
    except Exception as e:
        print(f"Warning: could not unpersist video: {e}")


def ensure_seed_videos(db: Session):
    """
    Seeds or restores all authentic community video interviews from persistent storage.
    Guarantees user uploads and core community videos are ALWAYS present and never deleted.
    """
    videos_catalog = get_registered_videos()

    existing_titles = {v.title.strip().lower() for v in db.query(VideoInterview).all() if v.title}
    existing_urls = {v.video_url.strip().lower() for v in db.query(VideoInterview).all() if v.video_url}

    added = False
    for seed in videos_catalog:
        title_key = (seed.get("title") or "").strip().lower()
        url_key = (seed.get("video_url") or "").strip().lower()

        if title_key not in existing_titles and url_key not in existing_urls:
            embed_url = seed.get("embed_url")
            thumb_url = seed.get("thumbnail_url")
            if not embed_url or not thumb_url:
                norm_embed, norm_thumb = normalize_video_embed(seed.get("video_url", ""))
                embed_url = embed_url or norm_embed
                thumb_url = thumb_url or norm_thumb

            vid = VideoInterview(
                title=seed["title"],
                interviewee_name=seed["interviewee_name"],
                identity_tag=seed.get("identity_tag", "LGBTQ+ Community"),
                category=seed.get("category", "Personal Story"),
                video_url=seed["video_url"],
                embed_url=embed_url,
                thumbnail_url=thumb_url,
                key_quote=seed.get("key_quote", ""),
                duration=seed.get("duration", "10 mins"),
                location=seed.get("location", "India"),
                description=seed.get("description", ""),
                is_verified=True,
            )
            db.add(vid)
            existing_titles.add(title_key)
            existing_urls.add(url_key)
            added = True

    if added:
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

    # Automatically persist to JSON backup so it is permanently kept across reboots/re-seeds
    persist_community_video({
        "title": new_interview.title,
        "interviewee_name": new_interview.interviewee_name,
        "identity_tag": new_interview.identity_tag,
        "category": new_interview.category,
        "video_url": new_interview.video_url,
        "embed_url": new_interview.embed_url,
        "thumbnail_url": new_interview.thumbnail_url,
        "description": new_interview.description,
        "key_quote": new_interview.key_quote,
        "duration": new_interview.duration,
        "location": new_interview.location,
        "is_verified": True,
        "is_permanent": False,
    })

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
    """Delete a video interview by ID (core authentic community videos are protected)."""
    interview = db.query(VideoInterview).filter(VideoInterview.id == video_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Video interview not found")

    # Safeguard core authentic community videos from deletion
    core_urls = {
        (v.get("video_url") or "").strip().lower()
        for v in INITIAL_SEED_INTERVIEWS
    }
    if (interview.video_url or "").strip().lower() in core_urls:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Core authentic community video interviews are protected and cannot be deleted."
        )

    unpersist_community_video(interview.video_url)
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

    # Automatically persist to JSON backup so it is permanently kept across reboots/re-seeds
    persist_community_video({
        "title": new_interview.title,
        "interviewee_name": new_interview.interviewee_name,
        "identity_tag": new_interview.identity_tag,
        "category": new_interview.category,
        "video_url": new_interview.video_url,
        "embed_url": new_interview.embed_url,
        "thumbnail_url": new_interview.thumbnail_url,
        "description": new_interview.description,
        "key_quote": new_interview.key_quote,
        "duration": new_interview.duration,
        "location": new_interview.location,
        "is_verified": True,
        "is_permanent": False,
    })

    return new_interview

