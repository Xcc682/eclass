"""党史情景模型：党史书卷场景与学习进度记录。"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())

class HistoryScenario(Base):
    __tablename__ = "history_scenarios"
    id = Column(String, primary_key=True, default=gen_uuid)
    title = Column(String(200), nullable=False)
    era = Column(String(100))
    year_from = Column(Integer)
    description = Column(Text)
    background = Column(Text, default="", nullable=False)
    knowledge_points_json = Column(Text, default="[]", nullable=False)
    decision_points_json = Column(Text, default="{}", nullable=False)
    duration_estimate = Column(Integer, default=15)
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class HistoryLearningRecord(Base):
    __tablename__ = "history_learning_records"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    scenario_id = Column(String, ForeignKey("history_scenarios.id"), nullable=False)
    progress = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    choice_index = Column(Integer, nullable=True)
    qa_json = Column(Text, default="[]", nullable=False)
