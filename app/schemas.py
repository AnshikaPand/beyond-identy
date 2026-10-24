"""
Pydantic schemas for Beyond Identity.
Defines data validation and serialization for Users, Listings, Incident Reports,
Scheme/NGO matching, Awareness, and Health Assistant decision trees.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr

from app.models import (
    UserRole,
    ListingCategory,
    VerificationStatus,
    IncidentType,
    UrgencyLevel,
    IncidentStatus,
)


# ==========================================
# 1. User Schemas
# ==========================================

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Optional[UserRole] = UserRole.user


class UserLoginJSON(BaseModel):
    name: Optional[str] = None
    email: str  # Accepts username, email, or user ID
    password: str


class GoogleLoginRequest(BaseModel):
    credential: str  # JWT ID Token returned by Google Identity Services
    role: Optional[str] = "user"  # Target role: "user" / "community" or "verifier" / "ngo"


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole
    is_active: bool
    is_verified: bool = False
    auth_provider: Optional[str] = "local"
    google_id: Optional[str] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserOut] = None


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class EmailVerificationResponse(BaseModel):
    message: str
    email: str
    is_verified: bool = False


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class PasswordResetResponse(BaseModel):
    message: str
    reset_token: Optional[str] = None
    email: Optional[str] = None


# ==========================================
# 2. Listing Schemas
# ==========================================

class ListingCreate(BaseModel):
    category: ListingCategory
    title: str
    description: Optional[str] = None
    organization_name: Optional[str] = None
    location: Optional[str] = None
    contact_info: Optional[str] = None


class ListingOut(BaseModel):
    id: int
    category: ListingCategory
    title: str
    description: Optional[str] = None
    organization_name: Optional[str] = None
    location: Optional[str] = None
    contact_info: Optional[str] = None
    status: VerificationStatus
    verification_notes: Optional[str] = None
    discrimination_reports: int
    created_at: datetime

    class Config:
        from_attributes = True



class VerificationUpdate(BaseModel):
    status: VerificationStatus
    verification_notes: Optional[str] = None


class DiscriminationReport(BaseModel):
    notes: Optional[str] = None


# ==========================================
# 3. Matching & Incident Report Schemas
# ==========================================

class SchemeMatchOut(BaseModel):
    name: str
    ministry_or_dept: str
    description: str
    eligibility: str
    benefits: str
    application_link: Optional[str] = None
    helpline: Optional[str] = None


class NGOMatchOut(BaseModel):
    name: str
    focus_area: str
    location: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    services_offered: List[str]


class IncidentReportCreate(BaseModel):
    incident_type: IncidentType
    title: str
    description: str
    incident_date: Optional[str] = None
    location_city: str
    location_state: str
    perpetrator_details: Optional[str] = None
    urgency_level: UrgencyLevel = UrgencyLevel.medium
    is_anonymous: bool = False
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    reporter_consent_public: bool = False
    public_summary: Optional[str] = None
    entity_type: Optional[str] = None


class IncidentReportOut(BaseModel):
    id: int
    incident_type: IncidentType
    title: str
    description: str
    incident_date: Optional[str] = None
    location_city: str
    location_state: str
    perpetrator_details: Optional[str] = None
    urgency_level: UrgencyLevel
    status: IncidentStatus
    case_notes: Optional[str] = None
    assigned_ngo: Optional[str] = None
    is_anonymous: bool
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    public_visible: bool = True
    reporter_consent_public: bool = False
    public_summary: Optional[str] = None
    entity_type: Optional[str] = None
    matched_schemes: List[SchemeMatchOut] = []
    matched_ngos: List[NGOMatchOut] = []
    created_at: datetime

    class Config:
        from_attributes = True


class IncidentStatusUpdate(BaseModel):
    status: Optional[IncidentStatus] = None
    case_notes: Optional[str] = None
    assigned_ngo: Optional[str] = None
    public_visible: Optional[bool] = None
    public_summary: Optional[str] = None
    entity_type: Optional[str] = None


# ==========================================
# 3b. Public Community Case Board Schemas
# (Strict privacy whitelist - NO personal data, NO contact info, generic entity only)
# ==========================================

class PublicCaseItemOut(BaseModel):
    id: int
    incident_type: IncidentType
    category_label: str
    title: str
    description: str
    public_summary: Optional[str] = None
    incident_date: Optional[str] = None
    display_date: str
    location_city: str
    location_state: str
    reporter_type: str  # "Anonymous Report" or "Community Member"
    entity_type: str    # Generic sanitized type e.g. "Private company", "Government hospital", "Police station", "Landlord"
    urgency_level: UrgencyLevel
    status: IncidentStatus
    case_notes: Optional[str] = None
    assigned_ngo: Optional[str] = None
    matched_schemes: List[SchemeMatchOut] = []
    matched_ngos: List[NGOMatchOut] = []
    created_at: datetime

    class Config:
        from_attributes = True


class PublicCasesResponse(BaseModel):
    items: List[PublicCaseItemOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class PublicCasesStatsResponse(BaseModel):
    total_cases: int
    public_cases: int
    private_cases: int
    count_by_category: dict
    count_by_status: dict
    count_by_severity: dict
    count_by_state: dict
    cases_escalated_to_ngo: int
    cases_resolved: int
    cases_under_review: int
    high_severity_count: int



# ==========================================
# 4. Awareness Module Schemas
# ==========================================

class AwarenessTopicOut(BaseModel):
    id: str
    title: str
    act_or_ruling: str
    category: str
    summary: str
    key_rights: List[str]
    remedies: List[str]
    official_portal: Optional[str] = None


class AwarenessQueryRequest(BaseModel):
    query: str
    category: Optional[str] = None
    language: Optional[str] = "en"


class AwarenessQueryResponse(BaseModel):
    query: str
    matched_topic: str
    applicable_law: str
    sections_cited: List[str]
    explanation: str
    actionable_steps: List[str]
    legal_aid_contact: str
    official_portals: List[str]
    language: Optional[str] = "en"


class AwarenessChatMessage(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str


class AwarenessChatRequest(BaseModel):
    messages: List[AwarenessChatMessage]
    voice_mode: bool = False
    category: Optional[str] = None
    language: Optional[str] = "en"


class AwarenessChatResponse(BaseModel):
    reply: str
    speech_text: str
    matched_topic: Optional[str] = None
    applicable_law: Optional[str] = None
    actionable_steps: List[str] = []
    legal_aid_contact: Optional[str] = None
    official_portals: List[str] = []
    language: Optional[str] = "en"


class QAKnowledgeItem(BaseModel):
    id: int
    category: str
    question: str
    answer: str
    applicable_law: str
    keywords: List[str]


class QAListResponse(BaseModel):
    total: int
    page: int
    limit: int
    items: List[QAKnowledgeItem]


# ==========================================
# 5. Health Assistant Decision-Tree Schemas
# ==========================================

class DecisionNodeOption(BaseModel):
    option_id: str
    text: str
    next_node_id: str


class DecisionNode(BaseModel):
    node_id: str
    title: str
    category: str
    message: str
    clinical_notes: Optional[str] = None
    warnings: Optional[List[str]] = None
    recommended_actions: Optional[List[str]] = None
    helpline_contacts: Optional[List[str]] = None
    options: List[DecisionNodeOption] = []
    is_leaf: bool = False


class HealthTraverseRequest(BaseModel):
    current_node_id: str
    option_id: str


class HealthTraverseResponse(BaseModel):
    node: DecisionNode
    disclaimer: str


# ==========================================
# 6. Live Database Chatbot Schemas
# ==========================================

class ChatbotItemOut(BaseModel):
    id: int
    category: str
    title: str
    organization_name: Optional[str] = None
    location: Optional[str] = None
    contact_info: Optional[str] = None
    description: Optional[str] = None
    status: str = "verified"
    verification_notes: Optional[str] = None
    badge: Optional[str] = None


class ChatbotCaseOut(BaseModel):
    id: int
    title: str
    incident_type: str
    status: str
    urgency_level: str
    location_city: str
    location_state: str
    assigned_ngo: Optional[str] = None
    case_notes: Optional[str] = None
    created_at: str


class ChatbotQueryRequest(BaseModel):
    query: str
    history: Optional[List[dict]] = []
    category_filter: Optional[str] = None
    location_filter: Optional[str] = None


class ChatbotQueryResponse(BaseModel):
    reply: str
    intent: str
    suggestions: List[ChatbotItemOut] = []
    user_cases: List[ChatbotCaseOut] = []
    suggested_prompts: List[str] = []
    total_database_records: int = 0


# ==========================================
# 7. Video Interview & Community Stories
# ==========================================

class VideoInterviewCreate(BaseModel):
    title: str
    interviewee_name: str
    identity_tag: Optional[str] = "LGBTQ+ Community"
    category: Optional[str] = "Personal Story"
    video_url: str
    description: Optional[str] = None
    key_quote: Optional[str] = None
    duration: Optional[str] = None
    location: Optional[str] = None


class VideoInterviewOut(BaseModel):
    id: int
    title: str
    interviewee_name: str
    identity_tag: Optional[str] = None
    category: str
    video_url: str
    embed_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    description: Optional[str] = None
    key_quote: Optional[str] = None
    duration: Optional[str] = None
    location: Optional[str] = None
    is_verified: bool = True
    created_at: datetime

    class Config:
        from_attributes = True

