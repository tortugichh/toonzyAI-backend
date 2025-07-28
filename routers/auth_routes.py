from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from typing import Dict, Any
from datetime import datetime, timedelta, timezone
import logging

from db.avatar_repository import get_db, User, PendingRegistration
from schemas.auth_schemas import (
    UserCreate, UserResponse, LoginRequest, Token, 
    RefreshTokenRequest, UserUpdate, PasswordChangeRequest,
    EmailVerificationRequest, PasswordResetRequest, PasswordResetConfirmRequest
)
from utils.auth import (
    get_password_hash, authenticate_user, create_tokens,
    get_current_active_user, verify_token, get_user_by_id,
    get_user_by_username, get_user_by_email, verify_password
)
from utils.email_service import send_verification_email, generate_verification_token, send_password_reset_email

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/register", response_model=Dict[str, str], status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Register a new user (pending verification)."""
    logger.info(f"Registration attempt for username: {user_data.username}")
    
    # Check if username or email already exists in users or pending_registrations
    existing_user = await get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    existing_email = await get_user_by_email(db, user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    result = await db.execute(select(PendingRegistration).where(PendingRegistration.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already pending verification"
        )
    result = await db.execute(select(PendingRegistration).where(PendingRegistration.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already pending verification"
        )
    try:
        verification_token = generate_verification_token()
        hashed_password = get_password_hash(user_data.password)
        expires = datetime.now(timezone.utc) + timedelta(hours=24)
        pending = PendingRegistration(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            verification_token=verification_token,
            verification_token_expires=expires
        )
        db.add(pending)
        await db.commit()
        # Send verification email
        logger.info(f"Attempting to send verification email to {user_data.email}")
        email_sent = await send_verification_email(
            user_data.email,
            user_data.username,
            verification_token
        )
        logger.info(f"Email send result: {email_sent}")
        if not email_sent:
            await db.delete(pending)
            await db.commit()
            logger.warning(f"Failed to send verification email to {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email. Registration cancelled."
            )
        logger.info(f"Pending registration created for: {user_data.username}")
        return {"message": "Verification email sent. Please check your inbox."}
    except Exception as e:
        await db.rollback()
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration"
        )


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> Token:
    """OAuth2 compatible token login (for Swagger UI). Accepts username or email."""
    logger.info(f"OAuth2 login attempt for login: {form_data.username}")
    
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        logger.warning(f"Failed OAuth2 login attempt for login: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    tokens = create_tokens(user)
    logger.info(f"OAuth2 user logged in successfully: {user.username}")
    return Token(**tokens)


@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> Token:
    """Login user and return JWT tokens. Accepts username or email."""
    logger.info(f"Login attempt for login: {login_data.login}")
    
    user = await authenticate_user(db, login_data.login, login_data.password)
    if not user:
        logger.warning(f"Failed login attempt for login: {login_data.login}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in"
        )
    
    tokens = create_tokens(user)
    logger.info(f"User logged in successfully: {user.username}")
    return Token(**tokens)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
) -> Token:
    """Refresh access token using refresh token."""
    token_data = verify_token(refresh_data.refresh_token, "refresh")
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await get_user_by_id(db, token_data.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    tokens = create_tokens(user)
    return Token(**tokens)


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """Get current user profile."""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Update current user profile."""
    try:
        updated = False
        
        if user_update.username and user_update.username != current_user.username:
            # Check if new username is available
            existing_user = await get_user_by_username(db, user_update.username)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
            current_user.username = user_update.username
            updated = True
        
        if user_update.email and user_update.email != current_user.email:
            # Check if new email is available
            existing_email = await get_user_by_email(db, user_update.email)
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            current_user.email = user_update.email
            current_user.is_verified = False  # Re-verification needed
            updated = True
        
        if user_update.password:
            current_user.hashed_password = get_password_hash(user_update.password)
            updated = True
        
        if updated:
            await db.commit()
            await db.refresh(current_user)
            logger.info(f"User profile updated: {current_user.username}")
        
        return UserResponse.model_validate(current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during profile update"
        )


@router.post("/change-password", response_model=Dict[str, str])
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Change user password."""
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    try:
        # Update password
        current_user.hashed_password = get_password_hash(password_data.new_password)
        await db.commit()
        
        logger.info(f"Password changed for user: {current_user.username}")
        return {"message": "Password changed successfully"}
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during password change"
        )


@router.post("/logout", response_model=Dict[str, str])
async def logout(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, str]:
    """Logout user (client should delete token)."""
    logger.info(f"User logged out: {current_user.username}")
    return {"message": "Successfully logged out"}


@router.get("/verify-token", response_model=Dict[str, Any])
async def verify_user_token(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Verify if token is valid and return user info."""
    return {
        "valid": True,
        "user": UserResponse.model_validate(current_user).model_dump()
    } 


@router.post("/verify-email", response_model=Dict[str, Any])
async def verify_email(
    verification_data: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Verify user email with token and create user."""
    logger.info(f"Email verification attempt with token: {verification_data.token[:10]}...")
    # Find pending registration by token
    result = await db.execute(
        select(PendingRegistration).where(
            PendingRegistration.verification_token == verification_data.token,
            PendingRegistration.verification_token_expires > datetime.now(timezone.utc)
        )
    )
    pending = result.scalar_one_or_none()
    if not pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    # Check if user already exists (should not, but for safety)
    existing_user = await get_user_by_username(db, pending.username)
    existing_email = await get_user_by_email(db, pending.email)
    if existing_user or existing_email:
        await db.delete(pending)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists"
        )
    # Create user
    user = User(
        username=pending.username,
        email=pending.email,
        hashed_password=pending.hashed_password,
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(user)
    await db.delete(pending)
    await db.commit()
    await db.refresh(user)
    logger.info(f"Email verified and user created: {user.username}")
    # Generate tokens for auto-login
    tokens = create_tokens(user)
    return {
        "message": "Email verified and account created successfully",
        "user": UserResponse.model_validate(user).model_dump(),
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": tokens["token_type"],
        "expires_in": tokens["expires_in"],
    }


@router.post("/resend-verification", response_model=Dict[str, Any])
async def resend_verification_email(
    email_data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Resend verification email to user or pending registration."""
    logger.info(f"Resend verification attempt for email: {email_data.email}")

    # 1. Check if user exists and is not verified
    user = await get_user_by_email(db, email_data.email)
    if user:
        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already verified"
            )
        # Generate new verification token for existing user
        verification_token = generate_verification_token()
        user.verification_token = verification_token
        user.verification_token_expires = datetime.now(timezone.utc) + timedelta(hours=24)
        await db.commit()
        email_sent = await send_verification_email(
            user.email,
            user.username,
            verification_token
        )
        if not email_sent:
            logger.warning(f"Failed to send verification email to {user.email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email"
            )
        logger.info(f"Verification email resent to: {user.email}")
        return {"message": "Verification email sent successfully"}

    # 2. Check if pending registration exists
    result = await db.execute(select(PendingRegistration).where(PendingRegistration.email == email_data.email))
    pending = result.scalar_one_or_none()
    if pending:
        # Generate new verification token for pending registration
        verification_token = generate_verification_token()
        pending.verification_token = verification_token
        pending.verification_token_expires = datetime.now(timezone.utc) + timedelta(hours=24)
        await db.commit()
        email_sent = await send_verification_email(
            pending.email,
            pending.username,
            verification_token
        )
        if not email_sent:
            logger.warning(f"Failed to send verification email to {pending.email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email"
            )
        logger.info(f"Verification email resent to pending registration: {pending.email}")
        return {"message": "Verification email sent successfully"}

    # 3. Don't reveal if email exists or not
    return {"message": "If the email exists, a verification link has been sent"}


@router.post("/forgot-password", response_model=Dict[str, str])
async def forgot_password(
    email_data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Send password reset email to user."""
    logger.info(f"Password reset requested for email: {email_data.email}")
    
    # Find user by email
    user = await get_user_by_email(db, email_data.email)
    if not user:
        # Don't reveal if email exists or not for security
        logger.info(f"Password reset requested for non-existent email: {email_data.email}")
        return {"message": "If the email exists, a password reset link has been sent."}
    
    if not user.is_active:
        logger.warning(f"Password reset requested for inactive user: {email_data.email}")
        return {"message": "If the email exists, a password reset link has been sent."}
    
    try:
        # Generate reset token
        reset_token = generate_verification_token()
        reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)  # 1 hour expiry
        
        # Update user with reset token
        user.password_reset_token = reset_token
        user.password_reset_token_expires = reset_token_expires
        await db.commit()
        
        # Send reset email
        email_sent = await send_password_reset_email(
            user.email,
            user.username,
            reset_token
        )
        
        if not email_sent:
            # Clear the token if email failed
            user.password_reset_token = None
            user.password_reset_token_expires = None
            await db.commit()
            logger.error(f"Failed to send password reset email to {email_data.email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send password reset email"
            )
        
        logger.info(f"Password reset email sent to {email_data.email}")
        return {"message": "If the email exists, a password reset link has been sent."}
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Password reset error for {email_data.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during password reset"
        )


@router.post("/reset-password", response_model=Dict[str, str])
async def reset_password(
    reset_data: PasswordResetConfirmRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Reset password using token."""
    logger.info("Password reset confirmation requested")
    
    if not reset_data.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token is required"
        )
    
    # Find user by reset token
    result = await db.execute(
        select(User).where(
            User.password_reset_token == reset_data.token,
            User.password_reset_token_expires > datetime.now(timezone.utc)
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    try:
        # Update password
        user.hashed_password = get_password_hash(reset_data.new_password)
        user.password_reset_token = None
        user.password_reset_token_expires = None
        user.updated_at = datetime.now(timezone.utc)
        await db.commit()
        
        logger.info(f"Password reset successful for user: {user.username}")
        return {"message": "Password reset successful. You can now login with your new password."}
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Password reset confirmation error for user {user.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during password reset"
        ) 