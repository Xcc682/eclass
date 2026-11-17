"""成长社区模型：帖子、回复、点赞、收藏、通知与内容审核。"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class CommunityPost(Base):
    __tablename__ = "community_posts"
    __table_args__ = (UniqueConstraint("user_id", "submission_id", name="uq_community_post_submission"),)
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50), default="学习心得", nullable=False, index=True)
    is_question = Column(Boolean, default=False, nullable=False, index=True)
    likes_count = Column(Integer, default=0, nullable=False)
    replies_count = Column(Integer, default=0, nullable=False)
    favorites_count = Column(Integer, default=0, nullable=False)
    view_count = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="active", nullable=False, index=True)
    moderation_status = Column(String(20), default="published", nullable=False, index=True)
    moderation_reason = Column(Text, default="", nullable=False)
    pinned = Column(Boolean, default=False, nullable=False)
    resolved = Column(Boolean, default=False, nullable=False)
    accepted_reply_id = Column(String, nullable=True)
    submission_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class CommunityReply(Base):
    __tablename__ = "community_replies"
    __table_args__ = (
        UniqueConstraint("post_id", "user_id", "submission_id", name="uq_community_reply_submission"),
    )
    id = Column(String, primary_key=True, default=gen_uuid)
    post_id = Column(String, ForeignKey("community_posts.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    parent_reply_id = Column(String, ForeignKey("community_replies.id"), nullable=True, index=True)
    content = Column(Text, nullable=False)
    is_teacher = Column(Boolean, default=False, nullable=False)
    likes_count = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="active", nullable=False, index=True)
    submission_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class CommunityLike(Base):
    __tablename__ = "community_likes"
    __table_args__ = (UniqueConstraint("user_id", "post_id", name="uq_community_like"),)
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    post_id = Column(String, ForeignKey("community_posts.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class CommunityFavorite(Base):
    __tablename__ = "community_favorites"
    __table_args__ = (UniqueConstraint("user_id", "post_id", name="uq_community_favorite"),)
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    post_id = Column(String, ForeignKey("community_posts.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class CommunityReplyLike(Base):
    __tablename__ = "community_reply_likes"
    __table_args__ = (UniqueConstraint("user_id", "reply_id", name="uq_community_reply_like"),)
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    reply_id = Column(String, ForeignKey("community_replies.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class CommunityTopicFollow(Base):
    __tablename__ = "community_topic_follows"
    __table_args__ = (UniqueConstraint("user_id", "topic", name="uq_community_topic_follow"),)
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    topic = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class CommunityNotification(Base):
    __tablename__ = "community_notifications"
    __table_args__ = (
        UniqueConstraint("user_id", "event_key", name="uq_community_notification_event"),
        Index("ix_community_notification_user_read", "user_id", "is_read", "created_at"),
    )
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    actor_id = Column(String, ForeignKey("users.id"), nullable=True)
    type = Column(String(40), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(String(500), default="", nullable=False)
    resource_type = Column(String(30), nullable=False)
    resource_id = Column(String, nullable=False)
    event_key = Column(String(160), nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class CommunityContentReport(Base):
    __tablename__ = "community_content_reports"
    __table_args__ = (
        UniqueConstraint("reporter_id", "target_type", "target_id", name="uq_community_report_target"),
    )
    id = Column(String, primary_key=True, default=gen_uuid)
    reporter_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    target_type = Column(String(20), nullable=False)
    target_id = Column(String, nullable=False, index=True)
    reason = Column(String(50), nullable=False)
    detail = Column(Text, default="", nullable=False)
    status = Column(String(20), default="pending", nullable=False, index=True)
    reviewer_id = Column(String, ForeignKey("users.id"), nullable=True)
    resolution = Column(Text, default="", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)


class CommunityAttachment(Base):
    __tablename__ = "community_attachments"
    id = Column(String, primary_key=True, default=gen_uuid)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    target_type = Column(String(30), nullable=True, index=True)
    target_id = Column(String, nullable=True, index=True)
    original_name = Column(String(300), nullable=False)
    storage_key = Column(String(600), nullable=False, unique=True)
    storage_backend = Column(String(20), default="local", nullable=False)
    mime_type = Column(String(120), nullable=False)
    size = Column(Integer, nullable=False)
    status = Column(String(20), default="temporary", nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)


class CommunityPostView(Base):
    __tablename__ = "community_post_views"
    __table_args__ = (UniqueConstraint("user_id", "post_id", "view_bucket", name="uq_community_post_view_bucket"),)
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    post_id = Column(String, ForeignKey("community_posts.id"), nullable=False, index=True)
    view_bucket = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
