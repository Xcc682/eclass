import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, String, Integer, DateTime, Text, ForeignKey, Index, UniqueConstraint, text
from app.database import Base

def gen_uuid():
    return str(uuid.uuid4())

class InterviewScenario(Base):
    __tablename__ = "interview_scenarios"
    id = Column(String, primary_key=True, default=gen_uuid)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    difficulty = Column(String(20), default="intermediate")
    estimated_duration = Column(Integer, default=15)
    ai_role_name = Column(String(100))
    ai_role_title = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)

class InterviewPracticeRecord(Base):
    __tablename__ = "interview_practice_records"
    __table_args__ = (UniqueConstraint("active_key", name="uq_interview_active_key"),)
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    scenario_id = Column(String, ForeignKey("interview_scenarios.id"), nullable=False)
    status = Column(String(20), default="in_progress")
    overall_score = Column(Integer)
    total_rounds = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    report_json = Column(Text, nullable=True)
    current_phase = Column(String(40), default="开场寒暄", nullable=False)
    current_step = Column(Integer, default=0, nullable=False)
    live_evaluation_json = Column(Text, default="{}", nullable=False)
    requested_scenario_id = Column(String, ForeignKey("interview_scenarios.id"), nullable=True)
    flow_version = Column(Integer, default=2, nullable=False)
    is_legacy = Column(Boolean, default=False, nullable=False)
    active_key = Column(String(500), nullable=True)
    report_status = Column(String(20), default="idle", nullable=False)
    report_started_at = Column(DateTime, nullable=True)

class InterviewMessage(Base):
    __tablename__ = "interview_messages"
    __table_args__ = (
        UniqueConstraint("record_id", "role", "submission_id", name="uq_interview_submission_role"),
        Index(
            "uq_interview_user_round", "record_id", "round_number", unique=True,
            sqlite_where=text("role = 'user'"), postgresql_where=text("role = 'user'"),
        ),
    )
    id = Column(String, primary_key=True, default=gen_uuid)
    record_id = Column(String, ForeignKey("interview_practice_records.id"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    analysis_json = Column(Text, nullable=True)
    round_number = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    submission_id = Column(String(64), nullable=True)
    delivery_status = Column(String(20), default="sent", nullable=False)
