"""Add immersive history and study-tour books.

Revision ID: 0006_immersive_books
Revises: 0005_debate_lifecycle
"""
from alembic import op
import sqlalchemy as sa


revision = "0006_immersive_books"
down_revision = "0005_debate_lifecycle"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "immersive_books",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("module", sa.String(20), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("subtitle", sa.String(300), server_default="", nullable=False),
        sa.Column("era", sa.String(100), server_default="", nullable=False),
        sa.Column("location", sa.String(200), server_default="", nullable=False),
        sa.Column("cover_url", sa.String(1000), server_default="", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(20), server_default="published", nullable=False),
        sa.Column("duration_estimate", sa.Integer(), server_default="15", nullable=False),
        sa.Column("order_index", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("module", "source_id", name="uq_immersive_book_source"),
    )
    op.create_index("ix_immersive_books_module", "immersive_books", ["module"])
    op.create_index("ix_immersive_books_source_id", "immersive_books", ["source_id"])
    op.create_index("ix_immersive_books_status", "immersive_books", ["status"])

    op.create_table(
        "immersive_spreads",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("book_id", sa.String(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("spread_type", sa.String(30), nullable=False),
        sa.Column("layout", sa.String(30), server_default="cinematic", nullable=False),
        sa.Column("image_url", sa.String(1000), server_default="", nullable=False),
        sa.Column("thumbnail_url", sa.String(1000), server_default="", nullable=False),
        sa.Column("audio_url", sa.String(1000), server_default="", nullable=False),
        sa.Column("narration", sa.Text(), server_default="", nullable=False),
        sa.Column("scene_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("source_refs_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["immersive_books.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("book_id", "order_index", name="uq_immersive_spread_order"),
    )
    op.create_index("ix_immersive_spreads_book_id", "immersive_spreads", ["book_id"])

    op.create_table(
        "immersive_progress",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("book_id", sa.String(), nullable=False),
        sa.Column("current_spread", sa.Integer(), server_default="0", nullable=False),
        sa.Column("discovered_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("choice_json", sa.Text(), server_default="{}", nullable=False),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
        sa.Column("qa_json", sa.Text(), server_default="[]", nullable=False),
        sa.Column("sound_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("captions_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("completed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("related_record_id", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["book_id"], ["immersive_books.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "book_id", name="uq_immersive_progress_user_book"),
    )
    op.create_index("ix_immersive_progress_user_id", "immersive_progress", ["user_id"])
    op.create_index("ix_immersive_progress_book_id", "immersive_progress", ["book_id"])


def downgrade():
    op.drop_table("immersive_progress")
    op.drop_table("immersive_spreads")
    op.drop_table("immersive_books")
