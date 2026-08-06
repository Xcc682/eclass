"""Add reliable knowledge question-answer message state."""

from alembic import op
import sqlalchemy as sa


revision = "0011_knowledge_qa_reliability"
down_revision = "0010_point_ledger"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("knowledge_messages") as batch:
        batch.add_column(sa.Column("answer_json", sa.Text(), server_default="{}", nullable=False))
        batch.add_column(sa.Column("submission_id", sa.String(64), nullable=True))
        batch.add_column(sa.Column("status", sa.String(20), server_default="sent", nullable=False))
        batch.add_column(sa.Column("error", sa.Text(), nullable=True))
        batch.add_column(sa.Column("feedback", sa.String(20), nullable=True))
        batch.add_column(sa.Column("feedback_reason", sa.Text(), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
        batch.create_index("ix_knowledge_messages_submission_id", ["submission_id"])
        batch.create_index("ix_knowledge_messages_status", ["status"])
        batch.create_unique_constraint(
            "uq_knowledge_message_submission_role",
            ["session_id", "role", "submission_id"],
        )
    op.execute("UPDATE knowledge_messages SET updated_at = created_at WHERE updated_at IS NULL")


def downgrade():
    with op.batch_alter_table("knowledge_messages") as batch:
        batch.drop_constraint("uq_knowledge_message_submission_role", type_="unique")
        batch.drop_index("ix_knowledge_messages_status")
        batch.drop_index("ix_knowledge_messages_submission_id")
        batch.drop_column("updated_at")
        batch.drop_column("feedback_reason")
        batch.drop_column("feedback")
        batch.drop_column("error")
        batch.drop_column("status")
        batch.drop_column("submission_id")
        batch.drop_column("answer_json")
