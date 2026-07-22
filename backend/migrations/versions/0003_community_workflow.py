"""Complete community questions, likes and teacher task submissions."""
from alembic import op
import sqlalchemy as sa


revision = "0003_community_workflow"
down_revision = "0002_knowledge_rag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("community_posts") as batch:
        batch.add_column(sa.Column("resolved", sa.Boolean(), server_default=sa.false(), nullable=False))
        batch.add_column(sa.Column("accepted_reply_id", sa.String(), nullable=True))
    with op.batch_alter_table("teacher_tasks") as batch:
        batch.add_column(sa.Column("creator_id", sa.String(), nullable=True))
        batch.create_foreign_key("fk_teacher_task_creator", "users", ["creator_id"], ["id"])
    op.create_table(
        "community_likes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("post_id", sa.String(), sa.ForeignKey("community_posts.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "post_id", name="uq_community_like"),
    )
    op.create_index("ix_community_likes_user_id", "community_likes", ["user_id"])
    op.create_index("ix_community_likes_post_id", "community_likes", ["post_id"])
    op.create_table(
        "task_submissions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("task_id", sa.String(), sa.ForeignKey("teacher_tasks.id"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), server_default="submitted", nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("feedback", sa.Text(), server_default="", nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("task_id", "user_id", name="uq_task_submission_user"),
    )
    op.create_index("ix_task_submissions_task_id", "task_submissions", ["task_id"])
    op.create_index("ix_task_submissions_user_id", "task_submissions", ["user_id"])


def downgrade() -> None:
    op.drop_table("task_submissions")
    op.drop_table("community_likes")
    with op.batch_alter_table("teacher_tasks") as batch:
        batch.drop_constraint("fk_teacher_task_creator", type_="foreignkey")
        batch.drop_column("creator_id")
    with op.batch_alter_table("community_posts") as batch:
        batch.drop_column("accepted_reply_id")
        batch.drop_column("resolved")
