"""
Comprehensive automated test suite for Beyond Identity backend.
Covers:
- Root & Metadata endpoints
- Authentication & RBAC (register, login, me, invalid credentials)
- Listings CRUD & Verification workflows
- Discrimination Incident Reporting & Scheme/NGO Matcher
- AI Legal Rights Awareness Module
- AI Health Assistant Decision Tree state machine
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ==========================================
# 1. Root & System Metadata Tests
# ==========================================

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Beyond Identity API is running" in data["message"]
    assert "sdg_alignment" in data
    assert any("SDG 10" in s for s in data["sdg_alignment"])
    assert any("SDG 3" in s for s in data["sdg_alignment"])


# ==========================================
# 2. Authentication & RBAC Tests
# ==========================================

def test_user_registration_and_login():
    # Register a new user
    user_payload = {
        "name": "Aarav Sharma",
        "email": "aarav.sharma@example.org",
        "password": "SecurePassword123!",
    }
    reg_res = client.post("/auth/register", json=user_payload)
    # May be 201 or 400 if already exists
    if reg_res.status_code == 201:
        reg_data = reg_res.json()
        assert reg_data["email"] == user_payload["email"]
        assert reg_data["role"] == "user"
        assert "hashed_password" not in reg_data

    # Duplicate registration should fail
    dup_res = client.post("/auth/register", json=user_payload)
    assert dup_res.status_code == 400
    assert "Email already registered" in dup_res.json()["detail"]

    # Login
    login_res = client.post(
        "/auth/login",
        data={"username": user_payload["email"], "password": user_payload["password"]},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert "user" in token_data and token_data["user"]["email"] == user_payload["email"]
    token = token_data["access_token"]

    # Access /auth/me with token
    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == user_payload["email"]


def test_registration_with_verifier_role():
    verifier_payload = {
        "name": "Humsafar Trust Partner",
        "email": "partner@humsafar.org",
        "password": "PartnerPassword123!",
        "role": "verifier"
    }
    res = client.post("/auth/register", json=verifier_payload)
    if res.status_code == 201:
        data = res.json()
        assert data["role"] == "verifier"
        assert data["email"] == verifier_payload["email"]


def test_registration_rejects_admin_role():
    admin_payload = {
        "name": "Unauthorized Admin",
        "email": "fakeadmin@example.org",
        "password": "FakePassword123!",
        "role": "admin"
    }
    res = client.post("/auth/register", json=admin_payload)
    assert res.status_code == 403
    assert "Admin role cannot be self-assigned" in res.json()["detail"]


def test_registration_password_length():
    short_pwd_payload = {
        "name": "Short Password User",
        "email": "shortpwd@example.org",
        "password": "123"
    }
    res = client.post("/auth/register", json=short_pwd_payload)
    assert res.status_code == 400
    assert "at least 6 characters" in res.json()["detail"]


def test_login_json_success():
    # Login via JSON endpoint
    json_payload = {
        "email": "admin@beyondidentity.org",
        "password": "admin123"
    }
    res = client.post("/auth/login-json", json=json_payload)
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "admin@beyondidentity.org"
    assert data["user"]["role"] == "admin"


def test_login_invalid_password():
    res = client.post(
        "/auth/login",
        data={"username": "admin@beyondidentity.org", "password": "WrongPassword"},
    )
    assert res.status_code == 401
    assert "Incorrect email or password" in res.json()["detail"]


# Helper function to get token for demo users
def get_auth_token(email: str, password: str) -> str:
    res = client.post("/auth/login", data={"username": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


# ==========================================
# 3. Listings & Verification Tests
# ==========================================

def test_listings_public_browsing():
    res = client.get("/listings/")
    assert res.status_code == 200
    listings = res.json()
    assert isinstance(listings, list)
    assert len(listings) > 0
    # Public browsing defaults to verified listings
    for l in listings:
        assert l["status"] == "verified"


def test_create_and_verify_listing():
    user_token = get_auth_token("user@example.com", "user123")
    verifier_token = get_auth_token("ngo@shreetrust.org", "verifier123")

    # Regular user creates a listing (starts as pending)
    payload = {
        "category": "employment",
        "title": "Inclusive Web Developer Role",
        "description": "Full-stack developer role with LGBTQ+ affirmative workplace culture.",
        "organization_name": "InclusiTech Labs",
        "location": "Bengaluru, Karnataka",
        "contact_info": "careers@inclusitech.io",
    }
    create_res = client.post(
        "/listings/",
        json=payload,
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert create_res.status_code == 201
    listing = create_res.json()
    assert listing["status"] == "pending"
    listing_id = listing["id"]

    # Verifier approves the listing
    verify_payload = {
        "status": "verified",
        "verification_notes": "Employer affirmative policy and POSH compliance verified.",
    }
    verify_res = client.patch(
        f"/listings/{listing_id}/verify",
        json=verify_payload,
        headers={"Authorization": f"Bearer {verifier_token}"},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "verified"
    assert verify_res.json()["verification_notes"] == verify_payload["verification_notes"]


# ==========================================
# 4. Discrimination Incident Reporting & Matcher Tests
# ==========================================

def test_report_discrimination_incident_authenticated():
    user_token = get_auth_token("user@example.com", "user123")

    incident_payload = {
        "incident_type": "workplace",
        "title": "Unlawful denial of promotion following transition disclosure",
        "description": "Passed over for promotion despite top performance ratings after updating gender identity.",
        "incident_date": "2026-09-01",
        "location_city": "Mumbai",
        "location_state": "Maharashtra",
        "perpetrator_details": "Tech Global Corporate HR",
        "urgency_level": "medium",
        "is_anonymous": False,
        "contact_phone": "+91-9876500001",
    }
    res = client.post(
        "/incidents/",
        json=incident_payload,
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == incident_payload["title"]
    assert data["incident_type"] == "workplace"
    assert data["status"] == "submitted"
    assert not data["is_anonymous"]

    # Check intelligent matching
    assert len(data["matched_schemes"]) > 0
    scheme_names = [s["name"] for s in data["matched_schemes"]]
    assert any("SMILE" in name or "NALSA" in name or "Maharashtra" in name for name in scheme_names)

    assert len(data["matched_ngos"]) > 0
    ngo_names = [n["name"] for n in data["matched_ngos"]]
    assert any("Humsafar" in name or "Tweet" in name or "Nazariya" in name for name in ngo_names)


def test_report_discrimination_incident_anonymous():
    # Anonymous reports require no Auth header
    incident_payload = {
        "incident_type": "police_harassment",
        "title": "Harassment and extortion at railway station",
        "description": "Police officers questioned and demanded illegal penalties without official challan.",
        "incident_date": "2026-09-12",
        "location_city": "New Delhi",
        "location_state": "Delhi",
        "perpetrator_details": "Railway Police Post",
        "urgency_level": "high",
        "is_anonymous": True,
        "contact_email": "anonymous.whistle@proton.me",
    }
    res = client.post("/incidents/", json=incident_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["is_anonymous"] is True
    assert data["incident_type"] == "police_harassment"
    # Urgent police harassment must match NALSA free legal aid
    scheme_names = [s["name"] for s in data["matched_schemes"]]
    assert any("NALSA" in name for name in scheme_names)


def test_list_and_update_incidents_rbac():
    user_token = get_auth_token("user@example.com", "user123")
    verifier_token = get_auth_token("ngo@shreetrust.org", "verifier123")

    # Verifier lists all incidents
    v_res = client.get("/incidents/", headers={"Authorization": f"Bearer {verifier_token}"})
    assert v_res.status_code == 200
    all_incidents = v_res.json()
    assert len(all_incidents) >= 1

    first_incident = all_incidents[0]
    first_id = first_incident["id"]

    # Verifier updates incident status to escalated_to_ngo
    patch_payload = {
        "status": "escalated_to_ngo",
        "case_notes": "Assigned to legal aid cell for urgent petition drafting.",
        "assigned_ngo": "The Humsafar Trust Legal Desk",
    }
    patch_res = client.patch(
        f"/incidents/{first_id}/status",
        json=patch_payload,
        headers={"Authorization": f"Bearer {verifier_token}"},
    )
    assert patch_res.status_code == 200
    updated_data = patch_res.json()
    assert updated_data["status"] == "escalated_to_ngo"
    assert updated_data["assigned_ngo"] == patch_payload["assigned_ngo"]

    # Regular user attempting to patch status should be forbidden (403)
    user_patch_res = client.patch(
        f"/incidents/{first_id}/status",
        json=patch_payload,
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert user_patch_res.status_code == 403


# ==========================================
# 5. AI Awareness Module Tests
# ==========================================

def test_awareness_topics_list_and_detail():
    res = client.get("/awareness/topics")
    assert res.status_code == 200
    topics = res.json()
    assert len(topics) >= 5
    topic_ids = [t["id"] for t in topics]
    assert "tg_act_2019" in topic_ids
    assert "nalsa_2014" in topic_ids

    # Detail view
    detail_res = client.get("/awareness/topics/tg_act_2019")
    assert detail_res.status_code == 200
    data = detail_res.json()
    assert "Section 3" in " ".join(data["key_rights"])
    assert len(data["remedies"]) > 0


def test_awareness_query_workplace():
    query_payload = {
        "query": "My company fired me after I changed my name on my ID card. Is this illegal?",
    }
    res = client.post("/awareness/query", json=query_payload)
    assert res.status_code == 200
    data = res.json()
    assert "Transgender" in data["applicable_law"]
    assert len(data["sections_cited"]) > 0
    assert len(data["actionable_steps"]) > 0
    assert "15100" in data["legal_aid_contact"] or "14566" in data["legal_aid_contact"]
    assert any("transgender.dosje.gov.in" in p or "nalsa" in p for p in data["official_portals"])


def test_awareness_query_police_harassment():
    query_payload = {
        "query": "Can police arrest or search me on the street for no reason?",
    }
    res = client.post("/awareness/query", json=query_payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data["actionable_steps"]) > 0
    assert "15100" in data["legal_aid_contact"]


# ==========================================
# 6. AI Health Assistant Decision Tree Tests
# ==========================================

def test_health_assistant_initial_tree():
    res = client.get("/health-assistant/tree")
    assert res.status_code == 200
    data = res.json()
    assert "disclaimer" in data
    assert "WPATH" in data["disclaimer"]
    node = data["node"]
    assert node["node_id"] == "root"
    assert len(node["options"]) >= 4
    option_ids = [o["option_id"] for o in node["options"]]
    assert "opt_crisis" in option_ids
    assert "opt_hrt" in option_ids
    assert "opt_surgery" in option_ids


def test_health_assistant_traversal_to_hrt_protocol():
    # Step 1: Traverse from root to hrt_start
    step1_res = client.post(
        "/health-assistant/traverse",
        json={"current_node_id": "root", "option_id": "opt_hrt"},
    )
    assert step1_res.status_code == 200
    node1 = step1_res.json()["node"]
    assert node1["node_id"] == "hrt_start"
    assert node1["warnings"] is not None

    # Step 2: Traverse from hrt_start to hrt_protocol (blood panels)
    step2_res = client.post(
        "/health-assistant/traverse",
        json={"current_node_id": "hrt_start", "option_id": "opt_hrt_protocol"},
    )
    assert step2_res.status_code == 200
    node2 = step2_res.json()["node"]
    assert node2["node_id"] == "hrt_protocol"
    rec_actions = " ".join(node2["recommended_actions"])
    assert "Complete Blood Count" in rec_actions
    assert "Liver Function Test" in rec_actions
    assert "Lipid Profile" in rec_actions


def test_health_assistant_traversal_to_crisis_sos():
    res = client.post(
        "/health-assistant/traverse",
        json={"current_node_id": "root", "option_id": "opt_crisis"},
    )
    assert res.status_code == 200
    node = res.json()["node"]
    assert node["node_id"] == "crisis_sos"
    assert node["is_leaf"] is True
    contacts = " ".join(node["helpline_contacts"])
    assert "14416" in contacts  # Tele-MANAS
    assert "1800-599-0019" in contacts  # Kiran Helpline


def test_health_assistant_traversal_to_surgery_ayushman():
    res = client.post(
        "/health-assistant/traverse",
        json={"current_node_id": "surgery_start", "option_id": "opt_surgery_ayushman"},
    )
    assert res.status_code == 200
    node = res.json()["node"]
    assert node["node_id"] == "surgery_ayushman"
    assert "Ayushman Bharat" in node["title"]
    assert "5,00,000" in node["message"] or "5,00,000" in (node.get("clinical_notes") or "")


def test_static_frontend_and_assets():
    # Browser request to root endpoint receives index.html
    html_res = client.get("/", headers={"Accept": "text/html,application/xhtml+xml"})
    assert html_res.status_code == 200
    assert "Beyond Identity" in html_res.text
    assert "styles.css" in html_res.text
    assert "app.js" in html_res.text

    # Dedicated /app endpoint
    app_res = client.get("/app")
    assert app_res.status_code == 200
    assert "Beyond Identity" in app_res.text

    # Static CSS and JS assets
    css_res = client.get("/static/css/styles.css")
    assert css_res.status_code == 200
    assert "var(--bg-primary)" in css_res.text

    js_res = client.get("/static/js/app.js")
    assert js_res.status_code == 200
    assert "setupTabs" in js_res.text

