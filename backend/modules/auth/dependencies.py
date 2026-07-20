from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from modules.auth import service as auth_service

security = HTTPBearer(auto_error=False)


class CurrentUser:
    def __init__(self, id: int, email: str, tier: str, is_verified: bool):
        self.id = id
        self.email = email
        self.tier = tier
        self.is_verified = is_verified


async def get_current_user(
    request: Request,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> CurrentUser:
    if not creds or not creds.credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = auth_service.decode_access_token(creds.credentials)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    user = auth_service.get_user_by_id(int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return CurrentUser(
        id=user["id"],
        email=user["email"],
        tier=user["subscription_tier"],
        is_verified=bool(user["is_verified"]),
    )


async def get_optional_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> CurrentUser | None:
    if not creds or not creds.credentials:
        return None
    try:
        payload = auth_service.decode_access_token(creds.credentials)
        user = auth_service.get_user_by_id(int(payload["sub"]))
        if not user:
            return None
        return CurrentUser(
            id=user["id"],
            email=user["email"],
            tier=user["subscription_tier"],
            is_verified=bool(user["is_verified"]),
        )
    except Exception:
        return None
