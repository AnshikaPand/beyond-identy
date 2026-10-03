from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/listings", tags=["listings"])


@router.post("/", response_model=schemas.ListingOut, status_code=201)
def create_listing(
    listing_in: schemas.ListingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Any logged-in user can submit a listing. It starts as 'pending' until an NGO/admin verifies it."""
    payload = listing_in.model_dump() if hasattr(listing_in, "model_dump") else listing_in.dict()
    listing = models.Listing(**payload, submitted_by_id=current_user.id)
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing



@router.get("/", response_model=List[schemas.ListingOut])
def list_listings(
    category: Optional[models.ListingCategory] = None,
    status: Optional[models.VerificationStatus] = models.VerificationStatus.verified,
    db: Session = Depends(get_db),
):
    """Public browsing endpoint. Defaults to showing only verified listings — that's the whole trust model."""
    query = db.query(models.Listing)
    if category:
        query = query.filter(models.Listing.category == category)
    if status:
        query = query.filter(models.Listing.status == status)
    return query.order_by(models.Listing.created_at.desc()).all()


@router.get("/ngo-directory")
def get_ngo_directory(
    query: Optional[str] = None,
    city_or_state: Optional[str] = None,
    service_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Public directory of verified NGOs, community shelters (Garima Greh),
    healthcare facilities, legal defense partners, and 24/7 crisis helplines.
    Powers the public login/landing support chatbot.
    """
    from app.services.matcher import VERIFIED_NGOS

    helplines = [
        {
            "name": "24/7 Transgender Crisis Helpline",
            "number": "868989330",
            "description": "Immediate 24/7 crisis de-escalation, suicide prevention, and emergency support.",
            "available": "24/7 Active",
            "category": "Emergency & Crisis",
            "icon": "🚨",
        },
        {
            "name": "Tele-MANAS Mental Health Helpline",
            "number": "14416",
            "description": "Government of India 24/7 affirmative mental health counseling and crisis support.",
            "available": "24/7 Toll-Free",
            "category": "Mental Health",
            "icon": "🧠",
        },
        {
            "name": "National Transgender Toll-Free Helpline (MoSJE)",
            "number": "14566",
            "description": "Central welfare schemes, certificate issues, and Garima Greh shelter connectivity.",
            "available": "Toll-Free (MoSJE)",
            "category": "Welfare & Shelters",
            "icon": "🏛️",
        },
        {
            "name": "NALSA Free Legal Aid Toll-Free Helpline",
            "number": "15100",
            "description": "Free advocate assignment, police harassment protection, Section 12 legal aid.",
            "available": "24/7 Toll-Free",
            "category": "Legal Defense",
            "icon": "⚖️",
        },
        {
            "name": "Ayushman Bharat PM-JAY Transgender Health Desk",
            "number": "14555",
            "description": "Inquiries for ₹5,00,000 cashless gender affirmation and medical package.",
            "available": "Toll-Free (NHA)",
            "category": "Healthcare",
            "icon": "🩺",
        },
    ]

    all_ngos = []
    for ngo in VERIFIED_NGOS:
        all_ngos.append({
            "name": ngo["name"],
            "focus_area": ngo.get("focus_area", "Community & Legal Rights"),
            "location": ngo.get("location", "Pan-India"),
            "contact_email": ngo.get("contact_email"),
            "contact_phone": ngo.get("contact_phone"),
            "services_offered": ngo.get("services_offered", []),
            "states": ngo.get("states", ["all"]),
            "verified": True,
            "source": "verified_partner",
        })

    # Integrate verified community/housing listings from database
    db_listings = (
        db.query(models.Listing)
        .filter(
            models.Listing.status == models.VerificationStatus.verified,
            models.Listing.category.in_([
                models.ListingCategory.community,
                models.ListingCategory.housing,
                models.ListingCategory.healthcare,
            ]),
        )
        .all()
    )
    for item in db_listings:
        org_name = (item.organization_name or item.title).strip()
        existing = [n["name"].lower() for n in all_ngos]
        if org_name.lower() not in existing and not any(org_name.lower() in n for n in existing):
            all_ngos.append({
                "name": org_name,
                "focus_area": item.title,
                "location": item.location or "India",
                "contact_email": item.contact_info if "@" in (item.contact_info or "") else None,
                "contact_phone": item.contact_info if "@" not in (item.contact_info or "") else None,
                "services_offered": [item.description] if item.description else [],
                "states": ["all"],
                "verified": True,
                "source": "community_listing",
            })

    # Apply search and filter
    filtered = all_ngos
    if query:
        q = query.strip().lower()
        filtered = [
            n for n in filtered
            if q in n["name"].lower()
            or q in n["focus_area"].lower()
            or q in n["location"].lower()
            or any(q in s.lower() for s in n["services_offered"])
        ]

    if city_or_state:
        cs = city_or_state.strip().lower()
        filtered = [
            n for n in filtered
            if cs in n["location"].lower()
            or any(cs in s.lower() for s in n["states"])
        ]

    if service_type:
        st = service_type.strip().lower()
        filtered = [
            n for n in filtered
            if st in n["focus_area"].lower()
            or any(st in s.lower() for s in n["services_offered"])
        ]

    return {
        "status": "success",
        "total": len(filtered),
        "helplines": helplines,
        "ngos": filtered,
    }


@router.get("/{listing_id}", response_model=schemas.ListingOut)
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    listing = db.query(models.Listing).filter(models.Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.patch("/{listing_id}/verify", response_model=schemas.ListingOut)
def verify_listing(
    listing_id: int,
    verification: schemas.VerificationUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        auth.require_role(models.UserRole.verifier, models.UserRole.admin)
    ),
):
    """NGO partners / community moderators / admins only — the phased verification rollout from slide 7."""
    listing = db.query(models.Listing).filter(models.Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    listing.status = verification.status
    listing.verification_notes = verification.verification_notes
    listing.verified_by_id = current_user.id
    db.commit()
    db.refresh(listing)
    return listing


@router.post("/{listing_id}/report", response_model=schemas.ListingOut)
def report_discrimination(
    listing_id: int,
    report: schemas.DiscriminationReport,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Discrimination reporting, per slide 7: 'reports are escalated to labor departments;
    repeat offenders are delisted.' Auto-delists after 3 reports — tune this threshold as needed.
    """
    listing = db.query(models.Listing).filter(models.Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    listing.discrimination_reports += 1
    if listing.discrimination_reports >= 3:
        listing.status = models.VerificationStatus.delisted
        listing.verification_notes = "Auto-delisted after repeated discrimination reports."

    db.commit()
    db.refresh(listing)
    return listing
