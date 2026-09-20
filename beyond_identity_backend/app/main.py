from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth, listings, incidents, awareness, health_assistant

# Creates tables if they don't exist yet (fine for dev/mock-data phase;
# use Alembic migrations once the schema stabilizes).
Base.metadata.create_all(bind=engine)

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

app.include_router(auth.router)
app.include_router(listings.router)
app.include_router(incidents.router)
app.include_router(awareness.router)
app.include_router(health_assistant.router)


@app.get("/")
def root():
    return {
        "message": "Beyond Identity API is running",
        "version": "0.2.0",
        "docs": "/docs",
        "sdg_alignment": ["SDG 3: Good Health", "SDG 10: Reduced Inequalities", "SDG 16: Access to Justice"],
    }

