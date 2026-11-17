"""认证路由：手机号注册登录、JWT 签发、易班 OAuth 适配与登录限流。"""
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request, status
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.security import create_access_token, get_current_user, get_optional_user

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])
password_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# In-memory login throttle. Slowapi is declared in requirements but not wired
# in; a small dependency-free guard is enough for the demo deployment. Buckets
# are keyed by client IP (all attempts, bounds mass registration / rapid
# brute-force) and by phone (password failures, bounds credential stuffing).
_AUTH_WINDOW_SECONDS = 600  # 10 minutes
_AUTH_MAX_ATTEMPTS_PER_IP = 40
_AUTH_MAX_FAILURES_PER_PHONE = 10
_auth_attempts: dict[str, deque[float]] = defaultdict(deque)
_auth_failures: dict[str, deque[float]] = defaultdict(deque)


def _prune(queue: deque[float]) -> None:
    now = time.monotonic()
    while queue and queue[0] < now - _AUTH_WINDOW_SECONDS:
        queue.popleft()


def _check_login_throttle(request: Request, phone: str) -> None:
    ip = request.client.host if request.client else "unknown"
    _prune(_auth_attempts[f"ip:{ip}"])
    _prune(_auth_failures[f"phone:{phone}"])
    if len(_auth_attempts[f"ip:{ip}"]) >= _AUTH_MAX_ATTEMPTS_PER_IP:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="请求过于频繁，请10分钟后再试")
    if len(_auth_failures[f"phone:{phone}"]) >= _AUTH_MAX_FAILURES_PER_PHONE:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="登录失败次数过多，请10分钟后再试")
    _auth_attempts[f"ip:{ip}"].append(time.monotonic())


def _record_login_failure(request: Request, phone: str) -> None:
    ip = request.client.host if request.client else "unknown"
    _auth_failures[f"ip:{ip}"].append(time.monotonic())
    _auth_failures[f"phone:{phone}"].append(time.monotonic())


def _clear_login_failures(phone: str) -> None:
    _auth_failures[f"phone:{phone}"].clear()


def reset_login_throttle() -> None:
    """清空登录限流计数，供测试与运维使用。"""
    _auth_attempts.clear()
    _auth_failures.clear()


class LoginRequest(BaseModel):
    phone: str = Field(pattern=r"^1\d{10}$")
    password: str = Field(min_length=6, max_length=128)


class RegisterRequest(BaseModel):
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


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    """Create a password account without SMS verification and sign it in."""
    _check_login_throttle(request, data.phone)
    existing = db.scalar(select(User.id).where(User.phone == data.phone))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该手机号已注册，请直接登录")
    user = User(
        phone=data.phone,
        nickname=f"同学{data.phone[-4:]}",
        hashed_password=password_context.hash(data.password),
    )
    db.add(user)
    db.flush()
    token = create_access_token(user)
    return {"code": 0, "data": {"token": token, "user": user_payload(user)}, "message": "注册成功"}


@router.post("/login")
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    _check_login_throttle(request, data.phone)
    user = db.scalar(select(User).where(User.phone == data.phone))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在，请先注册")
    if not user.hashed_password:
        # One-time migration for accounts created by the former SMS prototype.
        user.hashed_password = password_context.hash(data.password)
    elif not password_context.verify(data.password, user.hashed_password):
        _record_login_failure(request, data.phone)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="手机号或密码错误")
    else:
        _clear_login_failures(data.phone)
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
def yiban_status(user: User | None = Depends(get_optional_user)):
    configured = bool(settings.YIBAN_APP_ID and settings.YIBAN_APP_SECRET and settings.YIBAN_REDIRECT_URI)
    return {"code": 0, "data": {
        "configured": configured,
        "bound": bool(user and user.yiban_id),
        "yiban_id": user.yiban_id if user else None,
        "available": False,
        "message": "学校易班 OAuth 换票地址尚未配置" if configured else "易班应用参数尚未配置",
    }}


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return {"code": 0, "data": user_payload(user)}
