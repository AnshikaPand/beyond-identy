import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserOut, status_code=201)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    if len(user_in.password.strip()) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")

    if user_in.role == models.UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role cannot be self-assigned through public registration",
        )

    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_role = user_in.role if user_in.role else models.UserRole.user

    user = models.User(
        name=user_in.name.strip(),
        email=user_in.email.strip().lower(),
        hashed_password=auth.hash_password(user_in.password),
        role=user_role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm uses "username" field — we treat that as email
    user = db.query(models.User).filter(models.User.email == form_data.username.strip().lower()).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    token = auth.create_access_token(data={"sub": str(user.id)})
    return schemas.Token(access_token=token, token_type="bearer", user=user)


@router.post("/login-json", response_model=schemas.Token)
def login_json(credentials: schemas.UserLoginJSON, db: Session = Depends(get_db)):
    """JSON-based authentication endpoint for web frontends and mobile clients."""
    user = db.query(models.User).filter(models.User.email == credentials.email.strip().lower()).first()
    if not user or not auth.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    token = auth.create_access_token(data={"sub": str(user.id)})
    return schemas.Token(access_token=token, token_type="bearer", user=user)


@router.post("/google", response_model=schemas.Token)
def google_auth(req: schemas.GoogleLoginRequest, db: Session = Depends(get_db)):
    """
    Google Sign-In Authentication Endpoint.
    
    Workflow:
    1. Receives the Google ID token (JWT) from Google Identity Services on the frontend.
    2. Verifies the token's cryptographic signature server-side using Google's public certs.
    3. Validates that the Google account's email has been verified by Google.
    4. Automatically logs in the user if their email exists, or registers a new user with
       the selected role (Community Member or NGO Partner).
    5. Returns our standard platform JWT access_token for seamless session continuity.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    audience = client_id if (client_id and "your-google-client-id" not in client_id) else None

    # Step 1: Verify the Google ID Token cryptographically
    try:
        id_info = id_token.verify_oauth2_token(
            req.credential,
            google_requests.Request(),
            audience=audience,
        )
    except ValueError as e:
        # Token is invalid, expired, or audience doesn't match
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google authentication failed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to verify Google credential: {str(e)}",
        )

    # Step 2: Ensure email is verified by Google
    if not id_info.get("email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your Google account email address is not verified by Google.",
        )

    # Step 3: Extract verified profile information from the Google payload
    email = id_info.get("email", "").strip().lower()
    name = id_info.get("name", "").strip() or email.split("@")[0]
    google_id = id_info.get("sub", "")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account did not provide a valid email address.",
        )

    # Step 4: Check if this user already exists in our database
    user = db.query(models.User).filter(models.User.email == email).first()

    if user:
        # User already exists: link Google ID and update auth_provider if not set
        if not user.google_id and google_id:
            user.google_id = google_id
        if getattr(user, "auth_provider", "local") == "local":
            user.auth_provider = "google"
        db.commit()
        db.refresh(user)
    else:
        # User does not exist: create a new account automatically
        # Map requested role: "ngo" / "verifier" -> UserRole.verifier, otherwise UserRole.user
        role_param = (req.role or "").strip().lower()
        assigned_role = models.UserRole.verifier if role_param in ("ngo", "verifier") else models.UserRole.user

        user = models.User(
            name=name,
            email=email,
            hashed_password=None,  # No password required for Google OAuth accounts
            google_id=google_id,
            auth_provider="google",
            role=assigned_role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Step 5: Issue our own platform JWT access token
    access_token = auth.create_access_token(data={"sub": str(user.id)})
    return schemas.Token(access_token=access_token, token_type="bearer", user=user)


@router.get("/me", response_model=schemas.UserOut)
def read_current_user(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


@router.post("/forgot-password", response_model=schemas.PasswordResetResponse)
def forgot_password(req: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Initiates password recovery.
    Verifies user registration and generates a time-limited 30-minute password reset token.
    """
    clean_email = req.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == clean_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account registered with this email address",
        )

    token = auth.create_password_reset_token(clean_email)
    return schemas.PasswordResetResponse(
        message="Password reset token generated successfully. Please use this token to set a new password.",
        reset_token=token,
        email=clean_email,
    )


@router.post("/reset-password", response_model=schemas.PasswordResetResponse)
def reset_password(req: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Completes password recovery.
    Validates reset token authenticity, checks password length (min 6 characters),
    and updates the user's hashed password securely.
    """
    new_pw = req.new_password.strip()
    if len(new_pw) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters long",
        )

    email = auth.verify_password_reset_token(req.token.strip())
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid, expired, or malformed password reset token",
        )

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The account associated with this token no longer exists",
        )

    user.hashed_password = auth.hash_password(new_pw)
    db.commit()

    return schemas.PasswordResetResponse(
        message="Your password has been successfully updated. You can now sign in with your new password.",
        email=email,
    )

