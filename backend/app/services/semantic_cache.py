"""语义缓存：近义问题直接复用已生成的带引用答案。

实现对齐 GPTCache 的思路：以问题嵌入的余弦相似度判定命中，同义改写也能复用；
存储与淘汰交给成熟库 cachetools 的 TTLCache（TTL + LRU 上限），嵌入模型不可用
时退回规范化后的问题文本精确匹配。只缓存带知识库引用、非降级的回答，避免把
「资料不足」固化下来。
"""
from __future__ import annotations

import logging
import math
import threading
import time

from cachetools import TTLCache

from app.config import settings

logger = logging.getLogger(__name__)

_clock = time.monotonic
_LOCK = threading.Lock()
_CACHE: TTLCache | None = None
_CACHE_CONFIG: tuple[int, int] | None = None
_HITS = 0
_MISSES = 0

SEP = "\x1f"


def _cache() -> TTLCache:
    """按当前配置惰性构建缓存；配置变化时重建。"""
    global _CACHE, _CACHE_CONFIG
    config = (max(1, int(settings.SEMANTIC_CACHE_MAX_ITEMS)), max(0, int(settings.SEMANTIC_CACHE_TTL_SECONDS)))
    if _CACHE is None or config != _CACHE_CONFIG:
        ttl = config[1] if config[1] > 0 else math.inf
        _CACHE = TTLCache(maxsize=config[0], ttl=ttl, timer=_clock)
        _CACHE_CONFIG = config
    return _CACHE


def _normalize(text: str) -> str:
    return "".join(str(text).split()).lower()


def _embedding(text: str) -> list[float] | None:
    from app.services import knowledge_service

    try:
        model = knowledge_service._embedding_model()
        vectors = model.encode([text], normalize_embeddings=True)
        return [float(value) for value in vectors[0]]
    except Exception as exc:  # 嵌入不可用时退回精确匹配
        logger.debug("[cache] embedding_unavailable error=%s", exc.__class__.__name__)
        return None


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True))


def lookup(query: str, scope: str = "") -> dict | None:
    """按问题语义查缓存；命中返回缓存载荷（含 cached 标记）。"""
    global _HITS, _MISSES
    if not settings.SEMANTIC_CACHE_ENABLED:
        return None
    text = _normalize(query)
    if len(text) < 4:
        return None
    vector = _embedding(text)
    with _LOCK:
        cache = _cache()
        exact = cache.get(scope + SEP + text)
        if exact is not None:
            _HITS += 1
            return {**exact["payload"], "cached": True, "similarity": 1.0}
        best: dict | None = None
        best_score = 0.0
        for entry in cache.values():
            if entry["scope"] != scope or entry["vector"] is None or vector is None:
                continue
            score = _cosine(vector, entry["vector"])
            if score > best_score:
                best, best_score = entry, score
        if best is not None and best_score >= float(settings.SEMANTIC_CACHE_THRESHOLD):
            _HITS += 1
            return {**best["payload"], "cached": True, "similarity": round(best_score, 4)}
        _MISSES += 1
        return None


def store(query: str, payload: dict, scope: str = "") -> None:
    """写入缓存；TTLCache 负责按 TTL 过期与按条目上限淘汰。"""
    if not settings.SEMANTIC_CACHE_ENABLED:
        return
    text = _normalize(query)
    if len(text) < 4:
        return
    entry = {"text": text, "scope": scope, "vector": _embedding(text), "payload": payload}
    with _LOCK:
        _cache()[scope + SEP + text] = entry


def stats() -> dict:
    with _LOCK:
        total = _HITS + _MISSES
        return {
            "enabled": bool(settings.SEMANTIC_CACHE_ENABLED),
            "items": len(_cache()),
            "max_items": int(settings.SEMANTIC_CACHE_MAX_ITEMS),
            "ttl_seconds": int(settings.SEMANTIC_CACHE_TTL_SECONDS),
            "threshold": float(settings.SEMANTIC_CACHE_THRESHOLD),
            "hits": _HITS,
            "misses": _MISSES,
            "hit_rate": round(_HITS / total, 4) if total else None,
        }


def invalidate() -> None:
    """知识库内容变化后清空条目（保留命中统计）。"""
    global _CACHE
    with _LOCK:
        if _CACHE is not None:
            _CACHE.clear()


def reset() -> None:
    global _HITS, _MISSES, _CACHE, _CACHE_CONFIG
    with _LOCK:
        _CACHE = None
        _CACHE_CONFIG = None
        _HITS = 0
        _MISSES = 0
