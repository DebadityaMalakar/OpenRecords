"""
Authentication router for OpenRecords.
Handles signup, login, and logout endpoints.
"""
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from database import get_db_cursor
from models.auth import AuthResponse, LoginRequest, SignupRequest
from utils.auth import (
    create_jwt_token,
    generate_user_id,
    get_current_timestamp,
    hash_password,
    verify_password,
)
from utils.encryption import encrypt_master_key, generate_user_master_key

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_NAME = "openrecords_session"


@router.post("/signup", response_model=AuthResponse)
async def signup(request: Request, signup_data: SignupRequest):
    """
    Register a new user.

    Creates a new user account with the provided details.
    Returns the new user_id on success.
    """
    try:
        with get_db_cursor() as cursor:
            # Check if username already exists
            cursor.execute(
                "SELECT id FROM users WHERE username = ?", (signup_data.username,)
            )
            if cursor.fetchone():
                raise HTTPException(
                    status_code=409,
                    detail="Username already exists",
                )

            # Check if email already exists
            cursor.execute(
                "SELECT id FROM users WHERE email = ?", (signup_data.email,)
            )
            if cursor.fetchone():
                raise HTTPException(
                    status_code=409,
                    detail="Email already registered",
                )

            # Generate user ID and master key
            user_id = generate_user_id()
            master_key = generate_user_master_key()

            # Hash password and encrypt master key
            password_hash = hash_password(signup_data.password)
            encrypted_master_key = encrypt_master_key(master_key)

            # Create user record
            created_at = get_current_timestamp()
            cursor.execute(
                """
                INSERT INTO users (
                    id, username, full_name, email, password_hash,
                    encrypted_master_key, created_at, last_login
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    signup_data.username,
                    signup_data.full_name,
                    signup_data.email,
                    password_hash,
                    encrypted_master_key,
                    created_at,
                    None,
                ),
            )

            # Create session token and set cookie
            token = create_jwt_token(user_id, signup_data.username)

            from models.auth import UserPublic
            user_public = UserPublic(
                id=user_id,
                username=signup_data.username,
                full_name=signup_data.full_name,
                email=signup_data.email,
                created_at=created_at,
                last_login=None,
            )

            response = JSONResponse(
                content=AuthResponse(status="ok", user_id=user_id, user=user_public).model_dump(),
                status_code=200,
            )

            # Set HTTP-only cookie
            secure = not request.app.state.settings.is_dev
            response.set_cookie(
                key=COOKIE_NAME,
                value=token,
                httponly=True,
                secure=secure,
                samesite="lax",
                max_age=60 * 60 * 24 * 30,  # 30 days
            )

            return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.post("/login")
async def login(request: Request, login_data: LoginRequest):
    """
    Authenticate an existing user.

    Validates credentials and creates a new session.
    """
    try:
        with get_db_cursor() as cursor:
            # Find user by email or username
            cursor.execute(
                """
                SELECT id, username, password_hash, full_name, email, created_at
                FROM users
                WHERE username = ? OR email = ?
                """,
                (login_data.email_or_username, login_data.email_or_username),
            )

            row = cursor.fetchone()

            if not row:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid credentials",
                )

            user_id, username, password_hash, full_name, email, created_at = row

            # Verify password
            if not verify_password(login_data.password, password_hash):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid credentials",
                )

            # Update last_login
            current_time = get_current_timestamp()
            cursor.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (current_time, user_id),
            )

            # Create new JWT token
            token = create_jwt_token(user_id, username)

            from models.auth import UserPublic
            user_public = UserPublic(
                id=user_id,
                username=username,
                full_name=full_name,
                email=email,
                created_at=created_at,
                last_login=current_time,
            )

            response = JSONResponse(
                content=AuthResponse(status="ok", user_id=user_id, user=user_public).model_dump(),
                status_code=200,
            )

            # Set HTTP-only cookie
            secure = not request.app.state.settings.is_dev
            response.set_cookie(
                key=COOKIE_NAME,
                value=token,
                httponly=True,
                secure=secure,
                samesite="lax",
                max_age=60 * 60 * 24 * 30,  # 30 days
            )

            return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.post("/logout")
async def logout():
    """
    Log out the current user.

    Clears the session cookie.
    """
    response = JSONResponse(
        content=AuthResponse(status="ok").model_dump(),
        status_code=200,
    )

    # Clear the cookie
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        samesite="lax",
    )

    return response
