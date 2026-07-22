import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
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
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    scenario_id = Column(String, ForeignKey("interview_scenarios.id"), nullable=False)
    status = Column(String(20), default="in_progress")
    overall_score = Column(Integer)
    total_rounds = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    report_json = Column(Text, nullable=True)

class InterviewMessage(Base):
    __tablename__ = "interview_messages"
    id = Column(String, primary_key=True, default=gen_uuid)
    record_id = Column(String, ForeignKey("interview_practice_records.id"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    analysis_json = Column(Text, nullable=True)
    round_number = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
