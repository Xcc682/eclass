
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, ForeignKey
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

class DebateMessage(Base):
    __tablename__ = "debate_messages"
    id = Column(String, primary_key=True, default=gen_uuid)
    record_id = Column(String, ForeignKey("debate_practice_records.id"), nullable=False)
    stage = Column(String(50))
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    round_number = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
