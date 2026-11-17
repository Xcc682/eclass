"""按用户统计的 AI 每日 token 额度。

额度以自然日为单位，仅在进程内累计（单机演示部署足够）；管理员不受限。
令牌数在 LLM 网关处按上游返回的 usage 计，缺少 usage 时按字符数估算。
"""
from __future__ import annotations

import threading
from contextvars import ContextVar
from datetime import date

from app.config import settings

_CURRENT_USER: ContextVar[str | None] = ContextVar("ai_current_user", default=None)


def bind(user_id: str | None) -> None:
    """把当前请求的用户绑定到上下文，供 LLM 网关计量。"""
    _CURRENT_USER.set(user_id)


def current_user() -> str | None:
    return _CURRENT_USER.get()


class QuotaExceeded(RuntimeError):
    """当日额度用完。"""


_LOCK = threading.Lock()
_COUNTERS: dict[tuple[str, str], int] = {}


def _today() -> str:
    return date.today().isoformat()


def consume(user_id: str | None, tokens: int) -> None:
    if not user_id or tokens <= 0:
        return
    with _LOCK:
        key = (user_id, _today())
        _COUNTERS[key] = _COUNTERS.get(key, 0) + int(tokens)


def used(user_id: str | None) -> int:
    if not user_id:
        return 0
    with _LOCK:
        return _COUNTERS.get((user_id, _today()), 0)


def ensure(user_id: str | None, role: str = "student") -> None:
    """调用前检查额度；管理员与未登录调用不受限。"""
    if not user_id or role == "admin":
        return
    budget = int(getattr(settings, "AI_DAILY_TOKEN_BUDGET", 0) or 0)
    if budget <= 0:
        return
    if used(user_id) >= budget:
        raise QuotaExceeded("今日 AI 使用额度已用尽，请明天再试")


def describe(user_id: str | None) -> dict:
    budget = int(getattr(settings, "AI_DAILY_TOKEN_BUDGET", 0) or 0)
    remaining = max(0, budget - used(user_id)) if budget > 0 else None
    return {"budget": budget or None, "used_today": used(user_id), "remaining": remaining}


def reset() -> None:
    with _LOCK:
        _COUNTERS.clear()
