"""入党谈话模块的 Pydantic 数据模型。

注意：谈话路由当前在 `app/routers/interviews.py` 内内联定义模型，
本模块保留为后续统一抽出 schema 层的落点。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class InterviewScenarioResponse(BaseModel):
    id: str
    title: str
    description: str | None = ""
    difficulty: str = "intermediate"
    estimated_duration: int = 15
    cover_image: str | None = ""
    ai_role_name: str | None = ""
    ai_role_title: str | None = ""

    model_config = ConfigDict(from_attributes=True)


class StartPracticeRequest(BaseModel):
    scenario_id: str


class StartPracticeResponse(BaseModel):
    id: str
    first_question: str


class RespondRequest(BaseModel):
    content: str


class RespondResponse(BaseModel):
    question: str
    analysis: dict[str, Any] | None = None
    is_completed: bool = False


class InterviewMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    ai_analysis: dict[str, Any] | None = None
    round_number: int
    created_at: datetime


class InterviewReportResponse(BaseModel):
    overall_score: int
    grade: str
    dimension_scores: dict[str, int]
    dimension_analysis: list[dict[str, Any]]
    strengths: list[str]
    weaknesses: list[str]
    suggestion: str
    total_rounds: int
