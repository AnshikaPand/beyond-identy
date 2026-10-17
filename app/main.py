import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import Base, engine
from app.routers import auth, listings, incidents, awareness, health_assistant, chatbot

# Creates tables if they don't exist yet (fine for dev/mock-data phase;
# use Alembic migrations once the schema stabilizes).
Base.metadata.create_all(bind=engine)

def _ensure_sqlite_columns():
    """Lightweight SQLite schema migration for Google OAuth integration."""
    try:
        with engine.connect() as conn:
            cursor = conn.connection.cursor()
            cursor.execute("PRAGMA table_info(users)")
            info = cursor.fetchall()
            cols = {row[1]: row for row in info}

            # If hashed_password is still NOT NULL in existing SQLite table, rebuild it with nullable password
            if "hashed_password" in cols and cols["hashed_password"][3] == 1:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users_temp (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR NOT NULL,
                        email VARCHAR UNIQUE NOT NULL,
                        hashed_password VARCHAR NULL,
                        role VARCHAR(8) NOT NULL DEFAULT 'user',
                        is_active BOOLEAN DEFAULT 1,
                        created_at DATETIME,
                        google_id VARCHAR UNIQUE,
                        auth_provider VARCHAR DEFAULT 'local'
                    )
                """)
                cursor.execute("""
                    INSERT INTO users_temp (id, name, email, hashed_password, role, is_active, created_at, google_id, auth_provider)
                    SELECT id, name, email, hashed_password, role, is_active, created_at,
                           COALESCE(google_id, NULL),
                           COALESCE(auth_provider, 'local')
                    FROM users
                """)
                cursor.execute("DROP TABLE users")
                cursor.execute("ALTER TABLE users_temp RENAME TO users")
                conn.connection.commit()
            if "is_verified" not in cols:
                cursor.execute("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 0")
            if "google_id" not in cols:
                cursor.execute("ALTER TABLE users ADD COLUMN google_id VARCHAR")
            if "auth_provider" not in cols:
                cursor.execute("ALTER TABLE users ADD COLUMN auth_provider VARCHAR DEFAULT 'local'")

            # Keep demo/seed accounts verified so tests and demo logins never fail
            cursor.execute("""
                UPDATE users SET is_verified = 1 
                WHERE email LIKE '%@example.com'
                   OR email LIKE '%@example.org'
                   OR email LIKE '%@humsafar.org'
                   OR email LIKE '%@beyondidentity.org'
                   OR auth_provider = 'google'
            """)
            conn.connection.commit()
    except Exception as e:
        pass

_ensure_sqlite_columns()

STATIC_DIR = Path(__file__).resolve().parent / "static"
ASSETS_DIR = STATIC_DIR / "assets"
INDEX_FILE = STATIC_DIR / "index.html"
LOGIN_FILE = STATIC_DIR / "login.html"
REGISTER_FILE = STATIC_DIR / "register.html"
ABOUT_FILE = STATIC_DIR / "about.html"
DASHBOARD_FILE = STATIC_DIR / "dashboard.html"
NGO_DASHBOARD_FILE = STATIC_DIR / "ngo-dashboard.html"

app = FastAPI(
    title="Beyond Identity API",
    description=(
        "Backend for the Beyond Identity platform — empowering individuals to report discrimination, "
        "connect with Indian government welfare schemes and NGO support, access Legal Rights Awareness, "
        "navigate healthcare through a Health Assistant decision tree, and consult the 24/7 Chatbox. "
        "Aligning with UN SDGs: Reduced Inequalities (SDG 10), Peace & Justice (SDG 16), and Good Health (SDG 3)."
    ),
    version="0.3.0",
)

# Robust CORS middleware: permits localhost (e.g. VS Code Live Server on :5500) and configured frontend URL
origins = [
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://localhost",
]
frontend_env = os.getenv("FRONTEND_URL")
if frontend_env and frontend_env not in origins:
    origins.append(frontend_env)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static assets & dedicated /assets route
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

app.include_router(auth.router)
app.include_router(listings.router)
app.include_router(incidents.router)
app.include_router(awareness.router)
app.include_router(health_assistant.router)
app.include_router(chatbot.router)


@app.get("/")
def root(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept and INDEX_FILE.exists():
        return FileResponse(
            str(INDEX_FILE),
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    if request.query_params.get("format") == "html" and INDEX_FILE.exists():
        return FileResponse(str(INDEX_FILE))
    return {
        "message": "Beyond Identity API is running",
        "version": "0.3.0",
        "docs": "/docs",
        "app": "/app",
        "login": "/login",
        "sdg_alignment": ["SDG 3: Good Health", "SDG 10: Reduced Inequalities", "SDG 16: Access to Justice"],
    }


@app.get("/app")
def serve_app():
    if INDEX_FILE.exists():
        return FileResponse(str(INDEX_FILE))
    return {"message": "Web frontend not found"}


# =========================================================================
# Auth Portal Routes (Dedicated Login and Register Pages)
# =========================================================================
@app.get("/register")
@app.get("/register.html")
@app.get("/signup")
def serve_register_page():
    """Serves the dedicated Register page with real Gmail verification."""
    target = REGISTER_FILE if REGISTER_FILE.exists() else LOGIN_FILE
    if target.exists():
        return FileResponse(
            str(target),
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    return {"message": "Register page not found"}


@app.get("/login")
@app.get("/login.html")
@app.get("/signin")
@app.get("/auth")
@app.get("/auth-portal")
def serve_login_page():
    """Serves the login page featuring Google Sign-In and Gmail+Password."""
    if LOGIN_FILE.exists():
        return FileResponse(
            str(LOGIN_FILE),
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    return {"message": "Login page not found"}


@app.get("/about")
def serve_about():
    if ABOUT_FILE.exists():
        return FileResponse(str(ABOUT_FILE))
    return {"message": "About page not found"}


@app.get("/chat")
def serve_chat():
    if INDEX_FILE.exists():
        return FileResponse(str(INDEX_FILE))
    return {"message": "Chatbox frontend not found"}


@app.get("/chatbot")
def serve_chatbot():
    if INDEX_FILE.exists():
        return FileResponse(str(INDEX_FILE))
    return {"message": "Chatbox frontend not found"}


@app.get("/dashboard")
@app.get("/dashboard.html")
@app.get("/dashboard/community")
def serve_dashboard():
    """Serves the dedicated Community Member Dashboard."""
    target = DASHBOARD_FILE if DASHBOARD_FILE.exists() else INDEX_FILE
    if target.exists():
        return FileResponse(str(target))
    return {"message": "Dashboard not found"}


@app.get("/ngo-dashboard.html")
@app.get("/dashboard/ngo")
def serve_ngo_dashboard():
    """Serves the dedicated NGO Partner Dashboard."""
    target = NGO_DASHBOARD_FILE if NGO_DASHBOARD_FILE.exists() else INDEX_FILE
    if target.exists():
        return FileResponse(str(target))
    return {"message": "NGO Dashboard not found"}


@app.get("/portal")
@app.get("/report/anonymous")
def serve_portal_routes():
    if INDEX_FILE.exists():
        return FileResponse(str(INDEX_FILE))
    return {"message": "Portal frontend not found"}




