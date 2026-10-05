"""
Comprehensive automated test suite for Beyond Identity backend.
Covers:
- Root & Metadata endpoints
- Authentication & RBAC (register, login, me, invalid credentials)
- Listings CRUD & Verification workflows
- Discrimination Incident Reporting & Scheme/NGO Matcher
- Legal Rights Awareness Module
- Health Assistant Decision Tree state machine
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


def test_forgot_password_flow():
    # 1. Non-existent email fails
    bad_res = client.post("/auth/forgot-password", json={"email": "nonexistent@nowhere.org"})
    assert bad_res.status_code == 404

    # 2. Existing user succeeds and receives token
    res = client.post("/auth/forgot-password", json={"email": "user@example.com"})
    assert res.status_code == 200
    data = res.json()
    assert "reset_token" in data
    assert data["email"] == "user@example.com"
    token = data["reset_token"]

    # 3. Reset password with short password fails
    short_res = client.post("/auth/reset-password", json={"token": token, "new_password": "123"})
    assert short_res.status_code == 400
    assert "at least 6 characters" in short_res.json()["detail"]

    # 4. Reset with invalid token fails
    invalid_res = client.post("/auth/reset-password", json={"token": "invalid.jwt.token", "new_password": "NewValidPassword123!"})
    assert invalid_res.status_code == 400

    # 5. Reset with valid token succeeds
    reset_res = client.post("/auth/reset-password", json={"token": token, "new_password": "NewUserPassword456!"})
    assert reset_res.status_code == 200
    assert "successfully updated" in reset_res.json()["message"]

    # 6. Verify login with new password succeeds
    login_new = client.post("/auth/login-json", json={"email": "user@example.com", "password": "NewUserPassword456!"})
    assert login_new.status_code == 200

    # 7. Restore original password for subsequent tests
    tok2 = client.post("/auth/forgot-password", json={"email": "user@example.com"}).json()["reset_token"]
    client.post("/auth/reset-password", json={"token": tok2, "new_password": "user123"})



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
# 5. Awareness Module Tests
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


def test_awareness_chat_form():
    payload = {
        "messages": [
            {"role": "user", "content": "What are my rights if my landlord forces me out?"}
        ],
        "voice_mode": False,
    }
    res = client.post("/awareness/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert "speech_text" in data
    assert len(data["reply"]) > 0
    assert len(data["speech_text"]) > 0
    assert len(data["actionable_steps"]) > 0


def test_awareness_talking_form():
    payload = {
        "messages": [
            {"role": "user", "content": "Can an employer discriminate in salary?"}
        ],
        "voice_mode": True,
    }
    res = client.post("/awareness/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert "speech_text" in data
    assert "15100" in data["speech_text"] or "14566" in data["speech_text"] or "protected" in data["speech_text"]


# ==========================================
# 6. Health Assistant Decision Tree Tests
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


# ==========================================
# 7. Transgender Parents Domain & Q&A Manager Tests
# ==========================================

def test_transgender_parents_qa_domain():
    from app.data import PARENTS_QA, ALL_QA

    # Exactly 20 questions in domain 5
    assert len(PARENTS_QA) == 20
    assert len(ALL_QA) >= 220

    # IDs strictly 201 to 220
    parent_ids = [q["id"] for q in PARENTS_QA]
    assert parent_ids == list(range(201, 221))

    # Validate structure and completeness
    for q in PARENTS_QA:
        assert q["category"] == "Transgender Parents & Family Protections"
        assert len(q["question"]) > 10
        assert len(q["answer"]) > 25
        assert len(q["applicable_law"]) > 5
        assert len(q["keywords"]) >= 3


def test_qa_manager_aggregation_and_search():
    from app.data import get_all_qa, search_qa, get_qa_by_id, get_categories

    # Total questions
    all_items = get_all_qa()
    assert len(all_items) >= 220

    # Filter by category
    parent_items = get_all_qa(category="Transgender Parents")
    assert len(parent_items) == 20

    # Categories list
    cats = get_categories()
    assert "Transgender Parents & Family Protections" in cats

    # Search for adoption
    adopt_res = search_qa("adopt child cara")
    assert len(adopt_res) > 0
    assert any("CARA" in item["applicable_law"] or "adopt" in item["question"].lower() for item in adopt_res)

    # Search for custody
    custody_res = search_qa("custody family court")
    assert len(custody_res) > 0

    # Get by ID
    qa_201 = get_qa_by_id(201)
    assert qa_201 is not None
    assert "adopt" in qa_201["question"].lower()

    # Non-existent ID
    assert get_qa_by_id(99999) is None


def test_awareness_transgender_parents_topic():
    res = client.get("/awareness/topics/transgender_parents_and_family")
    assert res.status_code == 200
    topic = res.json()
    assert topic["id"] == "transgender_parents_and_family"
    assert "Transgender Parents" in topic["title"]
    assert "CARA" in topic["act_or_ruling"] or "TG Act" in topic["act_or_ruling"]
    assert len(topic["key_rights"]) >= 5
    assert len(topic["remedies"]) >= 4


def test_awareness_query_parents_adoption():
    query_payload = {
        "query": "Can a transgender parent legally adopt a child under Indian law through CARA?",
    }
    res = client.post("/awareness/query", json=query_payload)
    assert res.status_code == 200
    data = res.json()
    assert "Parents" in data["matched_topic"] or "Transgender" in data["matched_topic"]
    assert len(data["actionable_steps"]) > 0
    assert "cara" in " ".join(data["official_portals"]).lower() or "nalsa" in " ".join(data["official_portals"]).lower()


def test_qa_api_endpoints():
    # 1. List all categories
    cats_res = client.get("/awareness/qa/categories")
    assert cats_res.status_code == 200
    categories = cats_res.json()
    assert "Transgender Parents & Family Protections" in categories

    # 2. Browse QA items (paginated)
    qa_res = client.get("/awareness/qa?limit=10&page=1")
    assert qa_res.status_code == 200
    qa_data = qa_res.json()
    assert qa_data["total"] >= 220
    assert len(qa_data["items"]) == 10
    assert qa_data["page"] == 1

    # 3. Filter QA items by parent category
    parent_qa_res = client.get("/awareness/qa?category=Transgender+Parents")
    assert parent_qa_res.status_code == 200
    parent_qa_data = parent_qa_res.json()
    assert parent_qa_data["total"] == 20

    # 4. Search QA items
    search_res = client.get("/awareness/qa?q=cryopreservation")
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total"] > 0
    assert any("fertility" in item["answer"].lower() or "cryopreservation" in item["question"].lower() for item in search_data["items"])

    # 5. Get single QA item by ID
    single_res = client.get("/awareness/qa/201")
    assert single_res.status_code == 200
    item_201 = single_res.json()
    assert item_201["id"] == 201
    assert "adopt" in item_201["question"].lower()

    # 6. Not found
    nf_res = client.get("/awareness/qa/99999")
    assert nf_res.status_code == 404

