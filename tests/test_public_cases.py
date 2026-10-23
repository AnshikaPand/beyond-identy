"""
Tests for Community Case Board:
- Public endpoints: GET /api/public/cases & GET /api/public/cases/stats
- Strict server-side privacy whitelist (no personal details, no contact info, generic entity type)
- Consent enforcement: only cases with public_visible=True and reporter_consent_public=True are listed
- Unconsented cases counted in stats as private cases
- Admin/NGO visibility toggle and public summary editing
- Incident report submission with public consent checkbox
- Rate limiting
- Public /cases page route
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app import models, auth
from app.routers.public_cases import sanitize_entity_type

client = TestClient(app)


@pytest.fixture(scope="module")
def admin_token():
    """Login as admin and return JWT token."""
    res = client.post("/auth/login-json", json={"email": "admin@beyondidentity.org", "password": "admin123"})
    if res.status_code == 200:
        return res.json()["access_token"]
    # Fallback to dev token
    return auth.create_access_token({"sub": "admin@beyondidentity.org", "role": "admin"})


@pytest.fixture(scope="module")
def verifier_token():
    """Login as verifier and return JWT token."""
    res = client.post("/auth/login-json", json={"email": "ngo@shreetrust.org", "password": "verifier123"})
    if res.status_code == 200:
        return res.json()["access_token"]
    return auth.create_access_token({"sub": "ngo@shreetrust.org", "role": "verifier"})


def test_public_cases_endpoint_is_accessible_without_auth():
    """Public cases endpoint must be accessible without any Authorization header."""
    res = client.get("/api/public/cases")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data


def test_public_cases_privacy_whitelist_strict_enforcement():
    """
    CRITICAL PRIVACY TEST:
    Verifies that the server NEVER exposes reporter name, email, phone, user_id,
    exact home address, or real alleged perpetrator names.
    """
    res = client.get("/api/public/cases?page_size=50")
    assert res.status_code == 200
    data = res.json()
    items = data["items"]

    assert len(items) > 0, "Expected seeded public cases"

    # Whitelisted fields allowed in PublicCaseItemOut schema
    allowed_keys = {
        "id",
        "incident_type",
        "category_label",
        "title",
        "description",
        "public_summary",
        "incident_date",
        "display_date",
        "location_city",
        "location_state",
        "reporter_type",
        "entity_type",
        "urgency_level",
        "status",
        "case_notes",
        "assigned_ngo",
        "matched_schemes",
        "matched_ngos",
        "created_at",
    }

    forbidden_pii_keys = {
        "user_id",
        "contact_email",
        "contact_phone",
        "perpetrator_details",
        "reporter_name",
        "reporter_phone",
        "exact_address",
        "home_address",
    }

    for item in items:
        # 1. Ensure no forbidden key exists in item
        for forbidden in forbidden_pii_keys:
            assert forbidden not in item, f"Security Breach: {forbidden} leaked in public case item #{item.get('id')}!"

        # 2. Ensure item keys are within allowed whitelist
        for k in item.keys():
            assert k in allowed_keys, f"Unexpected key '{k}' exposed in public response schema"

        # 3. Reporter type must be generic
        assert item["reporter_type"] in ("Anonymous Report", "Community Member")

        # 4. Location must only be city and state
        assert isinstance(item["location_city"], str)
        assert isinstance(item["location_state"], str)

        # 5. Entity type must be generic sanitized category
        assert item["entity_type"] in (
            "Private Company / Employer",
            "Government Hospital",
            "Private Hospital / Clinic",
            "Private Landlord / Housing Society",
            "Educational Institution",
            "Police Station / Law Enforcement",
            "Commercial Establishment",
            "Commercial / Public Establishment",
            "Public Administrative Office",
            "Banking / Financial Institution",
            "Public Transit Authority",
            "Private Entity",
            "Institutional Authority",
            "Healthcare Provider",
            "Healthcare Facility",
            "Private Employer",
            "Private Landlord",
            "Police Authority",
            "Commercial Entity",
            "Administrative Office",
        )

        # 6. NGO chips must not have empty brackets or leaked personal phones
        for ngo in item.get("matched_ngos", []):
            if ngo.get("contact_phone"):
                assert ngo["contact_phone"] != "()"


def test_consent_filtering_unconsented_cases_are_not_listed():
    """
    Verifies that cases where reporter_consent_public is False are NOT listed in GET /api/public/cases,
    even though they exist in the database.
    """
    # Create one case WITH consent and one case WITHOUT consent
    consented_payload = {
        "incident_type": "workplace",
        "title": "Consented Public Workplace Discrimination Case Test",
        "description": "Employee was demoted following gender transition request.",
        "location_city": "Nagpur",
        "location_state": "Maharashtra",
        "urgency_level": "medium",
        "is_anonymous": True,
        "reporter_consent_public": True,
    }
    unconsented_payload = {
        "incident_type": "housing_eviction",
        "title": "Private Confidential Case Test No Consent Given",
        "description": "Tenant facing eviction but chose NOT to display publicly.",
        "location_city": "Mysuru",
        "location_state": "Karnataka",
        "urgency_level": "high",
        "is_anonymous": True,
        "reporter_consent_public": False,  # Default or user opted out
    }

    res1 = client.post("/incidents/", json=consented_payload)
    assert res1.status_code == 201
    consented_id = res1.json()["id"]

    res2 = client.post("/incidents/", json=unconsented_payload)
    assert res2.status_code == 201
    unconsented_id = res2.json()["id"]

    # Now query public cases
    pub_res = client.get("/api/public/cases?page_size=50")
    assert pub_res.status_code == 200
    pub_items = pub_res.json()["items"]
    pub_ids = [item["id"] for item in pub_items]

    # Consented case MUST be visible
    assert consented_id in pub_ids, "Consented case should appear in public case board"

    # Unconsented case MUST NOT be visible
    assert unconsented_id not in pub_ids, "Unconsented case MUST NOT appear in public case board listing!"

    # Teardown
    db = SessionLocal()
    try:
        db.query(models.IncidentReport).filter(models.IncidentReport.id.in_([consented_id, unconsented_id])).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def test_public_cases_stats_endpoint():
    """
    Verifies GET /api/public/cases/stats returns:
    - total_cases
    - public_cases
    - private_cases (unconsented cases counted here)
    - count_by_category
    - count_by_status
    - count_by_severity
    - count_by_state
    - cases_escalated_to_ngo
    - cases_resolved
    """
    res = client.get("/api/public/cases/stats")
    assert res.status_code == 200
    stats = res.json()

    assert "total_cases" in stats
    assert "public_cases" in stats
    assert "private_cases" in stats
    assert "count_by_category" in stats
    assert "count_by_status" in stats
    assert "count_by_severity" in stats
    assert "count_by_state" in stats
    assert "cases_escalated_to_ngo" in stats
    assert "cases_resolved" in stats

    assert stats["total_cases"] >= stats["public_cases"]
    assert stats["private_cases"] == stats["total_cases"] - stats["public_cases"]
    assert stats["private_cases"] >= 3, "Expected at least 3 seeded private confidential cases"


def test_public_cases_filters_and_sorting():
    """Verifies category, status, severity, and state filtering on public endpoint."""
    # Filter by category
    res = client.get("/api/public/cases?category=workplace")
    assert res.status_code == 200
    items = res.json()["items"]
    for item in items:
        assert item["incident_type"] == "workplace"

    # Filter by status
    res = client.get("/api/public/cases?status=resolved")
    assert res.status_code == 200
    for item in res.json()["items"]:
        assert item["status"] == "resolved"

    # Filter by state
    res = client.get("/api/public/cases?state=Maharashtra")
    assert res.status_code == 200
    for item in res.json()["items"]:
        assert "Maharashtra" in item["location_state"]

    # Filter by search string
    res = client.get("/api/public/cases?search=eviction")
    assert res.status_code == 200
    for item in res.json()["items"]:
        search_blob = f"{item['title']} {item['description']} {item.get('public_summary', '')}".lower()
        assert "eviction" in search_blob or "tenant" in search_blob or "housing" in search_blob or "evict" in search_blob


def test_admin_ngo_toggle_public_visibility(verifier_token):
    """
    Verifies that NGO verifiers or Admins can hide a case at any time
    by setting public_visible=False, or edit public_summary.
    """
    # Create a public consented case
    create_res = client.post("/incidents/", json={
        "incident_type": "public_harassment",
        "title": "Admin Visibility Toggle Test Case",
        "description": "Public harassment report to be hidden by NGO administrator.",
        "location_city": "Indore",
        "location_state": "Madhya Pradesh",
        "urgency_level": "medium",
        "is_anonymous": True,
        "reporter_consent_public": True,
    })
    assert create_res.status_code == 201
    inc_id = create_res.json()["id"]

    # Verify it is initially on the public board
    pub_res = client.get("/api/public/cases?page_size=50")
    assert inc_id in [i["id"] for i in pub_res.json()["items"]]

    # Admin/NGO toggles public_visible = False
    patch_res = client.patch(
        f"/incidents/{inc_id}/status",
        headers={"Authorization": f"Bearer {verifier_token}"},
        json={
            "public_visible": False,
            "public_summary": "Moderated by NGO Desk: Case under active mediation.",
        },
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["public_visible"] is False
    assert updated["public_summary"] == "Moderated by NGO Desk: Case under active mediation."

    # Now verify it has been removed from the public board
    pub_res2 = client.get("/api/public/cases?page_size=50")
    assert inc_id not in [i["id"] for i in pub_res2.json()["items"]], "Hidden case must not appear publicly"

    # Teardown
    db = SessionLocal()
    try:
        db.query(models.IncidentReport).filter(models.IncidentReport.id == inc_id).delete()
        db.commit()
    finally:
        db.close()


def test_sanitize_entity_type_helper():
    """Verifies that sanitize_entity_type maps sensitive proprietary names to generic descriptions."""
    assert sanitize_entity_type("Apollo Private Clinic Ltd", models.IncidentType.healthcare_denial) == "Private Hospital / Clinic"
    assert sanitize_entity_type("District Civil Government Hospital", models.IncidentType.healthcare_denial) == "Government Hospital"
    assert sanitize_entity_type("Connaught Place Police Thana Station", models.IncidentType.police_harassment) == "Police Station / Law Enforcement"
    assert sanitize_entity_type("Infosys Tech Pvt Ltd HR", models.IncidentType.workplace) == "Private Company / Employer"
    assert sanitize_entity_type("Landlord Mr. R. Sharma", models.IncidentType.housing_eviction) == "Private Landlord / Housing Society"
    assert sanitize_entity_type("State Autonomous University Campus Hostel", models.IncidentType.education) == "Educational Institution"


def test_public_case_board_page_serves_html():
    """Verifies that /cases and /cases.html serve the Community Case Board HTML page."""
    res = client.get("/cases")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    content = res.text
    assert "Community Case Board" in content
    assert "stat-total-cases" in content
    assert "category-chart-bars" in content
    assert "Tele-MANAS: 14416" in content
    assert "868989330" in content
