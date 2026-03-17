"""JWT authentication middleware for Supabase-issued tokens.

Provides ``get_current_user`` — an async FastAPI dependency that extracts a
Bearer token from the Authorization header, verifies it against the
``SUPABASE_JWT_SECRET`` env var using HS256, and returns the ``sub`` claim
(user_id UUID string).

Supabase uses HS256 by default with ``audience="authenticated"``.
"""

import logging
import os

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt

logger = logging.getLogger(__name__)

security = HTTPBearer()


def _get_jwt_secret() -> str:
    """Read the Supabase JWT secret from the environment.

    Raises ``ValueError`` if not set — surfaces immediately on first
    authenticated request.
    """
    secret = os.environ.get("SUPABASE_JWT_SECRET")
    if not secret:
        raise ValueError("SUPABASE_JWT_SECRET environment variable is not set")
    return secret


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """FastAPI dependency that verifies a Supabase JWT and returns the user_id.

    Returns:
        The ``sub`` claim (user_id UUID string) from the verified JWT.

    Raises:
        HTTPException 401: Token expired, invalid signature, malformed, or
            missing ``sub`` claim.
        HTTPException 403: No Authorization header (raised by ``HTTPBearer``).
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            _get_jwt_secret(),
            algorithms=["HS256"],
            audience="authenticated",
        )
    except ExpiredSignatureError:
        logger.warning("auth_failed", extra={"reason": "token_expired"})
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError as e:
        logger.warning("auth_failed", extra={"reason": str(e)})
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing sub claim")
    return user_id
