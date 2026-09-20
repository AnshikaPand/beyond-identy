"""
Discrimination Incident Reporting Router:
Allows users to report discrimination incidents (workplace, healthcare, housing, police harassment),
automatically connects them with matching Indian government schemes and verified NGOs,
and enables verifiers/admins to manage incident resolution workflows.
"""
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth
from app.services import matcher

router = APIRouter(prefix="/incidents", tags=["incidents"])


def _to_incident_out(incident: models.IncidentReport) -> schemas.IncidentReportOut:
    """Helper to convert IncidentReport DB model to IncidentReportOut schema with deserialized matches."""
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

    # If matches were not stored or empty, compute on the fly
    if not matched_schemes:
        matched_schemes = matcher.match_schemes(
            incident.incident_type, incident.location_state, incident.urgency_level
        )
    if not matched_ngos:
        matched_ngos = matcher.match_ngos(
            incident.incident_type, incident.location_state, incident.urgency_level
        )

    return schemas.IncidentReportOut(
        id=incident.id,
        incident_type=incident.incident_type,
        title=incident.title,
        description=incident.description,
        incident_date=incident.incident_date,
        location_city=incident.location_city,
        location_state=incident.location_state,
        perpetrator_details=incident.perpetrator_details,
        urgency_level=incident.urgency_level,
        status=incident.status,
        case_notes=incident.case_notes,
        assigned_ngo=incident.assigned_ngo,
        is_anonymous=incident.is_anonymous,
        contact_email=incident.contact_email,
        contact_phone=incident.contact_phone,
        matched_schemes=matched_schemes,
        matched_ngos=matched_ngos,
        created_at=incident.created_at,
    )


@router.post("/", response_model=schemas.IncidentReportOut, status_code=201)
def report_incident(
    report_in: schemas.IncidentReportCreate,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_optional_current_user),
):
    """
    Submit a discrimination incident report.
    Can be called anonymously or by an authenticated user.
    Immediately matches the incident with relevant Indian Government schemes and verified NGOs.
    """
    user_id = None
    is_anon = report_in.is_anonymous

    if current_user and not report_in.is_anonymous:
        user_id = current_user.id
    else:
        is_anon = True

    # Compute matches
    matched_schemes = matcher.match_schemes(
        report_in.incident_type, report_in.location_state, report_in.urgency_level
    )
    matched_ngos = matcher.match_ngos(
        report_in.incident_type, report_in.location_state, report_in.urgency_level
    )

    schemes_json = json.dumps([s.model_dump() if hasattr(s, "model_dump") else s.dict() for s in matched_schemes])
    ngos_json = json.dumps([n.model_dump() if hasattr(n, "model_dump") else n.dict() for n in matched_ngos])


    incident = models.IncidentReport(
        user_id=user_id,
        is_anonymous=is_anon,
        incident_type=report_in.incident_type,
        title=report_in.title,
        description=report_in.description,
        incident_date=report_in.incident_date,
        location_city=report_in.location_city,
        location_state=report_in.location_state,
        perpetrator_details=report_in.perpetrator_details,
        urgency_level=report_in.urgency_level,
        status=models.IncidentStatus.submitted,
        contact_email=report_in.contact_email or (current_user.email if current_user and not is_anon else None),
        contact_phone=report_in.contact_phone,
        matched_schemes_json=schemes_json,
        matched_ngos_json=ngos_json,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    return _to_incident_out(incident)


@router.get("/", response_model=List[schemas.IncidentReportOut])
def list_incidents(
    status: Optional[models.IncidentStatus] = None,
    incident_type: Optional[models.IncidentType] = None,
    urgency_level: Optional[models.UrgencyLevel] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    List incident reports.
    - Regular users see only their own filed incidents.
    - Verifiers and Admins see all incidents, with filtering capabilities.
    """
    query = db.query(models.IncidentReport)

    if current_user.role == models.UserRole.user:
        query = query.filter(models.IncidentReport.user_id == current_user.id)
    else:
        # Verifiers & Admins can filter by status, type, urgency
        if status:
            query = query.filter(models.IncidentReport.status == status)
        if incident_type:
            query = query.filter(models.IncidentReport.incident_type == incident_type)
        if urgency_level:
            query = query.filter(models.IncidentReport.urgency_level == urgency_level)

    incidents = query.order_by(models.IncidentReport.created_at.desc()).all()
    return [_to_incident_out(i) for i in incidents]


@router.get("/{incident_id}", response_model=schemas.IncidentReportOut)
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Get single incident details. Regular users can only access their own reports."""
    incident = db.query(models.IncidentReport).filter(models.IncidentReport.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident report not found")

    if current_user.role == models.UserRole.user and incident.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to view this incident")

    return _to_incident_out(incident)


@router.patch("/{incident_id}/status", response_model=schemas.IncidentReportOut)
def update_incident_status(
    incident_id: int,
    update_in: schemas.IncidentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        auth.require_role(models.UserRole.verifier, models.UserRole.admin)
    ),
):
    """
    Update incident status, case notes, and assigned NGO partner.
    Restricted to NGO verifiers and admins.
    """
    incident = db.query(models.IncidentReport).filter(models.IncidentReport.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident report not found")

    incident.status = update_in.status
    if update_in.case_notes is not None:
        incident.case_notes = update_in.case_notes
    if update_in.assigned_ngo is not None:
        incident.assigned_ngo = update_in.assigned_ngo

    db.commit()
    db.refresh(incident)
    return _to_incident_out(incident)
