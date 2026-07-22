import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    id = Column(String, primary_key=True, default=gen_uuid)
    title = Column(String(500), nullable=False)
    category = Column(String(100), index=True)
    content = Column(Text, nullable=False, default="")
    summary = Column(Text, default="")
    source = Column(String(200), default="")
    source_url = Column(String(1000), default="", nullable=False)
    is_template = Column(Boolean, default=False)
    view_count = Column(Integer, default=0)
    status = Column(String(30), default="published", index=True, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    file_name = Column(String(500), nullable=True)
    file_path = Column(String(1000), nullable=True)
    mime_type = Column(String(200), nullable=True)
    checksum = Column(String(64), nullable=True, unique=True)
    uploader_id = Column(String, ForeignKey("users.id"), nullable=True)
    reviewer_id = Column(String, ForeignKey("users.id"), nullable=True)
    chunk_count = Column(Integer, default=0, nullable=False)
    processing_error = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index", name="uq_knowledge_chunk_position"),)
    id = Column(String, primary_key=True, default=gen_uuid)
    document_id = Column(String, ForeignKey("knowledge_documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    char_count = Column(Integer, default=0, nullable=False)
    content_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class KnowledgeIngestionJob(Base):
    __tablename__ = "knowledge_ingestion_jobs"
    __table_args__ = (
        Index("ix_knowledge_jobs_document_id", "document_id"),
        Index("ix_knowledge_jobs_status", "status"),
    )
    id = Column(String, primary_key=True, default=gen_uuid)
    document_id = Column(String, ForeignKey("knowledge_documents.id"), nullable=False)
    status = Column(String(30), default="queued", nullable=False)
    progress = Column(Integer, default=0, nullable=False)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KnowledgeFavorite(Base):
    __tablename__ = "knowledge_favorites"
    __table_args__ = (UniqueConstraint("user_id", "document_id", name="uq_knowledge_favorite"),)
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("knowledge_documents.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class KnowledgeView(Base):
    __tablename__ = "knowledge_views"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(String, ForeignKey("knowledge_documents.id"), nullable=False, index=True)
    viewed_at = Column(DateTime, default=datetime.utcnow, index=True)


class KnowledgeSession(Base):
    __tablename__ = "knowledge_sessions"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(300), default="知识问答", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KnowledgeMessage(Base):
    __tablename__ = "knowledge_messages"
    id = Column(String, primary_key=True, default=gen_uuid)
    session_id = Column(String, ForeignKey("knowledge_sessions.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    citations_json = Column(Text, default="[]", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class KnowledgeTemplate(Base):
    __tablename__ = "knowledge_templates"
    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String(200), nullable=False)
    description = Column(Text, default="", nullable=False)
    prompt = Column(Text, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    order_index = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
