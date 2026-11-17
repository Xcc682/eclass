"""AI 运维接口：安全网关拦截统计与自主检索 Agent 的运行状态。

这两个接口给运维与评审演示用：安全网关统计回答「拦下了什么」，Agent 状态回答
「检索链路是否健康」，都不涉及用户内容本身。
"""
from fastapi import APIRouter, Depends

from app.config import settings
from app.models.user import User
from app.security import require_role
from app.services import safety

router = APIRouter(prefix="/api/v1/ai", tags=["AI 运维"])
admin_only = require_role("admin")


@router.get("/security/stats")
def get_security_stats(_: User = Depends(admin_only)) -> dict:
    """提示注入拦截、输出脱敏的累计计数与最近事件。"""
    return {"code": 0, "data": safety.stats()}


@router.get("/agent/status")
def get_agent_status() -> dict:
    """自主检索 Agent 的开关与超时配置。"""
    return {"code": 0, "data": {
        "enabled": settings.KNOWLEDGE_AGENT_ENABLED,
        "max_steps": 3,
        "timeout_seconds": settings.KNOWLEDGE_AGENT_TIMEOUT_SECONDS,
        "tools": ["search_knowledge", "list_documents", "read_chunk"],
    }}
