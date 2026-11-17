"""用户相关的 Pydantic 数据模型（响应体定义）。

注意：当前各路由直接在模块内内联定义请求/响应模型，本包保留为后续统一
抽出 schema 层的落点。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    nickname: str = "同学"
    avatar_url: str = ""
    school: str = ""
    college: str = ""
    political_status: str = "共青团员"


class UserCreate(BaseModel):
    phone: str
    code: str


class UserLogin(BaseModel):
    phone: str
    code: str


class UserResponse(UserBase):
    id: str
    role: str
    total_points: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


__all__ = [
    "UserBase",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
]
