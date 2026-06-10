import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import (
    UserCreate, UserLogin, UserResponse, Token, ForgotPasswordRequest, ResetPasswordConfirm
)
from app.auth import (
    get_password_hash, verify_password, create_access_token, create_refresh_token, get_current_user
)
from app.mail import send_verification_email, send_reset_password_email
from app.config import SMTP_USER, SMTP_PASSWORD

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # Validate password confirmation
    if user_in.password != user_in.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match."
        )

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered."
        )

    # Create new user
    verification_token = str(uuid.uuid4())
    hashed_pwd = get_password_hash(user_in.password)
    
    # Auto-activate user for local development if SMTP credentials are not configured
    is_active = False
    if not SMTP_USER or not SMTP_PASSWORD:
        is_active = True
        verification_token = None
    
    db_user = User(
        name=user_in.name,
        email=user_in.email,
        hashed_password=hashed_pwd,
        is_active=is_active,
        verification_token=verification_token
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Send verification email if not auto-activated
    if not is_active:
        send_verification_email(db_user.email, db_user.name, verification_token)

    return db_user

@router.get("/verify-email", response_class=HTMLResponse)
def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.verification_token == token).first()
    if not user:
        return """
        <html>
            <body style="font-family: 'Outfit', sans-serif; background-color: #fff0f3; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0;">
                <div style="text-align: center; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); border: 1px solid #ffe5ec; max-width: 400px;">
                    <div style="font-size: 50px; margin-bottom: 20px;">❌</div>
                    <h2 style="color: #d81b60; margin-top: 0;">Verification Failed</h2>
                    <p style="color: #666; line-height: 1.5;">The verification token is invalid or has already been used.</p>
                    <a href="/" style="margin-top: 20px; display: inline-block; background-color: #d81b60; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: bold;">Go to Home</a>
                </div>
            </body>
        </html>
        """

    # Activate user and clear token
    user.is_active = True
    user.verification_token = None
    db.commit()

    return """
    <html>
        <body style="font-family: 'Outfit', sans-serif; background-color: #fff0f3; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0;">
            <div style="text-align: center; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); border: 1px solid #ffe5ec; max-width: 400px;">
                <div style="font-size: 50px; margin-bottom: 20px;">✅</div>
                <h2 style="color: #d81b60; margin-top: 0;">Verification Successful!</h2>
                <p style="color: #666; line-height: 1.5;">Your BrandCraft account is active. You can now log in using your email and password.</p>
                <a href="/#login" style="margin-top: 20px; display: inline-block; background-color: #d81b60; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: bold; box-shadow: 0 4px 6px rgba(216, 27, 96, 0.2);">Go to Login</a>
            </div>
        </body>
    </html>
    """

@router.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in."
        )

    # Issue tokens
    access_token = create_access_token(user.email)
    refresh_token = create_refresh_token(user.email)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if user:
        reset_token = str(uuid.uuid4())
        user.reset_token = reset_token
        db.commit()
        send_reset_password_email(user.email, user.name, reset_token)
        
    # Always return success to prevent user enumeration attacks
    return {"message": "If this email is registered, a password reset link has been sent."}

@router.post("/reset-password")
def reset_password(req: ResetPasswordConfirm, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == req.token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token."
        )

    user.hashed_password = get_password_hash(req.password)
    user.reset_token = None
    db.commit()

    return {"message": "Password reset successfully. You can now log in."}

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
