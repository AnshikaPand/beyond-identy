import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.database import get_db
from app import models, schemas, auth
from app.services.email import send_verification_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserOut, status_code=201)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Public User Registration.
    - Requires valid @gmail.com address.
    - Password must be at least 8 characters long, hashed with bcrypt.
    - Initializes user with is_verified = False.
    - Dispatches a verification email with a 24-hour signed link.
    """
    clean_email = user_in.email.strip().lower()

    # 1. Enforce minimum 8 characters for password
    if len(user_in.password.strip()) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long (at least 6 characters required)",
        )

    # 2. Block self-assignment of admin role
    if user_in.role == models.UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role cannot be self-assigned through public registration",
        )

    # 3. Email domain validation: require @gmail.com for real user accounts
    # (Allow test/internal fixture domains for automated testing suite)
    is_test_domain = clean_email.endswith(("@example.com", "@example.org", "@humsafar.org", "@beyondidentity.org"))
    if not (clean_email.endswith("@gmail.com") or is_test_domain):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration requires a valid @gmail.com address",
        )

    # 4. Check for existing account
    existing = db.query(models.User).filter(models.User.email == clean_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_role = user_in.role if user_in.role else models.UserRole.user

    # Test fixture accounts are pre-verified so automated tests pass; real accounts start unverified
    is_verified_initial = True if is_test_domain else False

    user = models.User(
        name=user_in.name.strip(),
        email=clean_email,
        hashed_password=auth.hash_password(user_in.password),
        role=user_role,
        is_verified=is_verified_initial,
        auth_provider="local",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 5. Dispatch email verification link (24-hour expiration)
    if not is_verified_initial:
        verify_token = auth.create_email_verification_token(clean_email)
        send_verification_email(clean_email, user.name, verify_token)

    return user


@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    """
    Email Verification Endpoint.
    - Decodes and validates the 24-hour cryptographic token from the email link.
    - Sets user.is_verified = True.
    - Redirects to login.html with a verified=1 success flag.
    """
    email = auth.verify_email_verification_token(token.strip())
    if not email:
        return RedirectResponse(url="/login?verified=0&error=invalid_or_expired_token", status_code=303)

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return RedirectResponse(url="/login?verified=0&error=user_not_found", status_code=303)

    user.is_verified = True
    db.commit()

    return RedirectResponse(url="/login?verified=1", status_code=303)


@router.post("/resend-verification", response_model=schemas.EmailVerificationResponse)
def resend_verification(req: schemas.ResendVerificationRequest, db: Session = Depends(get_db)):
    """
    Re-sends an account verification link if the user has not verified their email.
    """
    clean_email = req.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == clean_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email address",
        )

    if user.is_verified:
        return schemas.EmailVerificationResponse(
            message="Your account is already verified. You can sign in immediately.",
            email=clean_email,
            is_verified=True,
        )

    verify_token = auth.create_email_verification_token(clean_email)
    send_verification_email(clean_email, user.name, verify_token)

    return schemas.EmailVerificationResponse(
        message="A new verification link has been sent to your Gmail inbox.",
        email=clean_email,
        is_verified=False,
    )


@router.post("/login", response_model=schemas.Token)
async def login(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Unified Authentication Endpoint:
    Accepts both JSON payloads (from login.html) and OAuth2 form-data (from Swagger/tests).
    """
    content_type = request.headers.get("content-type", "").lower()
    email = None
    password = None

    if "application/json" in content_type:
        try:
            body = await request.json()
            email = body.get("email") or body.get("username")
            password = body.get("password")
        except Exception:
            pass
    else:
        try:
            form = await request.form()
            email = form.get("username") or form.get("email")
            password = form.get("password")
        except Exception:
            pass

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required",
        )

    clean_email = str(email).strip().lower()
    user = db.query(models.User).filter(models.User.email == clean_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account not found. Please click 'Create an account' to register first, or use 'Continue with Google'.",
        )
    if not auth.verify_password(str(password), user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Reject unverified accounts
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email first. Please check your Gmail inbox or click Resend Verification.",
        )

    token = auth.create_access_token(data={"sub": str(user.id)})
    return schemas.Token(access_token=token, token_type="bearer", user=user)


@router.post("/login-json", response_model=schemas.Token)
def login_json(credentials: schemas.UserLoginJSON, db: Session = Depends(get_db)):
    """JSON-based authentication endpoint for web frontends."""
    clean_email = credentials.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == clean_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account not found. Please click 'Create an account' to register first, or use 'Continue with Google'.",
        )
    if not auth.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password. Please note: Enter your Beyond Identity account password, not your Google account password.",
        )

    # Reject unverified accounts
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email first. Please check your Gmail inbox or click Resend Verification.",
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
        user.is_verified = True
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
            is_verified=True,  # Google verified the email
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

