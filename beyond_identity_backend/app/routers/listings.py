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
