"""用户模型：手机号登录、角色权限与积分余额。"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=gen_uuid)
    yiban_id = Column(String(128), unique=True, nullable=True)
    phone = Column(String(20), unique=True, nullable=True)
    nickname = Column(String(100), default="同学")
    avatar_url = Column(String(512), default="")
    school = Column(String(100), default="")
    college = Column(String(100), default="")
    political_status = Column(String(50), default="共青团员")
    role = Column(String(20), default="student")
    total_points = Column(Integer, default=0)
    hashed_password = Column(String(256), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
