"""AI 安全网关：提示注入拦截、敏感信息脱敏、输出审核与结构化审计。

所有进入模型的用户文本先过 :func:`check_input`，模型产出的文本在返回前端前过
:func:`mask_output`。拦截事件写入进程内环形缓冲，供 ``/api/v1/ai/security/stats``
做可观测展示，同时输出结构化日志，方便接入外部告警。
"""
from __future__ import annotations

import logging
import re
import unicodedata
from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.config import settings

logger = logging.getLogger(__name__)

MAX_INPUT_CHARS = 4000

# 拦截级别：block 直接拒绝，flag 仅记录并放行（避免误伤正常表述）
_RULES: tuple[tuple[str, str, re.Pattern[str]], ...] = tuple(
    (name, level, re.compile(pattern))
    for name, level, pattern in (
        (
            "指令覆盖",
            "block",
            r"(忽略|无视|忘记|忘掉|不要理会|别管)(掉)?(之前|以上|上面|前面|先前|以前|此前|刚才)?的?"
            r"(所有|全部)?(指令|指示|提示词|规则|要求|设定|限制)",
        ),
        (
            "指令覆盖",
            "block",
            r"ignore\s*(all\s*)?(the\s*)?(previous|above|prior|earlier)\s*"
            r"(instructions?|prompts?|rules?|messages?)",
        ),
        (
            "身份劫持",
            "block",
            r"(你现在|从现在开始你|接下来你)(是|扮演|作为|充当)(一个)?"
            r"(系统|管理员|开发者|超级用户|root|审核员)",
        ),
        (
            "身份劫持",
            "block",
            r"(you are now|act as)\s+(a\s+)?(system|admin|administrator|developer|root)",
        ),
        (
            "提示词窃取",
            "block",
            r"(输出|打印|告诉我|显示|复述|重复|泄露)(一下)?(你的)?(系统)?"
            r"(提示词|prompt|system prompt|设定|初始指令|内部规则)",
        ),
        (
            "提示词窃取",
            "block",
            r"(reveal|print|show|repeat|leak)\s+(me\s+)?(your\s+)?(system\s+)?(prompt|instructions)",
        ),
        ("越狱尝试", "block", r"(开发者模式|越狱模式|jailbreak|dan\s*mode|developer\s*mode)"),
        (
            "评分操控",
            "flag",
            r"(直接|必须|务必|请你)?(给|打)(我)?(满分|100\s*分|最高分)",
        ),
        ("评分操控", "flag", r"(ignore|override).{0,12}(score|grading|evaluation)"),
    )
)

_PII_RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("手机号", re.compile(r"(?<!\d)(1[3-9]\d)(\d{4})(\d{4})(?!\d)"), r"\1****\3"),
    (
        "身份证号",
        re.compile(r"(?<!\d)(\d{6})(\d{8})(\d{3}[\dXx])(?!\d)"),
        r"\1********\3",
    ),
    ("银行卡号", re.compile(r"(?<!\d)(\d{4})(\d{8,11})(\d{4})(?!\d)"), r"\1********\3"),
)

_BRACKETS = re.compile(r"[\s　\-_·.,，。:：;；!！?？\"'“”‘’()（）\[\]【】<>《》]+")


@dataclass(frozen=True)
class SafetyVerdict:
    """一次输入检查的结论。"""

    allowed: bool
    category: str = ""
    reason: str = ""
    flags: tuple[str, ...] = field(default_factory=tuple)


_EVENTS: deque[dict] = deque(maxlen=200)
_COUNTERS: Counter[str] = Counter()


def _variants(text: str) -> tuple[str, str]:
    """返回两种归一化视图：保留单空格的（适配英文），与去掉全部空白的（适配中文拆字）。"""
    folded = unicodedata.normalize("NFKC", text or "").lower()
    return re.sub(r"\s+", " ", folded).strip(), _BRACKETS.sub("", folded)


def _hit(pattern: re.Pattern[str], variants: tuple[str, str]) -> bool:
    return any(pattern.search(item) for item in variants)


def check_input(text: str) -> SafetyVerdict:
    """检查用户输入是否存在提示注入、越权或评分操控意图。"""
    raw = (text or "").strip()
    if len(raw) > MAX_INPUT_CHARS:
        _record("input", "超长输入", "block", {"chars": len(raw)})
        return SafetyVerdict(False, "超长输入", f"输入超过 {MAX_INPUT_CHARS} 字，请精简后重试")

    variants = _variants(raw)
    flags: list[str] = []
    for name, level, pattern in _RULES:
        if not _hit(pattern, variants):
            continue
        if level == "block":
            _record("input", name, "block", {"chars": len(raw)})
            return SafetyVerdict(False, name, "输入包含试图改变模型指令的内容，已拦截")
        flags.append(name)
    if flags:
        _record("input", ",".join(sorted(set(flags))), "flag", {"chars": len(raw)})
    return SafetyVerdict(True, flags=tuple(sorted(set(flags))))


def mask_pii(text: str) -> tuple[str, list[str]]:
    """把手机号、身份证号、银行卡号替换为掩码，返回脱敏文本与命中的类别。"""
    hits: list[str] = []
    masked = text or ""
    for name, pattern, replacement in _PII_RULES:
        masked, count = pattern.subn(replacement, masked)
        if count:
            hits.append(name)
    return masked, hits


def mask_output(text: str) -> str:
    """模型输出返回前端前的最后一道处理：脱敏 + 敏感词替换。"""
    masked, hits = mask_pii(text)
    if hits:
        _record("output", ",".join(hits), "mask", {})
    terms = [item.strip() for item in settings.COMMUNITY_SENSITIVE_TERMS.split(",") if item.strip()]
    for term in terms:
        if term and term in masked:
            masked = masked.replace(term, "*" * len(term))
            _record("output", "敏感词", "mask", {"term_len": len(term)})
    return masked


def _record(stage: str, category: str, action: str, extra: dict) -> None:
    _COUNTERS[f"{stage}:{action}"] += 1
    event = {
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "stage": stage,
        "category": category,
        "action": action,
        **extra,
    }
    _EVENTS.append(event)
    logger.warning("[safety] stage=%s category=%s action=%s %s", stage, category, action, extra)


def stats() -> dict:
    """安全网关的累计拦截统计与最近事件（不含原文，避免二次泄露）。"""
    return {
        "counters": dict(sorted(_COUNTERS.items())),
        "recent": list(_EVENTS)[-20:],
        "max_input_chars": MAX_INPUT_CHARS,
        "rules": [name for name, _level, _pattern in _RULES],
    }
