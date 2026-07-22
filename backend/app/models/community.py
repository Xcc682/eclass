
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, ForeignKey, UniqueConstraint
from app.database import Base

def gen_uuid():
    return str(uuid.uuid4())


class CommunityPost(Base):
    __tablename__ = "community_posts"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50))
    is_question = Column(Boolean, default=False)
    likes_count = Column(Integer, default=0)
    replies_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    status = Column(String(20), default="active")
    resolved = Column(Boolean, default=False, nullable=False)
    accepted_reply_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CommunityReply(Base):
    __tablename__ = "community_replies"
    id = Column(String, primary_key=True, default=gen_uuid)
    post_id = Column(String, ForeignKey("community_posts.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_teacher = Column(Boolean, default=False)
    likes_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class CommunityLike(Base):
    __tablename__ = "community_likes"
    __table_args__ = (UniqueConstraint("user_id", "post_id", name="uq_community_like"),)
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    post_id = Column(String, ForeignKey("community_posts.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
