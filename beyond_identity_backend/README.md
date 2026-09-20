# Beyond Identity — Backend

FastAPI + SQLAlchemy backend empowering transgender and marginalized individuals across India to report discrimination, connect with authentic government schemes and verified NGO support, learn their statutory rights via the **AI Awareness Module**, and receive clinically guided triage via the **AI Health Assistant decision tree prototype**.

Aliged with United Nations Sustainable Development Goals:
- **SDG 10 (Reduced Inequalities)**: Promoting equal opportunities, inclusive workplaces, housing, and transparent discrimination redressal.
- **SDG 16 (Peace, Justice, and Strong Institutions)**: Access to justice under the Transgender Persons Act 2019, NALSA (2014) Supreme Court verdict, and NALSA free legal aid.
- **SDG 3 (Good Health and Well-being)**: Life-saving crisis mental health triage (Tele-MANAS, Kiran), safe HRT clinical roadmap, and Ayushman Bharat PM-JAY surgery access.

---

## Features & Modules

### 1. Authentication & Role-Based Access Control (RBAC)
- JWT token authentication (`HS256`, 24h expiration).
- Secure password hashing with `bcrypt`.
- Three user tiers:
  - `user`: Browse verified listings, submit listings, file confidential or anonymous discrimination reports, view own reports.
  - `verifier`: NGO partner / community moderator with rights to verify/reject/delist listings and escalate/manage discrimination cases.
  - `admin`: Full system control and case assignment.

### 2. Verified Opportunity Listings (`/listings`)
- Categories: Education, Employment, Housing, Healthcare, Scholarships, Government Schemes, Community/Mentorship.
- Trust & safety model: Listings start as `pending`; only `verifier` or `admin` accounts can approve them to `verified`.
- Listing-level discrimination reports: Repeat complaints (3+) trigger automated delisting.

### 3. Discrimination Incident Reporting & Matcher Engine (`/incidents`)
- Confidential or anonymous reporting of discrimination in:
  - Workplace (wrongful termination, harassment, unequal pay)
  - Healthcare denial (refusal of care, lack of separate wards, discrimination by doctors)
  - Housing & eviction (landlord harassment, arbitrary evictions)
  - Education (ragging, denied admissions)
  - Public & police harassment (illegal detention, extortion)
  - Documentation (rejection of name/gender change applications)
- **Automated Scheme & NGO Matcher**:
  - Automatically matches the incident by type and state with authentic Indian government schemes (e.g., **SMILE**, **Ayushman Bharat PM-JAY TG Package**, **Garima Greh**, **NALSA Free Legal Aid**, state welfare boards).
  - Matches with verified partner NGOs (**The Humsafar Trust**, **Tweet Foundation**, **Nazariya QFRG**, **Sahodari Foundation**, **Mitr Trust**, **Sappho for Equality**).
- Case lifecycle tracking: `submitted` -> `under_review` -> `escalated_to_ngo` -> `legal_aid_assigned` -> `resolved`.

### 4. AI Awareness Module — Know Your Rights (`/awareness`)
- Curated legal knowledge base covering:
  - **Transgender Persons (Protection of Rights) Act, 2019** (Sections 3, 4, 9, 10, 11, 12, 15, 18).
  - **NALSA vs. Union of India (2014)** Supreme Court Judgment (Articles 14, 15, 19, 21).
  - **National Portal for Transgender Persons** (`transgender.dosje.gov.in`) certificate & identity card rules.
  - **Section 12 Legal Services Authorities Act, 1987** (Free legal aid for all trans persons via Helpline `15100`).
  - Workplace Equal Opportunity Policies & statutory Complaints Officer mandates.
- **Interactive Query Engine (`POST /awareness/query`)**:
  - Accepts natural-language questions or incident descriptions.
  - Returns applicable laws, sections cited, plain-language rights explanation, step-by-step remedies, legal aid helpline contacts, and direct government portal links.

### 5. AI Health Assistant Decision-Tree Prototype (`/health-assistant`)
- Rule-based diagnostic/guidance state machine designed according to WPATH Standards of Care v8:
  - **Crisis SOS Triage**: Immediate connect to 24x7 crisis helplines (Tele-MANAS `14416`, Kiran Helpline `1800-599-0019`, emergency shelter).
  - **Safe Hormone Replacement Therapy (HRT)**: Clinical protocol, pre-HRT required blood panels (LFT, KFT, CBC, Lipid profile, Fasting Glucose, Baseline Testosterone/Estradiol, Prolactin), and explicit medical alerts against unsupervised DIY self-medication.
  - **Gender-Affirming Surgeries (GAS)**: Prerequisites, psychiatrist evaluations, and Ayushman Bharat PM-JAY coverage (up to ₹5,00,000/year).
  - **Affirmative Mental Health**: Affirmative therapy directory and dysphoria management.
  - **General Healthcare**: STI/HIV screening and inclusive primary care.
- Endpoints:
  - `GET /health-assistant/tree`: Full root tree structure for Flutter/mobile frontend rendering.
  - `POST /health-assistant/traverse`: Interactive step-by-step node traversal.

---

## Setup & Local Development

### 1. Environment & Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt pytest httpx
```

### 2. Seed Database with Real Data

```bash
python -m app.seed
```

This seeds:
- 3 demo users with distinct roles:
  - **Admin**: `admin@beyondidentity.org` / `admin123`
  - **Verifier**: `ngo@shreetrust.org` / `verifier123`
  - **User**: `user@example.com` / `user123`
- Verified listings across education, jobs, healthcare, shelters, and government schemes.
- 3 realistic discrimination incident reports with automated scheme/NGO matches.

### 3. Run Development Server

```bash
uvicorn app.main:app --reload
```

- Server runs at: `http://127.0.0.1:8000`
- Interactive OpenAPI / Swagger Documentation: `http://127.0.0.1:8000/docs`
- Alternative ReDoc: `http://127.0.0.1:8000/redoc`

---

## Running Automated Tests

```bash
pytest -v
```

The comprehensive test suite in `tests/test_api.py` verifies all 15 core behaviors including auth, RBAC, listing verification, incident reporting & matching, AI legal queries, and decision tree state traversal.

---

## Project Structure

```
beyond_identity_backend/
├── README.md
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application, CORS, and router registration
│   ├── database.py          # SQLAlchemy engine, session, and base declarative model
│   ├── models.py            # DB tables: User, Listing, IncidentReport
│   ├── schemas.py           # Pydantic request/response validation models
│   ├── auth.py              # JWT tokens, password hashing, and RBAC dependencies
│   ├── seed.py              # Real Indian schemes, NGOs, listings, and incidents seeder
│   ├── services/
│   │   ├── __init__.py
│   │   ├── matcher.py       # Scheme & NGO matching engine
│   │   ├── awareness.py     # AI Legal Awareness knowledge base & query engine
│   │   └── health_assistant.py # AI Health Assistant decision-tree state machine
│   └── routers/
│       ├── __init__.py
│       ├── auth.py          # /auth (register, login, me)
│       ├── listings.py      # /listings (CRUD, verify, report)
│       ├── incidents.py     # /incidents (report, match, RBAC list, status patch)
│       ├── awareness.py     # /awareness (topics, query)
│       └── health_assistant.py # /health-assistant (tree, traverse)
└── tests/
    ├── __init__.py
    └── test_api.py          # 15 automated test cases covering all endpoints
```

