"""
Google login for Beyond Identity.

Add to main.py or app/main.py:
    from app.google_auth import router as google_router
    app.include_router(google_router)
"""
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pydantic import BaseModel
from sqlalchemy.orm import Session

# ---- CHANGED these 3 imports to match Beyond Identity ----
from app.database import get_db              # your DB session dependency
from app.models import User, UserRole        # your User model & role enum
from app.auth import create_access_token     # your existing JWT function
# ----------------------------------------------------------

load_dotenv()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/google-client-id")
def get_google_client_id():
    """Returns the configured Google Client ID so frontend can initialize Google Sign-In dynamically."""
    return {"client_id": GOOGLE_CLIENT_ID or ""}


class GoogleLoginIn(BaseModel):
    credential: str                       # the ID token Google gave the browser
    role: Optional[str] = "community"     # "community" or "ngo"


@router.post("/google")
def google_login(data: GoogleLoginIn, db: Session = Depends(get_db)):
    role_normalized = (data.role or "community").lower().strip()
    if role_normalized not in ("community", "ngo", "verifier", "user"):
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'community' or 'ngo'.")

    # 1. Ask Google's library to verify the token (signature, expiry, our client id).
    #    Never trust an email sent directly from the browser.
    try:
        audience = (
            GOOGLE_CLIENT_ID
            if (GOOGLE_CLIENT_ID and "your-google-client-id" not in GOOGLE_CLIENT_ID.lower())
            else None
        )
        info = id_token.verify_oauth2_token(
            data.credential,
            google_requests.Request(),
            audience=audience,
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token.")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Google verification failed: {str(e)}")

    # 2. Only accept emails that Google itself has verified.
    if not info.get("email_verified"):
        raise HTTPException(status_code=401, detail="Google email is not verified.")

    email = info["email"].lower().strip()
    google_id = info.get("sub")
    name = info.get("name", email.split("@")[0]).strip()

    # Map role string to Beyond Identity UserRole Enum (community -> user, ngo -> verifier)
    mapped_role = UserRole.verifier if role_normalized in ("ngo", "verifier") else UserRole.user

    # 3. Existing user -> log in. New user -> create account (no password).
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(
            name=name,
            email=email,
            role=mapped_role,
            google_id=google_id,
            is_verified=True,             # Verified directly by Google
            auth_provider="google",
            hashed_password=None,         # No password required for Google accounts
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        changed = False
        if not user.google_id and google_id:
            user.google_id = google_id    # link Google to the existing account
            changed = True
        if not user.is_verified:
            user.is_verified = True       # Google verified the email
            changed = True
        if getattr(user, "auth_provider", "local") == "local":
            user.auth_provider = "google"
            changed = True
        if changed:
            db.commit()
            db.refresh(user)

    # 4. Return the platform JWT and user profile
    token = create_access_token({"sub": str(user.id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "is_verified": user.is_verified,
        },
    }
