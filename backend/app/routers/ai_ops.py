"""AI 运维接口：安全网关统计、自主检索 Agent、LLM 网关与缓存的可观测状态。

这些接口给运维与评审演示用：安全网关统计回答「拦下了什么」，Agent 状态回答
「检索链路是否健康」，可观测接口回答「模型调用花了多少、成功多少、熔断没有」，
都不涉及用户内容本身。
"""
from fastapi import APIRouter, Depends

from app.config import settings
from app.models.user import User
from app.security import get_current_user, require_role
from app.services import ai_quota, circuit_breaker, llm_metrics, safety, semantic_cache

router = APIRouter(prefix="/api/v1/ai", tags=["AI 运维"])
admin_only = require_role("admin")


@router.get("/security/stats")
def get_security_stats(_: User = Depends(admin_only)) -> dict:
    """提示注入拦截、输出脱敏的累计计数与最近事件。"""
    return {"code": 0, "data": safety.stats()}


@router.get("/agent/status")
def get_agent_status() -> dict:
    """自主检索 Agent 的开关、超时配置与可用工具。"""
    return {"code": 0, "data": {
        "enabled": settings.KNOWLEDGE_AGENT_ENABLED,
        "max_steps": 3,
        "timeout_seconds": settings.KNOWLEDGE_AGENT_TIMEOUT_SECONDS,
        "tools": [
            "search_knowledge", "list_documents", "read_chunk",
            "get_learning_profile", "list_my_practices", "get_practice_detail",
        ],
    }}


@router.get("/observability")
def get_observability(user: User = Depends(get_current_user)) -> dict:
    """LLM 调用的时延、token 与成功率，熔断器状态、本人额度与语义缓存命中率。"""
    return {"code": 0, "data": {
        "llm": llm_metrics.snapshot(),
        "circuit_breaker": circuit_breaker.breaker.describe(),
        "quota": ai_quota.describe(user.id),
        "semantic_cache": semantic_cache.stats(),
        "models": {"chat": settings.LLM_MODEL, "fast": settings.LLM_MODEL_FAST},
    }}
