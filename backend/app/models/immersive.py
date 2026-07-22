"""Persistence models for the immersive history and study-tour readers."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class ImmersiveBook(Base):
    __tablename__ = "immersive_books"
    __table_args__ = (UniqueConstraint("module", "source_id", name="uq_immersive_book_source"),)

    id = Column(String, primary_key=True)
    module = Column(String(20), nullable=False, index=True)
    source_id = Column(String, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    subtitle = Column(String(300), default="", nullable=False)
    era = Column(String(100), default="", nullable=False)
    location = Column(String(200), default="", nullable=False)
    cover_url = Column(String(1000), default="", nullable=False)
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(20), default="published", nullable=False, index=True)
    duration_estimate = Column(Integer, default=15, nullable=False)
    order_index = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ImmersiveSpread(Base):
    __tablename__ = "immersive_spreads"
    __table_args__ = (UniqueConstraint("book_id", "order_index", name="uq_immersive_spread_order"),)

    id = Column(String, primary_key=True)
    book_id = Column(String, ForeignKey("immersive_books.id", ondelete="CASCADE"), nullable=False, index=True)
    order_index = Column(Integer, nullable=False)
    spread_type = Column(String(30), nullable=False)
    layout = Column(String(30), default="cinematic", nullable=False)
    image_url = Column(String(1000), default="", nullable=False)
    thumbnail_url = Column(String(1000), default="", nullable=False)
    audio_url = Column(String(1000), default="", nullable=False)
    narration = Column(Text, default="", nullable=False)
    scene_json = Column(Text, default="{}", nullable=False)
    source_refs_json = Column(Text, default="[]", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ImmersiveProgress(Base):
    __tablename__ = "immersive_progress"
    __table_args__ = (UniqueConstraint("user_id", "book_id", name="uq_immersive_progress_user_book"),)

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    book_id = Column(String, ForeignKey("immersive_books.id", ondelete="CASCADE"), nullable=False, index=True)
    current_spread = Column(Integer, default=0, nullable=False)
    discovered_json = Column(Text, default="[]", nullable=False)
    choice_json = Column(Text, default="{}", nullable=False)
    note = Column(Text, default="", nullable=False)
    qa_json = Column(Text, default="[]", nullable=False)
    sound_enabled = Column(Boolean, default=False, nullable=False)
    captions_enabled = Column(Boolean, default=True, nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
    related_record_id = Column(String, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
