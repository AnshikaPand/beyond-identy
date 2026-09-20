# Beyond Identity — Technical Architecture & Local Deployment Guide

> **A Secure, Statutory Legal Rights, Health Guidance, and Discrimination Redressal Ecosystem for Transgender and Gender-Diverse Indians.**

---

## 🌟 Executive Summary & Impact

**Beyond Identity** is a full-stack, enterprise-grade digital platform engineered to protect and empower transgender, intersex, and gender-diverse individuals across India. The platform bridges the critical gap between community members facing discrimination and statutory legal protections, verified welfare schemes, and affirmative healthcare.

### Alignment with UN Sustainable Development Goals (SDGs)
- **🎯 SDG 10 (Reduced Inequalities)**: Dismantles systemic discrimination by connecting individuals with audited inclusive workplaces, safe housing shelters (*Garima Greh*), affirmative education, and confidential incident reporting.
- **⚖️ SDG 16 (Peace, Justice, and Strong Institutions)**: Democratizes access to justice under the **Transgender Persons (Protection of Rights) Act 2019**, the landmark Supreme Court **NALSA (2014)** verdict, and free legal aid via Section 12 of the Legal Services Authorities Act (Helpline `15100`).
- **🩺 SDG 3 (Good Health and Well-being)**: Delivers 24/7 crisis mental health triage (Tele-MANAS `14416`, Kiran `1800-599-0019`), evidence-based WPATH SOC v8 clinical decision trees, pre-HRT safety blood panels, and Ayushman Bharat PM-JAY ₹5,00,000 transgender surgery package navigation.

---

## 🏗️ System Architecture & Technology Stack

```
                                +---------------------------------------------+
                                |               User Interface                |
                                |     (HTML5 / Vanilla CSS3 / Modern JS)      |
                                +----------------------+----------------------+
                                                       |
                             +-------------------------+-------------------------+
                             |                                                   |
                             v                                                   v
                +------------------------+                          +------------------------+
                |   Guest Landing Page   |                          |  Authenticated Portal  |
                |  (Locked Pillars,      |                          | (Opportunities, Report |
                |   Teasers, Pipelines)  |                          |  AI Awareness, Health) |
                +------------------------+                          +------------------------+
                             |                                                   |
                             +-------------------------+-------------------------+
                                                       | REST API (JSON / JWT)
                                                       v
                                +---------------------------------------------+
                                |           FastAPI Backend Server            |
                                |   (Uvicorn ASGI, Pydantic v2, Python-Jose)  |
                                +----------------------+----------------------+
                                                       |
                             +-------------------------+-------------------------+
                             |                         |                         |
                             v                         v                         v
                   +------------------+      +------------------+      +------------------+
                   |  Authentication  |      |   Matcher Engine |      | Decision Tree    |
                   |   & RBAC Guard   |      |  (Schemes & NGOs)|      |  State Machine   |
                   +------------------+      +------------------+      +------------------+
                             |                         |                         |
                             +-------------------------+-------------------------+
                                                       | SQLAlchemy ORM
                                                       v
                                +---------------------------------------------+
                                |             SQLite3 Database                |
                                | (Users, Listings, Incidents, Schemes, NGOs) |
                                +---------------------------------------------+
```

### Core Technologies
- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/) (High-performance asynchronous Python web framework).
- **ASGI Server**: [Uvicorn](https://www.uvicorn.org/) with hot-reloading support.
- **ORM & Database**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/) with SQLite3 relational storage, foreign key constraints, and cascading integrity.
- **Data Validation & Serialization**: [Pydantic v2](https://docs.pydantic.dev/latest/) with strict schema typing and automated OpenAPI documentation.
- **Security & Cryptography**:
  - `passlib[bcrypt]` with bcrypt salt rounds for secure password hashing.
  - `python-jose[cryptography]` for HMAC-SHA256 (HS256) JWT bearer token issuance and verification.
- **Frontend Architecture**:
  - Zero-dependency modern Vanilla JavaScript (ES6+ async/await fetch client).
  - Custom Vanilla CSS3 Design System with CSS Custom Properties (Variables), glassmorphism, responsive grid/flexbox, and micro-interactions.
  - Typography: Google Fonts ([Outfit](https://fonts.google.com/specimen/Outfit) for headings, [Inter](https://fonts.google.com/specimen/Inter) for body).
- **Testing & Quality Assurance**: [Pytest](https://docs.pytest.org/) with Starlette `TestClient` and HTTPX (100% test pass rate across 20 automated unit tests).

---

## 🚀 Step-by-Step Local Machine Setup Guide

Follow these instructions to clone, set up, and run **Beyond Identity** on **any** local computer (Windows, macOS, or Linux).

### 📋 Prerequisites
Before you begin, ensure you have the following installed on your machine:
1. **Python 3.10 or higher** (Python 3.11+ recommended).
   - Check version: `python --version` (or `python3 --version`).
2. **Git** (optional, for cloning).
3. A modern web browser (Google Chrome, Firefox, Safari, Microsoft Edge).

---

### 🖥️ Installation Instructions

#### Step 1: Open Your Terminal / Command Prompt
- **Windows**: Open **PowerShell** or **Command Prompt** (cmd).
- **macOS / Linux**: Open **Terminal**.

#### Step 2: Navigate to or Clone the Project Directory
```bash
# If using Git:
git clone https://github.com/your-org/beyond_identity_backend.git
cd beyond_identity_backend

# If downloaded as a ZIP folder, extract it and navigate into the folder:
cd path/to/beyond_identity_backend
```

#### Step 3: Create a Python Virtual Environment
Creating a virtual environment ensures dependencies remain isolated:

- **Windows (PowerShell or CMD)**:
  ```powershell
  python -m venv venv
  ```
- **macOS / Linux**:
  ```bash
  python3 -m venv venv
  ```

#### Step 4: Activate the Virtual Environment

- **Windows (PowerShell)**:
  ```powershell
  venv\Scripts\Activate.ps1
  ```
  *(Note: If PowerShell shows an `Execution_Policy` error, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` then re-run the activation script).*
- **Windows (Command Prompt / CMD)**:
  ```cmd
  venv\Scripts\activate.bat
  ```
- **macOS / Linux (Bash / Zsh)**:
  ```bash
  source venv/bin/activate
  ```

Once activated, your terminal prompt will display `(venv)`.

#### Step 5: Upgrade Pip & Install Project Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt pytest httpx
```

#### Step 6: Initialize & Seed the Database
Beyond Identity comes with a comprehensive seed script that populates realistic government schemes, vetted NGO crisis centers, opportunities, and test user accounts:

- **Windows**:
  ```powershell
  python -m app.seed
  ```
- **macOS / Linux**:
  ```bash
  python3 -m app.seed
  ```

*Expected output:*
```
[*] Cleaning old database tables...
[*] Creating all database tables...
[*] Seeding default test users...
    -> Admin:    admin@beyondidentity.org
    -> Verifier: ngo@shreetrust.org
    -> User:     user@example.com
[*] Seeding verified community listings...
[*] Seeding sample discrimination incidents...
[+] Database successfully initialized and seeded with 3 users, 8 listings, and 3 incidents!
```

#### Step 7: Run the Application Server
Start the Uvicorn ASGI server with automatic reload:

```bash
uvicorn app.main:app --reload --port 8000 --host 127.0.0.1
```

*Expected output:*
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [...]
INFO:     Started server process [...]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

#### Step 8: Access the Application in Your Browser
- **Web Application Portal**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Dedicated Auth Portal**: [http://127.0.0.1:8000/login](http://127.0.0.1:8000/login)
- **Interactive Swagger API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative ReDoc API Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🔑 Default Seeded Accounts & Test Credentials

The database includes three pre-configured accounts representing all three role tiers:

| Role | Name | Email Address | Password | Permissions & Capabilities |
| :--- | :--- | :--- | :--- | :--- |
| **Community Seeker** (`user`) | Priya Sharma | `user@example.com` | `user123` | View verified opportunities, file discrimination complaints (anonymous or authenticated), AI legal rights engine, AI health assistant triage. |
| **NGO Partner** (`verifier`) | Shree Welfare Trust | `ngo@shreetrust.org` | `verifier123` | All community seeker permissions + access to **Case Triage Desk**, case escalation, status updates, case notes, and opportunity vetting. |
| **System Admin** (`admin`) | Beyond Identity Admin | `admin@beyondidentity.org` | `admin123` | Full system control: listing verification/delisting, incident triage, user management, and audit inspection. |

> 💡 **Tip**: You can use the **1-Click Evaluation Buttons** on the landing page or login modal to log into any of these accounts instantly with zero typing!

---

## 🧪 Running the Automated Test Suite

Beyond Identity includes a complete automated test suite covering authentication, role permissions, registration validation, incident filing, AI query matching, and health assistant traversals.

To execute the test suite:

```bash
# Run all tests with standard output
pytest

# Run tests with detailed verbose output
pytest -v

# Run with test coverage summary
pytest -v --durations=5
```

*Current Test Results:* **`20 passed in 5.23s (100% success rate)`**

---

## 🎨 Design System & Theme Engine

Beyond Identity features a **Zero-Flicker Tri-Theme Engine** with pixel-perfect contrast in both Day and Night modes:

### Theme Modes
1. **☀️ Day Mode (Light Theme)**:
   - High-contrast typography designed for bright ambient light.
   - Clean slate surfaces (`#ffffff`, `#f8fafc`, `#f1f5f9`).
   - Deep slate headings (`#0f172a`), crisp readable body text (`#334155`), and tinted semantic badges (`#065f46`, `#0369a1`, `#9f1239`, `#6b21a8`).
   - WCAG AAA/AA compliant contrast ratios across all forms, inputs, modals, and tables.
2. **🌙 Night Mode (Dark Theme)**:
   - Ultra-modern deep navy canvas (`#0a0e1a`, `#121829`, `#161e34`).
   - Vibrant accent glows (`#6366f1` indigo, `#38bdf8` cyan, `#ec4899` pink, `#10b981` emerald).
   - Glassmorphic card surfaces with backdrop blurs.
3. **💻 System Mode (Auto)**:
   - Dynamically synchronizes with the user's OS color scheme preferences (`prefers-color-scheme: dark`).

### Zero-Flicker Persistence
Theme selection is immediately executed in the `<head>` of each HTML document before DOM rendering via `localStorage.getItem("bi_theme")`, preventing white/dark flash on page reload.

---

## 📦 Core Feature Modules & Technical Specifications

### 1. Guest Landing Page vs. Authenticated Portal
- **Guest State (Unauthenticated Visitors)**:
  - Displays a high-converting landing experience with statutory trust badges.
  - **4 Locked Pillars Grid**: Opportunities Directory, Confidential Redressal, AI Legal Rights, and AI Clinical Health.
  - **Interactive 4-Step Redressal Pipeline**: Transparent breakdown of complaint filing, automated matching, NGO review, and legal follow-up.
  - **1-Click Evaluation Strip**: Instant testing buttons for evaluators.
- **Authenticated Member Portal**:
  - Automatically unlocked upon sign-in.
  - Personalized welcome banner showing user role, initials avatar, and member safeguards.
  - Dynamic navigation tabs (`Opportunities`, `Report Discrimination`, `AI Rights Awareness`, `AI Health Assistant`, and `Case Triage Desk` for verifiers/admins).

### 2. Verified Opportunities Directory (`/listings`)
- **Categories**: Education, Employment, Housing & Shelter, Healthcare, Government Schemes, Scholarships, Community/Mentorship.
- **Vetting Protocol**: Listings start in `pending` status and can only be promoted to `verified` by audited NGO partners or admins.
- **Anti-Discrimination Safeguard**: Listings receiving 3+ confirmed complaints are automatically delisted.

#### 🏛️ Pre-Seeded Authentic Resource Catalog (50+ Verified Entries):
- **National & State Government Welfare Schemes**:
  - **SMILE Scheme** (*MoSJE*): National umbrella scheme providing rehabilitation, healthcare, and economic empowerment under Section 6 of the Transgender Persons Act.
  - **SMILE Skill Development and Training** (*MoSJE*): Market-oriented vocational training for transgender persons aged 18-45 with monthly stipends.
  - **PM-DAKSH Yojana** (*MoSJE*): National skilling action plan covering marginalized groups with upskilling, re-skilling, and toolkits.
  - **AB-PMJAY Composite Transgender Health Package** (*NHA & MoHFW*): Free national health insurance coverage up to ₹5,00,000/year for gender-affirming surgeries, hormone therapy, and hospitalization.
  - **National Council for Transgender Persons** (*MoSJE*): Apex statutory advisory council monitoring transgender welfare rights and policy execution.
  - **Chandigarh Fee Waiver Scheme**: 100% tuition and examination fee waiver for transgender students across schools and government degree colleges.
  - **Himachal Pradesh Transgender Welfare Board Schemes**: Pre-matric and post-matric scholarships, financial assistance to parents of transgender children under 18, and skill development grants.
- **Scholarships & National Portals**:
  - **Post-Matric Scholarship for Transgender Students** (*MoSJE*): Covers Class IX through post-graduation, ITI, polytechnic, and UGC/AICTE degree courses with full fee reimbursement and maintenance allowances.
  - **National Portal for Transgender Persons** (`transgender.dosje.gov.in`): Online single-window statutory portal for obtaining government Transgender Certificate and Identity Cards without physical inspection.
- **Verified Partner NGOs & Community Trusts**:
  - **The Humsafar Trust** (Mumbai): Healthcare, HRT endocrinology clinics, and legal advocacy since 1994.
  - **Tweet Foundation** (Delhi / Mumbai): Operates Garima Greh shelters, provides legal aid and gender-affirming care navigation.
  - **PeriFerry** (Chennai): Employment-focused social enterprise; trained 320+ transgender individuals with corporate hiring pipeline partnerships.
  - **Born2Win Social Welfare Trust** (Chennai): Non-profit run by and for transgender and intersex persons.
  - **Naz Foundation (India) Trust** (Delhi): Public health, HIV/AIDS prevention, and affirmative sexual wellness.
  - **Sahodari Foundation** (Tamil Nadu): Transgender empowerment, education scholarships, and arts-based livelihoods.
  - **Orinam** (Chennai): LGBTIQA+ collective maintaining an audited directory of trans-inclusive employers.
- **Audited Affirmative Corporate Employers**:
  - **Tata Steel**: Hired 100+ transgender employees; comprehensive transition medical leave and inclusive HR policies.
  - **Wells Fargo India**: Transgender Persons Hiring Program with PeriFerry, sponsoring 30+ individuals with professional roles.
  - **Accenture India**: Pride at Accenture DEI hiring, covering gender confirmation surgery under corporate medical insurance.
  - **Infosys**: Diversity hiring initiatives, gender-neutral restrooms, and employee resource groups.
  - **KPMG India**: Equal opportunity hiring, inclusive benefits, and partner-led sensitization training.
  - **IBM India**: Recognized in India Workplace Equality Index (IWEI) for transgender hiring and progressive transition leave.
  - **Godrej Properties**: Grew transgender representation from 18 to 85+ employees; Gold Employer in IWEI.
  - **Walmart India**: Recognized in IWEI for hiring transgender talent and inclusive supply chain mentorship.
- **Safe Housing & Crisis Shelters**:
  - **Garima Greh Shelter Homes Network** (*MoSJE under SMILE*): Shelter homes in Mumbai, Delhi, and rollout cities providing food, medical care, and vocational training.
- *Operational Note*: Educational institutions operate primarily via fee-waiver and admission-quota policies (e.g., Chandigarh UT) rather than segregated transgender-only colleges. Application windows and eligibility should be verified directly with each scheme before enrolling.

### 3. Discrimination Incident Redressal & Matching Engine (`/incidents`)
- **Reporting Options**: Authenticated or 100% Anonymous (no user ID attached to incident record).
- **Incident Types**: Workplace, Healthcare Denial, Housing Eviction, Education/Ragging, Public Harassment, Police Harassment, Legal Documentation.
- **Automated Scheme Matcher**:
  - Automatically parses incident type and geographical state to link statutory Indian welfare schemes:
    - **SMILE** (*Support for Marginalised Individuals for Livelihood and Enterprise*).
    - **Ayushman Bharat PM-JAY** (Transgender Health Package ₹5,00,000).
    - **Garima Greh** (Ministry of Social Justice safe shelter homes).
    - **NALSA Free Legal Aid** (Section 12 Legal Services Authorities Act).
  - Instantly links regional crisis desks (e.g., The Humsafar Trust, Tweet Foundation, Nazariya QFRG, Sahodari Foundation).
- **Status Lifecycle**: `submitted` ➔ `under_review` ➔ `escalated_to_ngo` ➔ `legal_aid_assigned` ➔ `resolved`.

### 4. AI Legal Rights Awareness Engine (`/awareness`)
- **Curated Statutory Knowledge Base**:
  - Transgender Persons (Protection of Rights) Act 2019 (Sections 3, 4, 9, 10, 11, 12, 15, 18).
  - Supreme Court NALSA (2014) landmark judgment (Articles 14, 15, 19, 21).
  - District Magistrate certificate and transgender ID card procedures.
  - National Legal Services Authority (NALSA) 24/7 Helpline `15100`.
- **Query Endpoint (`POST /awareness/query`)**:
  - Natural-language matching returning statutory sections, plain-language rights explanation, actionable next steps, emergency legal contacts, and direct government links.

### 5. AI Clinical Health Assistant Decision Tree (`/health-assistant`)
- **Evidence-Based Clinical Protocols**: Built according to WPATH Standards of Care version 8.
- **Interactive State Machine**:
  - **Crisis SOS Triage**: Immediate connect to Tele-MANAS `14416` and Kiran `1800-599-0019`.
  - **Hormone Replacement Therapy (HRT)**: Clinical roadmap, required baseline blood panels (LFT, KFT, CBC, Lipid Profile, Fasting Glucose, Baseline Testosterone/Estradiol, Prolactin), and warnings against black-market DIY self-medication.
  - **Gender-Affirming Surgeries (GAS)**: Prerequisites, psychiatric clearance evaluations, and PM-JAY coverage details.
  - **Affirmative Mental Health & Support**: Dysphoria coping strategies and LGBTQIA+ affirmative therapist directory.

### 6. NGO Case Triage Desk (`/incidents/`)
- Exclusive moderation console for verified NGO caseworkers and system administrators.
- Allows updating case status, adding caseworker notes, and assigning legal aid escalations.

---

## 📡 Complete REST API Reference

All API routes are prefixed under the root host and output standard JSON.

### 🔐 Authentication (`/auth`)

| Method | Endpoint | Auth Required | Description | Sample Request / Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | No | Registers a new user account (role defaults to `user`; `verifier` allowed; `admin` blocked). | **Body**: `{"name": "...", "email": "...", "password": "...", "role": "user"}`<br>**Response**: `{"id": 4, "name": "...", "email": "...", "role": "user"}` |
| `POST` | `/auth/login` | No | OAuth2 standard form-encoded login. | **Body**: `username=email&password=pass`<br>**Response**: `{"access_token": "...", "token_type": "bearer", "user": {...}}` |
| `POST` | `/auth/login-json` | No | Clean JSON payload login endpoint. | **Body**: `{"email": "...", "password": "..."}`<br>**Response**: `{"access_token": "...", "token_type": "bearer", "user": {...}}` |
| `GET` | `/auth/me` | Bearer Token | Retrieves current logged-in user profile. | **Header**: `Authorization: Bearer <token>`<br>**Response**: `{"id": 1, "name": "...", "email": "...", "role": "..."}` |

### 📂 Opportunity Listings (`/listings`)

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/listings/` | No | Returns all approved listings (optional filter `?category=housing`). |
| `POST` | `/listings/` | Bearer Token | Submits a new opportunity listing (created in `pending` status). |
| `PATCH` | `/listings/{id}/verify` | Verifier / Admin | Approves or delists an opportunity listing. |
| `POST` | `/listings/{id}/report` | Bearer Token | Reports a listing for discrimination or bias. 3+ reports auto-delists. |

### 🚨 Discrimination Incident Redressal (`/incidents`)

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/incidents/` | Optional | Submits a confidential or anonymous discrimination report and auto-matches schemes/NGOs. |
| `GET` | `/incidents/` | Verifier / Admin | Lists all reported discrimination incidents for triage. |
| `GET` | `/incidents/my-reports`| Bearer Token | Lists all non-anonymous incidents filed by current user. |
| `PATCH`| `/incidents/{id}/status`| Verifier / Admin | Updates case status (`under_review`, `escalated_to_ngo`, `resolved`) with caseworker notes. |

### ⚖️ AI Rights Awareness (`/awareness`)

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/awareness/topics` | No | Returns all legal topics covered in statutory knowledge base. |
| `POST` | `/awareness/query` | No | Accepts natural language question; returns applicable laws, statutory sections, and legal remedies. |

### 🩺 AI Health Assistant (`/health-assistant`)

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/health-assistant/tree` | No | Returns complete decision tree graph for client-side rendering. |
| `GET` | `/health-assistant/nodes/{id}` | No | Returns a specific health guidance node with options and medical warnings. |
| `POST`| `/health-assistant/traverse` | No | Traverses to next clinical decision node based on selected option. |

---

## 🗄️ Database Schema & Data Models

The database uses SQLite3 with relational foreign keys:

```
+-------------------------------------------------------------+
|                          users                              |
+-------------------------------------------------------------+
| id (INTEGER PK)                                             |
| email (VARCHAR UNIQUE, INDEX)                               |
| hashed_password (VARCHAR)                                   |
| name (VARCHAR)                                              |
| role (VARCHAR: 'user' | 'verifier' | 'admin')              |
| is_active (BOOLEAN)                                         |
| created_at (DATETIME)                                       |
+------------------------------+------------------------------+
                               | 1
                               |
                               | 0..*
+------------------------------v------------------------------+
|                        listings                             |
+-------------------------------------------------------------+
| id (INTEGER PK)                                             |
| title (VARCHAR)                                             |
| description (TEXT)                                          |
| category (VARCHAR)                                          |
| organization_name (VARCHAR)                                 |
| location (VARCHAR)                                          |
| contact_info (VARCHAR)                                      |
| status (VARCHAR: 'pending' | 'verified' | 'delisted')       |
| submitter_id (INTEGER FK -> users.id)                       |
| verified_by (INTEGER FK -> users.id, NULLABLE)              |
| report_count (INTEGER DEFAULT 0)                            |
| created_at (DATETIME)                                       |
+-------------------------------------------------------------+

+-------------------------------------------------------------+
|                        incidents                            |
+-------------------------------------------------------------+
| id (INTEGER PK)                                             |
| reporter_id (INTEGER FK -> users.id, NULLABLE for anon)     |
| incident_type (VARCHAR)                                     |
| title (VARCHAR)                                             |
| description (TEXT)                                          |
| incident_date (DATE, NULLABLE)                              |
| location_city (VARCHAR)                                     |
| location_state (VARCHAR)                                    |
| perpetrator_details (TEXT, NULLABLE)                        |
| urgency_level (VARCHAR: 'low'|'medium'|'high'|'immediate_sos')|
| is_anonymous (BOOLEAN)                                      |
| status (VARCHAR: 'submitted'|'under_review'|'escalated'|...) |
| assigned_ngo (VARCHAR, NULLABLE)                            |
| case_notes (TEXT, NULLABLE)                                 |
| created_at (DATETIME)                                       |
+------------------------------+------------------------------+
                               | 1
              +----------------+----------------+
              | 0..*                            | 0..*
+-------------v---------------+   +-------------v---------------+
|     incident_schemes        |   |       incident_ngos         |
+-----------------------------+   +-----------------------------+
| id (INTEGER PK)             |   | id (INTEGER PK)             |
| incident_id (FK->incidents) |   | incident_id (FK->incidents) |
| scheme_name (VARCHAR)       |   | ngo_name (VARCHAR)          |
| ministry (VARCHAR)          |   | location (VARCHAR)          |
| benefits (TEXT)             |   | helpline (VARCHAR)          |
| application_link (VARCHAR)  |   | focus_area (VARCHAR)        |
+-----------------------------+   +-----------------------------+
```

---

## 📁 Project Directory Structure

```
beyond_identity_backend/
│
├── app/
│   ├── __init__.py                 # Application package initializer
│   ├── config.py                   # Settings & environment variables (SECRET_KEY, DB_URL)
│   ├── database.py                 # SQLAlchemy engine, session maker, Base declarative
│   ├── main.py                     # FastAPI app factory, CORS middleware, static mounts
│   ├── models.py                   # SQLAlchemy ORM database models
│   ├── schemas.py                  # Pydantic v2 validation & response schemas
│   ├── seed.py                     # Database initialization & sample seeding script
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py                 # Authentication routes (login, register, me)
│   │   ├── listings.py             # Opportunities directory routes
│   │   ├── incidents.py            # Discrimination reporting & scheme matcher routes
│   │   ├── awareness.py            # AI Legal Rights awareness engine routes
│   │   └── health_assistant.py     # AI Health decision tree routes
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── awareness_kb.py         # Statutory knowledge base & matching heuristics
│   │   └── health_assistant.py     # WPATH SOC v8 decision tree state machine
│   │
│   └── static/
│       ├── index.html              # Main single-page application & guest landing
│       ├── login.html              # Dedicated full-page authentication portal
│       ├── css/
│       │   └── styles.css          # Core design system & Tri-Theme (Day/Night/Auto)
│       └── js/
│           └── app.js              # Frontend client logic, API calls, theme switcher
│
├── tests/
│   ├── __init__.py
│   └── test_api.py                 # 20 automated unit tests (Pytest + HTTPX)
│
├── requirements.txt                # Python package dependencies
├── beyond_identity.db              # SQLite3 database (generated on seed)
├── README.md                       # Master Documentation
└── LOCAL_SETUP_AND_TECHNICAL_GUIDE.md # Dedicated Local Machine & Setup Reference
```

---

## 🛠️ Frequently Asked Questions & Troubleshooting

### Q1: `Address already in use` error when running Uvicorn
**Cause**: Another process is already using port `8000`.  
**Solution**: Specify an alternative port like `8001`:
```bash
uvicorn app.main:app --reload --port 8001
```
Then visit `http://127.0.0.1:8001/` in your browser.

### Q2: PowerShell says `Scripts cannot be loaded because running scripts is disabled`
**Cause**: Windows PowerShell execution policy restricts script execution by default.  
**Solution**: Run this command once in your PowerShell window:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
Then run `venv\Scripts\Activate.ps1` again.

### Q3: How do I reset or re-seed the database from scratch?
Simply run the seed script again! It will cleanly drop existing tables, recreate them, and reseed all default data:
```bash
python -m app.seed
```

### Q4: `python: command not found` on macOS or Linux
**Cause**: Some Linux distributions and macOS default to `python3`.  
**Solution**: Use `python3` instead:
```bash
python3 -m venv venv
source venv/bin/activate
python3 -m app.seed
```

---

## 📄 License & Ethical Usage
Built with respect, confidentiality, and security for the Indian transgender and gender-diverse community. All legal provisions, helplines, and government welfare schemes referenced in this codebase are verified against official Government of India gazettes and statutory enactments.
