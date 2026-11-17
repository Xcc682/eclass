"""思政辩论模型：辩题、练习记录与逐轮交锋消息。"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class DebateTopic(Base):
    __tablename__ = "debate_topics"
    id = Column(String, primary_key=True, default=gen_uuid)
    title = Column(String(500), nullable=False)
    category = Column(String(100))
    difficulty = Column(String(20), default="intermediate")
    is_ai_generated = Column(Boolean, default=False)
    owner_id = Column(String, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), default="published", nullable=False)
    usage_count = Column(Integer, default=0)
    context = Column(Text, default="")
    pro_hint = Column(Text, default="")
    con_hint = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

class DebatePracticeRecord(Base):
    __tablename__ = "debate_practice_records"
    __table_args__ = (UniqueConstraint("active_key", name="uq_debate_active_key"),)
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    topic_id = Column(String, ForeignKey("debate_topics.id"), nullable=False)
    status = Column(String(20), default="in_progress")
    overall_score = Column(Integer)
    total_rounds = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    stance = Column(String(20), default="pro")
    feedback_json = Column(Text, nullable=True)
    current_stage = Column(String(30), default="opening", nullable=False)
    mode = Column(String(20), default="full", nullable=False)
    current_step = Column(Integer, default=0, nullable=False)
    flow_version = Column(Integer, default=2, nullable=False)
    is_legacy = Column(Boolean, default=False, nullable=False)
    active_key = Column(String(500), nullable=True)
    report_status = Column(String(20), default="idle", nullable=False)
    report_started_at = Column(DateTime, nullable=True)

class DebateMessage(Base):
    __tablename__ = "debate_messages"
    __table_args__ = (
        UniqueConstraint("record_id", "role", "submission_id", name="uq_debate_submission_role"),
        Index(
            "uq_debate_user_round", "record_id", "round_number", unique=True,
            sqlite_where=text("role = 'user'"), postgresql_where=text("role = 'user'"),
        ),
    )
    id = Column(String, primary_key=True, default=gen_uuid)
    record_id = Column(String, ForeignKey("debate_practice_records.id"), nullable=False)
    stage = Column(String(50))
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    round_number = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    analysis_json = Column(Text, default="{}", nullable=False)
    evidence_json = Column(Text, default="[]", nullable=False)
    submission_id = Column(String(64), nullable=True)
    delivery_status = Column(String(20), default="sent", nullable=False)
