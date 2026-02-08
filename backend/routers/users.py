"""
User management router for OpenRecords.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from middleware.auth import get_current_user
from models.auth import AuthContext, UserPublic
from models.users import (
    DeleteAccountRequest,
    PasswordChangeRequest,
    UserSettingsResponse,
    UserSettingsUpdate,
    UserUpdateRequest,
)
from database import get_db_cursor
from utils.auth import create_jwt_token, hash_password, verify_password
from utils.auth import get_current_timestamp

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
async def get_me(user: AuthContext = Depends(get_current_user)):
    """Get the current authenticated user."""
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, username, full_name, email, created_at, last_login
            FROM users
            WHERE id = ?
            """,
            (user.user_id,),
        )
        row = cursor.fetchone()
        if not row:
            return UserPublic(
                id=user.user_id,
                username=user.username,
                full_name="",
                email="",
                created_at="",
                last_login=None,
            )

        return UserPublic(
            id=row[0],
            username=row[1],
            full_name=row[2],
            email=row[3],
            created_at=row[4],
            last_login=row[5],
        )


@router.patch("/me", response_model=UserPublic)
async def update_me(
    request: Request,
    payload: UserUpdateRequest,
    user: AuthContext = Depends(get_current_user),
):
    """Update the current user's profile."""
    updates = {
        "username": payload.username,
        "full_name": payload.full_name,
        "email": payload.email,
    }

    if all(value is None for value in updates.values()):
        raise HTTPException(status_code=400, detail="No updates provided")

    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, username, full_name, email, created_at, last_login
            FROM users
            WHERE id = ?
            """,
            (user.user_id,),
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        new_username = updates["username"] if updates["username"] is not None else row[1]
        new_full_name = updates["full_name"] if updates["full_name"] is not None else row[2]
        new_email = updates["email"] if updates["email"] is not None else row[3]

        if new_username != row[1]:
            cursor.execute(
                "SELECT id FROM users WHERE username = ? AND id != ?",
                (new_username, user.user_id),
            )
            if cursor.fetchone():
                raise HTTPException(status_code=409, detail="Username already exists")

        if new_email != row[3]:
            cursor.execute(
                "SELECT id FROM users WHERE email = ? AND id != ?",
                (new_email, user.user_id),
            )
            if cursor.fetchone():
                raise HTTPException(status_code=409, detail="Email already registered")

        cursor.execute(
            """
            UPDATE users
            SET username = ?, full_name = ?, email = ?
            WHERE id = ?
            """,
            (new_username, new_full_name, new_email, user.user_id),
        )

    updated_user = UserPublic(
        id=row[0],
        username=new_username,
        full_name=new_full_name,
        email=new_email,
        created_at=row[4],
        last_login=row[5],
    )

    response = JSONResponse(content=updated_user.model_dump(), status_code=200)

    if new_username != row[1]:
        token = create_jwt_token(user.user_id, new_username)
        secure = not request.app.state.settings.is_dev
        response.set_cookie(
            key="openrecords_session",
            value=token,
            httponly=True,
            secure=secure,
            samesite="lax",
            max_age=60 * 60 * 24 * 30,
        )

    return response


@router.patch("/me/password")
async def change_password(
    payload: PasswordChangeRequest,
    user: AuthContext = Depends(get_current_user),
):
    """Change the current user's password."""
    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT password_hash FROM users WHERE id = ?",
            (user.user_id,),
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        if not verify_password(payload.current_password, row[0]):
            raise HTTPException(status_code=401, detail="Current password is incorrect")

        new_hash = hash_password(payload.new_password)
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_hash, user.user_id),
        )

    return {"status": "ok"}


@router.delete("/me")
async def delete_account(
    payload: DeleteAccountRequest,
    user: AuthContext = Depends(get_current_user),
):
    """Delete the current user's account."""
    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT password_hash FROM users WHERE id = ?",
            (user.user_id,),
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        if not verify_password(payload.password, row[0]):
            raise HTTPException(status_code=401, detail="Password is incorrect")

        cursor.execute("DELETE FROM users WHERE id = ?", (user.user_id,))

    response = JSONResponse(content={"status": "ok"}, status_code=200)
    response.delete_cookie(
        key="openrecords_session",
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/settings", response_model=UserSettingsResponse)
async def get_settings(user: AuthContext = Depends(get_current_user)):
    """Get the current user's settings."""
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT default_chat_model, default_embed_model, theme, temperature, updated_at
            FROM user_settings
            WHERE user_id = ?
            """,
            (user.user_id,),
        )
        row = cursor.fetchone()

    if not row:
        return UserSettingsResponse()

    return UserSettingsResponse(
        default_chat_model=row[0],
        default_embed_model=row[1],
        theme=row[2],
        temperature=row[3],
        updated_at=row[4],
    )


@router.put("/settings", response_model=UserSettingsResponse)
async def update_settings(
    payload: UserSettingsUpdate,
    user: AuthContext = Depends(get_current_user),
):
    """Update the current user's settings."""
    updated_at = get_current_timestamp()
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT user_id FROM user_settings WHERE user_id = ?
            """,
            (user.user_id,),
        )
        exists = cursor.fetchone() is not None

        if exists:
            cursor.execute(
                """
                UPDATE user_settings
                SET default_chat_model = ?,
                    default_embed_model = ?,
                    theme = ?,
                    temperature = ?,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (
                    payload.default_chat_model,
                    payload.default_embed_model,
                    payload.theme,
                    payload.temperature,
                    updated_at,
                    user.user_id,
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO user_settings (
                    user_id, default_chat_model, default_embed_model, theme, temperature, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user.user_id,
                    payload.default_chat_model,
                    payload.default_embed_model,
                    payload.theme,
                    payload.temperature,
                    updated_at,
                ),
            )

    return UserSettingsResponse(
        default_chat_model=payload.default_chat_model,
        default_embed_model=payload.default_embed_model,
        theme=payload.theme,
        temperature=payload.temperature,
        updated_at=updated_at,
    )
