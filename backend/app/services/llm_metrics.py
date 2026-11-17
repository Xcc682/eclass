"""LLM 调用的轻量可观测层：时延、token 与成功率。

每次模型调用在网关处记一条记录，环形缓冲保留最近若干次，另维护累计计数，
管理员可通过 /api/v1/ai/observability 查看。只记录数值与错误类别，不保存提示词。
"""
from __future__ import annotations

import threading
import time
from collections import deque

MAX_RECORDS = 500

_LOCK = threading.Lock()
_RECORDS: deque[dict] = deque(maxlen=MAX_RECORDS)
_TOTALS = {
    "calls": 0,
    "success": 0,
    "failed": 0,
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "latency_ms": 0,
}


def record(model: str, latency_ms: int, *, ok: bool, prompt_tokens: int = 0,
           completion_tokens: int = 0, error: str = "") -> None:
    with _LOCK:
        _TOTALS["calls"] += 1
        _TOTALS["success" if ok else "failed"] += 1
        _TOTALS["prompt_tokens"] += max(0, int(prompt_tokens))
        _TOTALS["completion_tokens"] += max(0, int(completion_tokens))
        _TOTALS["latency_ms"] += max(0, int(latency_ms))
        _RECORDS.append({
            "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "model": model,
            "latency_ms": int(latency_ms),
            "prompt_tokens": int(prompt_tokens),
            "completion_tokens": int(completion_tokens),
            "ok": bool(ok),
            "error": error[:80],
        })


def snapshot(recent: int = 10) -> dict:
    with _LOCK:
        totals = dict(_TOTALS)
        records = list(_RECORDS)[-max(1, recent):]
    calls = totals["calls"]
    return {
        "totals": totals,
        "success_rate": round(totals["success"] / calls, 4) if calls else None,
        "average_latency_ms": round(totals["latency_ms"] / calls) if calls else None,
        "records_kept": len(_RECORDS),
        "recent": records,
    }


def reset() -> None:
    """测试与运维重置用。"""
    with _LOCK:
        _RECORDS.clear()
        for key in _TOTALS:
            _TOTALS[key] = 0
