import logging

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

logger = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    """FastAPI dependency — raises 401 when auth is enabled and token is wrong."""
    if not settings.nexus_secret_key:
        return
    token = credentials.credentials if credentials else None
    if token != settings.nexus_secret_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
