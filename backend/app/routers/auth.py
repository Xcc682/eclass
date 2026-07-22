from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.security import create_access_token, get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])
password_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


class LoginRequest(BaseModel):
    phone: str = Field(pattern=r"^1\d{10}$")
    password: str = Field(min_length=6, max_length=128)


class YibanLoginRequest(BaseModel):
    auth_code: str = Field(min_length=2)


def user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "nickname": user.nickname,
        "avatar_url": user.avatar_url,
        "school": user.school,
        "college": user.college,
        "political_status": user.political_status,
        "role": user.role,
        "total_points": user.total_points,
        "yiban_id": user.yiban_id,
    }


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.phone == data.phone))
    if not user:
        user = User(
            phone=data.phone,
            nickname=f"同学{data.phone[-4:]}",
            hashed_password=password_context.hash(data.password),
        )
        db.add(user)
        db.flush()
    elif not user.hashed_password:
        # One-time migration for accounts created by the former SMS prototype.
        user.hashed_password = password_context.hash(data.password)
    elif not password_context.verify(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="手机号或密码错误")
    admin_phones = {item.strip() for item in settings.ADMIN_PHONES.split(",") if item.strip()}
    teacher_phones = {item.strip() for item in settings.TEACHER_PHONES.split(",") if item.strip()}
    if data.phone in admin_phones:
        user.role = "admin"
    elif data.phone in teacher_phones:
        user.role = "teacher"
    token = create_access_token(user)
    return {"code": 0, "data": {"token": token, "user": user_payload(user)}, "message": "登录成功"}


@router.post("/yiban-login")
def yiban_login(data: YibanLoginRequest, db: Session = Depends(get_db)):
    if not settings.YIBAN_APP_ID or not settings.YIBAN_APP_SECRET:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="易班应用尚未配置")
    # The platform token exchange URL is deployment-specific. This endpoint
    # deliberately refuses to fabricate an identity when it is unavailable.
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="请配置学校易班 OAuth 换票地址")


@router.get("/yiban/status")
def yiban_status(user: User = Depends(get_current_user)):
    configured = bool(settings.YIBAN_APP_ID and settings.YIBAN_APP_SECRET and settings.YIBAN_REDIRECT_URI)
    return {"code": 0, "data": {
        "configured": configured,
        "bound": bool(user.yiban_id),
        "yiban_id": user.yiban_id,
        "available": False,
        "message": "学校易班 OAuth 换票地址尚未配置" if configured else "易班应用参数尚未配置",
    }}


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return {"code": 0, "data": user_payload(user)}
