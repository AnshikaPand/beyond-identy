from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import Base, engine
from app.routers import auth, listings, incidents, awareness, health_assistant

# Creates tables if they don't exist yet (fine for dev/mock-data phase;
# use Alembic migrations once the schema stabilizes).
Base.metadata.create_all(bind=engine)

STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_FILE = STATIC_DIR / "index.html"
LOGIN_FILE = STATIC_DIR / "login.html"

app = FastAPI(
    title="Beyond Identity API",
    description=(
        "Backend for the Beyond Identity platform — empowering individuals to report discrimination, "
        "connect with Indian government welfare schemes and NGO support, access AI Legal Rights Awareness, "
        "and navigate healthcare through an AI Health Assistant decision tree. "
        "Aligning with UN SDGs: Reduced Inequalities (SDG 10), Peace & Justice (SDG 16), and Good Health (SDG 3)."
    ),
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this to your actual frontend domain before deploying
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(auth.router)
app.include_router(listings.router)
app.include_router(incidents.router)
app.include_router(awareness.router)
app.include_router(health_assistant.router)


@app.get("/")
def root(request: Request):
    accept = request.headers.get("accept", "")
    # Serve interactive web application to browser requests
    if "text/html" in accept and "application/json" not in accept and INDEX_FILE.exists():
        return FileResponse(str(INDEX_FILE))
    return {
        "message": "Beyond Identity API is running",
        "version": "0.2.0",
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


@app.get("/login")
def serve_login():
    if LOGIN_FILE.exists():
        return FileResponse(str(LOGIN_FILE))
    return {"message": "Login page not found"}


@app.get("/register")
def serve_register():
    if LOGIN_FILE.exists():
        return FileResponse(str(LOGIN_FILE))
    return {"message": "Register page not found"}

