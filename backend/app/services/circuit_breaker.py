"""LLM 上游熔断器。

连续失败达到阈值后打开熔断，冷却期内直接快速失败，半开状态下放行一次试探，
成功即闭合。目的是在上游故障时保护线程与用户等待时间，而不是替代重试。
"""
from __future__ import annotations

import threading
import time

from app.config import settings


class CircuitOpenError(RuntimeError):
    """熔断打开期间请求被直接拒绝。"""


class CircuitBreaker:
    def __init__(self, threshold: int | None = None, cooldown: float | None = None,
                 clock=time.monotonic) -> None:
        self._threshold = threshold or settings.LLM_CIRCUIT_FAIL_THRESHOLD
        self._cooldown = cooldown if cooldown is not None else settings.LLM_CIRCUIT_COOLDOWN_SECONDS
        self._clock = clock
        self._failures = 0
        self._opened_at: float | None = None
        self._probe_in_flight = False
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            return self._state_locked()

    def _state_locked(self) -> str:
        if self._opened_at is None:
            return "closed"
        if self._clock() - self._opened_at >= self._cooldown:
            return "half_open"
        return "open"

    def allow(self) -> bool:
        """熔断打开时快速失败；半开状态只放行一次试探，避免并发打满上游。"""
        with self._lock:
            state = self._state_locked()
            if state == "closed":
                return True
            if state == "half_open" and not self._probe_in_flight:
                self._probe_in_flight = True
                return True
            return False

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = None
            self._probe_in_flight = False

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            now = self._clock()
            if self._opened_at is None:
                if self._failures >= self._threshold:
                    self._opened_at = now
            else:
                # 半开试探失败：重新开始冷却计时，否则会永久停在半开
                self._opened_at = now
            self._probe_in_flight = False

    def reset(self) -> None:
        self.record_success()

    def describe(self) -> dict:
        with self._lock:
            return {
                "state": self._state_locked(),
                "failures": self._failures,
                "threshold": self._threshold,
                "cooldown_seconds": self._cooldown,
            }


breaker = CircuitBreaker()
