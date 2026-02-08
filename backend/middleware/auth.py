"""
Authentication middleware for OpenRecords.
Provides dependency injection for protected routes.
"""
from fastapi import HTTPException, Request

from models.auth import AuthContext
from utils.auth import verify_jwt_token

COOKIE_NAME = "openrecords_session"


async def get_current_user(request: Request) -> AuthContext:
    """
    Dependency to get the current authenticated user.

    Usage:
        @router.get("/protected")
        async def protected_route(user: AuthContext = Depends(get_current_user)):
            return {"message": f"Hello {user.username}"}
    """
    # Extract token from cookie
    token = request.cookies.get(COOKIE_NAME)

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    # Verify token
    is_valid, auth_context = verify_jwt_token(token)

    if not is_valid or auth_context is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    # Store auth context in request state for potential use in routes
    request.state.auth_context = auth_context

    return auth_context


async def optional_auth(request: Request) -> AuthContext | None:
    """
    Dependency for optional authentication.

    Returns auth context if user is authenticated, None otherwise.
    Does not raise an error if not authenticated.
    """
    token = request.cookies.get(COOKIE_NAME)

    if not token:
        return None

    is_valid, auth_context = verify_jwt_token(token)

    if not is_valid:
        return None

    request.state.auth_context = auth_context
    return auth_context
