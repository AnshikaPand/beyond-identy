"""
Core data models for Beyond Identity.

- User: app users, including NGO verifiers and admins (role-based).
- Listing: single table covering every category from the deck
  (education, employment, housing, healthcare, schemes, community/mentorship).
  Kept as one table with a `category` field for the pilot/mock-data phase —
  easy to split into per-category tables later if fields diverge a lot.
"""
import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Boolean, Text, DateTime, Enum, ForeignKey
)
from sqlalchemy.orm import relationship

from app.database import Base


class UserRole(str, enum.Enum):
    user = "user"           # regular app user
    verifier = "verifier"   # NGO partner / community moderator
    admin = "admin"         # project admin


class ListingCategory(str, enum.Enum):
    education = "education"
    employment = "employment"
    housing = "housing"
    healthcare = "healthcare"
    scheme = "scheme"          # government schemes
    scholarship = "scholarship"
    community = "community"    # mentorship / peer networks


class VerificationStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"
    delisted = "delisted"      # repeat offenders, per deck slide 7


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.user, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    listings_submitted = relationship(
        "Listing", back_populates="submitted_by", foreign_keys="Listing.submitted_by_id"
    )
    incident_reports = relationship(
        "IncidentReport", back_populates="reporter", foreign_keys="IncidentReport.user_id"
    )


class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(Enum(ListingCategory), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    organization_name = Column(String, nullable=True)   # NGO / employer / school name
    location = Column(String, nullable=True)
    contact_info = Column(String, nullable=True)

    status = Column(Enum(VerificationStatus), default=VerificationStatus.pending, nullable=False)
    verification_notes = Column(Text, nullable=True)     # why verified/rejected/delisted
    discrimination_reports = Column(Integer, default=0)  # per slide 7: escalation trigger

    submitted_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    submitted_by = relationship("User", foreign_keys=[submitted_by_id], back_populates="listings_submitted")
    verified_by = relationship("User", foreign_keys=[verified_by_id])


class IncidentType(str, enum.Enum):
    workplace = "workplace"
    housing_eviction = "housing_eviction"
    healthcare_denial = "healthcare_denial"
    education = "education"
    public_harassment = "public_harassment"
    police_harassment = "police_harassment"
    legal_documentation = "legal_documentation"
    other = "other"


class UrgencyLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    immediate_sos = "immediate_sos"


class IncidentStatus(str, enum.Enum):
    submitted = "submitted"
    under_review = "under_review"
    escalated_to_ngo = "escalated_to_ngo"
    legal_aid_assigned = "legal_aid_assigned"
    resolved = "resolved"
    closed = "closed"


class IncidentReport(Base):
    """
    Discrimination Incident Report:
    Allows individuals to confidentially or anonymously report discrimination incidents.
    Automatically matched to relevant Indian government schemes and verified NGOs.
    """
    __tablename__ = "incident_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Nullable for anonymous reports
    is_anonymous = Column(Boolean, default=False, nullable=False)
    incident_type = Column(Enum(IncidentType), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    incident_date = Column(String, nullable=True)
    location_city = Column(String, nullable=False)
    location_state = Column(String, nullable=False)
    perpetrator_details = Column(String, nullable=True)
    urgency_level = Column(Enum(UrgencyLevel), default=UrgencyLevel.medium, nullable=False)
    status = Column(Enum(IncidentStatus), default=IncidentStatus.submitted, nullable=False)
    case_notes = Column(Text, nullable=True)
    assigned_ngo = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)

    # Persisted JSON array string of matched resources
    matched_schemes_json = Column(Text, nullable=True)
    matched_ngos_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reporter = relationship("User", foreign_keys=[user_id], back_populates="incident_reports")

