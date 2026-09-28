"""
Pydantic schemas for Beyond Identity.
Defines data validation and serialization for Users, Listings, Incident Reports,
Scheme/NGO matching, AI Awareness, and AI Health Assistant decision trees.
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
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole
    is_active: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserOut] = None


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
    matched_schemes: List[SchemeMatchOut] = []
    matched_ngos: List[NGOMatchOut] = []
    created_at: datetime

    class Config:
        from_attributes = True


class IncidentStatusUpdate(BaseModel):
    status: IncidentStatus
    case_notes: Optional[str] = None
    assigned_ngo: Optional[str] = None


# ==========================================
# 4. AI Awareness Module Schemas
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
# 5. AI Health Assistant Decision-Tree Schemas
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
