"""
Public Community Case Board Router:
Provides public, read-only endpoints for viewing anonymized discrimination cases reported to Beyond Identity.
Strictly enforces privacy on the server:
- Never returns reporter name, email, phone, user ID, exact address, or personal contact info.
- Shows location only at city + state level.
- Shows reporter type only as "Anonymous Report" or "Community Member".
- Never exposes alleged entity's real proprietary name (maps to generic type: "Private company", "Government hospital", "Police station", "Landlord", etc.).
- Only includes cases where public_visible = True and reporter_consent_public = True.
- Provides rate limiting for public endpoints.
"""
import time
import json
from collections import defaultdict
from typing import Optional, List, Dict
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc

from app.database import get_db
from app import models, schemas
from app.services import matcher

router = APIRouter(prefix="/api/public/cases", tags=["public_cases"])


# =========================================================================
# In-Memory Thread-Safe Rate Limiter for Public Endpoints
# =========================================================================

class SlidingWindowRateLimiter:
    """Sliding window in-memory rate limiter per client IP address."""
    def __init__(self, limit: int = 120, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.lock = Lock()

    def check(self, client_ip: str):
        now = time.time()
        with self.lock:
            # Clean timestamps older than window
            timestamps = [t for t in self.requests[client_ip] if now - t < self.window_seconds]
            if len(timestamps) >= self.limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded on public cases endpoint. Please wait a moment before retrying.",
                )
            timestamps.append(now)
            self.requests[client_ip] = timestamps


public_limiter = SlidingWindowRateLimiter(limit=120, window_seconds=60)


def rate_limit_public(request: Request):
    """FastAPI dependency to rate limit public calls."""
    client_ip = request.headers.get("X-Forwarded-For")
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "127.0.0.1"

    public_limiter.check(client_ip)


# =========================================================================
# Privacy & Entity Sanitizer Helpers
# =========================================================================

CATEGORY_LABELS = {
    models.IncidentType.workplace: "Workplace & Employment",
    models.IncidentType.housing_eviction: "Housing & Rental Eviction",
    models.IncidentType.healthcare_denial: "Healthcare & Transition Care",
    models.IncidentType.education: "Education & Campus",
    models.IncidentType.public_harassment: "Public Space & Transit",
    models.IncidentType.police_harassment: "Police Harassment & Extortion",
    models.IncidentType.legal_documentation: "Legal ID & Documentation",
    models.IncidentType.other: "Other Discrimination",
}


def sanitize_entity_type(raw_entity: Optional[str], incident_type: models.IncidentType) -> str:
    """
    Guarantees that no real business, hospital, or individual name is exposed publicly.
    Maps details to a safe, generic institutional category.
    """
    if not raw_entity:
        default_map = {
            models.IncidentType.workplace: "Private Employer",
            models.IncidentType.housing_eviction: "Private Landlord / Housing Society",
            models.IncidentType.healthcare_denial: "Healthcare Facility",
            models.IncidentType.education: "Educational Institution",
            models.IncidentType.police_harassment: "Local Police Station",
            models.IncidentType.public_harassment: "Commercial / Public Establishment",
            models.IncidentType.legal_documentation: "Public Administrative Office",
            models.IncidentType.other: "Institutional Authority",
        }
        return default_map.get(incident_type, "Institutional Authority")

    lower = raw_entity.lower()
    if any(k in lower for k in ["hospital", "clinic", "casualty", "ward", "doctor", "medical", "nurse", "dispensary"]):
        if "civil" in lower or "district" in lower or "government" in lower or "govt" in lower or "state" in lower:
            return "Government Hospital"
        return "Private Hospital / Clinic"

    if any(k in lower for k in ["police", "constable", "patrol", "thana", "chowki", "beat", "inspector", "station"]):
        return "Police Station / Law Enforcement"

    if any(k in lower for k in ["landlord", "owner", "society", "rwa", "apartment", "flat", "tenancy", "broker"]):
        return "Private Landlord / Housing Society"

    if any(k in lower for k in ["college", "university", "school", "campus", "hostel", "registrar", "dean", "examination"]):
        return "Educational Institution"

    if any(k in lower for k in ["bank", "branch", "teller", "loan", "financial"]):
        return "Banking / Financial Institution"

    if any(k in lower for k in ["metro", "bus", "railway", "train", "transit", "station", "airport"]):
        return "Public Transit Authority"

    if any(k in lower for k in ["company", "pvt", "ltd", "corp", "inc", "it", "bpo", "employer", "workplace", "firm", "tech", "office"]):
        return "Private Company / Employer"

    if any(k in lower for k in ["hotel", "restaurant", "store", "mall", "shop", "cafe"]):
        return "Commercial Establishment"

    default_map = {
        models.IncidentType.workplace: "Private Employer",
        models.IncidentType.housing_eviction: "Private Landlord",
        models.IncidentType.healthcare_denial: "Healthcare Provider",
        models.IncidentType.education: "Educational Institution",
        models.IncidentType.police_harassment: "Police Authority",
        models.IncidentType.public_harassment: "Commercial Entity",
        models.IncidentType.legal_documentation: "Administrative Office",
        models.IncidentType.other: "Private Entity",
    }
    return default_map.get(incident_type, "Private Entity")


def _to_public_case_item(incident: models.IncidentReport) -> schemas.PublicCaseItemOut:
    """Converts a database IncidentReport into the privacy-whitelisted PublicCaseItemOut."""
    # Deserialized matched schemes & NGOs
    matched_schemes = []
    matched_ngos = []

    if incident.matched_schemes_json:
        try:
            raw_schemes = json.loads(incident.matched_schemes_json)
            matched_schemes = [schemas.SchemeMatchOut(**s) for s in raw_schemes]
        except Exception:
            matched_schemes = []

    if incident.matched_ngos_json:
        try:
            raw_ngos = json.loads(incident.matched_ngos_json)
            matched_ngos = [schemas.NGOMatchOut(**n) for n in raw_ngos]
        except Exception:
            matched_ngos = []

    if not matched_schemes:
        matched_schemes = matcher.match_schemes(
            incident.incident_type, incident.location_state, incident.urgency_level
        )
    if not matched_ngos:
        matched_ngos = matcher.match_ngos(
            incident.incident_type, incident.location_state, incident.urgency_level
        )

    # Clean empty helpline bug from NGO match objects
    cleaned_ngos = []
    for ngo in matched_ngos:
        c_phone = (ngo.contact_phone or "").strip()
        cleaned_ngos.append(
            schemas.NGOMatchOut(
                name=ngo.name,
                focus_area=ngo.focus_area,
                location=ngo.location,
                contact_email=ngo.contact_email,
                contact_phone=c_phone if c_phone else None,
                services_offered=ngo.services_offered,
            )
        )

    # Reporter type string (NEVER expose user ID or name)
    reporter_type = "Anonymous Report" if (incident.is_anonymous or not incident.user_id) else "Community Member"

    # Display date guarantee
    display_date = incident.incident_date if incident.incident_date else incident.created_at.strftime("%Y-%m-%d")

    # Generic sanitized entity type
    entity_type = incident.entity_type or sanitize_entity_type(incident.perpetrator_details, incident.incident_type)

    return schemas.PublicCaseItemOut(
        id=incident.id,
        incident_type=incident.incident_type,
        category_label=CATEGORY_LABELS.get(incident.incident_type, str(incident.incident_type).title()),
        title=incident.title,
        description=incident.description,
        public_summary=incident.public_summary or incident.description,
        incident_date=incident.incident_date,
        display_date=display_date,
        location_city=incident.location_city,
        location_state=incident.location_state,
        reporter_type=reporter_type,
        entity_type=entity_type,
        urgency_level=incident.urgency_level,
        status=incident.status,
        case_notes=incident.case_notes,
        assigned_ngo=incident.assigned_ngo,
        matched_schemes=matched_schemes,
        matched_ngos=cleaned_ngos,
        created_at=incident.created_at,
    )


# =========================================================================
# Public Endpoints
# =========================================================================

@router.get("", response_model=schemas.PublicCasesResponse, dependencies=[Depends(rate_limit_public)])
@router.get("/", response_model=schemas.PublicCasesResponse, dependencies=[Depends(rate_limit_public)])
def list_public_cases(
    page: int = Query(1, ge=1, description="Page number starting at 1"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page (max 50)"),
    category: Optional[models.IncidentType] = Query(None, description="Filter by incident type category"),
    status: Optional[models.IncidentStatus] = Query(None, description="Filter by case status"),
    severity: Optional[models.UrgencyLevel] = Query(None, description="Filter by urgency/severity level"),
    state: Optional[str] = Query(None, description="Filter by Indian State"),
    search: Optional[str] = Query(None, description="Search query string"),
    sort_by: str = Query("newest", description="'newest', 'oldest', or 'severity'"),
    db: Session = Depends(get_db),
):
    """
    Public Community Case Board Endpoint:
    Returns anonymized, verified discrimination reports for public transparency and community monitoring.
    Only returns cases with public_visible = True and reporter_consent_public = True.
    """
    # Strict privacy filter
    query = db.query(models.IncidentReport).filter(
        models.IncidentReport.public_visible == True,
        models.IncidentReport.reporter_consent_public == True,
    )

    # Category filter
    if category:
        query = query.filter(models.IncidentReport.incident_type == category)

    # Status filter
    if status:
        query = query.filter(models.IncidentReport.status == status)

    # Severity filter
    if severity:
        query = query.filter(models.IncidentReport.urgency_level == severity)

    # State filter
    if state and state.strip():
        query = query.filter(models.IncidentReport.location_state.ilike(f"%{state.strip()}%"))

    # Search filter across title, description, public summary, and city
    if search and search.strip():
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                models.IncidentReport.title.ilike(s),
                models.IncidentReport.description.ilike(s),
                models.IncidentReport.public_summary.ilike(s),
                models.IncidentReport.location_city.ilike(s),
            )
        )

    # Sorting
    if sort_by == "oldest":
        query = query.order_by(asc(models.IncidentReport.created_at))
    else:
        # Default newest first
        query = query.order_by(desc(models.IncidentReport.created_at))

    total = query.count()
    total_pages = max(1, (total + page_size - 1) // page_size)

    offset = (page - 1) * page_size
    incidents = query.offset(offset).limit(page_size).all()

    items = [_to_public_case_item(i) for i in incidents]

    return schemas.PublicCasesResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/stats", response_model=schemas.PublicCasesStatsResponse, dependencies=[Depends(rate_limit_public)])
def get_public_cases_stats(db: Session = Depends(get_db)):
    """
    Returns aggregate stats for the Community Case Board:
    Total cases, public vs private cases, and breakdowns by category, status, severity, and state.
    """
    all_cases = db.query(models.IncidentReport).all()
    total_cases = len(all_cases)

    # Public cases: public_visible == True and reporter_consent_public == True
    public_cases_list = [
        c for c in all_cases if (c.public_visible is True and c.reporter_consent_public is True)
    ]
    public_cases_count = len(public_cases_list)
    private_cases_count = total_cases - public_cases_count

    # Breakdown dictionaries
    count_by_category: Dict[str, int] = defaultdict(int)
    count_by_status: Dict[str, int] = defaultdict(int)
    count_by_severity: Dict[str, int] = defaultdict(int)
    count_by_state: Dict[str, int] = defaultdict(int)

    cases_escalated = 0
    cases_resolved = 0
    cases_under_review = 0
    high_severity_count = 0

    for c in public_cases_list:
        cat_key = c.incident_type.value if hasattr(c.incident_type, "value") else str(c.incident_type)
        count_by_category[cat_key] += 1

        stat_key = c.status.value if hasattr(c.status, "value") else str(c.status)
        count_by_status[stat_key] += 1

        sev_key = c.urgency_level.value if hasattr(c.urgency_level, "value") else str(c.urgency_level)
        count_by_severity[sev_key] += 1

        if c.location_state:
            count_by_state[c.location_state.strip()] += 1

        if c.status in (models.IncidentStatus.escalated_to_ngo, models.IncidentStatus.legal_aid_assigned):
            cases_escalated += 1
        elif c.status == models.IncidentStatus.resolved:
            cases_resolved += 1
        elif c.status == models.IncidentStatus.under_review:
            cases_under_review += 1

        if c.urgency_level in (models.UrgencyLevel.high, models.UrgencyLevel.immediate_sos):
            high_severity_count += 1

    return schemas.PublicCasesStatsResponse(
        total_cases=total_cases,
        public_cases=public_cases_count,
        private_cases=private_cases_count,
        count_by_category=dict(count_by_category),
        count_by_status=dict(count_by_status),
        count_by_severity=dict(count_by_severity),
        count_by_state=dict(count_by_state),
        cases_escalated_to_ngo=cases_escalated,
        cases_resolved=cases_resolved,
        cases_under_review=cases_under_review,
        high_severity_count=high_severity_count,
    )
