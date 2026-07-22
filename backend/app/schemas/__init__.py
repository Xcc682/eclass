from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

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

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
