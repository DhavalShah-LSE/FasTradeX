import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from config import DEV_EXPOSE_OTP
from modules.auth import service as auth_service
from modules.auth.dependencies import CurrentUser, get_current_user
from modules.auth.email_service import send_otp_email

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class RefreshBody(BaseModel):
    refresh_token: str


class OtpBody(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)


class ResetPasswordBody(BaseModel):
    email: EmailStr
    otp: str
    new_password: str = Field(min_length=8, max_length=128)


class ResendOtpBody(BaseModel):
    email: EmailStr


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _issue_tokens(user: dict, device_hint: str | None) -> dict:
    access = auth_service.create_access_token(
        user["id"], user["email"], user["subscription_tier"]
    )
    refresh = auth_service.create_refresh_token()
    auth_service.store_refresh_token(user["id"], refresh, device_hint)
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "is_verified": bool(user["is_verified"]),
            "subscription_tier": user["subscription_tier"],
        },
    }


@router.post("/register")
async def register(body: RegisterBody, request: Request):
    if not auth_service.check_rate_limit(_client_ip(request), "register"):
        raise HTTPException(status_code=429, detail="Too many attempts")
    if auth_service.get_user_by_email(body.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = auth_service.create_user(body.email, body.password, body.full_name)
    otp = f"{secrets.randbelow(10**6):06d}"
    auth_service.save_otp(user["id"], otp, "verify_email")
    mail = send_otp_email(user["email"], otp, "verify_email")
    resp = {"message": "Registered. Verify email with OTP.", "user_id": user["id"]}
    if not mail.get("sent") and DEV_EXPOSE_OTP and mail.get("dev_otp"):
        resp["dev_otp"] = mail["dev_otp"]
    return resp


@router.post("/verify-email")
async def verify_email(body: OtpBody):
    user = auth_service.get_user_by_email(body.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not auth_service.verify_otp(user["id"], body.otp, "verify_email"):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    auth_service.set_user_verified(user["id"])
    user = auth_service.get_user_by_id(user["id"])
    return {"message": "Email verified", "user": {"email": user["email"], "is_verified": True}}


@router.post("/resend-otp")
async def resend_otp(body: ResendOtpBody, request: Request):
    if not auth_service.check_rate_limit(_client_ip(request), "resend_otp", max_attempts=5):
        raise HTTPException(status_code=429, detail="Too many OTP requests")
    user = auth_service.get_user_by_email(body.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    otp = f"{secrets.randbelow(10**6):06d}"
    auth_service.save_otp(user["id"], otp, "verify_email")
    mail = send_otp_email(user["email"], otp, "verify_email")
    resp = {"message": "OTP resent"}
    if not mail.get("sent") and DEV_EXPOSE_OTP and mail.get("dev_otp"):
        resp["dev_otp"] = mail["dev_otp"]
    return resp


@router.post("/login")
async def login(body: LoginBody, request: Request):
    if not auth_service.check_rate_limit(_client_ip(request), "login"):
        raise HTTPException(status_code=429, detail="Too many login attempts")
    user = auth_service.get_user_by_email(body.email)
    if not user or not auth_service.verify_password(body.password, user["password_hash"]):
        if user:
            auth_service.record_failed_login(user["id"])
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if auth_service.is_account_locked(user):
        raise HTTPException(status_code=423, detail="Account temporarily locked")
    if not user["is_verified"]:
        raise HTTPException(status_code=403, detail="Email not verified")
    auth_service.reset_failed_login(user["id"])
    device = request.headers.get("user-agent", "")[:120]
    return _issue_tokens(user, device)


@router.post("/refresh")
async def refresh(body: RefreshBody):
    row = auth_service.validate_refresh_token(body.refresh_token)
    if not row:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    auth_service.revoke_refresh_token(body.refresh_token)
    user = auth_service.get_user_by_id(row["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return _issue_tokens(user, row.get("device_hint"))


@router.post("/logout")
async def logout(body: RefreshBody):
    auth_service.revoke_refresh_token(body.refresh_token)
    return {"message": "Logged out"}


@router.post("/logout-all")
async def logout_all(user: Annotated[CurrentUser, Depends(get_current_user)]):
    auth_service.revoke_all_refresh_tokens(user.id)
    return {"message": "All sessions revoked"}


@router.post("/forgot-password")
async def forgot_password(body: ResendOtpBody, request: Request):
    if not auth_service.check_rate_limit(_client_ip(request), "forgot_password", max_attempts=5):
        raise HTTPException(status_code=429, detail="Too many requests")
    user = auth_service.get_user_by_email(body.email)
    if not user:
        return {"message": "If the email exists, an OTP was sent"}
    otp = f"{secrets.randbelow(10**6):06d}"
    auth_service.save_otp(user["id"], otp, "reset_password")
    mail = send_otp_email(user["email"], otp, "reset_password")
    resp = {"message": "If the email exists, an OTP was sent"}
    if not mail.get("sent") and DEV_EXPOSE_OTP and mail.get("dev_otp"):
        resp["dev_otp"] = mail["dev_otp"]
    return resp


@router.post("/reset-password")
async def reset_password(body: ResetPasswordBody):
    user = auth_service.get_user_by_email(body.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not auth_service.verify_otp(user["id"], body.otp, "reset_password"):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    auth_service.update_password(user["id"], body.new_password)
    auth_service.revoke_all_refresh_tokens(user["id"])
    return {"message": "Password updated"}


@router.get("/me")
async def me(user: Annotated[CurrentUser, Depends(get_current_user)]):
    full = auth_service.get_user_by_id(user.id)
    return {
        "id": full["id"],
        "email": full["email"],
        "full_name": full["full_name"],
        "is_verified": bool(full["is_verified"]),
        "subscription_tier": full["subscription_tier"],
    }
