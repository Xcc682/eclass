"""Domain models not covered by the original prototype."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class TourSite(Base):
    __tablename__ = "tour_sites"
    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String(200), nullable=False)
    location = Column(String(200), default="")
    description = Column(Text, default="")
    emoji = Column(String(20), default="🏛️")
    facts_json = Column(Text, default="[]")
    order_index = Column(Integer, default=0)


class TourRecord(Base):
    __tablename__ = "tour_records"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    site_id = Column(String, ForeignKey("tour_sites.id"), nullable=False)
    qa_json = Column(Text, default="[]")
    report = Column(Text, default="")
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class GeneratedReport(Base):
    __tablename__ = "generated_reports"
    __table_args__ = (UniqueConstraint("report_type", "source_record_id", name="uq_generated_report_source"),)
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    report_type = Column(String(40), nullable=False)
    title = Column(String(300), nullable=False)
    score = Column(Integer, nullable=True)
    content_json = Column(Text, default="{}")
    source_record_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TeacherTask(Base):
    __tablename__ = "teacher_tasks"
    id = Column(String, primary_key=True, default=gen_uuid)
    creator_id = Column(String, ForeignKey("users.id"), nullable=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, default="")
    deadline = Column(String(30), default="")
    deadline_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="published")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TaskSubmission(Base):
    __tablename__ = "task_submissions"
    __table_args__ = (UniqueConstraint("task_id", "user_id", name="uq_task_submission_user"),)
    id = Column(String, primary_key=True, default=gen_uuid)
    task_id = Column(String, ForeignKey("teacher_tasks.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    status = Column(String(20), default="submitted", nullable=False)
    score = Column(Integer, nullable=True)
    feedback = Column(Text, default="", nullable=False)
    next_step = Column(Text, default="", nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)


class TaskRubricCriterion(Base):
    __tablename__ = "task_rubric_criteria"
    id = Column(String, primary_key=True, default=gen_uuid)
    task_id = Column(String, ForeignKey("teacher_tasks.id"), nullable=False, index=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, default="", nullable=False)
    weight = Column(Integer, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)


class TaskRubricScore(Base):
    __tablename__ = "task_rubric_scores"
    __table_args__ = (UniqueConstraint("submission_id", "criterion_id", name="uq_task_rubric_score"),)
    id = Column(String, primary_key=True, default=gen_uuid)
    submission_id = Column(String, ForeignKey("task_submissions.id"), nullable=False, index=True)
    criterion_id = Column(String, ForeignKey("task_rubric_criteria.id"), nullable=False, index=True)
    score = Column(Integer, nullable=False)
    comment = Column(Text, default="", nullable=False)
