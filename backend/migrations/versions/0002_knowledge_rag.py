"""Add complete knowledge base and RAG metadata.

Revision ID: 0002_knowledge_rag
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0002_knowledge_rag"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A corrected 0001 creates the complete current baseline for new installs.
    # Existing installations that originally ran the smaller 0001 still need
    # this migration, so only skip when the RAG tables are already present.
    if inspect(op.get_bind()).has_table("knowledge_chunks"):
        return
    with op.batch_alter_table("knowledge_documents") as batch:
        batch.add_column(sa.Column("source_url", sa.String(1000), server_default="", nullable=False))
        batch.add_column(sa.Column("status", sa.String(30), server_default="published", nullable=False))
        batch.add_column(sa.Column("version", sa.Integer(), server_default="1", nullable=False))
        batch.add_column(sa.Column("file_name", sa.String(500), nullable=True))
        batch.add_column(sa.Column("file_path", sa.String(1000), nullable=True))
        batch.add_column(sa.Column("mime_type", sa.String(200), nullable=True))
        batch.add_column(sa.Column("checksum", sa.String(64), nullable=True))
        batch.add_column(sa.Column("uploader_id", sa.String(), nullable=True))
        batch.add_column(sa.Column("reviewer_id", sa.String(), nullable=True))
        batch.add_column(sa.Column("chunk_count", sa.Integer(), server_default="0", nullable=False))
        batch.add_column(sa.Column("processing_error", sa.Text(), nullable=True))
        batch.add_column(sa.Column("published_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
        batch.create_foreign_key("fk_knowledge_uploader", "users", ["uploader_id"], ["id"])
        batch.create_foreign_key("fk_knowledge_reviewer", "users", ["reviewer_id"], ["id"])
        batch.create_unique_constraint("uq_knowledge_documents_checksum", ["checksum"])
        batch.create_index("ix_knowledge_documents_status", ["status"])
        batch.create_index("ix_knowledge_documents_category", ["category"])

    op.execute("UPDATE knowledge_documents SET published_at = created_at, updated_at = created_at WHERE published_at IS NULL")

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("document_id", sa.String(), sa.ForeignKey("knowledge_documents.id"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("char_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_knowledge_chunk_position"),
    )
    op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"])

    op.create_table(
        "knowledge_ingestion_jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("document_id", sa.String(), sa.ForeignKey("knowledge_documents.id"), nullable=False),
        sa.Column("status", sa.String(30), server_default="queued", nullable=False),
        sa.Column("progress", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_knowledge_jobs_document_id", "knowledge_ingestion_jobs", ["document_id"])
    op.create_index("ix_knowledge_jobs_status", "knowledge_ingestion_jobs", ["status"])

    op.create_table(
        "knowledge_favorites",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("document_id", sa.String(), sa.ForeignKey("knowledge_documents.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "document_id", name="uq_knowledge_favorite"),
    )
    op.create_index("ix_knowledge_favorites_user_id", "knowledge_favorites", ["user_id"])
    op.create_index("ix_knowledge_favorites_document_id", "knowledge_favorites", ["document_id"])

    op.create_table(
        "knowledge_views",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("document_id", sa.String(), sa.ForeignKey("knowledge_documents.id"), nullable=False),
        sa.Column("viewed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_knowledge_views_user_id", "knowledge_views", ["user_id"])
    op.create_index("ix_knowledge_views_document_id", "knowledge_views", ["document_id"])
    op.create_index("ix_knowledge_views_viewed_at", "knowledge_views", ["viewed_at"])

    op.create_table(
        "knowledge_sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(300), server_default="知识问答", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_knowledge_sessions_user_id", "knowledge_sessions", ["user_id"])

    op.create_table(
        "knowledge_messages",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("session_id", sa.String(), sa.ForeignKey("knowledge_sessions.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_knowledge_messages_session_id", "knowledge_messages", ["session_id"])

    op.create_table(
        "knowledge_templates",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("order_index", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    for table in ["knowledge_templates", "knowledge_messages", "knowledge_sessions", "knowledge_views", "knowledge_favorites", "knowledge_ingestion_jobs", "knowledge_chunks"]:
        op.drop_table(table)
    with op.batch_alter_table("knowledge_documents") as batch:
        batch.drop_index("ix_knowledge_documents_category")
        batch.drop_index("ix_knowledge_documents_status")
        batch.drop_constraint("uq_knowledge_documents_checksum", type_="unique")
        batch.drop_constraint("fk_knowledge_reviewer", type_="foreignkey")
        batch.drop_constraint("fk_knowledge_uploader", type_="foreignkey")
        for column in ["updated_at", "published_at", "processing_error", "chunk_count", "reviewer_id", "uploader_id", "checksum", "mime_type", "file_path", "file_name", "version", "status", "source_url"]:
            batch.drop_column(column)
