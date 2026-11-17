"""JWT authentication and role dependencies."""
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User

bearer = HTTPBearer(auto_error=False)


def create_access_token(user: User) -> str:
    expires = datetime.now(UTC) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user.id, "role": user.role, "exp": expires},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    """解析 Bearer Token 并返回当前用户；未登录、令牌失效或账号停用均抛 401。"""
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id = payload.get("sub")
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效") from exc
    user = db.get(User, user_id) if user_id else None
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已停用")
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User | None:
    """Return the signed-in user while allowing genuinely anonymous catalog reads.

    A malformed or expired token is still rejected instead of silently being
    treated as anonymous, which avoids hiding authentication problems.
    """
    if not credentials:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id = payload.get("sub")
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效") from exc
    user = db.get(User, user_id) if user_id else None
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已停用")
    return user


def require_role(*roles: str) -> Callable:
    """生成角色守卫依赖：当前用户角色不在允许列表内时返回 403。"""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
        return user

    return dependency


async def get_ai_user(user: User = Depends(get_current_user)) -> User:
    """AI 调用入口：先查当日 token 额度，再把用户绑定到上下文供网关计量。

    必须是异步依赖：同步依赖会在线程池中执行，ContextVar 的写入不会回流到
    处理请求的协程上下文，额度就会永远记在 None 上。
    """
    from app.services import ai_quota

    try:
        ai_quota.ensure(user.id, user.role)
    except ai_quota.QuotaExceeded as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    ai_quota.bind(user.id)
    return user
